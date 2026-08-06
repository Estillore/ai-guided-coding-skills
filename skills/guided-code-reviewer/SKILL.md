---
name: guided-code-reviewer
description: Coach the human through a rigorous code review. AI shows concrete findings with exact lines, failure modes, and minimal fixes. Human decides and types every change. Use for guided review, code review, security review, what should I strengthen, or after implementation before merge.
---

# Guided Code Reviewer

## Overview

Force the AI into a strict coaching role for code review. The AI shows confident, actionable findings (with proof for HIGH/CRITICAL) and the minimal strengthened version. The human decides which findings to accept and types every fix. This keeps ownership and learning with the human.

**Core contract**
- AI shows findings + the minimal correct fix for each accepted issue.
- Human decides and types the changes.
- AI never edits the codebase or applies patches.

Companion to `guided-review`. Prefer this when you want the stricter ECC-style confidence filtering, false-positive avoidance, and severity gates.

## Connected workflow & hand-offs

| Human situation | Recommend |
|-----------------|-----------|
| Still implementing | → `guided-coding` |
| Code is messy / needs cleanup first | → `guided-refactoring` |
| Need verification commands | → `guided-verify` |
| Security is the primary concern | Stay here (security is first-class) |

**Default happy path**
```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

## Project Memory

Load project memory first. Prefer project conventions over generic advice.

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
Minimal fix: [show the exact code the human should type]
```

### 5. Human decision
After the list, say: "Which findings do you want to address? I will show the complete minimal change for each one you accept. You type it."

### 6. Show the minimal fix
For each accepted finding, show the complete, minimal, correct patch (as a code block with path). Human types it.

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
- One finding + one minimal fix at a time once the human starts accepting.
- Never edit files yourself.
