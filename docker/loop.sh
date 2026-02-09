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
# Processes the JSONL stream line-by-line. Three event types are handled:
#   "assistant" → tool calls (· Read ...) and subagent spawns (▶ Explore ...)
#   "user"      → subagent completions (✓ duration, tool calls, tokens)
# Everything else is ignored. The iteration summary (context + cost) is
# computed post-hoc in run_claude() since jq cannot track state across lines.
JQ_FILTER='
  def green: "\u001b[32m" + . + "\u001b[0m";
  def red:   "\u001b[1;31m" + . + "\u001b[0m";
  def dim:   "\u001b[2m" + . + "\u001b[0m";
  def kfmt:  if . >= 1000000 then ((. / 100000 | floor) / 10 | tostring) + "M"
              elif . >= 1000 then ((. / 100 | floor) / 10 | tostring) + "k"
              else tostring end;

  # ── assistant messages: text output + tool calls ──
  if .type == "assistant" then
    (.message.content[]? |
      if .type == "text" then
        ("\u001b[1m\u001b[37m" + .text + "\u001b[0m")
      elif .type == "tool_use" then
        if .name == "Task" then
          ("  \u001b[1;36m\u25b6 " + (.input.subagent_type // .input.sub_agent_type // "agent") + "\u001b[0m  \u001b[37m\"" + (.input.description // "\u2014") + "\"\u001b[0m" +
            (if .input.model then "  \u001b[2mmodel=\u001b[0m" + .input.model else "" end) +
            (if .input.max_turns then "  \u001b[2mmax_turns=\u001b[0m" + (.input.max_turns | tostring) else "" end))
        else
          ("  \u001b[2m\u00b7 " + .name + " " +
            ((if .input.file_path then (.input.file_path | tostring)
              elif .input.description then (.input.description | tostring)
              elif .input.command then (.input.command | tostring)
              elif .input.pattern then (.input.pattern | tostring)
              elif .input.query then (.input.query | tostring)
              elif .input.url then (.input.url | tostring)
              elif .input.skill then (.input.skill | tostring)
              else (.input | keys | join(", "))
              end) | if length > 60 then .[:60] + "\u2026" else . end) + "\u001b[0m")
        end
      else empty end
    ) // empty

  # ── user messages: subagent completions ──
  # Only Task tool results have .totalTokens (regular tools like Read/Bash do not).
  # totalTokens = input + cache_creation + cache_read + output across all subagent turns.
  elif .type == "user" then
    (if .tool_use_result.totalTokens then
      if .tool_use_result.status == "completed" then
        ("  " + ("  \u2713 " | green) + ((.tool_use_result.totalDurationMs // 0 | . / 1000 | tostring) + "s, " + (.tool_use_result.totalToolUseCount // 0 | tostring) + " tool calls, " + (.tool_use_result.totalTokens // 0 | kfmt) + " tokens" | dim))
      else
        ("  " + ("  \u2717 " + (.tool_use_result.status // "unknown") | red))
      end
    else empty end) // empty

  else empty end
'

# ─── Stats accumulators (across all iterations) ─────────────────
TOTAL_COST=0              # sum of total_cost_usd from result events
PEAK_CONTEXT=0            # high-water mark: max context window fill across iterations
TOTAL_SUBAGENT_TOKENS=0   # cumulative tokens consumed by all subagents
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
    local pct=$(( PEAK_CONTEXT * 100 / 200000 ))
    local peak_fmt
    if [ "$PEAK_CONTEXT" -ge 1000000 ] 2>/dev/null; then
        peak_fmt="$(echo "scale=1; $PEAK_CONTEXT / 1000000" | bc)M"
    elif [ "$PEAK_CONTEXT" -ge 1000 ] 2>/dev/null; then
        peak_fmt="$(echo "scale=1; $PEAK_CONTEXT / 1000" | bc)k"
    else
        peak_fmt="$PEAK_CONTEXT"
    fi
    local sub_fmt
    if [ "$TOTAL_SUBAGENT_TOKENS" -ge 1000000 ] 2>/dev/null; then
        sub_fmt="$(echo "scale=1; $TOTAL_SUBAGENT_TOKENS / 1000000" | bc)M"
    elif [ "$TOTAL_SUBAGENT_TOKENS" -ge 1000 ] 2>/dev/null; then
        sub_fmt="$(echo "scale=1; $TOTAL_SUBAGENT_TOKENS / 1000" | bc)k"
    else
        sub_fmt="$TOTAL_SUBAGENT_TOKENS"
    fi
    printf  "${BBLUE}│${RST}  ${DIM}Peak context${RST}  ${CYAN}%-20s${RST} ${BBLUE}│${RST}\n" "${peak_fmt} / 200k (${pct}%)"
    printf  "${BBLUE}│${RST}  ${DIM}Subagent tokens${RST} ${CYAN}%-16s${RST} ${BBLUE}│${RST}\n" "${sub_fmt}"
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

    # Iteration summary: peak context window fill + cost.
    # Context = max(input + cache_creation + cache_read) across all turns in this
    # iteration. This is how much of the 200k window the parent agent consumed.
    # Cost comes from the result event (includes parent + subagents).
    local iter_line
    iter_line=$(jq -rs '
      def kfmt: if . >= 1000000 then ((. / 100000 | floor) / 10 | tostring) + "M"
                elif . >= 1000 then ((. / 100 | floor) / 10 | tostring) + "k"
                else tostring end;
      ([.[] | select(.type == "assistant") |
        ((.message.usage.input_tokens // 0) +
         (.message.usage.cache_creation_input_tokens // 0) +
         (.message.usage.cache_read_input_tokens // 0))] | max // 0) as $peak |
      ([.[] | select(.type == "result") |
        (.total_cost_usd // .cost_usd // 0)] | add // 0) as $cost |
      ($peak * 100 / 200000 | floor) as $pct |
      "\u001b[2m\u2500\u2500\u2500\u2500\u001b[0m " +
      ($peak | kfmt) + " / 200k context (" + ($pct | tostring) + "%)" +
      (if $cost > 0 then "  \u001b[35m$" + ($cost * 10000 | floor / 10000 | tostring) + "\u001b[0m" else "" end)
    ' "$LAST_LOG_FILE" 2>/dev/null) || iter_line=""
    [ -n "$iter_line" ] && echo -e "\n  ${iter_line}"
    echo -e "  ${DIM}raw log: ${LAST_LOG_FILE}${RST}"
}

# Extract per-iteration stats from a completed JSONL log and fold into accumulators.
# - cost:  from the "result" event (total_cost_usd includes parent + subagents)
# - peak:  highest context window fill across all assistant turns
# - sub:   sum of totalTokens from all subagent (Task) tool results
accumulate_stats() {
    local log_file="$1"
    [ -f "$log_file" ] || return 0

    local stats
    stats=$(jq -s '
      {
        cost:  ([ .[] | select(.type == "result") | (.cost_usd // .total_cost_usd // 0) ] | add // 0),
        peak:  ([ .[] | select(.type == "assistant") |
                  ((.message.usage.input_tokens // 0) +
                   (.message.usage.cache_creation_input_tokens // 0) +
                   (.message.usage.cache_read_input_tokens // 0))] | max // 0),
        sub:   ([ .[] | select(.type == "user") | .tool_use_result.totalTokens // empty ] | add // 0)
      }
    ' "$log_file" 2>/dev/null) || stats=""

    if [ -n "$stats" ]; then
        local cost peak sub
        cost=$(echo "$stats" | jq -r '.cost')
        peak=$(echo "$stats" | jq -r '.peak')
        sub=$(echo "$stats" | jq -r '.sub')
        TOTAL_COST=$(echo "$TOTAL_COST + $cost" | bc 2>/dev/null || echo "$TOTAL_COST")
        [ "${peak%.*}" -gt "$PEAK_CONTEXT" ] 2>/dev/null && PEAK_CONTEXT=${peak%.*}
        TOTAL_SUBAGENT_TOKENS=$((TOTAL_SUBAGENT_TOKENS + ${sub%.*}))
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
