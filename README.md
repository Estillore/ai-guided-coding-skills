# AI Guided Coding Skills

Coaching skills for **Kiro** and **Grok** that keep **you** writing the code.

Works on **Windows** and **macOS** (Linux too).

| AI does | You do |
|---------|--------|
| Shows the complete minimal solution | Type every line |
| Plans, reviews, and verifies | Own the production code |

AI never edits your repo. You learn by typing, not by accepting patches.

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

Default installs **both Kiro and Grok**. Use a target if you only need one.

#### Windows (PowerShell)

```powershell
# Both Kiro + Grok (recommended)
.\install.ps1

# Or only one tool:
.\install.ps1 -Target kiro
.\install.ps1 -Target grok
```

If PowerShell blocks scripts:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
# then run .\install.ps1 again
```

#### macOS (Terminal)

```bash
chmod +x install.sh

# Both Kiro + Grok (recommended)
./install.sh

# Or only one tool:
./install.sh kiro
./install.sh grok
```

### 3. Restart & try

1. Restart **Kiro** and/or **Grok** (or open a new chat)
2. Run:

```
/guided-docs
```

or

```
/guided-coding
```

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

- **Human Design Support** — AI implements *your* design, not a different architecture
- **Active Confirmation Gate** — short “why does this matter?” checks on security, auth, and DB rules
- **Database invariants** — constraints shown as real migrations/DDL, not only app checks
- **Transactional Outbox** — default for “write DB + publish event” flows
- **Done checklist** — slice is finished only after behavior, invariants, and understanding are confirmed

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

## What gets installed

| Tool | From this repo | Goes to (Windows) | Goes to (macOS) |
|------|----------------|-------------------|-----------------|
| **Kiro** skills | `skills/*` | `%USERPROFILE%\.kiro\skills` | `~/.kiro/skills` |
| **Kiro** agent | `agents/guided.json` | `%USERPROFILE%\.kiro\agents` | `~/.kiro/agents` |
| **Kiro** steering | `steering/ponytail.md` | `%USERPROFILE%\.kiro\steering` | `~/.kiro/steering` |
| **Grok** skills | `skills/*` | `%USERPROFILE%\.grok\skills` | `~/.grok/skills` |

Kiro and Grok use **different folders** — installing both is safe.

> **Note:** `agents/` and `steering/` are for **Kiro**.  
> Grok loads coaching rules from each skill’s `SKILL.md`.

---

## Manual install (if you prefer copy-paste)

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

### Grok — Windows

```powershell
cd ai-guided-coding-skills

New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

### Grok — macOS

```bash
cd ai-guided-coding-skills

mkdir -p ~/.grok/skills
cp -R skills/* ~/.grok/skills/
```

### Workspace only (one project)

Run from **your project root**. Adjust the path to this repo if needed.

**Windows**

```powershell
$SRC = "..\ai-guided-coding-skills"

New-Item -ItemType Directory -Force -Path ".\.kiro\skills", ".\.kiro\agents", ".\.kiro\steering" | Out-Null
Copy-Item -Path "$SRC\skills\*" -Destination ".\.kiro\skills\" -Recurse -Force
Copy-Item -Path "$SRC\agents\guided.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path "$SRC\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

**macOS**

```bash
SRC=../ai-guided-coding-skills

mkdir -p .kiro/skills .kiro/agents .kiro/steering
cp -R "$SRC"/skills/* .kiro/skills/
cp "$SRC"/agents/guided.json .kiro/agents/
cp "$SRC"/steering/ponytail.md .kiro/steering/
```

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

### Windows paths

| Check | Path |
|-------|------|
| Kiro skill | `C:\Users\YourName\.kiro\skills\guided-coding\SKILL.md` |
| Kiro agent | `C:\Users\YourName\.kiro\agents\guided.json` |
| Grok skill | `C:\Users\YourName\.grok\skills\guided-coding\SKILL.md` |

### macOS paths

| Check | Path |
|-------|------|
| Kiro skill | `~/.kiro/skills/guided-coding/SKILL.md` |
| Kiro agent | `~/.kiro/agents/guided.json` |
| Grok skill | `~/.grok/skills/guided-coding/SKILL.md` |

In chat, type `/` — you should see guided skills like `/guided-coding`.

---

## Repo layout

```
install.ps1             ← Windows installer
install.sh              ← macOS / Linux installer
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
4. **Project memory** — skills may use `.kiro/project-memory.md` or `.grok/project-memory.md`

---

## License

Use and adapt freely for personal and team learning workflows.
