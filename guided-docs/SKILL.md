---
name: guided-docs
description: Extract the essential mental model and key things to remember when learning a library or existing code. Supports library mode (up-to-date external docs) and project mode (codemap + architecture from real code). Uses codebase mapping and self-regenerative project memory. Ideal at the start of a Kiro Spec or Plan workflow, or any time you need to understand before implementing. Works in any Kiro workflow, in Grok, in OpenCode, and in Zed. Use for guided docs, explain this library, help me learn, what does this code do, mental model, key things to remember, or understand this codebase.
---

# Guided Docs

## Overview

Help the developer learn and understand. Focus on the essential mental model, the few important rules to remember, and clear, complete minimal examples.

**Core contract**
- AI shows the complete, accurate information needed (external docs or project structure).
- Human reads, internalizes, and types any notes or examples they want to keep.
- AI never edits the codebase or documentation files unless the human explicitly asks later.

This skill is the learning entry point for the guided family. Use it first, then switch to the other skills.

Pairs with:
- `guided-docs` → understand (this skill)
- `guided-plan` → short plan / architecture
- `guided-coding` → implement
- `guided-refactoring` → clean structure
- `guided-review` → quality + security review
- `guided-verify` → close the loop with evidence

## Project Memory (self-regenerative)

When learning existing project code (not just a library):

- First check `.grok/project-memory.md` or `.kiro/project-memory.md` (or `AGENTS.md` / `CLAUDE.md` / `docs/project-notes/`).
- If present, load it and use it as the starting point for the mental model.
- After extracting new high-value facts about architecture, conventions, or gotchas, update the memory file (prefer `.kiro/project-memory.md` when inside Kiro, or append/update a Project Memory section in `AGENTS.md` when running in OpenCode) so future sessions (and the other guided skills) start smarter.

This is the same lightweight memory protocol used by all guided skills.

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

Only record what will still be useful next week. Prune ruthlessly.

## Kiro IDE support

Works in every Kiro environment via the Agent Skills standard. Install to `~/.kiro/skills/` (global) or `.kiro/skills/` (workspace). Type `/` to invoke.

**Pairing with Kiro built-in workflows**

| Kiro workflow | How to use this skill |
|---------------|-----------------------|
| **Spec** | Use first to lock the mental model before requirements or design go too far |
| **Quick Spec** | Same — start here so the lighter workflow still rests on correct understanding |
| **Plan** | Use to understand the current code or library before creating the plan |
| **Bug Fix** (Debug) | Use when you need to understand existing code or a library involved in the bug |
| **Default** | Use any time you need to learn or clarify a mental model |

This skill is the natural starting point for learning in Kiro.

## OpenCode support

Works natively in OpenCode via the Agent Skills standard. Install to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project). Also compatible with `~/.claude/skills/` and `.claude/skills/`.

OpenCode agents load the skill on demand when the task matches the description. Prefer the **Plan** agent for pure learning/docs work (read-only). Update project knowledge into `AGENTS.md` (created by `/init`) or `.grok/project-memory.md`.

This skill is the natural starting point for learning in OpenCode as well.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-docs` or `@guided-docs`, or ask the agent to use the skill. Prefer updating `AGENTS.md` for project memory.

## Modes

### 1. Library mode (external docs)

Activate when the human asks about a library, framework, or API (“how does Prisma work?”, “show me the current Next.js middleware pattern”, “Auth.js setup”, “Socket.io events”, etc.).

**Behavior**
- **Documentation is Truth**: treat the current official documentation of that library as the source of truth. Prefer it over training data.
- Give the simplest correct mental model that matches the official docs.
- Show the complete minimal working examples the human should understand and type if needed.
- List only the 3–7 rules that prevent common mistakes.
- Never dump full documentation pages.

### 2. Project mode (codemap + architecture)

Activate when the human needs to understand *this* codebase (“explain this folder”, “what is the architecture?”, “how does auth flow work here?”, “update the mental model”, etc.).

**Behavior** (drawn from ECC doc-updater style)
- Load project memory first.
- Map the real structure: entry points, domain/layer boundaries, dependency direction, key modules.
- Produce a short, accurate mental model + codemap-style summary.
- Focus on what is actually present in the code, not idealized architecture.
- Update project memory with any new high-value facts.
- Keep the output under a few hundred lines of dense, useful content. Prefer clarity over completeness.

## Core Rules

1. **Explain the mental model first.** Give the simplest correct picture of how the library or code works.
2. **Extract only the essentials.** List the 3–7 things the developer should keep in mind. No long tutorials.
3. **Show complete minimal examples.** Prefer short, correct, copy-ready snippets that illustrate the point. The human still decides what to type or keep.
4. **Connect to implementation.** When useful, note how this understanding should influence the next step with guided-coding or guided-plan.
5. **Stay terse.** One clear explanation is better than many paragraphs.
6. **Never edit the codebase.** This skill only explains and extracts mental models.

## Workflow

### 1. Identify what is being learned
- A specific library / framework / API → Library mode
- A piece of existing code or the overall project → Project mode
- A concept or pattern in the current project → Project mode (or mixed)

### 2. Load memory + map (Project mode)
- Read `.grok/project-memory.md` or `.kiro/project-memory.md` if it exists.
- Also notice Kiro files (`.kiro/`, steering, specs) when present.
- Identify entry points, domain/layer boundaries, and dependency direction that matter for the current question.
- Keep the mapping short.

### 3. Give the mental model
- Explain in plain language how it works at a high level.
- Use a short analogy only if it truly helps.

### 4. List the key things to remember
- Keep the list short and actionable.
- Focus on the rules that prevent common mistakes.

### 5. Show complete minimal examples
- Provide the smallest useful, correct code snippets.
- Annotate only what is necessary.
- In Library mode these should reflect current recommended usage.

### 6. Link to next step + update memory
- Briefly say how this knowledge should guide the next coding or planning step.
- Suggest switching to `guided-plan`, `guided-coding`, or `guided-refactoring` when ready.
- If new high-value project facts were discovered, update `.grok/project-memory.md` (or the Kiro equivalent).

## Style

- Short paragraphs or bullet points.
- Prefer concrete examples over abstract theory.
- Never dump full documentation pages.
- When explaining existing project code, first apply Adaptability thinking (match the project’s real style + use the memory).
- Terse senior voice — same family style as guided-coding.

## Connected workflow & hand-offs

This skill is the entry point of a complete guided workflow. After the mental model is clear, actively recommend the next skill based on what the human is facing:

| Human situation | Recommend |
|-----------------|-----------|
| “I understand, now I need to decide structure / approach” | → `guided-plan` |
| “I know what to build, let’s implement” | → `guided-coding` |
| “The existing code is messy / vibe-coded” | → `guided-refactoring` |
| “Is this solid? What should I strengthen?” | → `guided-review` |
| “Are we done? Show me the checks” | → `guided-verify` |

**Default happy path**
```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

When cleaning existing code:
```
guided-docs → guided-refactoring → guided-verify
```

Always state the recommendation clearly so the human can switch with one command.

## Anti-patterns

- Writing long tutorials or copying official docs wholesale.
- Explaining every possible feature.
- Generating full production implementations (that belongs to guided-coding).
- Overwhelming the developer with options.
- Editing the codebase or applying code/documentation changes. This skill only explains and extracts mental models.

## Resources

- Place library-specific quick notes in `references/` when needed.
- Place minimal annotated examples in `assets/` when helpful.
