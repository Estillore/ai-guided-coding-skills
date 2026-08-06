# AI Guided Coding Skills

Lean coaching skills and a `guided` agent for **Kiro**, **Grok**, and other Agent Skills–compatible tools.

**Core contract (all skills + agent)**
- AI **shows** the complete minimal correct solution / plan / findings
- Human **types** every change
- AI never edits the codebase

## Contents

```
skills/                 Guided family skills
agents/guided.json      Guided coaching agent
steering/ponytail.md    Always-on Ponytail minimalism style
```

### Skills

| Skill | Role |
|-------|------|
| `guided-docs` | Mental model / key things to remember |
| `guided-plan` | Short / architecture / full plan |
| `guided-planner` | Planner companion (ECC-style depth) |
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

Use `guided-refactoring` when the surrounding code is messy. Use `guided-tdd` when you want pure red-green-refactor.

## Install

### Kiro (global — recommended)

```powershell
# Clone
git clone https://github.com/Estillore/ai-guided-coding-skills.git
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

Restart Kiro or open a new chat. Type `/` to invoke skills.

### Grok

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\.grok\skills" | Out-Null
Copy-Item -Path ".\skills\*" -Destination "$HOME\.grok\skills\" -Recurse -Force
```

### Workspace-only (Kiro)

```powershell
New-Item -ItemType Directory -Force -Path ".\.kiro\skills", ".\.kiro\agents", ".\.kiro\steering" | Out-Null
Copy-Item -Path ".\skills\*" -Destination ".\.kiro\skills\" -Recurse -Force
Copy-Item -Path ".\agents\guided.json" -Destination ".\.kiro\agents\" -Force
Copy-Item -Path ".\steering\ponytail.md" -Destination ".\.kiro\steering\" -Force
```

## Principles

1. **Documentation is Truth** — official library docs first, then project convention, then canonical structure
2. **Ponytail ladder** — skip → reuse → stdlib → platform → existing dep → one-liner → absolute minimum
3. **Lazy ≠ negligent** — keep validation, security, error handling, accessibility
4. **Project memory** — skills read/update `.kiro/project-memory.md` or `.grok/project-memory.md`

## License

Use and adapt freely for personal and team learning workflows.
