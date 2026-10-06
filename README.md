# AI Guided Coding Skills

Automation skills that ship quality code end-to-end.

Works with **Kiro**, **Grok**, **OpenCode**, and **Zed** on **Windows** and **macOS** (Linux too).

| AI does | You get |
|---------|---------|
| Implements the complete minimal solution | Reviewed, verified changes |
| Plans, refactors, reviews, and verifies | Evidence + one-sentence why per decision |

AI edits your repo directly, runs checks, and auto-fixes (max 3 loops) — fully autonomous.

## Guided Buddy: learning mode

Use `guided-buddy` when you want to learn rather than delegate the whole task. It starts in Recall or Coach, makes the learning path visible, and permits AI edits only after an explicit Pair or Delegate contract. It never auto-chains to the automation loop.

---

## Supported tools

| Tool | What gets installed | Global skills path |
|------|---------------------|--------------------|
| **Kiro** | Skills + guided agent + Ponytail steering | `~/.kiro/skills` |
| **Grok** | Skills | `~/.grok/skills` |
| **OpenCode** | Skills + primary agents + read-only specialists | `~/.config/opencode/skills` |
| **Zed** | Skills (Agent Skills standard) | `~/.agents/skills` |

Skills use the open **Agent Skills** format (`SKILL.md`), so the same folders work across these tools.

> **Kiro extras:** `agents/*.json` (orchestrator + planner/builder/reviewer) and `steering/ponytail.md`  
> **OpenCode extras:** `agents/opencode/*.md` — 6 primary agents plus 3 read-only specialist subagents, per-phase permissions, a shared read-only shell allowlist for planner + architect, and no primary-agent auto-chaining
> Grok and Zed load coaching rules from each skill’s `SKILL.md`.

### OpenCode agent runtime

The five guided automation modes are **Primary-agent orchestrators**, not repeated skill wrappers. Their compact agent prompts own the normal phase loop; matching skills provide **optional, on-demand skill guidance** only when an advanced mode needs more detail. `guided-buddy` remains a deliberate single-agent coaching mode.

Complex work can use three **read-only specialist subagents**: `guided-architect`, `guided-test-design`, and `guided-reviewer`. OpenCode built-in `explore` handles broad repository discovery. Specialists cannot edit or recurse; the primary remains the only writer and owns final verification.

`guided-architect` **owns the architecture decision** for its slice: it frames measurable constraints, grounds them in measured current state, makes one call with a named rejection and an exit cost, and says so when a change does not need architecture at all. `guided-plan` carries that decision into the Plan IR; overruling it requires a written reason.

`guided-plan` and `guided-architect` share one **read-only shell allowlist**: git inspection subcommands, `rg`/`grep`, file listings, and the `validate-plan` gate. Enforced at the level of the parsed command, with `deny` as the catch-all and explicit denies for write- and exec-capable flags (`--output`, `--pre`, `-O`, `tee`, interpreters). `find` and `fd` are deliberately excluded — `-delete` and `-exec` turn them into writers. This is a command-name and flag allowlist, not a sandbox: it blocks the documented primitives, it does not prove absence of all others. `guided-test-design` and `guided-reviewer` keep `bash: deny` because both are scoped to files the parent hands them. `guided-plan` may write `docs/plans/*.json` and `docs/guided-memory.md`. The plan file is what makes the mandated `validate-plan` gate reachable.

> Known gap: `guided-docs` and `guided-infra` have no OpenCode agent. They remain skill-only: invoke `/guided-docs` or `/guided-infra` from a writable primary.

After reinstalling agent files, **Quit and restart OpenCode**. Running sessions keep the configuration that was loaded at startup.

## Host phase contract

One behavior per phase. A phase skill does not auto-chain into the next skill. It finishes its own work, names the next phase, and stops. The Kiro `guided` orchestrator is the only runtime that still runs the loop for you.

| Host | How to start a phase | What that phase may do |
|------|----------------------|------------------------|
| OpenCode | Select the matching primary (`guided-plan`, `guided-coding`, `guided-refactoring`, `guided-review`, `guided-verify`, `guided-buddy`) before the slash skill | The primary's permissions apply. A slash skill inside Build does not. |
| Zed | Paste **Guided Plan** or **Guided Buddy** for read-only work. Use the Write profile for every other phase | Guided Plan delivers the plan in chat and does not run `validate-plan`. |
| Kiro / Grok | Invoke the skill | The skill writes and runs its own phase, then stops. |

`guided-test-design` is the read-only OpenCode specialist. It designs the failing test. The `guided-tdd` skill, and the `guided-coding` primary, write that test and run it.

OpenCode loads skills from both `~/.config/opencode/skills` and `~/.agents/skills`. Installing OpenCode and Zed registers the same skills twice. Restart OpenCode after an agent install so the new files replace a retired `guided-tdd` agent.

## Optional LSP retrieval

The guided skills prefer a host-provided LSP or equivalent semantic tool when one is available. They use it for symbol discovery, definitions, references, implementations, hover, and call hierarchy, then read only the returned ranges. They fall back to `glob`/`grep` and ranged `read` for strings, configuration, generated files, and unsupported languages.

### OpenCode v1

OpenCode v1 has an experimental native `lsp` tool. Enable it in the OpenCode config:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "lsp": true,
  "permission": {
    "lsp": "allow"
  }
}
```

Start OpenCode with `OPENCODE_EXPERIMENTAL_LSP_TOOL=true` (or `OPENCODE_EXPERIMENTAL=true`) in the environment. The tool supports read-only operations including `goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, and call hierarchy. It needs a known file and position; use lexical search or document symbols to find the initial location.

Check host prerequisites without changing config:

```powershell
# Report CLI/flag prerequisites only
python ~/.guided/scripts/guided_run.py lsp --repo .

# Probe a real semantic symbol response
python ~/.guided/scripts/guided_run.py lsp --repo . --query your_symbol

# Print the OpenCode v1 config fragment
python ~/.guided/scripts/guided_run.py lsp --print-snippet opencode
```

Without `--query`, the command checks only the CLI and experimental flag. With `--query`, it invokes OpenCode's LSP symbol probe and reports `READY` only when symbols are returned. It never reads secrets or edits config.

For an opt-in live smoke test after configuring a language server:

```powershell
$env:GUIDED_LSP_E2E = "1"
$env:GUIDED_LSP_QUERY = "your_symbol"
$env:GUIDED_LSP_REPO = "."
python -m unittest tests.test_semantic_retrieval_contract.SemanticRetrievalContractTest.test_live_opencode_lsp_symbol_lookup -v
```

OpenCode v2 currently preserves `lsp` configuration but does not provide an active LSP runtime or tool. Other hosts may expose LSP through their own editor or MCP integration. The skills detect the available capability and never claim semantic retrieval when it is unavailable.

Language servers execute project tooling with access to the workspace. Enable only trusted, project-compatible servers; the guided family does not auto-install them. Never share raw `opencode debug config` output; it may contain provider credentials.

---

## Quick start (Windows + Mac)

### 1. Clone

```bash
git clone https://github.com/Estillore/ai-guided-coding-skills.git
cd ai-guided-coding-skills
```

| OS | Terminal |
|----|----------|
| **Windows** | PowerShell |
| **macOS** | Terminal (bash / zsh) |

### 2. Install (one command)

Default installs **all four tools**: Kiro, Grok, OpenCode, and Zed.

#### Windows (PowerShell)

```powershell
# All tools (recommended)
.\install.ps1

# Or pick one:
.\install.ps1 -Target kiro
.\install.ps1 -Target grok
.\install.ps1 -Target opencode
.\install.ps1 -Target zed

# Kiro + Grok only:
.\install.ps1 -Target both
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# then run .\install.ps1 again
```

#### macOS (Terminal)

```bash
chmod +x install.sh

# All tools (recommended)
./install.sh

# Or pick one:
./install.sh kiro
./install.sh grok
./install.sh opencode
./install.sh zed

# Kiro + Grok only:
./install.sh both
```

### 3. Verify the install (drift gate)

The installer verifies itself. `skills/` is the single source of truth and
every tool path must be byte-identical to it:

```powershell
python ~/.guided/scripts/guided_run.py sync --check
```

```bash
python3 ~/.guided/scripts/guided_run.py sync --check
```

It prints one line per drifted skill and exits `1` on drift. Run it any time
you suspect a tool is running an old skill:

```
  opencode   stale        guided-buddy
  zed        stale        guided-coding
  zed        missing      guided-buddy
```

A tool root that does not exist yet reports `not-installed` and is not drift.
Foreign skills that merely share `~/.agents/skills` are ignored on purpose.

Two more states the gate refuses to let pass:

| State | Means | Fix |
|-------|-------|-----|
| `invalid` | a directory in `skills/` has no `SKILL.md` | add one, or delete the directory |
| `orphaned` | a guided skill was removed from `skills/` but still sits in a tool root | delete it from the tool root |

Orphan detection needs the manifest the installer writes to
`~/.guided/installed.json` (via `record-install`). That manifest is what lets the
gate tell a removed guided skill apart from another agent's skill sharing the
same root. Until it exists, `sync` says so instead of pretending to check.

### 4. Restart & try

1. Restart your tool (or open a new chat / agent session)
2. Run:

```
/guided-docs
```

or

```
/guided-coding
```

Natural language also works, for example:  
`Use guided-coding to help me implement this feature step by step.`

---

## Happy path (automation loop)

```
guided-docs → guided-plan → guided-coding → guided-refactoring → guided-review → guided-verify
```

Recommend `guided-refactoring` after coding. It does not auto-chain. Review and verify run only when you invoke them.

When the change touches infrastructure (or growth signals cross), `guided-verify` appends a growth watch and points to `guided-infra`, which turns signals into a staged Now/Next/Later roadmap (Docker reliability, Cloudflare edge, data scale, architecture rungs).

| When… | Use |
|-------|-----|
| Learning a library or codebase | `guided-docs` |
| Need a plan before code | `guided-plan` |
| Implementing a feature / bug fix | `guided-coding` |
| Keep structure clean (always-on in loop) | `guided-refactoring` |
| Pure test-first automation | `guided-tdd` |
| Quality + security review + auto-fix | `guided-review` |
| Confirm tests / checks are green | `guided-verify` |
| Infra / architecture growth roadmap | `guided-infra` |

---

## Complex features (ECC-style rigor, architecture focus)

Simple tasks run single-agent with the loop above. Complex/multi-slice work splits into roles with fresh context per phase:

| Agent (Kiro `agents/`) | Role | Skills used |
|------------------------|------|-------------|
| `guided` | Orchestrator — runs the whole loop | all |
| `guided-planner` | Read-only: maps slice, emits validated Plan IR | guided-docs, guided-plan |
| `guided-builder` | Implements slices with TDD + refactoring, stays in blast radius | guided-coding, guided-refactoring |
| `guided-reviewer` | Review-fixes + verify with evidence report | guided-review, guided-verify |

Two archify-inspired artifacts make phases machine-checkable instead of prose-only:

- **Plan IR** (`skills/guided-plan/references/plan-schema.json`) — typed plan JSON (goal, blast radius, steps, test strategy, invariants, outbox, accuracy, done criteria, optional `nfr` for measurable non-functional targets). Gate: `python ~/.guided/scripts/guided_run.py validate-plan <plan.json> [--changed <files>]` must print `PLAN IR: PASS` before building; verify re-runs it with `--changed` to catch blast-radius drift.
- **Repo-map** (`skills/guided-docs/references/repo-map-schema.json`) — structured snapshot (`docs/repo-map.json`) with framework, entry points, dependency direction, conventions, and real test commands. Emitted by guided-docs, loaded by every later phase instead of re-discovering.

---

## Harness (`guided-run`)

Skills are the agent contract; `scripts/guided_run.py` (stdlib-only, installed to `~/.guided/scripts/`) is the enforcement. The harness runs every deterministic part, the agent keeps every judgment part (writing code, review findings):

| Command | What it enforces |
|---------|------------------|
| `validate-plan <plan.json> [--changed <files>]` | Strict IR keys, steps-in-radius, blast-radius drift |
| `verify [--repo DIR] [--plan plan.json]` | Ladder (typecheck→unit→lint→build, stops at first red) + planned mutation/contract/arch gates, writes `guided-receipts/<run-id>/verify.json`, exit 0 only on full PASS |
| `react-doctor [--repo DIR] [--scope S] [--blocking LVL]` | React-only audit lane: detects React, provisions the pinned react-doctor (auto-download on first use), scans as JSON. PASS/SKIP = 0, blocking findings = 1 |
| `growth [--repo DIR] [--no-memory]` | Advisory infra + architecture growth scan (compose/Dockerfile gaps, Cloudflare, DB, queue, cache, storage, auth, observability, secret hygiene, layer signals). Writes `growth.json` + refreshes repo-map `infrastructure`/`growth`. Always exit 0 |
| `php-audit [--repo DIR] [--scope full\|changed] [--blocking LVL]` | PHP audit lane: runs project-installed auditors only (phpstan JSON, pint --test, composer audit JSON, rector dry-run, deptrac JSON, psalm taint, warden JSON). Never installs anything. PASS/SKIP = 0, blocking findings = 1 |
| `js-lint [--repo DIR] [--scope full\|changed] [--blocking LVL] [--no-init-config]` | JavaScript correctness lane: detects `.js/.mjs/.cjs`, uses the project's own oxlint if it has one, else the pinned npx download. Never installs into the project, never runs `--fix`, refuses the npx path when the repo ships an evaluable config (`oxlint.config.ts`/`jsPlugins`). Writes a starter `.oxlintrc.json` when the project has none — **never overwrites an existing one**; `--no-init-config` disables. Reports `inline_js_coverage` — `<script>` bodies in `.php` templates that oxlint cannot see. PASS/SKIP = 0, blocking findings = 1 |
| `js-lint --all [--roots DIR[,DIR...]] [--discover]` | Sweeps every project under the scan roots so no repo has to be named by hand. With no `--roots`, scans the usual home dev folders (Desktop, Documents, Projects, code, repos…). `--discover` lists the roots and writes nothing. Per-project receipt + one summary; exit 1 if any project fails |
| `orchestrator [--repo DIR]` | External-supervision check: detects the Agent Orchestrator (`ao`) CLI + git worktree readiness. Never installs or clones. Always exit 0 |
| `mcp [--repo DIR] [--print-snippet PLATFORM]` | PHP MCP readiness: locate each guided MCP server, handshake over stdio, list tools. `--print-snippet` emits a ready-to-paste client block with resolved paths. Never installs or clones. Always exit 0 |
| `lsp [--repo DIR] [--query SYMBOL] [--print-snippet opencode]` | Reports OpenCode prerequisites, optionally probes a real LSP symbol response, or prints the OpenCode v1 semantic-tool config. Never reads secrets or edits config. Always exit 0 |
| `init [--repo DIR]` | Scaffolds `docs/repo-map.json` from detected project facts |

```powershell
python ~/.guided/scripts/guided_run.py verify --repo . --plan plan.json
```

---

## What’s new (vNext)

- **Install drift gate** — `guided_run.py sync --check` diffs `skills/` against all four tool paths and exits `1` on drift, so a stale Zed install can no longer hide for weeks; both installers run it automatically
- **Zed agent profiles** — `agents/zed/profiles.snippet.jsonc` ships read-only `Guided Plan` and `Guided Buddy` profiles (Zed removed custom modes; profiles are tool sets, skills carry the contract)
- **Native OpenCode agent orchestration** — `agents/opencode/` ships 6 primary phase agents plus 3 read-only specialists. Primaries delegate bounded discovery, test design, architecture, or review work while keeping one-writer ownership, phase permissions, and no primary-agent auto-chaining
- **OpenCode + Zed skill text** — `guided-coding`, `guided-plan`, `guided-review`, `guided-verify`, and `guided-buddy` include native OpenCode and Zed support (install paths, agents, project memory)
- **DeepSeek Harness as the Heart** — folded into the workflow skills (no separate skill). Harness explores and verifies; the guided skill stays the ownership layer and is never the final source of truth
- **Large Codebase Mode** — map the relevant slice only and default blast radius to 1–3 files
- **Guided ownership modes** — normal guided skills keep the human as production author; `guided-buddy` adds explicit bounded Pair/Delegate edits after a contract
- **Human Design Support** — AI implements *your* design, not a different architecture
- **Active Confirmation Gate** — short “why does this matter?” checks on security, auth, and DB rules
- **Database invariants** — constraints shown as real migrations/DDL, not only app checks
- **Transactional Outbox** — default for “write DB + publish event” flows
- **Done checklist** — slice is finished only after behavior, invariants, understanding, and typed-by-you changes are confirmed

---

## Skills

| Skill | Role |
|-------|------|
| `guided-docs` | Mental model and key things to remember |
| `guided-buddy` | AI-assisted apprenticeship with bounded Pair/Delegate edits |
| `guided-plan` | Short or full testable plan |
| `guided-coding` | Implementation + strong TDD |
| `guided-tdd` | Pure red → green → refactor |
| `guided-refactoring` | Clean messy / vibe-coded code |
| `guided-review` | Quality + security review |
| `guided-verify` | Commands, expected results, minimal fixes |
| `guided-infra` | Infra + architecture growth roadmap (Now/Next/Later) |

Install always copies from the `skills/` folder (canonical source).

`agents/guided-planner.json` is the read-only planner agent. It loads `guided-plan` and `guided-docs`. It is not a skill. Review uses `guided-review`; the reviewer agent is `agents/guided-reviewer.json`.

---

## Install paths (Windows + Mac)

| Tool | Windows | macOS / Linux |
|------|---------|----------------|
| **Kiro** skills | `%USERPROFILE%\.kiro\skills` | `~/.kiro/skills` |
| **Kiro** agent | `%USERPROFILE%\.kiro\agents` | `~/.kiro/agents` |
| **Kiro** steering | `%USERPROFILE%\.kiro\steering` | `~/.kiro/steering` |
| **Grok** | `%USERPROFILE%\.grok\skills` | `~/.grok/skills` |
| **OpenCode** | `%USERPROFILE%\.config\opencode\skills` | `~/.config/opencode/skills` |
| **OpenCode** agents | `%USERPROFILE%\.config\opencode\agent` | `~/.config/opencode/agent` |
| **Zed** | `%USERPROFILE%\.agents\skills` | `~/.agents/skills` |
| **Zed** profiles (paste-in) | `%APPDATA%\Zed\settings.json` | `~/.config/zed/settings.json` |

These folders do not conflict — you can install every tool on the same machine.

**Notes**

- OpenCode also discovers skills in `~/.agents/skills` (same path Zed uses). Installing with `-Target all` / `./install.sh` covers both native OpenCode and Zed paths.
- Zed loads skills from `~/.agents/skills` (global) or `.agents/skills` (project).
- Zed removed custom modes; `agent.profiles` replaced them. A profile is a
  **tool set plus a default model** and carries no prompt, so it cannot hold
  a guided contract by itself — pair it with the slash command. See below.

---

## Zed agent profiles

Zed replaced custom modes with **agent profiles**. A profile is a tool set plus
a default model — there is no `prompt` field — so a profile alone cannot carry
the guided contract. The split is deliberate:

| Layer | Surface | Carries |
|-------|---------|---------|
| Tool set | `agent.profiles` in Zed settings | mechanical safety (a plan cannot edit) |
| Behavior | `/guided-plan`, `/guided-buddy` in `~/.agents/skills` | the actual contract |

Install, then paste `agents/zed/profiles.snippet.jsonc` into your Zed settings inside
the existing `"agent"` object (the file is an object fragment — do not replace
your whole settings file):

```
Zed: zed: open settings file
Windows  : %APPDATA%\Zed\settings.json
macOS    : ~/.config/zed/settings.json
```

You get two read-only profiles:

| Profile | Pair with | Cannot |
|---------|-----------|--------|
| `Guided Plan` | `/guided-plan` | edit, write, move, delete, run terminal commands |
| `Guided Buddy (read-only)` | `/guided-buddy` | same, plus no subagent fan-out |

`Guided Buddy (read-only)` covers the Recall and Coach rungs. Its **Pair** and
**Delegate** rungs let the AI implement a bounded slice, so switch to the built-in
**Write** profile for those — a deliberate mode switch, which is exactly what the
skill's ownership rule asks for.

`Guided Coding` is intentionally absent — Zed's built-in **Write** profile
already has exactly the right tool set. Profiles apply to the Zed Agent only;
External Agent threads (e.g. the OpenCode ACP bridge) ignore `agent.profiles`.

---

## Manual install (if you prefer copy-paste)

### Skills only (Grok / OpenCode / Zed) — Windows

```powershell
cd ai-guided-coding-skills

# Grok
New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force

# OpenCode
New-Item -ItemType Directory -Force -Path "$HOME\.config\opencode\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.config\opencode\skills\" -Recurse -Force

# Zed (Agent Skills standard)
New-Item -ItemType Directory -Force -Path "$HOME\.agents\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.agents\skills\" -Recurse -Force
```

### Skills only (Grok / OpenCode / Zed) — macOS

```bash
cd ai-guided-coding-skills

# Grok
mkdir -p ~/.grok/skills
cp -R skills/* ~/.grok/skills/

# OpenCode
mkdir -p ~/.config/opencode/skills
cp -R skills/* ~/.config/opencode/skills/

# Zed (Agent Skills standard)
mkdir -p ~/.agents/skills
cp -R skills/* ~/.agents/skills/
```

### Kiro — Windows

```powershell
cd ai-guided-coding-skills

New-Item -ItemType Directory -Force -Path "$HOME\.kiro\skills", "$HOME\.kiro\agents", "$HOME\.kiro\steering" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.kiro\skills\" -Recurse -Force
Copy-Item -Path ".\agents\*.json" -Destination "$HOME\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force
```

### Kiro — macOS

```bash
cd ai-guided-coding-skills

mkdir -p ~/.kiro/skills ~/.kiro/agents ~/.kiro/steering
cp -R skills/* ~/.kiro/skills/
cp agents/*.json ~/.kiro/agents/
cp steering/ponytail.md ~/.kiro/steering/
```

### Workspace only (one project)

Run from **your project root**. Adjust the path to this repo if needed.

**Kiro project**

```powershell
# Windows
$SRC = "..\ai-guided-coding-skills"
New-Item -ItemType Directory -Force -Path ".\.kiro\skills", ".\.kiro\agents", ".\.kiro\steering" | Out-Null
Copy-Item -Path "$SRC\skills\*" -Destination ".\.kiro\skills\" -Recurse -Force
Copy-Item -Path "$SRC\agents\*.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path "$SRC\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

```bash
# macOS — Kiro project
SRC=../ai-guided-coding-skills
mkdir -p .kiro/skills .kiro/agents .kiro/steering
cp -R "$SRC"/skills/* .kiro/skills/
cp "$SRC"/agents/*.json .kiro/agents/
cp "$SRC"/steering/ponytail.md .kiro/steering/
```

**Zed / OpenCode project** (Agent Skills standard)

```powershell
# Windows
$SRC = "..\ai-guided-coding-skills"
New-Item -ItemType Directory -Force -Path ".\.agents\skills" | Out-Null
Copy-Item -Path "$SRC\skills\*" -Destination ".\.agents\skills\" -Recurse -Force
```

```bash
# macOS — Zed / OpenCode project
SRC=../ai-guided-coding-skills
mkdir -p .agents/skills
cp -R "$SRC"/skills/* .agents/skills/
```

OpenCode project-native path is also `.opencode/skills` if you prefer that over `.agents/skills`.

---

## Update later

### Windows

```powershell
cd ai-guided-coding-skills
git pull
.\install.ps1
```

### macOS

```bash
cd ai-guided-coding-skills
git pull
./install.sh
```

---

## Check it worked

| Tool | Windows check file | macOS check file |
|------|--------------------|------------------|
| Kiro | `C:\Users\You\.kiro\skills\guided-coding\SKILL.md` | `~/.kiro/skills/guided-coding/SKILL.md` |
| Grok | `C:\Users\You\.grok\skills\guided-coding\SKILL.md` | `~/.grok/skills/guided-coding/SKILL.md` |
| OpenCode | `C:\Users\You\.config\opencode\skills\guided-coding\SKILL.md` | `~/.config/opencode/skills/guided-coding/SKILL.md` |
| Zed | `C:\Users\You\.agents\skills\guided-coding\SKILL.md` | `~/.agents/skills/guided-coding/SKILL.md` |

In chat / agent panel, look for skills like `/guided-coding` or ask the agent to use `guided-coding`.

---

## Repo layout

```
install.ps1             ← Windows installer (all tools)
install.sh              ← macOS / Linux installer (all tools)
skills/                 ← canonical source installed by the installers
agents/guided*.json     ← Kiro agents: orchestrator + planner/builder/reviewer
agents/opencode/*.md    ← OpenCode primary agents + read-only specialists
steering/ponytail.md    ← Kiro always-on style
guided-*/               ← legacy mirrors; installers do not read them
backup-old/             ← previous snapshot (reference only)
README.md
```

---

## Principles

1. **Documentation is Truth** — official library docs → project convention → canonical structure  
2. **Ponytail ladder** — skip → reuse → stdlib → platform → existing dep → one-liner → absolute minimum  
3. **Lazy ≠ negligent** — keep validation, security, error handling, accessibility  
4. **Project memory** — skills may use `.kiro/project-memory.md`, `.grok/project-memory.md`, or project notes your tool already reads

---

## License

Use and adapt freely for personal and team learning workflows.
