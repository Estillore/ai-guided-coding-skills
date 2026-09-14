---
name: guided-planner
description: Create a complete, actionable implementation plan and proceed. AI outputs the full plan with phases, exact file paths, risks, and testing strategy, updates memory, and chains to implementation in autonomous runs. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use for planning, architecture decision, or when you need a testable plan first.
---

# Guided Planner

## Overview

Force the AI into autonomous planning. The AI outputs a complete, minimal, correct implementation plan (phases, file paths, risks, testing strategy), updates memory, and proceeds to implementation.

**Core contract**
- AI outputs the complete plan (structure and concrete steps).
- AI updates memory and chains to `guided-coding` in autonomous runs.
- AI may create plan files directly when the project uses them.

Companion to `guided-plan`. Prefer this when you want the richer ECC-style plan format with explicit phases, risks, and success criteria.

## Connected workflow & hand-offs

| Human situation | Recommend |
|-----------------|-----------|
| Need mental model of the library/area | → `guided-docs` |
| Ready to implement after the plan | → `guided-coding` |
| Surrounding code is messy | → `guided-refactoring` |
| Implementation looks done | → `guided-review` |
| Need verification | → `guided-verify` |

**Default happy path (automation loop)**
```
guided-docs → guided-planner → guided-coding → guided-refactoring → guided-review → guided-verify
```

## Project Memory

Load `.grok/project-memory.md` (or `.kiro/project-memory.md` / `AGENTS.md`) plus `docs/repo-map.json` when present first. Do not re-discover what is already recorded. Update after meaningful architectural discoveries (prefer a Project Memory section in `AGENTS.md` when running in OpenCode).

## OpenCode support

Install to `~/.config/opencode/skills/` or `.opencode/skills/` (or Claude-compatible paths). Prefer the **Plan** agent for analysis, then chain to Build for autonomous implementation.

## Zed support

Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-planner` or `@guided-planner`. Prefer updating `AGENTS.md`.

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

### 3. Apply ownership
Save the plan to memory (and to a plan file when the project uses one). In autonomous runs proceed directly to implementation.

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
- Chain to the next guided skill immediately after the plan is saved.
- Never write the plan file yourself.
