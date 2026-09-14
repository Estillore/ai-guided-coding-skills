---
name: guided-refactoring
description: Autonomous refactoring of vibe-coded or messy code to match framework standards and project conventions. AI diagnoses code smells, applies the complete cleaned version directly, runs checks, and reports. Uses Documentation-is-Truth, codebase mapping, self-regenerative project memory, and Ponytail minimalism. Works in any Kiro workflow (especially Bug Fix and Spec), in Grok, in OpenCode, and in Zed. Use for refactor this, clean this vibe code, make it match standards, or fix structural problems.
---

# Guided Refactoring

## Overview

Force the AI into autonomous refactoring that eliminates guesswork and ships the cleanup.

**Core contract**
- AI diagnoses the mismatches and applies the complete cleaned version directly.
- AI runs the relevant checks and auto-fixes (max 3 loops).
- AI reports each change with file:line + technique used.

This skill is the natural follow-up to `guided-docs`. Use guided-docs first to extract the essential standards of the framework (Next.js, Laravel, etc.), then switch here to drive the refactor.

## Connected workflow & hand-offs

This skill is the structural cleanup step of the guided family. Actively recommend the right next (or previous) skill based on what the human is facing:

| Human situation | Recommend |
|-----------------|-----------|
| “I don’t understand the framework standards yet” | → `guided-docs` |
| “This refactor is large — need a short plan first” | → `guided-plan` |
| “Structure is clean, now implement the new feature” | → `guided-coding` |
| “Refactor done — is the code solid?” | → `guided-review` |
| “Confirm nothing broke” | → `guided-verify` |

**Automation loop position (always-on quality step)**
```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```
`guided-refactoring` always runs after coding in autonomous runs: clean structure, remove duplication, re-apply Ponytail — then chain to review. Auto-skip rule: if no smells, no Ponytail violations, and no convention drift are found, log `refactor: clean, skipped` and chain forward immediately (no empty edits).

**Typical cleaning path**
```
guided-docs → guided-refactoring → guided-verify
```

When the refactor is large:
```
guided-docs → guided-plan → guided-refactoring → guided-verify
```

## Project Memory (self-regenerative)

Before Adaptability or diagnosis, check for project memory:

- Preferred: `.grok/project-memory.md` or `.kiro/project-memory.md` (Kiro) or `AGENTS.md` (OpenCode)
- Fallbacks: `docs/project-notes/key_facts.md`, `CLAUDE.md`

**If present** → load it first and treat it as known ground truth.

**Self-regeneration**  
After diagnosis or successful refactor steps that reveal new architecture facts, conventions, or gotchas, update the memory file (prefer `.kiro/project-memory.md` when inside Kiro, or a Project Memory section in `AGENTS.md` when inside OpenCode). Keep entries short and high-value only. This makes the skill smarter on the same project over time.

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
| **Spec** | When the design reveals vibe-coded or messy parts that need to match framework standards |
| **Quick Spec** | Same — clean structure before or while implementing tasks |
| **Plan** | Use when the plan itself involves structural cleanup |
| **Bug Fix** (Debug) | After root cause is clear, use to clean structural problems one tiny step at a time |
| **Default** | Any time you want to strengthen existing code without the agent rewriting everything |

Diagnose first, then coach one tiny structural step at a time. This pairs cleanly with Kiro’s sequenced tasks.

## OpenCode support

Works natively in OpenCode via the Agent Skills standard. Install to `~/.config/opencode/skills/` (global) or `.opencode/skills/` (project); also under `.claude/skills/`.

**Pairing with OpenCode agents**

| OpenCode agent | How to use this skill |
|----------------|-----------------------|
| **Plan** | Safe for diagnosis and planning the cleanup sequence (read-only). |
| **Build** | Use for the actual cleanup steps. AI applies each step directly, runs checks, and auto-fixes. |

Update project memory into `AGENTS.md` or `.grok/project-memory.md` so the cleaned conventions stick for later sessions and other guided skills.

## Zed support

Works natively with the Zed Agent. Install to `~/.agents/skills/` (global) or `.agents/skills/` (project). Invoke with `/guided-refactoring` or `@guided-refactoring`. Automation contract (AI applies the cleaned version directly). Prefer updating `AGENTS.md`.

## Documentation is Truth (highest priority for the target shape)

The cleaned code must be recognizable by a teammate as “the standard way the official docs recommend.”

**Rule**  
Before recommending any cleaned structure or pattern that involves a library or framework, treat the **current official documentation** of that library/framework as the source of truth (Auth.js, Socket.io, Prisma, Next.js, NestJS, Laravel, etc.).

## Adaptive Architecture & Framework Standards

This skill must work well across many different codebases and frameworks (Next.js, Laravel, NestJS, vanilla PHP/JS, and others). It is designed for on-call engineers who need to adapt quickly across companies and tech stacks.

### Priority Order (strict)

1. **Official documentation** of the current framework or library
2. **Project’s existing clear and consistent architecture** (from Adaptability + project memory)
3. **Feature / Module Cohesion** — prefer keeping related business logic together and avoid mixing unrelated features in the same files
4. **Canonical structure** (only when 1–3 are absent or the codebase is very messy)  
   - Frontend: FSD-inspired hybrid (`app/` + `features/` + `entities/` + `shared/`)  
   - Backend: feature modules with internal clean layers (`domain` → `application` → `infrastructure` → `interface`)  
   - Vanilla: same canonical structure

### Rules

- Always detect the framework (or detect that the codebase is vanilla) first.
- When the project uses a framework **incorrectly** or with outdated patterns, prefer the current official documentation of that framework.
- When the project has a clear and consistent architecture style, respect it.
- When files mix unrelated business concerns (e.g. Authentication + Inventory + Reports in the same controller or file), treat it as a structural problem and help increase cohesion in a way that still fits the project’s architecture.
- Prefer the smallest safe improvement (Ponytail). Never force a large architectural rewrite unless the human explicitly asks for it.
- This skill must remain useful for on-call work across many different companies and tech stacks.

## Adaptability (when the target is an existing project)

1. **Load memory + repo-map first** — read `.grok/project-memory.md` / `.kiro/project-memory.md` (or fallbacks) and `docs/repo-map.json` when present. Skip re-discovery of known facts.
2. **Discover** — detect framework + version, then check for `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, project-local skills, and Kiro files. Map:
   - Entry points, domain/layer boundaries, dependency direction
   - Folder layout, Server vs Client boundaries, naming, data-fetching style
3. **Infer** the dominant patterns that matter for the current refactor.
4. **Summarize** in a few short bullets only. State which source of standards is being used.
5. All coaching and the cleaned target must follow the Documentation is Truth priority order above.
6. **Update memory** if new high-value facts were found.

## Core Rules (always enforce)

1. **AI applies the complete cleaned version directly.**
   - Apply the full correct cleaned version for each step, including the rewritten logic, via edit/write tools.
   - Run the relevant checks after each step; auto-fix (max 3 loops).
   - Never leave stubs or unapplied patches.

2. **Documentation is Truth** (official docs of every library → project convention → canonical).

3. **Ponytail ladder** on every suggestion (same decision ladder used by guided-coding).

4. **Behavior stays identical.** Never change what the feature does — only how it is structured (unless the human explicitly asks for a behavior change).

5. **One tiny step at a time, applied immediately.** Apply the single next change, verify it, then continue.

6. **Terse automation voice.** Speak like the laziest senior developer. Short, direct, no fluff.

## Workflow (follow in order)

### 1. Confirm the target standards
- If the developer has not yet used guided-docs for the framework, say so and suggest doing that first.
- Otherwise, restate the key framework patterns that matter for this piece of code (3–6 bullets max).
- Also run the Adaptability discovery if this is an existing codebase and summarize the project conventions that apply.

### 2. Diagnose (code smells + standards)
- Look at the current code the human provides.
- Identify the real problems using two lenses:
  1. **Standards violations** — framework docs, project conventions, Documentation-is-Truth rules, Ponytail.
  2. **Code smells** (Refactoring Guru style) — name the dominant smells when they help the human understand *why*:
     - Bloaters (Long Method, Large Class, Long Parameter List, Primitive Obsession, Data Clumps…)
     - Object-Orientation Abusers (Switch Statements, Temporary Field, Refused Bequest…)
     - Change Preventers (Divergent Change, Shotgun Surgery, Parallel Inheritance…)
     - Dispensables (Comments, Duplicate Code, Dead Code, Lazy Class…)
     - Couplers (Feature Envy, Inappropriate Intimacy, Message Chains…)
- List only the mismatches that actually matter, ordered by severity.
- Ignore pure style nits that do not affect structure, correctness, or maintainability.
- Keep the diagnosis short and actionable.

### 3. Plan the order (minimal sequence)
- Produce a short ordered list of the smallest possible changes that will bring the code in line with the standards.
- Prefer structural moves first (Extract Class, Move Method, extract Server Component, split client boundary, extract service, etc.), then smaller clean-ups.
- When useful, name the refactoring technique that will be applied in each step (Extract Method, Introduce Parameter Object, Decompose Conditional, Replace Temp with Query, etc.).
- Explicitly reject any change that is not required or that violates Ponytail.
- Ask for confirmation only if the order is ambiguous.

### 4. Apply one step at a time
- Open the exact file and section via read tools.
- Optionally name the refactoring technique being applied.
- Apply the complete cleaned version for **this single step** directly.
- Re-diagnose only what remains and continue to the next step.
- Repeat until the definition of done is reached.

### 5. Close
- Confirm that the code now matches the framework patterns, the project conventions, keeps the same behavior, and is minimal.
- Stop. Do not continue “improving” further unless the human explicitly asks.

## Definition of done

Stop when all of the following are true:

- Code follows the framework’s recommended patterns (e.g. Next.js App Router + Server Components by default).
- Code also matches the specific project’s own conventions (Adaptability).
- Observable behavior is identical (unless a behavior change was requested).
- Code is as minimal as possible under the Ponytail ladder.

## Anti-patterns (refuse these)

- Editing the codebase or applying patches.
- Dumping a complete new version of an entire file as the first step.
- Suggesting large architectural rewrites that go beyond the framework standards or the current task.
- Continuing after the definition of done is met.
- Long explanatory paragraphs or lectures.
- Introducing new libraries or abstractions unless the framework or the existing project already uses them.

## Example coaching style

**Bad:**
“Here is the fully refactored Server Component with all the data fetching moved and the client boundary cleaned up…”

**Good:**
“Smell: Long Method + Feature Envy in the page component.  
Technique: Extract Method + move data fetching to the server (Next.js docs pattern).

Open `app/dashboard/page.tsx`.  
This is the exact change for step 1:

```tsx
export default async function DashboardPage() {
  const data = await getDashboardData();
  return <DashboardView data={data} />;
}
```

Type that change. Leave everything else untouched for now. Paste the result when ready.”

## Resources

- Reuse the same Ponytail ladder and lean quality rules that live in the guided-coding skill.
- Diagnosis language and named techniques are informed by Refactoring Guru (code smells + catalog of refactorings).
- No extra local references needed yet. Add them only if a specific framework pattern keeps being repeated.
