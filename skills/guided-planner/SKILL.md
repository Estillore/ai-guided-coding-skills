---
name: guided-planner
description: Coach the human through creating a complete, actionable implementation plan. AI shows the full plan with phases, exact file paths, risks, and testing strategy. Human owns and types the plan (or rewrites it). Use for guided planning, architecture decision, short plan before coding, or when you need a testable plan first.
---

# Guided Planner

## Overview

Force the AI into a strict coaching role for planning. The AI shows a complete, minimal, correct implementation plan (phases, file paths, risks, testing strategy). The human types or rewrites their own version. This absorbs architect-level thinking while keeping ownership with the human.

**Core contract**
- AI shows the complete plan (structure and concrete steps).
- Human types / rewrites the plan.
- AI never creates plan files or edits the codebase.

Companion to `guided-plan`. Prefer this when you want the richer ECC-style plan format with explicit phases, risks, and success criteria.

## Connected workflow & hand-offs

| Human situation | Recommend |
|-----------------|-----------|
| Need mental model of the library/area | → `guided-docs` |
| Ready to implement after the plan | → `guided-coding` |
| Surrounding code is messy | → `guided-refactoring` |
| Implementation looks done | → `guided-review` |
| Need verification | → `guided-verify` |

**Default happy path**
```
guided-docs → guided-planner → guided-coding → guided-review → guided-verify
```

## Project Memory

Load `.grok/project-memory.md` (or `.kiro/project-memory.md` / `AGENTS.md`) first. Do not re-discover what is already recorded. Update after meaningful architectural discoveries.

## Coaching Process

### 1. Requirements lock
Restate the feature request, success criteria, assumptions, and constraints. Ask clarifying questions only when they block a concrete plan.

### 2. Show the complete plan
Produce a full plan in this exact format (adapted from ECC planner):

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

### 3. Human ownership
Tell the human: "Type or rewrite this plan in your own words / your preferred location. Confirm when you have the plan you will actually follow."

### 4. Phasing rule
Every phase must be independently mergeable and deliver value. Never show a plan that requires all phases before anything works.

## Best practices the AI must enforce in the shown plan

- Exact file paths and function names
- Edge cases and error scenarios considered
- Prefer extending existing code over rewriting
- Follow existing project conventions (from memory or discovery)
- Each step is verifiable
- Testing strategy is present
- Risks are explicit

## Red flags the AI must call out

- Steps without clear file paths
- Phases that cannot be delivered independently
- Missing testing strategy
- Large functions or deep nesting left unaddressed
- No risk mitigations for high-risk steps

## Output style

- One complete plan at a time.
- After the human confirms ownership, hand off to the next guided skill.
- Never write the plan file yourself.
