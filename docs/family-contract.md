# Guided family contract

Shared rules for every guided skill. A skill is not done until this contract holds.

## Exclusive trigger

Load one skill. If two could match, use this order and stop:

1. Teach, coach, pair, manual mode, Odin mode → `guided-buddy`
2. Map a library or codebase, mental model, repo-map → `guided-docs`
3. Plan, architecture, decide structure, phases → `guided-plan`
4. Explicit test-first or coverage goal → `guided-tdd`
5. Implement, fix a bug, ship a change → `guided-coding`
6. Clean structure without new behavior → `guided-refactoring`
7. Review findings, security review → `guided-review`
8. Run checks, are we done, evidence → `guided-verify`
9. Infra or growth roadmap → `guided-infra`

`agents/guided-planner.json` and `agents/guided-reviewer.json` are agents, not skills.

## Stop

Do not auto-chain. Recommend the next skill in one line, then stop.

## Blast radius

Default 1–3 files. A larger set needs an explicit why before any edit.

## Evidence line

End every run with one line the host can check:

`EVIDENCE: <command or artifact> -> <PASS|FAIL|SKIP> (<one-line why>)`

SKIP is allowed only when the host cannot run the command. Say which host limit caused it.

## Memory

Read `docs/guided-memory.md` when it exists. Update it after a real discovery. If `AGENTS.md` exists and has no pointer, add one line naming `docs/guided-memory.md`. Do not append a project-memory section to `AGENTS.md`.

## Vanilla PHP

Page-script PHP uses `docs/vanilla-php.md`. Map the symptom include chain before editing. Do not treat a missing framework as permission to rewrite the app.
