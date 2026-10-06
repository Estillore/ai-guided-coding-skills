---
name: guided-planner
description: Pointer to guided-plan full mode. Use when the user wants phases, file paths, risks, and success criteria. Does not implement and does not auto-chain. Works in Kiro, Grok, OpenCode, and Zed.
---

# Guided Planner

Use `guided-plan` full mode.

This skill is the full-plan entry. Follow `guided-plan` for the operating contract: measurable constraints, blast radius, Plan IR when the host can write it, and a stop. Do not implement. Do not invoke another guided phase.

## Project memory

Read and update `docs/guided-memory.md`. If `AGENTS.md` exists and has no pointer, add one line that names `docs/guided-memory.md`. Do not append a project-memory section to `AGENTS.md`.

## OpenCode

Select the `guided-plan` primary. It writes `docs/plans/*.json` and `docs/guided-memory.md` only.

## Zed

Invoke `/guided-plan` on the Guided Plan profile. On the Zed Guided Plan profile, deliver the plan in chat and stop. That profile cannot write files or run a terminal, so it does not run validate-plan.

## Full mode shape

`guided-plan` full mode uses this shape. Every phase must be independently mergeable.

```markdown
# Implementation Plan: [Feature Name]

## Overview
[2-3 sentence summary]

## Requirements
- [Requirement 1]

## Architecture Changes
- [Change: file path and description]

## Implementation Steps

### Phase 1: [Phase Name]
1. **[Step Name]** (File: path/to/file)
   - Action: Specific action to take
   - Why: Reason for this step
   - Dependencies: None
   - Risk: Low/Medium/High

## Testing Strategy
- Unit tests: ...
- Integration tests: ...

## Risks & Mitigations
- **Risk**: ...
  - Mitigation: ...

## Success Criteria
- [ ] Criterion 1
```

Recommend `guided-coding` when the human is ready to implement. Then stop.
