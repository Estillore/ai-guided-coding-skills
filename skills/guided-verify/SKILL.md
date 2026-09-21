---
name: guided-verify
description: Close the loop with evidence, autonomously. AI runs the verification commands, auto-applies minimal fixes, re-runs until green, and reports evidence. Uses project memory. Prefers package-scoped checks on large codebases. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use for verify, run the checks, are we done, test coverage, or confirm this works.
---

# Guided Verify

## Overview

Turn “it looks done” into “we have evidence it works.”

**Core contract**
- AI runs the exact verification commands, auto-applies the minimal fix for any failure, and re-runs until green (max 3 fix loops).
- AI edits the codebase directly when fixes are needed.
- AI reports commands run + results as evidence at the end.

This is the final gate of the guided family.

## Project Memory (self-regenerative)

Load `.grok/project-memory.md` or `.kiro/project-memory.md` or `AGENTS.md` first, plus `docs/repo-map.json` when present. Prefer its `test_commands` over guessing. Use known test commands, scripts, and conventions. Update memory only when a new high-value verification fact appears (e.g. the real way this project runs e2e). Prefer writing into `AGENTS.md` when running in OpenCode.

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

## OpenCode support

Works natively in OpenCode via the Agent Skills standard. Install to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project); also under `.claude/skills/`.

**Pairing with OpenCode agents**

| OpenCode agent | How to use this skill |
|----------------|-----------------------|
| **Plan** | Safe for listing and interpreting verification results (read-only). |
| **Build** | Use when fixes are needed; AI applies them and re-runs. |

Show exact commands the human should run in the terminal. Update known test/verification commands into `AGENTS.md` or project memory so future sessions stay accurate.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-verify` or `@guided-verify`. Prefer updating `AGENTS.md`.

## Core Rules

1. **AI runs checks + auto-fixes; reports evidence. This rule is absolute.**
   - Edit the codebase directly when a fix is needed.
   - Run commands with the execution tool; never ask the human to run them.
   - On failure: diagnose, apply the minimal fix, re-run only the failed check (max 3 loops, then report blocker).

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
7. **React audit (React projects only)** — `python ~/.guided/scripts/guided_run.py react-doctor --repo <dir> --scope changed --blocking error` (pinned binary auto-downloads on first use; SKIP when not React/offline → note in one line and continue). FAIL routes back to `guided-coding` like any red check; stale-green rule applies.
8. **Growth watch (infra touched)** — when the change touched infra files (Dockerfile, compose, wrangler, migrations, queue/cron config), run `python ~/.guided/scripts/guided_run.py growth --repo <dir>`. If it recommends an audit, append 3 lines (top gaps + recommendation) and point to `guided-infra`. Cooldown: automatic runs skip when `growth.last_audit` in the repo-map is under 14 days old (explicit asks always run).
9. **PHP audit (PHP projects only)** — `python ~/.guided/scripts/guided_run.py php-audit --repo <dir> --scope changed --blocking error` (runs only auditors the project already has; never installs; SKIP when not PHP / no php / no tools → note in one line and continue). FAIL routes back to `guided-coding` like any red check; stale-green rule applies.

Framework-aware checks (Django, Laravel, Next.js, etc.) activate automatically when the project type is clear from memory or files.

## Accuracy gates (prove the tests themselves)

Green suites can lie. Run the gate that matches the change; thresholds come from the Plan IR `accuracy` block (defaults below):

1. **Mutation gate (test-the-tests)** — scoped to touched business logic only, never the whole repo.
   - PHP: `vendor/bin/infection --filter=<touched files> --min-msi=<n> --threads=4` (default min 70 MSI on covered code).
   - React/TS: `npx stryker run` with `coverageAnalysis: perTest`, `mutate` limited to touched files, `break` threshold from plan (default 50, raise toward 75).
   - Each survived mutant → write the missing test, re-run. Use incremental mode in CI.
2. **Contract gate (the seam)** — when request/response shape changed or a consumer reads new fields.
   - Full: Pact consumer test (React, `PactV4` + `MatchersV3`) + provider `Verifier` replay against real PHP; `can-i-deploy` before release. Nullable fields need explicit `nullValue()` matchers.
   - Light (same repo, one consumer): backend asserts exact JSON shape + frontend fixture mirrors it; one contract test compares fixture vs live response.
3. **Architecture gate (shape, not behavior)** — when layers, dependencies, or conventions are touched.
   - PHP: `vendor/bin/deptrac analyse` (controllers→services→repositories, domain framework-free, no cycles). Baseline legacy debt with `skip_violations`, never new ones.
   - PHP alt: Pest `arch()` tests. React/TS: `dependency-cruiser` boundaries.
4. **Flake rule** — a test that passes 9/10 proves nothing. Fresh DB per test (transactions), seeded data, frozen time, no real network, no order dependence. Retry once to detect flakes; a flaky test FAILS the gate until fixed or quarantined with a tracked follow-up.

**Harness as the Heart + package-scoped verification**
When the change involves an agent, multi-step tool use, large/monorepo code, or Harness plugins:
- Prefer package-scoped or targeted test commands over full-suite runs.
- Optionally use official DeepSeek Harness commands or Minimal mode for verification.
- Same automation contract: AI runs the commands and applies fixes directly.

## Workflow

1. **Load context + deterministic gates**
   Memory + what just changed (diff, file list, or recent edits).
   - If a Plan IR exists: run `python ~/.guided/scripts/guided_run.py validate-plan <plan.json> --changed <touched files>` (or `verify --plan` to run the full harness). A FAIL (or blast-radius drift) blocks the green declaration — route back to `guided-coding` first.
   - Confirm touched files ⊆ planned blast radius; flag drift as a finding.

2. **Run the verification plan (prefer the harness)**
   `python ~/.guided/scripts/guided_run.py verify --repo <dir> [--plan <plan.json>]` runs the ladder + planned accuracy gates and writes a JSON receipt (exit 0 = PASS).
   Run the relevant commands in order, capturing output for each (harness does this; manual runs must match it).
   - React projects: run the react-doctor gate (checklist item 7) alongside the ladder — its FAIL routes back to guided-coding.
   - PHP projects: run the php-audit gate (checklist item 9) alongside the ladder — its FAIL routes back to guided-coding. Registered PHP MCPs (`phpstan_analyze`, `phpcs_check`, Boost tools) may assist exploration mid-verify, but only harness receipts count as evidence.
   - Infra touched: run the growth watch (checklist item 8) and include its recommendation in the close report.

3. **On failure (error-count rule)**
   - Diagnose the failure (build-error-resolver style).
   - Apply the complete minimal fix directly.
   - Re-run only the failed check.
   - Track the error count: keep fixing while it reaches a new minimum (max 3 loops). If two consecutive rounds do not reduce it, stop and report the blocker truthfully — never disguise it.
   - Stale-green rule: any edit invalidates all prior green outputs. Never report an old PASS as current evidence; re-run after every fix. A non-zero exit is never success.

4. **Close**
   When the relevant checks are green, report the short Done checklist with evidence:

    ```
    Done?
    - [x] Relevant tests / checks are green (outputs below)
    - [x] Database invariants hold (if any)
    - [x] Events use Transactional Outbox (if any)
    - [x] Changes applied + verified by AI
    ```

   Then stop. Do not invent extra work.

## CI/CD pipelines (when asked)

When the human asks for a CI/CD pipeline, GitHub Actions, or “what should run on push/PR”:

1. Load the reference: `references/ecc-ci-cd.md`
2. Detect the project's real package manager, test scripts, and language from project memory / codebase.
3. Create the **smallest complete pipeline** that matches the project (usually the test job first) by writing `.github/workflows/ci.yml` directly.
4. Run available local validation (or `actionlint` if present) and fix until green.

## Output format (three separated claims — never conflate)

Pin the revision first: `git rev-parse --short HEAD` (or state `uncommitted` when nothing is committed).

```markdown
## Verify — <short-sha or uncommitted>

1. Checks (tool output only):
   - `npm test -- createOrder` → PASS (12 passed)
   - `npx tsc --noEmit` → clean
   - `npm run lint` → clean
   - `react-doctor (changed)` → clean / N errors (React only)
   - `php-audit (changed)` → clean / N errors + M warnings (PHP only)

2. Review (static findings): none / [fixed CRITICAL file:line …]

3. Manual (needs a human): <only if perceptual/manual review is required, else `n/a`>

Done?
- [x] Relevant tests / checks are green (outputs above, current revision)
- [x] Database invariants hold (if any)
- [x] Events use Transactional Outbox (if any)
- [x] Changes applied + verified by AI
```

On failure:

```markdown
## Failure → Fixed

Command: `npm test -- createOrder`
Problem: …
Fix applied in `src/orders/cancelOrder.ts:34-41`:
```ts
// exact code applied
```
Re-ran: PASS.
```

## Anti-patterns

- Asking the human to run checks or type fixes.
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
| “Infra/scaling growth needs a roadmap” | → `guided-infra` |
| All relevant checks green | → Stop. Loop is closed. |

**Typical happy path (automation loop)**
```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```

**Cleaning path**
```
guided-docs → guided-refactoring → guided-verify
```

## Resources

- Reuse Ponytail and quality rules from guided-coding.
- Project memory should eventually record the project’s real test and CI commands so verification stays fast and accurate.
