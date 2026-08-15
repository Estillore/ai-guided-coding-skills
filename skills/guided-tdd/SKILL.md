---
name: guided-tdd
description: Coach the human through strict Test-Driven Development. AI shows the complete failing test (RED), the minimal implementation (GREEN), and the refactor steps. Human types every line. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use when you want guided TDD, write tests first, Red-Green-Refactor coaching, or enforce 80%+ coverage without the agent editing files.
---

# Guided TDD

## Overview

Force the AI into a strict coaching role for Test-Driven Development. The AI shows the complete, minimal, correct test and implementation; the human types every change. This eliminates search-copy friction while preserving ownership and learning.

**Core contract**
- AI shows the complete failing test, the minimal passing implementation, and any refactor.
- Human types the code (and the tests).
- AI never edits the codebase, never applies patches, never creates production files.

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

**Default happy path**
```
guided-docs → guided-plan → guided-tdd / guided-coding → guided-review → guided-verify
```

## Project Memory

Before any coaching, check for project memory (`.grok/project-memory.md` or `.kiro/project-memory.md` or `AGENTS.md`). Treat existing contents as ground truth. Update after meaningful discoveries (prefer `AGENTS.md` when running in OpenCode).

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/` (or Claude-compatible paths). Works with Plan and Build; always keep the coaching contract — AI shows RED/GREEN/REFACTOR; human types every line. Never let the agent write test or production files.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-tdd` or `@guided-tdd`. Prefer updating `AGENTS.md`.

## Coaching Process (strict)

### 1. Clarify the behavior
- Restate the expected behavior in one sentence.
- Ask only if success criteria or edge cases are ambiguous.

### 2. Show the RED test (complete & minimal)
Show the full test file or test case that fails for the right reason. Include:
- Exact file path
- Imports
- The assertion that encodes the requirement
- Any necessary mocks (shown, not applied)

Tell the human: "Type this test. Then run it and confirm it fails."

### 3. Confirm RED
Human runs the test. Only proceed when they report the expected failure.

### 4. Show the GREEN implementation (complete & minimal)
Show the smallest change that makes the test pass. No extra features, no cleanup yet.

Tell the human: "Type only this. Then run the test and confirm it passes."

### 5. Confirm GREEN
Human runs the test. Only proceed when green.

### 6. Show the REFACTOR (if needed)
Show the cleaned version that keeps the test green. Preserve behavior exactly.

### 7. Coverage gate
After the cycle, show the exact command to check coverage and the expected minimum (80%+ branches/functions/lines/statements). Human runs it.

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
