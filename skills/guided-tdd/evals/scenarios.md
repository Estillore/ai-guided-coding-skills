# guided-tdd evals

### GT-01: RED before GREEN

**User**

> TDD the cancellation validator. Tests first.

**Required**

- Writes the failing test and runs it before implementation.
- Reports the RED failure from tool output.
- Applies the minimal GREEN change and re-runs.
- Coverage gate on touched code.
- `EVIDENCE:` line.

**Forbidden**

- Implementation before a failing test run.
- Extra features beyond the current test.

### GT-02: General implement is not this skill

**User**

> Just ship the cancellation endpoint.

**Required**

- Names `guided-coding` as the match.

**Forbidden**

- Inventing a coverage-only workflow the user did not ask for.
