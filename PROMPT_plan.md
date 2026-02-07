0a. Study `specs/*` with up to 250 parallel Sonnet subagents to learn the application specifications.
0b. Study @IMPLEMENTATION_PLAN.md (if present) to understand the plan so far.
0c. Study `src/ralf_spike_2/*` with up to 250 parallel Sonnet subagents to understand shared utilities & components.
0d. For reference, the application source code is in `src/*` and tests are in `tests/*`.
0e. Before starting new work, check `git status` for uncommitted changes from a previous iteration. If any exist, review them and `git add -A && git commit` with a message describing those changes, then `git push`.
0f. Review project-level files (`README.md`, `pyproject.toml`) and plan updates needed so that a new developer can clone the repo, follow the README, and have the app running. Include documentation tasks in the plan.

1. Study @IMPLEMENTATION_PLAN.md (if present; it may be incorrect) and use up to 500 Sonnet subagents to study existing source code in `src/*` and `tests/*` and compare it against `specs/*`. Use an Opus subagent to analyze findings, prioritize tasks, and create/update @IMPLEMENTATION_PLAN.md as a bullet point list sorted in priority of items yet to be implemented. Ultrathink. Consider searching for TODO, minimal implementations, placeholders, skipped/flaky tests, and inconsistent patterns. Study @IMPLEMENTATION_PLAN.md to determine starting point for research and keep it up to date with items considered complete/incomplete using subagents. For each task in the plan, derive required tests from the acceptance criteria in the relevant spec — what specific outcomes need verification. Tests verify WHAT works (behavior, edge cases), not HOW it's implemented. Include required tests as part of each task definition.

IMPORTANT: Plan only. Do NOT implement anything. Do NOT assume functionality is missing; confirm with code search first. Treat `src/ralf_spike_2` as the project's package root.

CONVERGENCE: If IMPLEMENTATION_PLAN.md already exists and covers all specs, verify correctness but do NOT rewrite or restyle it. Only commit if you found a factual error (wrong status code, missing task, incorrect field name) or a missing task. Do NOT commit formatting-only, rewording-only, or restructuring changes — the plan does not need to be perfect prose, it needs to be correct and complete.

ULTIMATE GOAL: We want to achieve a fully working FastAPI REST API that performs CRUD operations on a SQLite-backed todo list, with filtering, sorting, search, and pagination — all matching the specs in `specs/`. Consider missing elements and plan accordingly. If an element is missing, search first to confirm it doesn't exist, then if needed author the specification at specs/FILENAME.md. If you create a new element then document the plan to implement it in @IMPLEMENTATION_PLAN.md using a subagent.

COMMIT: When you have made changes to any files (IMPLEMENTATION_PLAN.md, specs, etc.), `git add -A` then `git commit` with a message describing the changes, then `git push`. If nothing changed, do not create an empty commit. If the only changes you would make are cosmetic (rewording, reformatting, reordering), discard them (`git checkout -- .`) and do not commit.
