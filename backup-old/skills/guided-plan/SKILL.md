---
name: guided-plan
description: Produce a short or full testable plan before any code. AI shows the complete plan (short mode or full ECC-style with phases, risks, mitigations, success criteria); the human types or rewrites their own version. Absorbs architect-level thinking. Uses codebase mapping and self-regenerative project memory. Works in any Kiro workflow (especially Plan and Spec) and in Grok. Use for guided plan, full implementation plan, architecture, short plan before coding, ADR, phased plan, or decide the structure first.
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

- Preferred: `.grok/project-memory.md` or `.kiro/project-memory.md` (Kiro)
- Fallbacks: `docs/project-notes/key_facts.md`, `AGENTS.md`, `CLAUDE.md`

**If present** → load it first and treat it as known ground truth. Do not re-discover known architecture.

**Self-regeneration**  
After a useful planning session that reveals new architecture facts, decisions, or constraints, update the memory file. Keep entries short and high-value only.

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

## Documentation is Truth (highest priority for every recommendation)

Plans must produce code that a teammate will recognize as “the standard way the official docs recommend.”

**Rule**  
Before recommending any structure, pattern, or integration that involves a library or framework, treat the **current official documentation** of that library/framework as the source of truth (Auth.js, Socket.io, Prisma, Next.js, NestJS, etc.).

**Priority order (strict):**

1. **Official documentation of the specific libraries and framework being used**
2. **Project’s own consistent structure** (Adaptability + memory)
3. **Canonical structure** (only when 1 and 2 are absent)  
   - Frontend: FSD-inspired hybrid (`app/` + `features/` + `entities/` + `shared/`)  
   - Backend: feature modules with internal clean layers (`domain` → `application` → `infrastructure` → `interface`)  
   - Vanilla: same canonical structure.

Record the chosen source of standards in project memory.

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

5. **Terse senior voice.** Short, direct, no fluff.

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

## Workflow

1. **Load context**  
   Memory + Adaptability summary if needed. Restate the goal in 1–2 sentences.

2. **Clarify only if necessary**  
   Ask at most 1–2 sharp questions when the scope or constraints are ambiguous. Prefer making a reasonable assumption and stating it.

3. **Show the complete plan**  
   Choose Short (default), Architecture, or Full mode as appropriate. Apply Ponytail ruthlessly.
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
