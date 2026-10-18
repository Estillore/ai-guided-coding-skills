---
name: guided-frontend
description: Design the UI surface before implementation. Use for design, layout, visual direction, landing page, dashboard, or "how should this look". Classifies the surface, picks a design direction (anti-slop, design-system aware, motion-aware), and outputs a short design decision. Does not implement. Hands off to guided-plan or guided-coding. Works in Kiro, Grok, OpenCode, and Zed.
---

# Guided Frontend

## Overview

Lock the design decision before any code is written. This is the frontend counterpart to `guided-plan`.

**Core contract**
- AI outputs a complete, minimal design decision (surface type, layout approach, key visual/motion rules, accessibility constraints).
- Record `ui.surface` in the `## Guided` section of `AGENTS.md`.
- Stop after the design decision. Do not implement and do not auto-chain.

This skill sits before planning and implementation for UI-heavy work:

- `guided-docs` → understand (if needed)
- `guided-frontend` → decide design (this skill)
- `guided-plan` → fold the design into structure
- `guided-coding` → implement the decided design

## Done gate

Follow `docs/family-contract.md`. This skill is done only when all of these hold:

- The exclusive trigger matched this skill, not a neighbor.
- Blast radius was declared before any edit.
- The evidence line is present: `EVIDENCE: <command or artifact> -> <PASS|FAIL|SKIP> (<why>)`.
- The next skill is named in one line, then stop. Do not auto-chain.

## Project Memory

Replace the `## Guided` section of `AGENTS.md`. Include `ui.surface: existing | webapp | website` and a one-line design direction. Create `docs/guided-memory.md` only when `AGENTS.md` is absent.

## Documentation is Truth

Design decisions must be recognizable by a teammate as consistent with the project's existing system or the official docs of the UI library already in use. Never invent a new UI library or CSS framework unless the human explicitly asks.

**Priority order**
1. Existing project design system / components / tokens
2. Official documentation of the UI library already used
3. Canonical presets below (only when 1 and 2 are weak or absent)

## Design decision process

### 1. Classify the surface
- **existing** — shared components, tokens, or a repeated layout already exist. Copy that spacing, type, color, radius, and motion.
- **webapp** — dashboard, admin, portal, tool, or task shell (nav + table/form/settings/list/detail). Keep it minimal and readable.
- **website** — site, landing, marketing, homepage, campaign, or portfolio. Use open sections and deliberate entrance.

Record the classification.

### 2. Choose a design direction (anti-slop, on par with design-taste / ui-ux-pro-max thinking)
When no strong existing system exists, pick one concrete direction and state it:

- **Webapp preset**: One accent. Body text ≥ 16px. Tight but readable density. Motion only for hover, focus, open, close, and feedback. `prefers-reduced-motion` shows content in place. No scroll-pinned scenes.
- **Website preset**: Clear visual hierarchy. Distinctive type (avoid Inter/Arial as the only face). Limited palette with one strong accent. Entrance fades (opacity + short rise) and scroll reveals only. `prefers-reduced-motion` shows content in place.
- **Anti-slop rules** (always apply when inventing): No generic gradient cards, no single accent word in a headline, no ALL-CAPS labels everywhere, no default "AI aesthetic". Ground choices in the subject and audience.

### 3. Motion note (emil-style, optional)
When the surface has interaction (drawers, toasts, page transitions, micro-interactions):
- Enter: ease-out
- On-screen morph: ease-in-out
- Hover: ease
- Duration: micro 100–150ms, standard 150–250ms, modals 200–300ms, exits ~20% faster
- Prefer transform/opacity. Avoid layout-thrashing properties.

Skip the motion note for static or low-interaction surfaces.

### 4. Accessibility constraints
- Semantic markup, labels, focus states, keyboard access, sufficient contrast.
- Minimum hit area guidance when relevant.

### 5. Output the design decision and stop

**Output shape**
- Surface: existing | webapp | website
- Design direction (1–3 sentences or bullets)
- Layout regions / key components (short)
- Type / color / spacing notes (only what matters)
- Motion note (or "none")
- Accessibility constraints
- Definition of done for this design
- Next skill recommendation (one line)

Then stop. Do not write component code.

## Modes

### Default (new or weak design system)
Produce the full design decision above using the presets and anti-slop rules.

### Existing design system
Restate the existing patterns you will copy. Do not invent a new direction. Hand off.

### Human design support
When the human already has a visual direction, restate it accurately, map only friction points, and do not replace it.

## Workflow

1. Load memory + detect existing design system if present.
2. Classify the surface.
3. Choose or restate the design direction.
4. Output the complete design decision.
5. Record `ui.surface` and the one-line direction in `AGENTS.md`.
6. Name the next skill (`guided-plan` for non-trivial structure, or `guided-coding` when the design is simple and ready to implement). Stop.

## Anti-patterns

- Writing component or page code from this skill.
- Introducing a new UI library or CSS framework without an explicit ask.
- Auto-chaining into `guided-coding` or `guided-plan`.
- Generic "make it modern" advice without a concrete direction.
- Overriding a strong existing design system.

## Connected workflow

```
guided-docs → guided-frontend → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```

For simple UI slices the design decision may go straight to `guided-coding`.
