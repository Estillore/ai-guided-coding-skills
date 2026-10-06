# guided-docs evals

Pass only when every Required behavior is present and no Forbidden behavior occurs.

### GD-01: Codebase map, not a lesson

**User**

> What does this code do? Give me the mental model.

**Required**

- Maps the relevant slice: entry points, dependency direction, conventions, real test command.
- Writes or shows a repo-map shaped snapshot.
- Ends with `EVIDENCE:` naming `docs/repo-map.json` or SKIP plus the host limit.
- Recommends `guided-plan` and stops.

**Forbidden**

- A step-by-step lesson or hint ladder.
- An implementation plan with phases.
- Editing production code.

### GD-02: Library question stays on official docs

**User**

> Explain this library's mental model before we use it.

**Required**

- Cites current official docs as the source of truth.
- States when to use it and one failure mode.
- Does not invent API names.

**Forbidden**

- Teaching exercises.
- A feature implementation.

### GD-03: Vibe-coded PHP is a page map

**User**

> This vanilla PHP app is a mess. Where does the login bug live?

**Required**

- Treats it as vanilla PHP, not a framework.
- Lists entry scripts, shared includes, and the login include chain.
- Does not claim the whole tree was read.

**Forbidden**

- A Laravel or MVC rewrite proposal as the map.
- Editing the page before the chain exists.
