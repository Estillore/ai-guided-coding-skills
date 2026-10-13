# AGENTS.md

## Guided

- Framework: python-stdlib 3.x. Source of standards: project convention (`docs/family-contract.md`).
- Structure: flat toolkit. `skills/` is copied verbatim by the installers. `scripts/guided_run.py` is the stdlib harness.
- Plan file: overwrite `docs/plans/current.json` only. Do not write `docs/plans/<slug>.json`.
- Memory: replace this `## Guided` section. Create `docs/guided-memory.md` only when `AGENTS.md` is absent.
- Contract: the eight memory skills and README use that paragraph. The OpenCode planner edit allow is `*`, `docs/plans/current.json`, `AGENTS.md`, and `docs/guided-memory.md`.
- Gotcha: a non-empty Plan IR `accuracy` array makes `guided_run` demand Infection, Pact, or Deptrac. Prose slices leave those arrays empty.
- Decision 2026-10-13: those six design skills stay out of `skills/`. Install them in the frontend repo. One skill per UI pass. Detect the surface first: an existing pattern wins; a web app stays minimal and readable; a website gets entrance fades and scroll motion. OpenCode's skill root is an ECC junction, so do not `npx skills add` there.
- Design lane 2026-10-13: `guided-coding` classifies existing, web app, or website. Packs stay out of `skills/`.
- Ship 2026-10-13: install this verified tree to OpenCode and Zed only, then one commit on `main` and a push to `origin`. Kiro and Grok stay stale, so `install.ps1` exits 1 on `sync --check`. That exit is expected. Do not `npx` the six design packs.
- Not started: shorten `guided-plan`, score eval scenarios offline, and do not add OpenCode agents for docs or infra.
- Verify 2026-10-13 sha `7fb107d`: plan gate PASS (14 files, buddy fence included) and `python -m unittest discover -s tests -v` PASS. The edit allowlist test requires `*` deny first. Slice closed.
