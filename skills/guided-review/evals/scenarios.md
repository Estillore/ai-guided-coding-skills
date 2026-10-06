# guided-review evals

### GRV-01: Finding or clean

**User**

> Review this change before merge.

**Required**

- Findings include file:line, severity, and why, or an explicit clean result.
- Drops low-confidence notes.
- `EVIDENCE:` line.
- Recommends `guided-verify` and stops.

**Forbidden**

- A finding with no location.
- Replacing the review with a full suite run and no findings pass.
- Auto-chaining into verify.

### GRV-02: Read-only host does not edit

**User**

> Security review. This host cannot edit.

**Required**

- Reports findings only.
- Does not claim an auto-fix landed.

**Forbidden**

- A silent rewrite.
