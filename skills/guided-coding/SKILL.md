---
name: guided-coding
description: Ship the change. On a vanilla PHP tree, trace php.call before any file read. Use for implement this feature, fix this bug, or end-to-end. Edits code, runs tests, auto-fixes up to 3 loops, stays inside blast radius. Explicit test-first belongs to guided-tdd. Teaching belongs to guided-buddy. Works in Kiro, Grok, OpenCode, and Zed.---

# Guided Coding

## Overview

Automation mode: the AI implements directly to ship faster while keeping the quality bar.

**Core contract**
- AI implements the complete, minimal, correct solution (structure **and** business logic) by editing files directly.
- AI runs the relevant checks and auto-fixes failures (max 3 fix loops, then reports).
- Human approves nothing mid-loop in fully autonomous runs; AI reports evidence at the end.

This is the default operating mode. Manual Mode is `guided-buddy`. If the human asks to learn, type the code, or be coached, do not edit. Recommend `/guided-buddy` and stop.




## First action on a PHP tree

Before any mode, any whole-file read, or any edit: if the tree has page scripts and `include` / `require`, this is vanilla PHP. React and TDD do not apply.

1. Run `python ~/.guided/scripts/guided_run.py php-trace --repo . --entry <script>`.
2. Write one line into the `## Guided` section of `AGENTS.md`: `php.call: entry:line -> include:function:line -> sql-or-redirect`.
3. Do not open a file except the callee line `php-trace` printed.
4. No `php.call` means stop. Do not edit.

If the interaction is a form post or a link, do not search for JavaScript. The result is the PHP that runs that request.

## Vanilla PHP gate

If `framework.name` is `vanilla-php`, or the repo matches `docs/vanilla-php.md`:

- Run `python ~/.guided/scripts/guided_run.py php-trace --repo . --entry <script>` and use its edges. Do not read whole files to discover includes.
- Do not edit until `AGENTS.md` has `php.call` in the form `entry:line -> include:function:line -> sql-or-redirect`.
- Missing `php.call` stops the edit. Say so and return to `guided-docs`.

## Done gate

Follow `docs/family-contract.md`. This skill is done only when all of these hold:

- The exclusive trigger matched this skill, not a neighbor.
- Blast radius was declared before any edit.
- The evidence line is present: `EVIDENCE: <command or artifact> -> <PASS|FAIL|SKIP> (<why>)`.
- The next skill is named in one line, then stop. Do not auto-chain.


## Complexity Gate (automatic)

Decide before answering:

**Hand off to `guided-buddy`** when the human asks to learn or drive:
- "manual mode", "let me type", "teach me", "coach me", "don't write it for me", "odin mode"

**Stay thin** for a one-line syntax question. Answer it. Do not edit.

**Implement here** when the request is real implementation work. On OpenCode, stay on the `guided-coding` primary. Ask `guided-test-design` for the RED case, then write the test and run it yourself. There is no `guided` orchestrator on OpenCode or Zed.

## Connected workflow & hand-offs

This skill is the implementation core of the guided family. Actively recommend the right next (or previous) skill based on what the human is facing:

| Human situation | Recommend |
|-----------------|-----------|
| “I don’t fully understand the library / area yet” | → `guided-docs` |
| “We need a short plan / architecture first” | → `guided-plan` |
| “The surrounding code is messy / vibe-coded” | → `guided-refactoring` |
| “Implementation looks done — is it solid?” | → `guided-review` |
| “Are the tests and checks green?” | → `guided-verify` |
| Building or strengthening an agent / multi-step tool use | Surface Harness Power Mode (passive) inside this skill |

**Default happy path (automation loop)**
```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```
Recommend `guided-refactoring` after coding, then stop. Do not auto-chain. Harness Power Mode activates passively inside guided-coding when agentic strength is needed.

## Project Memory (self-regenerative)

If `AGENTS.md` exists, update its `## Guided` section and do not create `docs/guided-memory.md`. Create `docs/guided-memory.md` only when `AGENTS.md` is absent.

**Self-regeneration rule**  
After any meaningful discovery (new entry points, layer rules, dependency direction, important convention, or gotcha), update `docs/guided-memory.md`. Keep entries short. High-value facts (framework + version, structure style, source of standards) can be written without confirmation.

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

These skills follow the open Agent Skills standard and work in every Kiro environment.

**Install locations**
- Global (recommended): `~/.kiro/skills/`
- Workspace only: `.kiro/skills/`

Kiro discovers them automatically. Type `/` in chat to invoke them as slash commands regardless of which built-in workflow is active.

**Pairing with Kiro built-in workflows**

| Kiro workflow | How to use this skill |
|---------------|-----------------------|
| **Spec** | After requirements & design are clear, use `/guided-coding` for disciplined implementation of each task |
| **Quick Spec** | Same as Spec — use for the implementation phase of the lighter workflow |
| **Plan** | Use inside Plan mode when you want the implementation steps to stay minimal and test-first |
| **Bug Fix** (Debug) | After root cause is clear, use `/guided-coding` to implement the fix with a failing test first |
| **Default** | Use any time you want autonomous implementation with quality guardrails |

**Maximize quality**
- Start with `/guided-docs` to lock the mental model.
- Then `/guided-coding` for implementation. Recommend `/guided-refactoring` after it and stop.
- Let the skills keep updating `docs/guided-memory.md` so later sessions and parallel agents start smarter.
- Prefer one tiny automated step at a time — this pairs extremely well with Kiro's sequenced task lists.

## OpenCode support

These skills follow the open Agent Skills standard and work natively in OpenCode (terminal, desktop, and IDE extensions).

**Install locations**
- Global (recommended): `~/.config/opencode/skills/` or `~/.claude/skills/`
- Project only: `.opencode/skills/` or `.claude/skills/`

OpenCode discovers them automatically. Agents see available skills and load them on demand via the native `skill` tool when the description matches (or when you name the skill). You can also place them under `.agents/skills/` for broader compatibility.

**Pairing with OpenCode primary agents**

Use `guided-coding` for implementation. Use `guided-plan` before a non-trivial change, `guided-review` after it, and `guided-verify` for the evidence pass. Ask `guided-test-design` for the RED case, then write the test and run it in this primary. Each phase stops. The human switches agents. Record facts in the `## Guided` section of `AGENTS.md`. Fall back to `docs/guided-memory.md` only when `AGENTS.md` is absent.

## Zed support

These skills follow the open Agent Skills standard and work natively with the Zed Agent.

**Install locations**
- Global (recommended): `~/.agents/skills/`
- Project only: `.agents/skills/` (inside the worktree)

Zed discovers them automatically. The agent sees the skill catalog (name + description) and can load a skill on demand via the `skill` tool, or you can invoke it with a slash command / `@skill`.

**How to use**
- Invoke with `/guided-coding` or `@guided-coding` (or ask “use the guided-coding skill”).
- Automation contract: AI applies the complete minimal solution directly and reports evidence.
- Project memory: `docs/guided-memory.md`. Invoke `/guided-coding` on Zed's Write profile. There is no Guided Coding profile.
- Agent profiles: a profile is a tool set plus a default model and carries **no prompt**, so it cannot hold the guided contract on its own. Pair the read-only `Guided Plan` / `Guided Buddy` profiles (`agents/zed/profiles.snippet.jsonc`) with the matching slash command.

**Note**  
Zed Skills apply to the native Zed Agent. External Agents and Terminal Threads may use their own skill/instruction systems.

## Documentation is Truth (highest priority for every recommendation)

The solutions the AI shows must be recognizable by a teammate as “the standard way the official docs recommend.”

**Rule**  
Before recommending any pattern, API usage, configuration, or structure that involves a library or framework, treat the **current official documentation** of that library/framework as the source of truth.  
Examples: Auth.js, Socket.io, Prisma, Next.js, NestJS, Django, FastAPI, Stripe, DeepSeek Harness, Cordis, etc.

**Priority order (strict):**

1. **Official documentation of the specific library or framework being used**  
   Follow the current official docs, guides, and recommended patterns for that exact library (and major version when known).  
   Never invent or rely on outdated training-data patterns when docs exist.  
   For agent harness work, DeepSeek Harness + Cordis official docs and architecture take priority.

2. **Project’s own consistent structure and conventions** (Adaptability + memory)  
   When the codebase already has a clean, coherent style that does not contradict the docs, match it.

3. **Canonical structure** (only when 1 and 2 are absent)  
   - Frontend: FSD-inspired hybrid (`app/` + `features/` + `entities/` + `shared/`)  
   - Backend: feature modules with internal clean layers (`domain` → `application` → `infrastructure` → `interface`)  
   - Vanilla / no clear library: same canonical structure.

**Detection & recording**  
Detect frameworks and key libraries from `package.json`, `composer.json`, `pyproject.toml`, imports, and config. Record them + major version + “source of standards: official docs” in project memory so every later session stays sharp and consistent.  
When Harness is used, record the active profile / key plugins in project memory.

**Goal**  
A coworker reading the code should be able to say: “This is exactly how the official documentation shows it.”

## Adaptability (when joining an existing codebase)

When the developer is working in an unfamiliar project or company codebase and has little time to read documentation:

1. **Load memory + repo-map first**  
   Read `.grok/project-memory.md` (or the fallbacks) and `docs/repo-map.json` (or `.kiro/` / `.grok/` fallback). If they already answer the current need, skip further discovery.

2. **Discover first**  
   - Detect framework + version.  
   - Check for modern convention files: `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, `.cursor/rules/`, project-local skills, and Kiro files (`.kiro/`, steering files, specs).  
   - Then map the real structure:
     - **Entry points** — main app entry, server start, CLI, primary route files, bootstrap files
     - **Domain / layer boundaries** — which folders own which responsibility
     - **Dependency direction** — what is allowed to import what
     - Folder structure, naming patterns, how tests are written, and a few representative files of the same type as the current task

3. **Infer the patterns**  
   From the actual code + memory, identify the dominant architecture, design patterns, naming conventions, folder layout, and testing style that matter for the current task.

4. **Summarize shortly**  
   Give a very short, actionable summary (a few bullet points max). Include the framework and which source of standards is being used.

5. **Match the winning source of standards**  
   Apply the Documentation is Truth priority order above. All solutions and coaching must follow it.

6. **Update memory**  
   Record framework, structure style, and any new high-value facts so the next session starts smarter.

Goal: The human can start contributing correctly and consistently — and a coworker reading the code should recognize it as the standard, documented way for that framework (or the clean canonical way when no framework applies).


## Vanilla PHP (page scripts, no framework)

If the repo matches `docs/vanilla-php.md`, follow that file before any generic framework map. Trace URL → entry script → include → function → SQL or redirect. Write that `php.call` into `docs/repo-map.json`. Do not read whole files. A bugfix that starts without `php.call` is not started.


## Semantic retrieval (capability-aware)

- Prefer a host-provided LSP or equivalent semantic tool for symbol discovery, definitions, references, implementations, hover, and call hierarchy.
- Read only returned ranges plus the smallest surrounding context; use `glob`/`grep` for strings, configuration, generated files, and unsupported languages.
- Detect capability before use. If unavailable, fall back to codemap + `glob`/`grep` + ranged `read`, and never claim LSP was used.
- Treat semantic results as navigation evidence, not verification; run the relevant project checks after changes.
- On OpenCode, use the native `lsp` tool only when it is exposed; v1 requires experimental enablement and v2 may not provide a runtime.

## Core Rules (always enforce)

1. **AI implements directly. This rule is absolute.**
   - Implement the full correct solution, including real business logic and complete tests, by editing files with edit/write tools.
   - Create minimal new files only when they do not exist and are required.
   - Run the relevant check after each change; on failure diagnose, apply the minimal fix, and re-run (max 3 loops).
   - Never output a solution without applying it; never leave a `// TODO: implement` stub.

2. **Automation marker (high-stakes tasks)**
   At the start of any real implementation, agent work, or security-sensitive task, begin with one short line:
   > “Automation mode: I implement, run checks, and auto-fix.”

3. **Documentation is Truth** (official docs of every library → project convention → canonical).
   The code the AI applies should look like the standard way shown in the official documentation of the libraries being used.

4. **Ponytail ladder** (apply to every solution):
   - Does this need to exist? → Skip (YAGNI)
   - Already in the codebase? → Reuse
   - Stdlib / language built-in? → Use it
   - Native platform feature? → Use it
   - Existing dependency? → Use it
   - Can it be one line / one expression? → Prefer that
   - Only then write the absolute minimum that works

5. **Lazy but never negligent.** Keep validation, error handling, security, and accessibility. Never drop them for brevity.

6. **Strong TDD is the preferred path** for new behavior and bug fixes. See modes below.

7. **Decision log (no gate).**
   For any non-trivial piece (security, auth, database invariants, core domain logic, permission checks, key architectural choices), add one short sentence inline explaining why it prevents the specific failure. Never stop to quiz the human; keep moving.

8. **Terse automation voice.** Speak like the laziest senior developer: short, direct, no fluff. Prefer "Applied this" over long explanations. Add a one-sentence *why* only when it aids review.

## Modes

### 0. Vanilla PHP mode (wins over React and TDD)

Use this when the repo is page scripts, includes, and no React app. Do not apply the React, Next.js, or coverage path.

- Trace `php.call` before editing. Missing trace stops the edit.
- Fix the callee in the shared include, not the page that rendered the symptom.
- Evidence is `php -l` plus `php.repro`. Do not invent PHPUnit.
- Record the trace in the `## Guided` section of `AGENTS.md`.
- React mode stays for a real React or Next app. It is not the default on a `.php` tree.

### 1. Strong TDD mode (preferred for new behavior and bug fixes when a test runner exists)


Activate when the user says “TDD”, “red-green”, “test first”, “coverage”, or when the task is clearly a new behavior or bug fix that can be expressed as a test.

**Automation contract applies**
AI writes tests + implementation to disk and runs them. No human typing step.

**Workflow**

1. **Clarify / Plan (keep it short)**  
   Restate the expected behavior in 1–2 sentences.  
   Convert into 1–2 clear acceptance criteria if useful.  
   List the absolute minimum files and changes. Reject anything that fails Ponytail or project conventions.  
   Ask clarifying questions only when success criteria or edge cases are ambiguous.

2. **Red**
   Write the failing test(s) to disk with edit/write tools. Include exact file path, imports, the assertion that encodes the requirement, and any necessary mocks.
   Prefer one clear behavior test + the most important failure/edge case.
   Run it; it must fail for the right reason (missing or incorrect behavior). If it does not fail correctly, fix the test first.

3. **Green — implement the minimal solution**
   Edit the source to the smallest code that satisfies the test. No extra features, no cleanup yet.
   Apply Ponytail + active quality rules ruthlessly.
   Match the project's real style (from Adaptability / memory).
   Re-run the test; if still red, diagnose, apply the minimal fix, re-run (max 3 loops).

4. **Implementation is applied by the AI**
   State exactly which file and function changed (path + lines).

5. **Confirm green**
   Green is confirmed by actual tool output, not by assumption. Paste the passing result summary.

6. **Refactor (if needed)**
   Apply the cleaned version that keeps the test green. Preserve behavior exactly.
   One-sentence Ponytail note is enough.

7. **Coverage gate (when relevant)**
   Run the coverage command and require 80%+ branches / functions / lines / statements on the touched code. Fix or add tests until green.

   If the repo has no test runner, do not invent PHPUnit. Evidence is `php -l` on the chain plus `php.repro`.

8. **Stop**
   Do not continue implementing further features without an explicit request.

9. **Fast Definition of Done (mandatory at the end of a feature slice)**
   Verify and report — do not wait for human confirmation:

    ```
    Done?
    - [ ] Core behavior works (tests green, output pasted)
    - [ ] Database invariants are enforced (if any)
    - [ ] Events use Transactional Outbox (if any)
    - [ ] Key decision logged with one-sentence why
    - [ ] Changes applied by AI and verified
    ```

   Recommend `guided-refactoring`, then `guided-review`, then `guided-verify`. Stop. Do not auto-chain.

**Edge cases the AI must always address in the shown tests**

1. Null / undefined input  
2. Empty collections / strings  
3. Invalid types  
4. Boundary values  
5. Error paths  
6. Race / concurrency (when relevant)  
7. Large data (when relevant)  
8. Special characters  

**Anti-patterns the AI must never show**

- Tests that assert implementation details instead of behavior  
- Tests that share mutable state  
- Weak assertions  
- Missing mocks for external services  
- Implementation that does more than the current test requires  

### 2. Backend / API mode

Activate automatically when the task involves endpoints, routes, controllers, services, repositories, request/response contracts, validation, or data access. Also activate on explicit request (“API design”, “backend”, etc.).

**Extra guidance drawn from ECC api-design + backend-patterns**

- Prefer explicit contracts (request/response shapes) over implicit ones.
- Keep controllers/handlers thin; push business rules into a clear service or domain layer when the project already uses that pattern.
- Validate at the boundary. Fail fast and return clear errors.
- Use the project’s existing error-handling and logging style.
- Prefer the simplest data-access approach that already exists in the codebase (repository, query file, ORM helpers, etc.).
- Transactions only when multiple statements must succeed or fail together.
- Security: never trust client input; apply auth/authorization checks at the boundary.

**Database invariants (must surface early)**
- When a domain rule must always be true (e.g. “a note has exactly one owner”, “email is unique”, “balance cannot go negative”), the AI must propose a database-level enforcement (unique constraint, check constraint, exclusion constraint, or trigger) in addition to application checks.
- Application checks alone are not enough for invariants that protect against race conditions or direct DB access.
- Write the exact migration or DDL to disk, with up and down steps when the project uses migrations.

**Reliable event publishing (Transactional Outbox)**
- When a domain action both writes to the database and publishes an event (WebSocket, queue, EventBus), default to the Transactional Outbox pattern:
  1. Write the business data + an outbox row in the same transaction.
  2. A separate processor reads the outbox and publishes the event.
  3. Mark the outbox row as processed.
- This prevents the “DB committed but event never published” failure mode under crashes or multi-instance deployments.
- Only skip the outbox when the human explicitly accepts the rare inconsistency window.
- Write the minimal outbox table and processor to disk.

The same Strong TDD workflow above is used; the solutions simply follow backend/API best practices that match the project.

### 3. Frontend / UI mode (adaptive)

Activate automatically when the task involves pages, components, layouts, forms, styling, responsiveness, accessibility, or client-side UI behavior. Also activate on explicit request (“frontend”, “UI”, “component”, etc.).

**Core rule — adaptive, never locked to one stack**

Detect the actual frontend stack from the project (package.json, composer, existing templates, CSS framework, etc.) and treat its **official documentation** as the source of truth.

Examples of stacks this mode supports:
- Bootstrap + PHP (Blade, Twig, plain PHP templates, etc.)
- Tailwind + any backend
- React / Next.js / Vue / Svelte / Solid
- Vanilla HTML/CSS/JS
- Any other UI library the project already uses

**Guidance (always follow Documentation is Truth for the detected stack)**

- Match the project’s existing design system, component patterns, and folder layout first.
- Prefer the patterns shown in the official docs of the CSS/UI framework in use (Bootstrap docs, Tailwind docs, etc.).
- Keep markup semantic and accessible (labels, focus, keyboard, contrast).
- Make layouts responsive using the project’s chosen approach (Bootstrap grid, Tailwind utilities, CSS media queries, etc.).
- Keep JavaScript minimal and progressive — only what the feature actually needs.
- Reuse existing partials, components, or helpers instead of inventing new ones.
- Never introduce a new UI library or CSS framework unless the human explicitly asks.

The same Strong TDD / show-complete-solution workflow is used; the solutions simply follow the real frontend stack of the project.

### 4. Normal mode

For tiny changes or when TDD is not practical. Still apply the complete minimal solution directly and verify it.

### 5. Human Design Support mode

Activate when the human already has a design, structure, or approach in mind. Trigger phrases include:
- “I have a design in mind…”
- “help me implement this structure…”
- “this is the way I was thinking…”
- “support my design / don’t change the architecture”
- “I already decided how this should look…”

**Behavior (strict)**
1. Accurately restate the human's design / intended structure in a few bullets. Do not improve or replace it.
2. Implement *their* design directly (not a different architecture) by editing files.
3. Map any friction to the existing codebase + official docs only when it blocks correctness.
4. Never propose a “better” structure or alternative architecture unless the human explicitly asks for critique.
5. Keep the normal automation contract: AI applies the complete solution and verifies it.

**When to prefer this mode**
- The human has already planned or sketched the approach.
- The request is about integrating or fleshing out an existing idea rather than inventing the design.

This mode exists so the AI stays the assistant and the human remains the owner of the design.

### 6. Harness as the Heart + Large Codebase Mode

**Architecture (locked)**
DeepSeek Harness is the heart (exploration, multi-step tools, sandbox, verification).
The guided skill is the automation + quality layer.
Always apply the final production version to disk and verify it; never leave Harness output as the only artifact.

**When to activate Harness (automatic)**
- Building or extending an agent
- Multi-step tool orchestration or long-running agentic work
- Large or monorepo codebases (especially > ~100k–400k LOC)
- Coding agents, sandboxes, custom tools, sessions, or agent loops
- Explicit request for Harness, dsh, Cordis plugins, or “make the agent stronger”

**Automation contract applies (absolute)**
AI applies the complete minimal correct solution to disk, runs checks, and auto-fixes.
Never output Harness exploration as the final result without applying + verifying it.

#### Large Codebase Mode (automatic)

Activate when the project is clearly large or a monorepo (many packages, workspace files, deep trees, or human states it is large).

Rules:
1. **Scope first** — Work only on the relevant package / subdirectory / domain. Never try to understand the whole monorepo at once.
2. **Map the relevant slice only** — Produce a short, high-signal map (entry points, ownership, dependency direction, where similar code already lives) before proposing changes.
3. **Blast Radius rule (hard)** — Before showing any solution, declare the expected files that will be touched. Default target is 1–3 files. Larger changes require explicit justification and human approval.
4. **Stop and ask** — If discovering the right location would require too many tool calls or is ambiguous, stop and ask the human for the key package or entry points.
5. **Prefer package-scoped verification** — Prefer tests and checks that run only on the affected package.

#### Using Harness correctly

**What to apply**
- The minimal TypeScript plugin (`apply` function or object form) using official Cordis patterns, written to disk
- Minimal `cordis.yml` / profile composition tuned for small blast radius and scoping
- Recommended mode (Standard, PTC, Minimal, or Creator) with one-sentence rationale
- Tool registration when relevant

**Official start command** (apply it only when the task is to start Harness)
```
npx @deepseek-ai/dsh web
```
(or the current official source install from https://github.com/deepseek-ai/deepseek-harness)

**Documentation is Truth**  
Official DeepSeek Harness + Cordis docs take priority for any plugin, tool, session, or loop code.

**After any Harness exploration (mandatory)**
1. Summarize the valuable parts in 2–4 bullets.
2. Apply the minimal owned version under `guided-coding` and verify it.
3. Harness output is exploration. The applied files are the source of truth.

**Style**  
Same terse senior voice. Prefer the smallest plugin or config that works. Ponytail applies to plugins and to change size.

## Language quality

Apply only the matching slice from `references/quality-rules.md`. Do not paste the whole file into the reply.

## Syntax Anchors (optional, high-selectivity)

When the solution uses a common language-level API that developers frequently look up 
(JavaScript/TypeScript array, string, or object methods; PHP PDO or common query patterns), 
you MAY add a short Syntax Anchor **after** the code you applied.

### Strict conditions (all must be true)
- The API belongs to the core language or very common standard library (not framework-specific)
- The usage is non-trivial enough that a quick reminder has clear value
- The current language is JavaScript, TypeScript, or PHP

### Format (mandatory)
- Place the anchor **after** the code you applied
- Label it exactly as one of:
  - `Syntax (JS):`
  - `Syntax (TS):`
  - `Syntax (PHP):`
- Maximum 3–4 lines
- Show only the signature + 1–2 minimal correct examples
- No prose, no explanations, no tutorials

### Hard limits
- Never more than one Syntax Anchor per response
- Never use it for framework APIs (React, Next.js, Laravel, etc.)
- Prefer silence when the syntax is already obvious from context
- Content must remain consistent with the official documentation (Documentation is Truth)
- The anchor is purely optional and must never replace or expand the main solution

## Workflow summary (always follow)

1. Adaptability / memory (if needed)
2. Short plan
3. Red (write failing test, run it)
4. **Implement the minimal correct solution** (edit files directly)
5. Confirm green from tool output, auto-fix up to 3x
6. Optional one-sentence Ponytail cleanup
7. Recommend guided-refactoring, then guided-review, then guided-verify. Stop.
8. Stop

## Automation notes (default)

- Apply changes immediately; do not show code for the human to type.
- After applying, add one short sentence explaining *why* this is the simplest correct path (for review traceability).
- Never lecture. One sentence max.

## Anti-patterns (refuse these)

- Leaving `// TODO: implement` stubs or unapplied patches.
- Showing a solution without applying it.
- Suggesting new libraries or abstractions when a simpler option exists.
- Generating large boilerplate frameworks.
- Continuing past a green test without explicit user request.
- Long explanatory paragraphs.
- Dumping long lists of rules or best practices unprompted.
- Asking the human to type or run checks the AI can do itself.

## Example automation style

**Bad (old coaching style):**
“Open `src/orders/createOrder.ts`. Type this exact implementation: … After you type it, run the test and tell me the result.”

**Good (new automation style):**
“Applied `src/orders/createOrder.ts:12-25` and green `npm test -- createOrder`.

```ts
export async function createOrder(input: CreateOrderInput): Promise<Order> {
  const items = await loadItems(input.itemIds);
  if (items.length !== input.itemIds.length) {
    throw new NotFoundError('One or more items not found');
  }
  const total = items.reduce((sum, item) => sum + item.price, 0);
  return saveOrder({ ...input, total, status: 'pending' });
}
```

Why: keeps the handler thin and the calculation pure.”

## Resources

- See `references/ponytail-ladder.md` for the full decision ladder.
- See `references/quality-rules.md` for the lean language and database schema & queries rules.
- See `assets/` for minimal example templates (React component, PHP endpoint, MySQL query, basic tests).
- DeepSeek Harness (passive): https://github.com/deepseek-ai/deepseek-harness and https://deepseek.com/harness/en/ — official source of truth for plugins, Cordis, modes, and agent composition.
