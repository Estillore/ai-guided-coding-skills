# AI Guided Coding Skills

Coaching skills that keep **you** writing the code.

Works with **Kiro**, **Grok**, **OpenCode**, and **Zed** on **Windows** and **macOS** (Linux too).

| AI does | You do |
|---------|--------|
| Shows the complete minimal solution | Type every line |
| Plans, reviews, and verifies | Own the production code |

AI never edits your repo. You learn by typing, not by accepting patches.

---

## Supported tools

| Tool | What gets installed | Global skills path |
|------|---------------------|--------------------|
| **Kiro** | Skills + guided agent + Ponytail steering | `~/.kiro/skills` |
| **Grok** | Skills | `~/.grok/skills` |
| **OpenCode** | Skills | `~/.config/opencode/skills` |
| **Zed** | Skills (Agent Skills standard) | `~/.agents/skills` |

Skills use the open **Agent Skills** format (`SKILL.md`), so the same folders work across these tools.

> **Kiro-only extras:** `agents/guided.json` and `steering/ponytail.md`  
> OpenCode, Grok, and Zed load coaching rules from each skill’s `SKILL.md`.

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

## Happy path

```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

| When… | Use |
|-------|-----|
| Learning a library or codebase | `guided-docs` |
| Need a plan before code | `guided-plan` |
| Implementing a feature / bug fix | `guided-coding` |
| Code is messy / vibe-coded | `guided-refactoring` |
| Pure test-first coaching | `guided-tdd` |
| Quality + security review | `guided-review` |
| Confirm tests / checks are green | `guided-verify` |

---

## What’s new (vNext)

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
Copy-Item -Path ".\agents\guided.json" -Destination "$HOME\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force
```

### Kiro — macOS

```bash
cd ai-guided-coding-skills

mkdir -p ~/.kiro/skills ~/.kiro/agents ~/.kiro/steering
cp -R skills/* ~/.kiro/skills/
cp agents/guided.json ~/.kiro/agents/
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
Copy-Item -Path "$SRC\agents\guided.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path "$SRC\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

```bash
# macOS — Kiro project
SRC=../ai-guided-coding-skills
mkdir -p .kiro/skills .kiro/agents .kiro/steering
cp -R "$SRC"/skills/* .kiro/skills/
cp "$SRC"/agents/guided.json .kiro/agents/
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
skills/                 ← install from here (all guided skills)
agents/guided.json      ← Kiro guided agent
steering/ponytail.md    ← Kiro always-on style
guided-*/               ← core workflow skills (same content as skills/)
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
