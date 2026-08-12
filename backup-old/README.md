# AI Guided Coding Skills

Lean coaching skills and a `guided` agent for **Kiro** and **Grok**.

**Core contract (all skills + agent)**

- AI **shows** the complete minimal correct solution / plan / findings
- Human **types** every change
- AI never edits the codebase

Supported tools on this repo: **Kiro** and **Grok** only.

---

## What’s inside

```
skills/                 Guided family skills
agents/guided.json      Guided coaching agent (Kiro)
steering/ponytail.md    Always-on Ponytail style (Kiro)
README.md               This setup guide
```

### Skills

| Skill | Role |
|-------|------|
| `guided-docs` | Mental model / key things to remember |
| `guided-plan` | Short / architecture / full plan |
| `guided-planner` | Planner companion (deeper plan) |
| `guided-coding` | Implementation + Strong TDD |
| `guided-tdd` | Pure test-first coaching |
| `guided-refactoring` | Clean vibe-coded / messy code |
| `guided-review` | Quality + security review |
| `guided-code-reviewer` | Code-review companion |
| `guided-verify` | Verification commands + expected results |

### Happy path

```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

Use `guided-refactoring` when surrounding code is messy.  
Use `guided-tdd` when you want pure red → green → refactor.

---

## Setup on any laptop

Works on **Windows**, **macOS**, and **Linux**.  
You only need **Git** and either **Kiro**, **Grok**, or both.

### 1. Prerequisites

1. Install [Git](https://git-scm.com/downloads) if you don’t have it.
2. Install the tool you use:
   - **Kiro** — install the Kiro app/IDE for your OS
   - **Grok** — install Grok CLI / Grok Build for your OS
3. Open a terminal:
   - Windows: **PowerShell**
   - macOS / Linux: **Terminal** (bash or zsh)

### 2. Clone this repository

```bash
git clone https://github.com/Estillore/ai-guided-coding-skills.git
cd ai-guided-coding-skills
```

Keep this folder. You will copy files from it into Kiro/Grok folders.

---

## Setup for Kiro

Kiro reads skills, agents, and steering from your user home (global) or the project (workspace).

### Option A — Global install (recommended)

Use this so skills work in **every** Kiro project on this laptop.

#### Windows (PowerShell)

```powershell
cd ai-guided-coding-skills

# Skills
New-Item -ItemType Directory -Force -Path "$HOME\.kiro\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.kiro\skills\" -Recurse -Force

# Agent
New-Item -ItemType Directory -Force -Path "$HOME\.kiro\agents" | Out-Null
Copy-Item -Path ".\agents\guided.json" -Destination "$HOME\.kiro\agents\" -Force

# Steering (always-on Ponytail)
New-Item -ItemType Directory -Force -Path "$HOME\.kiro\steering" | Out-Null
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force
```

#### macOS / Linux

```bash
cd ai-guided-coding-skills

mkdir -p ~/.kiro/skills ~/.kiro/agents ~/.kiro/steering
cp -R skills/* ~/.kiro/skills/
cp agents/guided.json ~/.kiro/agents/
cp steering/ponytail.md ~/.kiro/steering/
```

#### What gets installed (Kiro global)

| From this repo | Goes to |
|----------------|---------|
| `skills/*` | `~/.kiro/skills/` |
| `agents/guided.json` | `~/.kiro/agents/guided.json` |
| `steering/ponytail.md` | `~/.kiro/steering/ponytail.md` |

On Windows, `~` is your user folder (e.g. `C:\Users\YourName`).

### Option B — Workspace only (one project)

Use this if you only want the guided family inside **one** project.

#### Windows (PowerShell) — run from your project root

```powershell
# From your project folder (not necessarily this repo)
# Assume this repo is cloned at ..\ai-guided-coding-skills (adjust path if needed)
$SRC = "..\ai-guided-coding-skills"

New-Item -ItemType Directory -Force -Path ".\.kiro\skills", ".\.kiro\agents", ".\.kiro\steering" | Out-Null
Copy-Item -Path "$SRC\skills\*" -Destination ".\.kiro\skills\" -Recurse -Force
Copy-Item -Path "$SRC\agents\guided.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path "$SRC\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

#### macOS / Linux — run from your project root

```bash
SRC=../ai-guided-coding-skills   # adjust if needed

mkdir -p .kiro/skills .kiro/agents .kiro/steering
cp -R "$SRC"/skills/* .kiro/skills/
cp "$SRC"/agents/guided.json .kiro/agents/
cp "$SRC"/steering/ponytail.md .kiro/steering/
```

### Finish Kiro setup

1. Restart Kiro, or open a **new chat**.
2. Type `/` in chat — you should see skills like `/guided-coding`, `/guided-docs`, etc.
3. Start with:

```
/guided-docs
```

or

```
/guided-coding
```

---

## Setup for Grok

Grok discovers skills from `~/.grok/skills/` (user-level).

### Global install (recommended)

#### Windows (PowerShell)

```powershell
cd ai-guided-coding-skills

New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

#### macOS / Linux

```bash
cd ai-guided-coding-skills

mkdir -p ~/.grok/skills
cp -R skills/* ~/.grok/skills/
```

#### What gets installed (Grok)

| From this repo | Goes to |
|----------------|---------|
| `skills/*` | `~/.grok/skills/` |

### Finish Grok setup

1. Restart Grok / open a new session if skills don’t appear.
2. Invoke a skill by name, for example:

```
/guided-coding
```

or ask in natural language:

```
Use guided-coding to help me implement this feature step by step.
```

> **Note:** The `agents/guided.json` and `steering/ponytail.md` files are for **Kiro**.  
> Grok uses the skills under `~/.grok/skills/` (coaching rules live inside each skill’s `SKILL.md`).

---

## Install both Kiro and Grok on the same laptop

You can install both. They use **different folders** and do not conflict.

#### Windows (PowerShell)

```powershell
cd ai-guided-coding-skills

# --- Kiro ---
New-Item -ItemType Directory -Force -Path "$HOME\.kiro\skills", "$HOME\.kiro\agents", "$HOME\.kiro\steering" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.kiro\skills\" -Recurse -Force
Copy-Item -Path ".\agents\guided.json" -Destination "$HOME\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force

# --- Grok ---
New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

#### macOS / Linux

```bash
cd ai-guided-coding-skills

# Kiro
mkdir -p ~/.kiro/skills ~/.kiro/agents ~/.kiro/steering
cp -R skills/* ~/.kiro/skills/
cp agents/guided.json ~/.kiro/agents/
cp steering/ponytail.md ~/.kiro/steering/

# Grok
mkdir -p ~/.grok/skills
cp -R skills/* ~/.grok/skills/
```

---

## How to update later

On any laptop, pull the latest and re-copy:

```bash
cd ai-guided-coding-skills
git pull
```

Then re-run the **Kiro** and/or **Grok** copy commands from above (same as install).

---

## Quick check (did it work?)

### Kiro

- Folder exists: `~/.kiro/skills/guided-coding/SKILL.md`
- Agent exists: `~/.kiro/agents/guided.json`
- In chat, `/` shows guided skills

### Grok

- Folder exists: `~/.grok/skills/guided-coding/SKILL.md`
- Skill commands or natural-language “use guided-coding” work

### Windows path reminder

| Shortcut | Typical path |
|----------|----------------|
| `$HOME` / `~` | `C:\Users\YourName` |
| Kiro skills | `C:\Users\YourName\.kiro\skills` |
| Grok skills | `C:\Users\YourName\.grok\skills` |

### macOS / Linux path reminder

| Shortcut | Typical path |
|----------|----------------|
| `~` | `/Users/you` (macOS) or `/home/you` (Linux) |
| Kiro skills | `~/.kiro/skills` |
| Grok skills | `~/.grok/skills` |

---

## Principles

1. **Documentation is Truth** — official library docs first, then project convention, then canonical structure  
2. **Ponytail ladder** — skip → reuse → stdlib → platform → existing dep → one-liner → absolute minimum  
3. **Lazy ≠ negligent** — keep validation, security, error handling, accessibility  
4. **Project memory** — skills may use `.kiro/project-memory.md` (Kiro) or `.grok/project-memory.md` (Grok)

---

## License

Use and adapt freely for personal and team learning workflows.
