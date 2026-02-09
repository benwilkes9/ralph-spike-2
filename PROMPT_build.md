SCOPE: You are ONE iteration of a loop. Implement exactly ONE task from @IMPLEMENTATION_PLAN.md — the highest-priority incomplete item. After ALL tests pass (not just your task's tests — the entire suite) and you have committed and pushed, STOP. Do not look for more work. Do not start the next task. Your job is done.

0a. Study @IMPLEMENTATION_PLAN.md — this is your task list and primary source of truth for what to do next.
0b. For reference, the application source code is in `src/ralf_spike_2/**/*.py` and tests are in `tests/**/*.py`.
0c. Before starting new work, check `git status` for uncommitted changes from a previous iteration. If any exist, run the tests for the affected code — if they pass, `git add -A && git commit` with a message describing those changes and `git push`. If they fail, fix them first.

1. Pick the highest-priority incomplete (`[ ]`) task from @IMPLEMENTATION_PLAN.md. Before implementing, verify whether it's already done — search the codebase and run its required tests. If they all pass, mark it `[x]` in the plan and continue down the list to the next `[ ]` task. Repeat until you find a genuinely incomplete task — that is your ONE task for this iteration. If every task is `[x]` and all tests pass, update the plan, commit, push, and STOP. For implementation: search the codebase first (don't assume not implemented) using Sonnet subagents. You may use up to 500 parallel Sonnet subagents for searches/reads and only 1 Sonnet subagent for build/tests. Use Opus subagents when complex reasoning is needed (debugging, architectural decisions).
2. After implementing functionality or resolving problems, run all required tests specified in the task definition. Tasks include required tests — implement tests as part of task scope. All required tests must exist and pass before the task is considered complete. If functionality is missing then it's your job to add it as per the application specifications. Ultrathink.
3. When you discover issues, immediately update @IMPLEMENTATION_PLAN.md with your findings using a subagent. When resolved, update and remove the item.
4. Run the FULL test suite, not just the tests for your task. If anything fails — including tests unrelated to your work — fix it before committing. When all tests pass, mark your task `[x]` in @IMPLEMENTATION_PLAN.md, run the validation steps from @AGENTS.md, then `git add -A` then `git commit` with a message describing the changes. After the commit, `git push`. Then STOP — the outer loop will start the next iteration with a fresh context.

9999. Required tests derived from acceptance criteria must exist and pass before committing. Tests are part of implementation scope, not optional.
99999. Important: When authoring documentation, capture the why — tests and implementation importance.
999999. Important: Single sources of truth, no migrations/adapters. If tests unrelated to your work fail, resolve them as part of the increment.
9999999. As soon as there are no build or test errors create a git tag. If there are no git tags start at 0.0.0 and increment patch by 1 for example 0.0.1 if 0.0.0 does not exist.
99999999. You may add extra logging if required to debug issues.
999999999. Keep @IMPLEMENTATION_PLAN.md current with learnings using a subagent — future work depends on this to avoid duplicating efforts. Update especially after finishing your turn.
9999999999. When you learn something new about how to run the application, update @AGENTS.md using a subagent but keep it brief. For example if you run commands multiple times before learning the correct command then that file should be updated.
99999999999. For any bugs you notice, resolve them or document them in @IMPLEMENTATION_PLAN.md using a subagent even if it is unrelated to the current piece of work.
999999999999. Implement functionality completely. Placeholders and stubs waste efforts and time redoing the same work.
9999999999999. When @IMPLEMENTATION_PLAN.md becomes large periodically clean out the items that are completed from the file using a subagent.
99999999999999. Do NOT create or modify spec files in `specs/*`. Only implement what is already in @IMPLEMENTATION_PLAN.md. If you find a spec inconsistency, document it in the plan for a human to resolve.
999999999999999. IMPORTANT: Keep @AGENTS.md operational only — status updates and progress notes belong in `IMPLEMENTATION_PLAN.md`. A bloated AGENTS.md pollutes every future loop's context.
