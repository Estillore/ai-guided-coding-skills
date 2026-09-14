---
name: guided-code-reviewer
description: Autonomous rigorous code review that auto-fixes. AI finds concrete issues with exact lines and failure modes, applies minimal fixes for CRITICAL/HIGH, and lists the rest. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use for review, code review, security review, what should I strengthen, or after implementation before merge.
---

# Guided Code Reviewer

## Overview

Force the AI into autonomous code review. The AI finds confident, actionable issues (with proof for HIGH/CRITICAL), applies minimal fixes for must-fix items, and reports the rest.

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

Load project memory first (`.grok/project-memory.md`, `.kiro/project-memory.md`, or `AGENTS.md`). Prefer project conventions over generic advice. When running in OpenCode, update findings that become permanent conventions into `AGENTS.md`.

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/` (or Claude-compatible locations). Works with Plan (read-only review) and Build (AI auto-fixes must-fix findings). Follows the same Agent Skills standard as the rest of the guided family.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-code-reviewer` or `@guided-code-reviewer`. Prefer updating `AGENTS.md`.

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
