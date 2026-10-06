---
name: guided-tdd
description: Autonomous strict Test-Driven Development. AI writes the failing test (RED), runs it, implements the minimal fix (GREEN), refactors, and runs coverage. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use when you want TDD, write tests first, Red-Green-Refactor, or enforce 80%+ coverage. The OpenCode subagent guided-test-design only designs the case. This skill writes and runs it.
---

# Guided TDD

## Overview

Force the AI into autonomous Test-Driven Development. The AI writes the complete, minimal, correct test and implementation to disk, runs them, and auto-fixes.

**Core contract**
- AI writes the complete failing test, the minimal passing implementation, and any refactor directly.
- AI runs tests + coverage and fixes failures (max 3 loops).
- AI reports evidence at the end.

This is the TDD specialist companion to `guided-coding`. Prefer this when the task is explicitly test-first or coverage-focused.

## Connected workflow & hand-offs

| Human situation | Recommend |
|-----------------|-----------|
| Need the mental model first | → `guided-docs` |
| Need a short plan first | → `guided-plan` |
| Ready to implement a feature | → `guided-coding` (or stay here for pure TDD) |
| Code is messy | → `guided-refactoring` |
| Implementation done | → `guided-review` |
| Check tests & coverage | → `guided-verify` |

**Default happy path (automation loop)**
```
guided-docs → guided-plan → guided-tdd / guided-coding → guided-refactoring → guided-review → guided-verify
```

## Project Memory

Read `docs/guided-memory.md` when it exists and treat it as ground truth. Update it after meaningful discoveries. If `AGENTS.md` exists and has no pointer, add one line that names `docs/guided-memory.md`. Do not append a project-memory section to `AGENTS.md`.

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/`. Invoke this skill from the `guided-coding` primary, or run it as the writable skill. `guided-test-design` is read-only and only returns the RED case. Write the failing test to disk and run it.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-tdd` or `@guided-tdd` on the Write profile. Write the failing test to disk and run it. Record facts in `docs/guided-memory.md`.

## Automation Process (strict)

### 1. Clarify the behavior
- Restate the expected behavior in one sentence.
- Ask only if success criteria or edge cases are ambiguous.

### 2. Write the RED test (complete & minimal)
Write the failing test to disk and run it. Include:
- Exact file path
- Imports
- The assertion that encodes the requirement
- Any necessary mocks (applied, not just shown)

Run it; it must fail for the right reason. Fix the test first if it does not.

### 3. Confirm RED
RED is confirmed by actual tool output, not by human report.

### 4. Apply the GREEN implementation (complete & minimal)
Apply the smallest change that makes the test pass. No extra features, no cleanup yet. Re-run; auto-fix up to 3x.

### 5. Confirm GREEN
GREEN is confirmed by actual tool output. Only proceed when green.

### 6. Apply the REFACTOR (if needed)
Apply the cleaned version that keeps the test green. Preserve behavior exactly.

### 7. Coverage gate
Run the coverage command and require 80%+ branches/functions/lines/statements on the touched code. Add tests until green.

## Edge cases the AI must always address in the shown tests

1. Null / undefined input
2. Empty collections / strings
3. Invalid types
4. Boundary values
5. Error paths
6. Race / concurrency (when relevant)
7. Large data (when relevant)
8. Special characters

## Anti-patterns the AI must never show

- Tests that assert implementation details instead of behavior
- Tests that share mutable state
- Weak assertions
- Missing mocks for external services
- Implementation that does more than the current test requires

## Output style

- Write the failing test to disk and run it before any implementation.
- Apply the minimal implementation with edit tools. Report `file:line` and the command output.
- Recommend the next phase and stop. Do not auto-chain.

## When to prefer this over guided-coding

Use `guided-tdd` when the human explicitly wants the Red-Green-Refactor discipline or when coverage is the primary goal. Use `guided-coding` for general feature implementation that happens to include tests.
