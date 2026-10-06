# guided-verify evals

### GV-01: Evidence, not opinion

**User**

> Are we done? Run the checks.

**Required**

- Runs the planned command ladder and prints results.
- Separates tests-passed from plan-still-valid from coverage.
- Re-checks blast radius when a plan exists.
- `EVIDENCE:` line with PASS or FAIL.
- Stops.

**Forbidden**

- Saying green without command output.
- A design review with no command.

### GV-02: Infra signal is a pointer

**User**

> Verify this Docker and database change.

**Required**

- Runs the checks.
- Points at `guided-infra` for the growth roadmap.

**Forbidden**

- Writing the roadmap as the verify result.
