#!/bin/bash
set -euo pipefail
# Usage: ./docker/loop.sh [plan] [max_iterations]
# Examples:
#   ./docker/loop.sh              # Build loop, unlimited iterations
#   ./docker/loop.sh 20           # Build loop, max 20 iterations
#   ./docker/loop.sh plan         # Plan mode, 3 iterations (default)
#   ./docker/loop.sh plan 5       # Plan mode, max 5 iterations

CURRENT_BRANCH=$(git branch --show-current)
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# ─── ANSI colours ─────────────────────────────────────────────────
RST='\033[0m'
BOLD='\033[1m'
DIM='\033[2m'
BRED='\033[1;31m'
BGREEN='\033[1;32m'
YELLOW='\033[0;33m' ; BYELLOW='\033[1;33m'
BBLUE='\033[1;34m'
BMAGENTA='\033[1;35m'
CYAN='\033[0;36m'   ; BCYAN='\033[1;36m'
WHITE='\033[0;37m'  ; BWHITE='\033[1;37m'

# ─── jq filter: human-readable lines from stream-json ─────────────
JQ_FILTER='
  def green: "\u001b[32m" + . + "\u001b[0m";
  def red:   "\u001b[1;31m" + . + "\u001b[0m";
  def dim:   "\u001b[2m" + . + "\u001b[0m";

  if .type == "assistant" then
    (.message.content[]? |
      if .type == "text" then
        ("\u001b[1m\u001b[37m" + .text + "\u001b[0m")
      elif .type == "tool_use" then
        ("  \u001b[36m" + .name + "\u001b[0m \u001b[2m" + (.input | keys | join(", ")) + "\u001b[0m")
      else empty end
    ) // empty

  elif .type == "tool_use_result" then
    if .tool_use_result.status == "completed" then
      ("  " + ("  \u2713 " | green) + ((.tool_use_result.totalDurationMs // 0 | . / 1000 | tostring) + "s, " + (.tool_use_result.totalToolUseCount // 0 | tostring) + " tool calls" | dim))
    else
      ("  " + ("  \u2717 " + (.tool_use_result.status // "unknown") | red))
    end

  elif .type == "result" then
    "\n\u001b[2m\u2500\u2500\u2500 turn complete \u2500\u2500\u2500 cost=\u001b[0m\u001b[35m$" + (.total_cost_usd // 0 | tostring) + "\u001b[0m\u001b[2m  in=" + (.usage.input_tokens // 0 | tostring) + "  out=" + (.usage.output_tokens // 0 | tostring) + "\u001b[0m\n"

  else empty end
'

# ─── Stats accumulators ───────────────────────────────────────────
TOTAL_COST=0
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0
TOTAL_ITERATIONS=0
START_TIME=$SECONDS

# ─── Helper functions ─────────────────────────────────────────────

print_summary() {
    local elapsed=$((SECONDS - START_TIME))
    local mins=$((elapsed / 60))
    local secs=$((elapsed % 60))
    echo ""
    echo -e "${BBLUE}┌──────────────────────────────────────┐${RST}"
    echo -e "${BBLUE}│${RST}         ${BOLD}${WHITE}  JOB SUMMARY  ${RST}             ${BBLUE}│${RST}"
    echo -e "${BBLUE}├──────────────────────────────────────┤${RST}"
    printf  "${BBLUE}│${RST}  ${DIM}Iterations${RST}    ${BWHITE}%-20s${RST} ${BBLUE}│${RST}\n" "$TOTAL_ITERATIONS"
    printf  "${BBLUE}│${RST}  ${DIM}Wall time${RST}     ${BWHITE}%-20s${RST} ${BBLUE}│${RST}\n" "${mins}m ${secs}s"
    printf  "${BBLUE}│${RST}  ${DIM}Input tokens${RST}  ${CYAN}%-20s${RST} ${BBLUE}│${RST}\n" "$TOTAL_INPUT_TOKENS"
    printf  "${BBLUE}│${RST}  ${DIM}Output tokens${RST} ${CYAN}%-20s${RST} ${BBLUE}│${RST}\n" "$TOTAL_OUTPUT_TOKENS"
    printf  "${BBLUE}│${RST}  ${DIM}Total cost${RST}    ${BMAGENTA}%-20s${RST} ${BBLUE}│${RST}\n" "$(printf '$%.4f' "$TOTAL_COST")"
    echo -e "${BBLUE}└──────────────────────────────────────┘${RST}"
}

print_banner() {
    local color="$1" label="$2" num="$3"
    local inner="  ${label}  #${num}"
    local pad_len=$(( 38 - ${#inner} ))
    echo ""
    echo -e "${color}  ╔══════════════════════════════════════╗${RST}"
    printf "${color}  ║${RST}  ${color}%s${RST}  ${BWHITE}#%s${RST}%*s${color}║${RST}\n" \
        "$label" "$num" "$pad_len" ""
    echo -e "${color}  ╚══════════════════════════════════════╝${RST}"
    echo ""
}

run_claude() {
    local prompt_file="$1"
    LAST_LOG_FILE="$LOG_DIR/$(date +%Y%m%d-%H%M%S).jsonl"

    claude -p \
        --dangerously-skip-permissions \
        --output-format=stream-json \
        --model opus \
        --verbose \
        < "$prompt_file" \
    | tee "$LAST_LOG_FILE" \
    | jq -r --unbuffered "$JQ_FILTER" 2>/dev/null \
    || true

    echo -e "  ${DIM}raw log: ${LAST_LOG_FILE}${RST}"
}

accumulate_stats() {
    local log_file="$1"
    [ -f "$log_file" ] || return 0

    local stats
    stats=$(jq -s '
      [ .[] | select(.type == "result") ] |
      {
        cost: (map(.total_cost_usd // 0) | add // 0),
        input: (map(.usage.input_tokens // 0) | add // 0),
        output: (map(.usage.output_tokens // 0) | add // 0)
      }
    ' "$log_file" 2>/dev/null) || stats=""

    if [ -n "$stats" ]; then
        local cost input output
        cost=$(echo "$stats" | jq -r '.cost')
        input=$(echo "$stats" | jq -r '.input')
        output=$(echo "$stats" | jq -r '.output')
        TOTAL_COST=$(echo "$TOTAL_COST + $cost" | bc 2>/dev/null || echo "$TOTAL_COST")
        TOTAL_INPUT_TOKENS=$((TOTAL_INPUT_TOKENS + ${input%.*}))
        TOTAL_OUTPUT_TOKENS=$((TOTAL_OUTPUT_TOKENS + ${output%.*}))
    fi
    TOTAL_ITERATIONS=$((TOTAL_ITERATIONS + 1))
}

LAST_LOG_FILE=""
trap 'print_summary; exit 130' INT

# ─── Parse arguments ──────────────────────────────────────────────

if [ "${1:-}" = "plan" ]; then
    MODE_LABEL="PLAN"
    MODE_COLOR="$BCYAN"
    PROMPT_FILE="PROMPT_plan.md"
    MAX_ITERATIONS=${2:-3}
elif [[ "${1:-}" =~ ^[0-9]+$ ]]; then
    MODE_LABEL="BUILD"
    MODE_COLOR="$BGREEN"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=$1
else
    MODE_LABEL="BUILD"
    MODE_COLOR="$BGREEN"
    PROMPT_FILE="PROMPT_build.md"
    MAX_ITERATIONS=0
fi

if [ ! -f "$PROMPT_FILE" ]; then
    echo -e "${BRED}Error:${RST} $PROMPT_FILE not found"
    exit 1
fi

# ─── Header ───────────────────────────────────────────────────────

echo -e "${BBLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
MODE_LOWER=$(echo "$MODE_LABEL" | tr '[:upper:]' '[:lower:]')
echo -e "  ${DIM}Mode${RST}     ${MODE_COLOR}${MODE_LOWER}${RST}"
echo -e "  ${DIM}Prompt${RST}   ${WHITE}$PROMPT_FILE${RST}"
echo -e "  ${DIM}Branch${RST}   ${BCYAN}$CURRENT_BRANCH${RST}"
[ $MAX_ITERATIONS -gt 0 ] && echo -e "  ${DIM}Max${RST}      ${WHITE}$MAX_ITERATIONS iterations${RST}"
echo -e "${BBLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"

# ─── Main loop ────────────────────────────────────────────────────
# Both plan and build use the same loop:
#   run claude → push → check for stale (no new commits).

ITERATION=0
STALE_COUNT=0
MAX_STALE=2

while true; do
    if [ $MAX_ITERATIONS -gt 0 ] && [ $ITERATION -ge $MAX_ITERATIONS ]; then
        echo -e "${BYELLOW}Reached max iterations: $MAX_ITERATIONS${RST}"
        break
    fi

    HEAD_BEFORE=$(git rev-parse HEAD 2>/dev/null)

    print_banner "$MODE_COLOR" "$MODE_LABEL" "$((ITERATION + 1))"
    run_claude "$PROMPT_FILE"
    accumulate_stats "$LAST_LOG_FILE"

    git push origin "$CURRENT_BRANCH" 2>/dev/null || {
        echo -e "${YELLOW}Failed to push. Creating remote branch...${RST}"
        git push -u origin "$CURRENT_BRANCH"
    }

    ITERATION=$((ITERATION + 1))

    HEAD_AFTER=$(git rev-parse HEAD 2>/dev/null)
    if [ "$HEAD_BEFORE" = "$HEAD_AFTER" ]; then
        STALE_COUNT=$((STALE_COUNT + 1))
        echo -e "${BYELLOW}No new commits this iteration${RST} ${DIM}(stale: $STALE_COUNT/$MAX_STALE)${RST}"
        if [ $STALE_COUNT -ge $MAX_STALE ]; then
            echo -e "${BRED}Stale loop detected:${RST} $MAX_STALE consecutive iterations with no commits. Stopping."
            print_summary
            exit 1
        fi
    else
        STALE_COUNT=0
    fi
done

print_summary
