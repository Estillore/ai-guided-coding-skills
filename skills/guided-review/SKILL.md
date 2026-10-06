---
name: guided-review
description: Quality and security findings only. Use for review, what should I strengthen, or before merge. Report file:line findings that pass the confidence gate. Running the suite is guided-verify. Works in Kiro, Grok, OpenCode, and Zed.---

# Guided Review

## Overview

Give a clear, actionable review and apply the important fixes immediately — without waiting for the human to type them.

**Core contract**
- AI performs the review (quality + security), applies minimal fixes for CRITICAL/HIGH directly, and reports MEDIUM/LOW as follow-ups.
- AI edits the codebase directly.
- AI reports each fix with file:line + failure mode prevented.

This skill is the quality and security gate of the guided family.


## Done gate

Follow `docs/family-contract.md`. This skill is done only when all of these hold:

- The exclusive trigger matched this skill, not a neighbor.
- Blast radius was declared before any edit.
- The evidence line is present: `EVIDENCE: <command or artifact> -> <PASS|FAIL|SKIP> (<why>)`.
- The next skill is named in one line, then stop. Do not auto-chain.


## Connected workflow & hand-offs

This skill is the quality and security gate of the guided family. Actively recommend the right next (or previous) skill based on what the human is facing:

| Human situation | Recommend |
|-----------------|-----------|
| “I still need to understand the area better” | → `guided-docs` |
| “Findings require structural cleanup” | → `guided-refactoring` |
| “Findings require new implementation” | → `guided-coding` |
| “Fixes are typed — confirm everything works” | → `guided-verify` |
| “Need a short plan before fixing large issues” | → `guided-plan` |
| “Infra is growing — scaling/reliability roadmap” | → `guided-infra` |

**Typical path after implementation (automation loop)**
```
guided-coding → guided-refactoring → guided-review → guided-verify
```
`guided-refactoring` runs before review so review checks already-cleaned code.

Harness as the Heart: when reviewing agent, plugin, multi-step tool, or large-codebase changes, apply official DeepSeek Harness + Cordis patterns as the source of truth. Surface blast-radius and ownership concerns. Harness output is never treated as the final production source of truth.

## Project Memory (self-regenerative)

Before reviewing, check for project memory:

- Read `docs/guided-memory.md` when it exists, plus `docs/repo-map.json`.
- Fallbacks for reading only: `CLAUDE.md`, `docs/project-notes/`.

Respect the project's own conventions. Update `docs/guided-memory.md` only when the review surfaces a new high-value gotcha. If `AGENTS.md` exists and has no pointer, add one line that names `docs/guided-memory.md`. Do not append a project-memory section to `AGENTS.md`.

## Semantic retrieval (capability-aware)

- Prefer a host-provided LSP or equivalent semantic tool for symbol discovery, definitions, references, implementations, hover, and call hierarchy.
- Read only returned ranges plus the smallest surrounding context; use `glob`/`grep` for strings, configuration, generated files, and unsupported languages.
- Detect capability before use. If unavailable, fall back to codemap + `glob`/`grep` + ranged `read`, and never claim LSP was used.
- Treat semantic results as navigation evidence, not verification; run the relevant project checks after changes.

## Kiro IDE support

Works in every Kiro environment. Install to `~/.kiro/skills/` or `.kiro/skills/`. Type `/` to invoke.

**Pairing with Kiro built-in workflows**

| Kiro workflow | How to use this skill |
|---------------|-----------------------|
| **Spec** | After implementation tasks are done, before closing the spec |
| **Quick Spec** | Same — final quality + security pass |
| **Plan** | When the plan has been implemented and needs a review |
| **Bug Fix** (Debug) | After the fix is written, to catch remaining quality or security issues |
| **Default** | Any time the human asks “is this solid?” or “what should I strengthen?” |

## OpenCode support

Works natively in OpenCode via the Agent Skills standard. Install to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project); also under `.claude/skills/`.

**Pairing with OpenCode agents**

The `guided-review` primary applies fixes. The `guided-reviewer` subagent is read-only and does not edit. Auto-fix CRITICAL and HIGH only when the active host can edit. Record facts in `docs/guided-memory.md`.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-review` or `@guided-review` on the Write profile. Auto-fix CRITICAL and HIGH only when the active host can edit. Record facts in `docs/guided-memory.md`.

## Core Rules

1. **Auto-fix CRITICAL and HIGH only when the active host can edit.**
   - Edit the codebase directly for must-fix findings.
   - MEDIUM/LOW: fix if trivial (≤3 lines), otherwise list as follow-ups.
   - Report each applied fix with exact file:line + one-sentence why.

2. **Confidence filter (strict).** Only report issues where confidence > 80%.  
   Pre-report gate — all four must be yes, otherwise drop or demote:
   1. Can I cite the exact file and line?
   2. Can I describe the concrete failure mode (input + state + bad outcome)?
   3. Have I considered surrounding context / callers / existing guards?
   4. Is the severity defensible?  
   **Zero findings is acceptable and preferred when the code is clean.** Do not manufacture nits.

3. **Severity-ordered, actionable findings only.**  
   - CRITICAL (security, data loss, auth bypass) — must fix  
   - HIGH (bugs, missing error handling that can fail in production)  
   - MEDIUM (performance, maintainability that will bite soon)  
   - LOW (style, docs) — only if they violate project conventions  
   HIGH/CRITICAL require proof: exact snippet, concrete failure scenario, and why existing guards do not catch it.

4. **Ponytail on every suggested fix.** Prefer the smallest change that removes the problem.

5. **Terse senior voice.** Short, direct, no fluff.

## Modes

### 1. Quality review (default)
Uses code-reviewer style thinking:
- Correctness and edge cases
- Error handling and failure modes
- Clarity and structure
- Project convention mismatches
- Unnecessary complexity (Ponytail violations)
- **Feature / Module Cohesion** — Flag files that mix unrelated business concerns (e.g. Authentication logic mixed with Inventory logic) as a maintainability issue, especially when the file is large.
- **Layer discipline** — controllers/handlers must not touch repositories or the DB directly; domain must stay framework-free (no HTTP/ORM imports in domain code). Flag the exact `use`/import line.
- **DTO discipline** — API boundaries accept/return DTOs or explicit shapes, never persistence entities; a renamed field that a consumer reads is CRITICAL.
- **Missing database invariants** — domain rules that must always hold (exactly one owner, unique email, non-negative balance, etc.) but are only enforced in application code. Prefer DB constraints.
- **Missing Transactional Outbox** — when a write is followed by an event publish (WebSocket, queue, EventBus) without an outbox, flag the crash window.

### 2. Security review
Uses security-reviewer style thinking:
- Trust boundaries and input validation
- Auth / authorization gaps
- Injection, XSS, CSRF, secret exposure
- Insecure defaults and missing safeguards
- Data leakage
- Privilege escalation paths that rely only on application checks

### 3. Combined review
Run both when the human asks for a full scan or when the change touches auth, payments, user data, or external input.

## React lane (react-doctor evidence — external tool, never bundled)

When the code under review is a React project, deterministic scanner evidence feeds the review. The skill stays the judge:

1. **Detect** — React runtime dep in package.json (react/next/preact/React Native/Expo). Not React → skip this lane, one line at most.
2. **Provision + scan via the harness** (downloads the pinned binary on first use; degrades gracefully offline):
   `python ~/.guided/scripts/guided_run.py react-doctor --repo <dir> --scope full --blocking error`
   - `SKIP` (not React / no Node / no network) → continue skill-only, note why in one line.
   - Findings map to severity: `error` → CRITICAL/HIGH pipeline (auto-fix), `warning` → MEDIUM/LOW follow-ups — each still passes the confidence gate above before reporting.
   - Respect the repo's `doctor.config.*`; never re-implement react-doctor rules here — consume its JSON.

## Vanilla PHP bug review

On vanilla PHP, do not demand PHPStan above level 0 or Oxlint on inline script tags. Those are later rungs in `guided-refactoring`, not review failures.


On vanilla PHP, review the symptom include chain from `docs/vanilla-php.md`, not the whole repo. A finding outside that chain needs a reason. Blank pages, double includes, header-already-sent, and concatenated SQL in the chain outrank style nits. A structural mix (SQL or HTML in the case) is a `guided-refactoring` hand-off for that case only. Injection, a client-owned total, or a missing constraint stays in this review. Bootstrap findings are version mismatches (`data-toggle` on 5.x), a CDN next to a vendored copy, or a second bundle. Do not report a Bootstrap-free receipt as a defect when the project keeps it free.

If the interaction is a form post or a link, do not search for JavaScript. The result is the PHP that runs that request.

On a mixed router, the bugfix also extracts this case only: SQL to the service, markup to the view, case becomes a call. Do not rewrite the rest of the switch.

## PHP lane (deterministic auditors — external tools, never bundled)

When the code under review is a PHP project, deterministic auditor evidence feeds the review. The skill stays the judge:

1. **Detect** — `composer.json` at the repo root. Not PHP → skip this lane, one line at most.
2. **Scan via the harness** (runs only tools the project already has; never installs anything; degrades gracefully):
   `python ~/.guided/scripts/guided_run.py php-audit --repo <dir> --scope full --blocking error`
   - `SKIP` (not PHP / no php on PATH / no tools installed) → continue skill-only, note why in one line. A bare `composer.json` with zero tools is itself a follow-up: recommend installing phpstan + pint.
   - Findings map to severity: `error` class (phpstan, psalm-taint, deptrac, composer critical/high, warden) → CRITICAL/HIGH pipeline (auto-fix), `warning` class (pint, rector drift, composer medium/low) → MEDIUM/LOW follow-ups — each still passes the confidence gate above before reporting.
   - Respect the repo's configs (`phpstan.neon`, `psalm.xml`, `pint.json`, `rector.php`, `deptrac.yaml`, baselines); never re-implement auditor rules here — consume the receipt JSON.
   - Interactive complement (optional, never evidence): if PHP MCPs are registered (`guided_run.py mcp`), the agent may call `phpstan_analyze` / `phpcs_check` / Boost tools mid-review for exploration. MCP output is a lead — only harness receipts and re-run tool output enter the report.

## JS lane (oxlint evidence — external tool, never bundled)

When the code under review ships JavaScript assets — including vanilla-PHP projects whose page scripts are externalized to `.js` for CSP — deterministic linter evidence feeds the review. The skill stays the judge:

1. **Detect** — any `.js` / `.mjs` / `.cjs` asset. None → skip this lane, one line at most.
2. **Scan via the harness** (uses the project's own oxlint when it has one, else the pinned npx download; never installs into the project; never runs `--fix`; degrades gracefully offline):
   `python ~/.guided/scripts/guided_run.py js-lint --repo <dir> --scope full --blocking error`
   - `SKIP` (no JS / no Node / below the 20.19+ / 22.12+ floor / offline / the repo ships an evaluable oxlint config) → continue skill-only, note why in one line. A `SKIP` from the `ensure` step means the scan did not run; never restate it as a clean result.
   - Findings map to severity: oxlint `error` → CRITICAL/HIGH pipeline (auto-fix), `warning` → MEDIUM/LOW follow-ups — each still passes the confidence gate above before reporting.
   - **Never `--fix` from the review lane.** The receipt prints the fix hint; the agent applies the change deliberately, then re-runs the gate. A review that silently rewrote code is not a review.
   - Respect the repo's `.oxlintrc.*` / `oxlint.config.*`; never re-implement oxlint rules here — consume the receipt JSON.
3. **Coverage honesty** — read `inline_js_coverage` from the receipt. oxlint lints `.js/.mjs/.cjs` plus the `<script>` blocks of `.vue/.svelte/.astro`; a script body inside a `.php` template is invisible to it. A non-zero `inline_script_blocks` is a **roadmap item, not a review finding**: recommend `guided-refactoring` to externalize those blocks so the next change to them is actually gated. Do not report it as a defect in the code under review.

### Config gotcha (do not get this wrong)

Absent config, `no-undef` is a default-on correctness rule and fires on `document`, `window`, `setInterval` — every finding is then a false positive. The minimal correct `.oxlintrc.json` for a browser-targeted PHP project:

```jsonc
{
  "env": { "browser": true },
  // `plugins` REPLACES the default plugin set — all four must be listed.
  // Omitting any one silently disables its rules, including correctness ones.
  "plugins": ["eslint", "typescript", "unicorn", "oxc"],
  "categories": { "correctness": "error", "suspicious": "warn" }
}
```

When the receipt's `config` step reports no config found, say so before acting on any finding, and recommend the snippet above as a follow-up. The lane now writes that starter config itself when one is absent — it never overwrites an existing config, so a project that already tuned its rules keeps them.

Prefer the JSON form. The npx path deliberately refuses a repo that ships `oxlint.config.ts`/`.mts` or a `jsPlugins` entry, because oxlint *evaluates* those — a repo-authored one would run code on the reviewer's machine before any diagnostic exists. That refusal is a `SKIP`, not a finding: the fix is to install oxlint as a devDependency so the project supplies its own binary, not to remove the config.

## Infrastructure diff lane (in-diff safety only)

When the diff touches infra files (Dockerfile, compose, wrangler config, deploy/CI config, queue config):

- Run the deterministic growth scan: `python ~/.guided/scripts/guided_run.py growth --repo <dir> --no-memory`
- In-diff `critical`/`high` gaps (tracked `.env`, literal secret in compose) are review findings — apply the minimal fix (untrack, rotate, move to env/secret) per the core contract.
- `medium`/`low` gaps, and anything beyond the diff, are **not** review findings — they are roadmap items. Recommend `guided-infra` and stop.

## Workflow

1. **Load context**
   Project memory + the code under review (diff, changed files, or pointed paths — read directly, never ask for paste).

2. **Scan with confidence filters**
   Apply the pre-report gate. Produce only high-confidence findings, severity-ordered.

3. **Auto-fix CRITICAL/HIGH**
   Apply the minimal fix directly for each must-fix finding. For each use this format in the report:

    ```
    [SEVERITY] Short title
    File: path:line
    Issue: concrete description of the failure mode
    Why existing guards do not catch it: …
    Fix applied: [exact code applied]
    ```

4. **Follow-ups**
   List MEDIUM/LOW that were not auto-fixed (or were trivially fixed inline).

5. **Re-scan (error-count rule)**
   Re-scan only the changed parts to confirm fixes hold.
   Track open must-fix findings: keep fixing while the count reaches a new minimum (max 3 rounds). If two consecutive rounds do not reduce it, stop and report the remainder truthfully with file:line + risk.

6. **Close**
   Confirm remaining risk (if any) with evidence and recommend `guided-verify` and stop.
   If no important issues: say so in one sentence, recommend `guided-verify` and stop.

## Common false positives — never report these

- “Consider adding error handling” when the caller or framework already handles it
- Missing input validation on internal functions whose callers already validate
- Magic numbers that are well-known constants or obvious from context
- Function length for exhaustive switches, configs, or test tables
- Missing JSDoc on self-describing internal helpers
- Possible null when a guard or type narrowing is already present
- “Should use TypeScript” in a JavaScript-only project

## Anti-patterns

- Asking the human to type fixes.
- Manufacturing findings to look thorough.
- Dumping dozens of stylistic nits.
- Long lectures on theory.
- Suggesting large rewrites when a small fix is enough.
- Continuing to “improve” after the human has addressed the real issues.

## Example coaching style

**Good:**
```
[CRITICAL] Client-controlled total
File: src/orders/createOrder.ts:42
Issue: createOrder trusts input.total from the client — attacker can set any price.
Why existing guards do not catch it: no server-side recalculation; total is written directly.
Minimal fix:
```ts
const total = items.reduce((sum, i) => sum + i.price, 0);
```

[MEDIUM] Missing status guard on cancel
File: src/orders/cancel.ts:18
…
Next: guided-verify on this slice.

[CRITICAL] Concatenated SKU
File: public/save.php:3
Issue: sku from the request is interpolated into SQL.
Why existing guards do not catch it: no prepare on this path.
Fix applied: prepared insert; total computed server-side.
```

## Resources

- Reuse Ponytail and quality rules from guided-coding.
- Project memory keeps reviews consistent with the real architecture.
