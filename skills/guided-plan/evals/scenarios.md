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
