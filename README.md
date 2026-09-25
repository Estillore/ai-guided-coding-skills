# AI Guided Coding Skills

Automation skills that ship quality code end-to-end.

Works with **Kiro**, **Grok**, **OpenCode**, and **Zed** on **Windows** and **macOS** (Linux too).

| AI does | You get |
|---------|---------|
| Implements the complete minimal solution | Reviewed, verified changes |
| Plans, refactors, reviews, and verifies | Evidence + one-sentence why per decision |

AI edits your repo directly, runs checks, and auto-fixes (max 3 loops) — fully autonomous.

---

## Supported tools

| Tool | What gets installed | Global skills path |
|------|---------------------|--------------------|
| **Kiro** | Skills + guided agent + Ponytail steering | `~/.kiro/skills` |
| **Grok** | Skills | `~/.grok/skills` |
| **OpenCode** | Skills + guided agents | `~/.config/opencode/skills` |
| **Zed** | Skills (Agent Skills standard) | `~/.agents/skills` |

Skills use the open **Agent Skills** format (`SKILL.md`), so the same folders work across these tools.

> **Kiro extras:** `agents/*.json` (orchestrator + planner/builder/reviewer) and `steering/ponytail.md`  
> **OpenCode extras:** `agents/opencode/*.md` — 5 primary agents (coding, refactoring, review, verify, plan), per-phase permissions, no auto-chaining  
> Grok and Zed load coaching rules from each skill’s `SKILL.md`.

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

### 3. Restart & try

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

`guided-refactoring` always runs after coding as the quality-maintenance step (auto-skips when clean), so review + verify check already-maintained code.

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

- **Plan IR** (`skills/guided-plan/references/plan-schema.json`) — typed plan JSON (goal, blast radius, steps, test strategy, invariants, outbox, accuracy, done criteria). Gate: `python ~/.guided/scripts/guided_run.py validate-plan <plan.json> [--changed <files>]` must print `PLAN IR: PASS` before building; verify re-runs it with `--changed` to catch blast-radius drift.
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
| `orchestrator [--repo DIR]` | External-supervision check: detects the Agent Orchestrator (`ao`) CLI + git worktree readiness. Never installs or clones. Always exit 0 |
| `lsp [--repo DIR] [--query SYMBOL] [--print-snippet opencode]` | Reports OpenCode prerequisites, optionally probes a real LSP symbol response, or prints the OpenCode v1 semantic-tool config. Never reads secrets or edits config. Always exit 0 |
| `init [--repo DIR]` | Scaffolds `docs/repo-map.json` from detected project facts |

```powershell
python ~/.guided/scripts/guided_run.py verify --repo . --plan plan.json
```

---

## What’s new (vNext)

- **Native OpenCode agents** — `agents/opencode/` ships 5 primary agents (coding, refactoring, review, verify, plan): thin wrappers over the skills with per-phase permissions (plan is read-only) and no auto-chaining
- **OpenCode + Zed skill text** — `guided-coding`, `guided-plan`, `guided-review`, and `guided-verify` now include native OpenCode and Zed support (install paths, agents, project memory)
- **DeepSeek Harness as the Heart** — folded into those four skills (no separate skill). Harness explores and verifies; the guided skill stays the ownership layer and is never the final source of truth
- **Large Codebase Mode** — map the relevant slice only and default blast radius to 1–3 files
- **Hard coaching ownership** — mandatory refusal to edit files; you type every production change
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
| `guided-plan` | Short or full testable plan |
| `guided-planner` | Deeper planner companion |
| `guided-coding` | Implementation + strong TDD |
| `guided-tdd` | Pure red → green → refactor |
| `guided-refactoring` | Clean messy / vibe-coded code |
| `guided-review` | Quality + security review |
| `guided-code-reviewer` | Code-review companion |
| `guided-verify` | Commands, expected results, minimal fixes |
| `guided-infra` | Infra + architecture growth roadmap (Now/Next/Later) |

Install always copies from the `skills/` folder (canonical source).

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

These folders do not conflict — you can install every tool on the same machine.

**Notes**

- OpenCode also discovers skills in `~/.agents/skills` (same path Zed uses). Installing with `-Target all` / `./install.sh` covers both native OpenCode and Zed paths.
- Zed loads skills from `~/.agents/skills` (global) or `.agents/skills` (project).

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
agents/opencode/*.md    ← OpenCode agents: coding / refactoring / review / verify / plan
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
