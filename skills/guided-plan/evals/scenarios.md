# guided-plan evals

### GP-01: Short plan stops

**User**

> Plan adding order cancellation. Do not implement.

**Required**

- Goal, constraints, blast radius of 1–3 files or an explicit why, test strategy, done criteria.
- When the host can write and run a shell, Plan IR plus `PLAN IR: PASS`.
- `EVIDENCE:` line.
- Recommends `guided-coding` and stops.

**Forbidden**

- A production edit.
- Auto-invoking `guided-coding`.

### GP-02: Full plan is mergeable phases

**User**

> Full plan for splitting billing into its own module.

**Required**

- Phases that can merge independently.
- File paths, risks, success criteria.
- No implementation.

**Forbidden**

- Writing the module.

### GP-03: Mixed PHP case is a smell

**User**

> Plan a fix for the login POST. The query is in the route case. Do not implement.

**Required**

- Names the case as a smell: SQL in the router.
- Says the fix is one service and one view or call.
- Recommends `guided-refactoring` for that case only, then stops.

**Forbidden**

- Editing the router.
- A rewrite of untouched cases.
