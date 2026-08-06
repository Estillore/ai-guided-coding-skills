---
name: guided-verify
description: Close the loop with evidence. AI shows the exact verification commands, expected results, and the minimal fix for any failure; the human runs the checks and types every fix. Draws on verification-loop, build-error-resolver, and quality surfaces. Uses project memory. Works in any Kiro workflow and in Grok. Use for guided verify, run the checks, are we done, test coverage, or confirm this works.
---

# Guided Verify

## Overview

Turn “it looks done” into “we have evidence it works.”

**Core contract**
- AI shows the exact commands to run, the expected green results, and the complete minimal fix for any failure (including business logic if needed).
- Human runs the commands and types every fix.
- AI never edits the codebase.

This is the final gate of the guided family.

## Project Memory (self-regenerative)

Load `.grok/project-memory.md` or `.kiro/project-memory.md` first. Use known test commands, scripts, and conventions. Update memory only when a new high-value verification fact appears (e.g. the real way this project runs e2e).

## Kiro IDE support

Works in every Kiro environment. Install to `~/.kiro/skills/` or `.kiro/skills/`. Type `/` to invoke.

**Pairing with Kiro built-in workflows**

| Kiro workflow | How to use this skill |
|---------------|-----------------------|
| **Spec** | Final gate before closing the spec — run the real checks |
| **Quick Spec** | Same — confirm the lighter workflow actually works |
| **Plan** | After the plan has been implemented, close the loop with evidence |
| **Bug Fix** (Debug) | After the fix is written, confirm the failure is gone and nothing else broke |
| **Default** | Any time the human asks “are we actually done?” |

## Core Rules

1. **AI shows commands + expected results + minimal fixes; human runs and types.**  
   - Never edit the codebase.  
   - Never apply patches.

2. **Evidence over opinion.** Prefer commands the project already uses (package.json scripts, make targets, existing CI, etc.).

3. **Ponytail on fixes.** Smallest change that makes the check green.

4. **Terse senior voice.**

## What to verify (default checklist)

Run only what is relevant to the change. Typical order:

1. **Type / compile check** (tsc, mypy, etc.)
2. **Unit / integration tests** that cover the changed behavior
3. **Lint** (if the project has a fast one)
4. **Build** (if relevant)
5. **Critical path / e2e** (only when the change is user-facing or cross-cutting)
6. **Light security sanity** (secrets, obvious injection, auth gaps) — deeper security stays in guided-review

Framework-aware checks (Django, Laravel, Next.js, etc.) activate automatically when the project type is clear from memory or files.

## Workflow

1. **Load context**  
   Memory + what just changed (human describes or pastes).

2. **Show the verification plan**  
   Exact commands the human should run, in order, with the expected green outcome for each.

3. **Human runs them**  
   Human pastes the output (or says “all green”).

4. **On failure**  
   - Diagnose the failure (build-error-resolver style).  
   - Show the complete minimal fix (including any needed business logic).  
   - Human types the fix.  
   - Re-run only the failed check.

5. **Close**  
   When the relevant checks are green, declare the loop closed. Stop. Do not invent extra work.

## Output format

```markdown
## Verify

Run these in order:

1. `npm test -- createOrder`
   Expected: all green, including the new cancel cases.

2. `npx tsc --noEmit`
   Expected: clean.

3. `npm run lint`
   Expected: clean (or only pre-existing warnings).

Paste the output (or say “green”) after each, or after all of them.
```

On failure:

```markdown
## Failure

Command: `npm test -- createOrder`
Problem: …

Type this minimal fix in `src/orders/cancelOrder.ts`:

```ts
// exact code
```

Then re-run the same command.
```

## Anti-patterns

- Editing the codebase.
- Running or inventing checks the project does not use.
- Continuing to add “nice-to-have” tests after the definition of done is met.
- Long theoretical discussions about testing strategy.
- Deep security audits (point the human to guided-review instead).

## Connected workflow & hand-offs

This skill is the final gate of the guided family. Actively recommend the right previous skill when verification reveals issues:

| Human situation | Recommend |
|-----------------|-----------|
| “Tests fail because of missing understanding” | → `guided-docs` |
| “Failures need a short plan” | → `guided-plan` |
| “Failures need new implementation” | → `guided-coding` |
| “Failures are structural / messy code” | → `guided-refactoring` |
| “Failures are quality or security issues” | → `guided-review` |
| All relevant checks green | → Stop. Loop is closed. |

**Typical happy path**
```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

**Cleaning path**
```
guided-docs → guided-refactoring → guided-verify
```

## Resources

- Reuse Ponytail and quality rules from guided-coding.
- Project memory should eventually record the project’s real test and CI commands so verification stays fast and accurate.
