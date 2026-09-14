---
name: guided-tdd
description: Autonomous strict Test-Driven Development. AI writes the failing test (RED), implements the minimal fix (GREEN), refactors, runs coverage, and auto-fixes. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use when you want TDD, write tests first, Red-Green-Refactor, or enforce 80%+ coverage.
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
| Implementation done | → `guided-review` or `guided-code-reviewer` |
| Check tests & coverage | → `guided-verify` |

**Default happy path (automation loop)**
```
guided-docs → guided-plan → guided-tdd / guided-coding → guided-refactoring → guided-review → guided-verify
```

## Project Memory

Before any coaching, check for project memory (`.grok/project-memory.md` or `.kiro/project-memory.md` or `AGENTS.md`). Treat existing contents as ground truth. Update after meaningful discoveries (prefer `AGENTS.md` when running in OpenCode).

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/` (or Claude-compatible paths). Works with Plan and Build; automation contract — AI writes + runs RED/GREEN/REFACTOR and auto-fixes.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-tdd` or `@guided-tdd`. Prefer updating `AGENTS.md`.

## Automation Process (strict)

### 1. Clarify the behavior
- Restate the expected behavior in one sentence.
- Ask only if success criteria or edge cases are ambiguous.

### 2. Write the RED test (complete & minimal)
Write the full test file or test case to disk that fails for the right reason. Include:
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

- Always show complete, copy-paste-ready (but human must type) code blocks with exact paths.
- One tiny coached step at a time.
- After each human confirmation, advance.
- Never run `Write`, `Edit`, or create files yourself.

## When to prefer this over guided-coding

Use `guided-tdd` when the human explicitly wants the Red-Green-Refactor discipline or when coverage is the primary goal. Use `guided-coding` for general feature implementation that happens to include tests.
