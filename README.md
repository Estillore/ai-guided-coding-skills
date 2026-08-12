# AI Guided Coding Skills

Coaching skills for **Kiro** and **Grok** that keep **you** writing the code.

| AI does | You do |
|---------|--------|
| Shows the complete minimal solution | Type every line |
| Plans, reviews, and verifies | Own the production code |

AI never edits your repo. You learn by typing, not by accepting patches.

---

## Quick start

1. [Clone the repo](#1-clone)
2. Install for [Kiro](#2a-kiro) and/or [Grok](#2b-grok)
3. Restart the tool (or open a new chat)
4. Run: `/guided-docs` or `/guided-coding`

**Need both tools?** Install both — they use different folders and do not conflict.

---

## Happy path

```
guided-docs → guided-plan → guided-coding → guided-review → guided-verify
```

| When… | Use |
|-------|-----|
| Learning a library or codebase | `guided-docs` |
| Need a plan before code | `guided-plan` |
| Implementing a feature / bugfix | `guided-coding` |
| Code is messy / vibe-coded | `guided-refactoring` |
| Pure test-first coaching | `guided-tdd` |
| Quality + security review | `guided-review` |
| Confirm tests / checks are green | `guided-verify` |

---

## What’s new (vNext)

Core skills now include:

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

## 1. Clone

```bash
git clone https://github.com/Estillore/ai-guided-coding-skills.git
cd ai-guided-coding-skills
```

You need **Git** plus **Kiro**, **Grok**, or both.

| OS | Terminal |
|----|----------|
| Windows | PowerShell |
| macOS / Linux | Terminal (bash or zsh) |

---

## 2a. Kiro

### Global install (recommended — all projects)

**Windows (PowerShell)**

```powershell
cd ai-guided-coding-skills

New-Item -ItemType Directory -Force -Path "$HOME\.kiro\skills", "$HOME\.kiro\agents", "$HOME\.kiro\steering" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.kiro\skills\" -Recurse -Force
Copy-Item -Path ".\agents\guided.json" -Destination "$HOME\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force
```

**macOS / Linux**

```bash
cd ai-guided-coding-skills

mkdir -p ~/.kiro/skills ~/.kiro/agents ~/.kiro/steering
cp -R skills/* ~/.kiro/skills/
cp agents/guided.json ~/.kiro/agents/
cp steering/ponytail.md ~/.kiro/steering/
```

| From this repo | Installs to |
|----------------|-------------|
| `skills/*` | `~/.kiro/skills/` |
| `agents/guided.json` | `~/.kiro/agents/guided.json` |
| `steering/ponytail.md` | `~/.kiro/steering/ponytail.md` |

### One project only (workspace)

Run from **your project root** (adjust `$SRC` / `SRC` if the clone is elsewhere):

**Windows**

```powershell
$SRC = "..\ai-guided-coding-skills"

New-Item -ItemType Directory -Force -Path ".\.kiro\skills", ".\.kiro\agents", ".\.kiro\steering" | Out-Null
Copy-Item -Path "$SRC\skills\*" -Destination ".\.kiro\skills\" -Recurse -Force
Copy-Item -Path "$SRC\agents\guided.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path "$SRC\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

**macOS / Linux**

```bash
SRC=../ai-guided-coding-skills

mkdir -p .kiro/skills .kiro/agents .kiro/steering
cp -R "$SRC"/skills/* .kiro/skills/
cp "$SRC"/agents/guided.json .kiro/agents/
cp "$SRC"/steering/ponytail.md .kiro/steering/
```

### Check Kiro

1. Restart Kiro or open a **new chat**
2. Type `/` — you should see `/guided-coding`, `/guided-docs`, etc.
3. Start with `/guided-docs` or `/guided-coding`

---

## 2b. Grok

### Global install (recommended)

**Windows (PowerShell)**

```powershell
cd ai-guided-coding-skills

New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

**macOS / Linux**

```bash
cd ai-guided-coding-skills

mkdir -p ~/.grok/skills
cp -R skills/* ~/.grok/skills/
```

| From this repo | Installs to |
|----------------|-------------|
| `skills/*` | `~/.grok/skills/` |

> **Note:** `agents/guided.json` and `steering/ponytail.md` are for **Kiro**.  
> Grok loads coaching rules from each skill’s `SKILL.md` under `~/.grok/skills/`.

### Check Grok

1. Restart Grok or start a new session
2. Run `/guided-coding`, or ask:  
   `Use guided-coding to help me implement this feature step by step.`

---

## Install Kiro + Grok together

**Windows**

```powershell
cd ai-guided-coding-skills

# Kiro
New-Item -ItemType Directory -Force -Path "$HOME\.kiro\skills", "$HOME\.kiro\agents", "$HOME\.kiro\steering" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.kiro\skills\" -Recurse -Force
Copy-Item -Path ".\agents\guided.json" -Destination "$HOME\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination "$HOME\.kiro\steering\" -Force

# Grok
New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

**macOS / Linux**

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

## Update later

```bash
cd ai-guided-coding-skills
git pull
```

Then re-run the same **Kiro** and/or **Grok** copy commands from above.

---

## Paths cheat sheet

| Shortcut | Windows | macOS / Linux |
|----------|---------|----------------|
| Home | `C:\Users\YourName` | `/Users/you` or `/home/you` |
| Kiro skills | `%USERPROFILE%\.kiro\skills` | `~/.kiro/skills` |
| Grok skills | `%USERPROFILE%\.grok\skills` | `~/.grok/skills` |

**Sanity check files**

- Kiro: `~/.kiro/skills/guided-coding/SKILL.md` and `~/.kiro/agents/guided.json`
- Grok: `~/.grok/skills/guided-coding/SKILL.md`

---

## Repo layout

```
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
