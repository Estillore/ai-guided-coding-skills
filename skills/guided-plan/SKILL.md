---
name: guided-plan
description: Write a short or full testable plan and stop. Use for plan, architecture, phased plan, or decide the structure first. Emits Plan IR and runs validate-plan when the host can write and run a shell. Does not implement and does not auto-chain. Works in Kiro, Grok, OpenCode, and Zed.---

# Guided Plan

## Overview

Force a short, high-quality plan before implementation. This prevents wasted coding.

**Core contract**
- AI outputs the complete minimal plan (goals, constraints, structure, key decisions, test strategy, blast radius).
- AI updates `docs/guided-memory.md` with new architecture facts.
- Stop after the plan. Do not implement and do not invoke another guided phase.

This skill sits between understanding and implementation:

- `guided-docs` → understand
- `guided-plan` → decide structure and approach (this skill)
- `guided-coding` → implement
- `guided-refactoring` → clean later if needed
- `guided-review` / `guided-verify` → close the loop



## Vanilla PHP gate

If `framework.name` is `vanilla-php`, or the repo matches `docs/vanilla-php.md`:

- Run `python ~/.guided/scripts/guided_run.py php-trace --repo . --entry <script>` and use its edges. Do not read whole files to discover includes.
- Do not edit until `docs/repo-map.json` has `php.call` in the form `entry:line -> include:function:line -> sql-or-redirect`.
- Missing `php.call` stops the edit. Say so and return to `guided-docs`.

## Done gate

Follow `docs/family-contract.md`. This skill is done only when all of these hold:

- The exclusive trigger matched this skill, not a neighbor.
- Blast radius was declared before any edit.
- The evidence line is present: `EVIDENCE: <command or artifact> -> <PASS|FAIL|SKIP> (<why>)`.
- The next skill is named in one line, then stop. Do not auto-chain.


## Project Memory (self-regenerative)

Before planning, check for project memory:

- Read `docs/guided-memory.md` when it exists. Also read `docs/repo-map.json`.
- Fallbacks for reading only: `.grok/project-memory.md`, `.kiro/project-memory.md`, `docs/project-notes/key_facts.md`. Do not append a project-memory section to `AGENTS.md`. If `AGENTS.md` exists and has no pointer, add one line that names `docs/guided-memory.md`.

**Memory health check (quick)**  
Note whether useful memory was found. If missing or very thin, create or expand it after the first useful discovery.

**If present** → load it first and treat it as known ground truth. Do not re-discover known architecture.

**Self-regeneration**  
After a useful planning session that reveals new architecture facts, decisions, or constraints, update `docs/guided-memory.md`. Keep entries short and high-value only. High-value facts (framework, structure style, source of standards) can be written without confirmation.

### Memory file format (keep it tiny)

```markdown
# Project Memory (guided skills)
Last updated: YYYY-MM-DD

## Framework
- Name + major version: ...
- Source of standards: official docs (preferred) | project convention | canonical

## Architecture Snapshot
- Entry points: ...
- Domain / layers: ...
- Dependency direction: ...
- Structure style: feature-sliced / clean-layered / framework-default / custom

## Key Conventions
- ...

## Decisions & Gotchas
- ...

## Open Questions
- ...
```

## Kiro IDE support

Works in every Kiro environment via the Agent Skills standard. Install to `~/.kiro/skills/` (global) or `.kiro/skills/` (workspace). Type `/` to invoke.

**Pairing with Kiro built-in workflows**

| Kiro workflow | How to use this skill |
|---------------|-----------------------|
| **Spec** | After requirements are clear, use `/guided-plan` to lock structure and decisions before tasks are generated |
| **Quick Spec** | Same — keep the lighter workflow from jumping straight into code |
| **Plan** | Primary home for this skill |
| **Bug Fix** (Debug) | Use for any non-trivial fix that needs a short plan before changing code |
| **Default** | Use whenever a change is large enough to benefit from a short plan first |

## OpenCode support

Works natively in OpenCode via the Agent Skills standard. Install to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project); also works under `.claude/skills/`.

**Pairing with OpenCode agents**

Select the `guided-plan` primary. It may overwrite `docs/plans/current.json` and the `## Guided` section of `AGENTS.md`. Do not create another plan file. It does not edit source. When the plan is done, tell the human to switch to `guided-coding`. Then stop.

Shell access on that agent is an inspection allowlist.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-plan` or `@guided-plan` on the Guided Plan profile. On the Zed Guided Plan profile, deliver the plan in chat and stop. That profile cannot write files or run a terminal, so it does not run validate-plan. Record facts in `docs/guided-memory.md` only after the human switches to a profile that can write.

## Documentation is Truth (highest priority for every recommendation)

Plans must produce code that a teammate will recognize as “the standard way the official docs recommend.”

**Rule**  
Before recommending any structure, pattern, or integration that involves a library or framework, treat the **current official documentation** of that library/framework as the source of truth (Auth.js, Socket.io, Prisma, Next.js, NestJS, DeepSeek Harness, Cordis, etc.).

**Priority order (strict):**

1. **Official documentation of the specific libraries and framework being used**  
   For agent harness work, DeepSeek Harness + Cordis official docs take priority.
2. **Project’s own consistent structure** (Adaptability + memory)
3. **Canonical structure** (only when 1 and 2 are absent)  
   - Frontend: FSD-inspired hybrid (`app/` + `features/` + `entities/` + `shared/`)  
   - Backend: feature modules with internal clean layers (`domain` → `application` → `infrastructure` → `interface`)  
   - Vanilla: same canonical structure.

Record the chosen source of standards in project memory. When Harness is recommended, note the suggested mode or key plugins.

## Adaptability (when planning inside an existing codebase)

1. Load project memory + `docs/repo-map.json` first (fallbacks: `.kiro/repo-map.json`, `.grok/repo-map.json`).
2. Detect framework + version, then discover entry points, layer boundaries, dependency direction, and relevant conventions if memory is incomplete.
3. Summarize only what matters for the current plan (a few bullets). Include which source of standards is being used.
4. All plans must follow the Documentation is Truth priority order above.
5. Update memory if new high-value decisions are made.

## Semantic retrieval (capability-aware)

- Prefer a host-provided LSP or equivalent semantic tool for symbol discovery, definitions, references, implementations, hover, and call hierarchy.
- Read only returned ranges plus the smallest surrounding context; use `glob`/`grep` for strings, configuration, generated files, and unsupported languages.
- Detect capability before use. If unavailable, fall back to codemap + `glob`/`grep` + ranged `read`, and never claim LSP was used.
- Treat semantic results as navigation evidence, not verification; run the relevant project checks after changes.
- Shell inspection (`git log`, `git diff`, `rg`, `wc`) is a separate capability from LSP and is host-dependent: the OpenCode planner and architect have a read-only allowlist, other hosts and the Zed `Guided Plan` profile do not. Detect it, never assume it.

## Core Rules

1. **AI outputs the complete minimal plan and stops. This rule is absolute.**
   - Present a full short plan, including structure and key decisions.
   - Update `docs/guided-memory.md`.
   - When the host can write `docs/plans/*.json` and run a shell, write the Plan IR and run validate-plan until it prints `PLAN IR: PASS`.
   - Stop after the plan. Do not implement and do not invoke another guided phase. Recommend `guided-coding` or `guided-refactoring`, then stop.

2. **Documentation is Truth** (official docs of every library → project convention → canonical).

3. **Keep plans testable; match depth to need.**  
   - Short mode: one page or less.  
   - Full mode: phases + risks are allowed when the feature warrants it.  
   - Every plan should make it obvious what “done” looks like and how it will be verified.

4. **Ponytail on architecture.**  
   - Prefer the simplest structure that satisfies the requirements and the winning source of standards.  
   - Reject unnecessary layers, abstractions, or new dependencies.

5. **Database invariants must be planned.**  
   When a domain rule must always be true (exactly one owner, unique constraint, non-negative value, etc.), the plan must include a database-level enforcement, not only application checks.

6. **Reliable events use Transactional Outbox.**  
   When a write must be followed by an event (WebSocket, queue, EventBus), default to the outbox pattern so a crash cannot leave the system with committed data but no event.

7. **Decision log (no gate).**
   For critical or non-obvious choices (permission model, invariant, event strategy, architecture decision), add a one-line rationale inline. Never stop to quiz; keep moving.

8. **Plan the accuracy gates.**
   Every non-trivial plan fills the Plan IR `accuracy` block: mutation scope + thresholds for touched business logic (Infection/Stryker), contract tests for any changed request/response shape (Pact or fixture-vs-live), arch rules for any layer/dependency touch (Deptrac / Pest `arch()` / dependency-cruiser). Trivial slices may set only thresholds; never skip silently — record `n/a` with a reason.

9. **Terse senior voice.** Short, direct, no fluff.

## Modes

### 1. Short plan mode (default)

For most features and bug fixes.

**Output shape**
- Goal (1–2 sentences)
- Constraints / non-goals
- Minimal files and changes
- Key decisions (with one-line rationale)
- Test strategy (what will prove it works)
- Accuracy gates (mutation scope/thresholds, contract tests, arch rules — the Plan IR `accuracy` block)
- Definition of done

### 2. Architecture mode

Activate when the change is large, cross-cutting, or the human asks for architecture / ADR / “how should we structure this?”.

**Extra content** (drawn from ECC architect thinking)
- Current architecture snapshot (from memory + discovery) — measured, not recalled. Use `git log`/`git blame` to learn *why* the code looks as it does before proposing changes to it.
- Proposed structure (layers, boundaries, dependency direction)
- Key trade-offs and the recommended decision, plus its exit cost (how hard to undo)
- When scale or maintainability is the question, a per-feature growth table: coupling and scalability signal per feature, ranked by signal strength
- Migration or sequencing notes if the change is not green-field
- Still keep it short — architecture mode is denser, not longer for its own sake

**Harness as the Heart + Large Codebase rules**
- When the plan involves agents, multi-step tools, or a large/monorepo codebase, treat DeepSeek Harness as the exploration and verification engine.
- Force a short map of the *relevant slice only* (package, ownership, entry points).
- Declare expected blast radius (files touched). Default to 1–3 files. Larger changes need explicit justification.
- Include a short recommended Harness composition (mode + key constraints) using official patterns.
- Keep the same contract: output the plan and stop. Never leave Harness output as the only artifact.

### 3. Full plan mode (ECC-style)

Activate when the user says “full plan”, “implementation plan”, “with risks”, “phased plan”, or when the feature is clearly large and needs a real implementation roadmap.

**Output shape** (adapted from ECC planner):

```markdown
# Implementation Plan: [Feature Name]

## Overview
[2-3 sentence summary]

## Requirements
- [Requirement 1]
- [Requirement 2]

## Architecture Changes
- [Change 1: file path and description]
- [Change 2: file path and description]

## Implementation Steps

### Phase 1: [Phase Name]
1. **[Step Name]** (File: path/to/file.ts)
   - Action: Specific action to take
   - Why: Reason for this step
   - Dependencies: None / Requires step X
   - Risk: Low/Medium/High

### Phase 2: ...

## Testing Strategy
- Unit tests: ...
- Integration tests: ...
- E2E tests: ...

## Risks & Mitigations
- **Risk**: ...
  - Mitigation: ...

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

**Rules for Full mode**
- Every phase must be independently mergeable and deliver value
- Exact file paths and function names required
- Risks must be explicit; high-risk steps need mitigations
- Prefer extending existing code over rewriting
- Never show a plan that requires all phases before anything works

### 4. Human Design Support mode

Activate when the human already has a design or structure in mind. Trigger phrases include:
- “I have a design in mind…”
- “help me integrate this…”
- “this is the way I was thinking…”
- “support my design / don’t change the architecture”
- “I already decided the structure…”

**Behavior (strict)**
1. Accurately restate the human’s design in 3–6 bullets. Do not improve or replace it.
2. Map it onto the existing codebase + official docs (Documentation is Truth).
3. Surface only friction points, missing pieces, risks, or tiny adaptations needed.
4. Never propose a different architecture or “better” structure unless the human explicitly asks for critique.
5. Help the human refine *their* plan. Write that plan when the host can write. Do not implement it.

**Output shape**
- Your design (restated)
- How it maps to the current codebase / official docs
- Friction / gaps / risks only
- Suggested minimal adaptations (if any)
- Definition of done for *this* design

This mode exists to keep the AI in the assistant seat and the human as the owner of the design.

## Workflow

1. **Load context**  
   Memory + Adaptability summary if needed. Restate the goal in 1–2 sentences.

2. **Frame the constraints**  
   Convert the goal into measurable targets: growth horizon, load, latency, availability, cost ceiling, security. Anything the human never specified goes into `nfr.assumptions` — name it, never assume it silently. "It should scale" is not a requirement; "20k orders/day in 12 months, p95 < 300ms, 2 devs" is.

3. **Clarify only if necessary**  
   Ask at most 1–2 sharp questions when the scope or constraints are ambiguous. Prefer making a reasonable assumption and stating it.

4. **Show the complete plan**  
   Choose Short (default), Architecture, Full, or **Human Design Support** mode as appropriate. Apply Ponytail ruthlessly.  
   When the human already has a design, prefer Human Design Support mode.
5. **Apply it + Plan IR gate (mandatory)**
   Save the final plan to memory. Overwrite `docs/plans/current.json` matching `references/plan-schema.json` (shape example: `examples/plan-ir.example.json — structural reference only, never copy its facts`) and run the validator:
   `python ~/.guided/scripts/guided_run.py validate-plan docs/plans/<slug>.json` (harness entry; raw script lives at `scripts/` in the skills repo).
   When the host can write `docs/plans/*.json` and run a shell, write the Plan IR and run validate-plan until it prints `PLAN IR: PASS`. `guided-builder` must not start on a FAIL, and never on a missing IR.
   On the Zed Guided Plan profile, deliver the plan in chat and stop. That profile cannot write files or run a terminal, so it does not run validate-plan.
   Carry the architect's `Decision` block into `key_decisions` (with `exit_cost`), `invariants`, `accuracy.arch_rules`, and `nfr`. If you overrule the architect, record the reason in one line — silence is not an override.
   Stop after the plan. Do not implement and do not invoke another guided phase. Recommend `guided-coding` (or `guided-refactoring` for cleanup).

6. **Update memory** (if new decisions are high-value)

7. **Hand off**  
   Actively recommend the next skill based on the situation:

| Human situation | Recommend |
|-----------------|-----------|
| Plan is ready, time to implement | → `guided-coding` |
| Plan is about cleaning messy existing code | → `guided-refactoring` |
| Still missing mental model of a library or area | → `guided-docs` |
| Plan is done and code already exists | → `guided-review` then `guided-verify` |
| The whole app is growing and needs a scale/maintainability audit | → `guided-infra` (repo-wide, infra + evolution ladder) — not this skill |

Always state the recommendation clearly.

## Connected workflow (automation loop)

```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```

Recommend `guided-refactoring` after coding, then stop. Do not auto-chain. Review and verify run only when the human invokes them.

Harness guidance surfaces passively inside guided-plan (Architecture mode) and guided-coding (Harness Power Mode) when the work is agentic. No separate skill required.

## Style

- Bullet points and short paragraphs only.
- Prefer concrete file and module names over abstract diagrams unless a tiny ASCII sketch truly helps.
- Explicitly reject over-engineering.
- One-sentence rationale for every important decision is enough.

## Anti-patterns

- Long design documents or multi-page ADRs by default.
- Inventing new architectural layers the project does not already use.
- Implementing source code from this skill.
- Auto-chaining into `guided-coding`.
- Proceeding straight to code without a plan when the change is non-trivial.
- Vague plans that cannot be turned into tests or a clear definition of done.

## Example output style (Normal mode)

```markdown
## Plan: Add order cancellation

**Goal**  
Allow a user to cancel a pending order. Status becomes `cancelled` and inventory is released.

**Non-goals**  
Refunds, partial cancellation, admin override.

**Minimal changes**
- `src/orders/cancelOrder.ts` (new)
- `src/orders/orderRepository.ts` (add status update + inventory release)
- Test: `cancelOrder.test.ts`

**Key decisions**
- Keep the use-case pure; repository owns the transaction.
- Only `pending` orders may be cancelled (explicit guard).

**Test strategy**
- Happy path: pending → cancelled + inventory restored
- Rejection: already shipped → clear error

**Done when**
- Tests green, no new dependencies, matches existing order service style.
```

## Resources

- Reuse Ponytail ladder and quality rules from guided-coding.
- Project memory is the main long-lived knowledge store.
