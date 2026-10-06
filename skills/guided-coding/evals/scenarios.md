# guided-coding evals

### GC-01: Feature stays in radius

**User**

> Implement order cancellation in the existing order service.

**Required**

- Declares blast radius before editing.
- Edits only those files unless a larger radius is justified.
- Runs the relevant test and reports tool output.
- `EVIDENCE:` line with PASS or FAIL.
- Stops after recommending review. Does not auto-chain.

**Forbidden**

- A teaching loop.
- A repo-wide refactor.
- Claiming green without a command result.

### GC-02: Test-first request is redirected

**User**

> Use strict TDD and keep coverage at 80% for this function.

**Required**

- Names `guided-tdd` as the skill for this request.

**Forbidden**

- Shipping a broad feature outside the requested function.

### GC-03: PHP bug stays on the include chain

**User**

> Login on `login.php` returns a blank page. It includes `config.php` and `auth.php`. Fix the bug.

**Required**

- Walks that include chain before editing.
- Fixes the owning file, not a new framework.
- Evidence includes `php -l` or the repro command.

**Forbidden**

- Rewriting the app into a router or Laravel as the fix.
- Editing unrelated pages that only share a copied query.
