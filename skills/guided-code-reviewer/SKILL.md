---
name: guided-code-reviewer
description: Pointer to guided-review. Use for review, code review, security review, what should I strengthen, or after implementation before merge. Auto-fix only when the active host can edit. Works in Kiro, Grok, OpenCode, and Zed.
---

# Guided Code Reviewer

Use `guided-review`.

## Overview

This skill is the strict review entry. Follow `guided-review`. Auto-fix CRITICAL and HIGH only when the active host can edit. The OpenCode `guided-reviewer` subagent is read-only and does not edit.

**Core contract**
- AI applies minimal fixes for CRITICAL/HIGH directly.
- AI lists MEDIUM/LOW as follow-ups (or fixes trivial ones inline).
- AI reports each fix with file:line + failure mode prevented.

Companion to `guided-review`. Prefer this when you want the stricter ECC-style confidence filtering, false-positive avoidance, and severity gates.

## Connected workflow & hand-offs

| Human situation | Recommend |
|-----------------|-----------|
| Still implementing | → `guided-coding` |
| Code is messy / needs cleanup first | → `guided-refactoring` |
| Need verification commands | → `guided-verify` |
| Security is the primary concern | Stay here (security is first-class) |

**Default happy path (automation loop)**
```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```

## Project Memory

Read `docs/guided-memory.md` first. Prefer project conventions over generic advice. Update `docs/guided-memory.md` when a finding becomes a permanent convention. If `AGENTS.md` exists and has no pointer, add one line that names `docs/guided-memory.md`. Do not append a project-memory section to `AGENTS.md`.

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/`. The `guided-review` primary applies fixes. The `guided-reviewer` subagent is read-only and does not edit.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-review` on the Write profile. Record facts in `docs/guided-memory.md`.

## Coaching Process

### 1. Gather context
Ask the human (or use available tools) for:
- The diff or the files to review
- What the change is intended to do

### 2. Apply confidence filters (strict)
Only report issues where confidence > 80%.

**Pre-report gate** (all four must be yes):
1. Can I cite the exact file and line?
2. Can I describe the concrete failure mode (input + state + bad outcome)?
3. Have I considered surrounding context / callers / existing guards?
4. Is the severity defensible?

If any answer is no → drop or demote.

**It is acceptable and expected to return zero findings.** Do not manufacture nits.

### 3. Severity order
- CRITICAL (security, data loss, auth bypass) — must fix
- HIGH (bugs, missing error handling that can fail in production)
- MEDIUM (performance, maintainability that will bite soon)
- LOW (style, docs) — only if they violate project conventions

### 4. Show findings
For each finding use:

```
[SEVERITY] Short title
File: path:line
Issue: concrete description of the failure mode
Why existing guards do not catch it: ...
Minimal fix: [the edit to apply when the host can write]
```

### 5. Auto-fix decision
Auto-apply minimal fixes for CRITICAL/HIGH; list MEDIUM/LOW as follow-ups (fix trivial ones inline).

### 6. Apply the minimal fix
For each must-fix finding, apply the complete, minimal, correct patch directly and report file:line.

## Common false positives the AI must never report

- "Consider adding error handling" when the caller or framework already handles it
- Missing input validation on internal functions whose callers already validate
- Magic numbers that are well-known constants or obvious from context
- Function length for exhaustive switches, configs, or test tables
- Missing JSDoc on self-describing internal helpers
- Possible null when a guard or type narrowing is already present
- "Should use TypeScript" in a JavaScript-only project

## Output style

- Zero findings is a valid and preferred outcome when the code is clean.
- Never invent issues to look thorough.
- Apply one finding + one minimal fix at a time, re-scanning after each.
