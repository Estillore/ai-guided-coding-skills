---
name: guided-plan
description: Produce a short or full testable plan before any code. AI shows the complete plan (short mode or full ECC-style with phases, risks, mitigations, success criteria); the human types or rewrites their own version. Absorbs architect-level thinking. Uses codebase mapping and self-regenerative project memory. Includes passive DeepSeek Harness guidance for agent and multi-step tool plans. Works in any Kiro workflow (especially Plan and Spec), in Grok, in OpenCode, and in Zed. Use for guided plan, full implementation plan, architecture, short plan before coding, ADR, phased plan, or decide the structure first.
---

# Guided Plan

## Overview

Force a short, high-quality plan before implementation. This prevents wasted coding and keeps the human in control of the design.

**Core contract**
- AI shows the complete minimal plan (goals, constraints, structure, key decisions, test strategy).
- Human types or rewrites their own final version.
- AI never edits the codebase or creates plan files unless the human explicitly asks.

This skill sits between understanding and implementation:

- `guided-docs` → understand
- `guided-plan` → decide structure and approach (this skill)
- `guided-coding` → implement
- `guided-refactoring` → clean later if needed
- `guided-review` / `guided-verify` → close the loop

## Project Memory (self-regenerative)

Before planning, check for project memory:

- Preferred: `.grok/project-memory.md` or `.kiro/project-memory.md` (Kiro) or `AGENTS.md` (OpenCode)
- Fallbacks: `docs/project-notes/key_facts.md`, `CLAUDE.md`

**If present** → load it first and treat it as known ground truth. Do not re-discover known architecture.

**Self-regeneration**  
After a useful planning session that reveals new architecture facts, decisions, or constraints, update the memory file (prefer `.kiro/project-memory.md` inside Kiro, or a Project Memory section in `AGENTS.md` inside OpenCode). Keep entries short and high-value only.

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

| OpenCode agent | How to use this skill |
|----------------|-----------------------|
| **Plan** | Primary home. Use guided-plan to produce the testable plan while staying read-only. |
| **Build** | Use only after the plan is accepted; switch to guided-coding for the implementation steps. |

Prefer updating `AGENTS.md` (OpenCode `/init`) or `.grok/project-memory.md` so later sessions inherit the architecture decisions.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-plan` or `@guided-plan`. Prefer updating `AGENTS.md` for project memory.

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

1. Load project memory first.
2. Detect framework + version, then discover entry points, layer boundaries, dependency direction, and relevant conventions if memory is incomplete.
3. Summarize only what matters for the current plan (a few bullets). Include which source of standards is being used.
4. All plans must follow the Documentation is Truth priority order above.
5. Update memory if new high-value decisions are made.

## Core Rules

1. **AI shows the complete minimal plan; human owns the final version.**  
   - AI may present a full short plan, including structure and key decisions.  
   - The human must type or consciously rewrite their own plan.  
   - Never create or edit plan/ADR files unless the human explicitly requests it.

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

7. **Active Confirmation on key decisions.**  
   When the plan contains a critical design choice (permission model, invariant, event strategy, library integration boundary), after showing the plan the AI asks one short question.  
   - Correct answer → continue.  
   - “I don’t know” or wrong answer → AI gives a one-sentence explanation, then asks the human to restate it. Only then continue.  
   This keeps ownership and learning high without creating a blocker.

8. **Terse senior voice.** Short, direct, no fluff.

## Modes

### 1. Short plan mode (default)

For most features and bug fixes.

**Output shape**
- Goal (1–2 sentences)
- Constraints / non-goals
- Minimal files and changes
- Key decisions (with one-line rationale)
- Test strategy (what will prove it works)
- Definition of done

### 2. Architecture mode

Activate when the change is large, cross-cutting, or the human asks for architecture / ADR / “how should we structure this?”.

**Extra content** (drawn from ECC architect thinking)
- Current architecture snapshot (from memory + discovery)
- Proposed structure (layers, boundaries, dependency direction)
- Key trade-offs and the recommended decision
- Migration or sequencing notes if the change is not green-field
- Still keep it short — architecture mode is denser, not longer for its own sake

**Harness passive note**  
When the plan involves building or strengthening an agent, multi-step tool use, or long-running agentic behavior, include a short recommended DeepSeek Harness composition (mode + key plugins or profile) using official patterns. Keep it minimal and under the same “AI shows, human owns” contract.

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
5. Help the human refine *their* plan so they can type the final version themselves.

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

2. **Clarify only if necessary**  
   Ask at most 1–2 sharp questions when the scope or constraints are ambiguous. Prefer making a reasonable assumption and stating it.

3. **Show the complete plan**  
   Choose Short (default), Architecture, Full, or **Human Design Support** mode as appropriate. Apply Ponytail ruthlessly.  
   When the human already has a design, prefer Human Design Support mode.
4. **Human owns it**  
   Tell the human to type or rewrite the final plan in their own words / file.  
   Offer to refine after they paste their version.

5. **Update memory** (if new decisions are high-value)

6. **Hand off**  
   Actively recommend the next skill based on the situation:

| Human situation | Recommend |
|-----------------|-----------|
| Plan is ready, time to implement | → `guided-coding` |
| Plan is about cleaning messy existing code | → `guided-refactoring` |
| Still missing mental model of a library or area | → `guided-docs` |
| Plan is done and code already exists | → `guided-review` then `guided-verify` |

Always state the recommendation clearly.

## Connected workflow

```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
                 ↘ guided-refactoring ↗
```

Harness guidance surfaces passively inside guided-plan (Architecture mode) and guided-coding (Harness Power Mode) when the work is agentic. No separate skill required.

## Style

- Bullet points and short paragraphs only.
- Prefer concrete file and module names over abstract diagrams unless a tiny ASCII sketch truly helps.
- Explicitly reject over-engineering.
- One-sentence rationale for every important decision is enough.

## Anti-patterns

- Long design documents or multi-page ADRs by default.
- Inventing new architectural layers the project does not already use.
- Editing the codebase or creating files without explicit request.
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
