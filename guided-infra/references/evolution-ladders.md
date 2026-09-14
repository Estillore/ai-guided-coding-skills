# Evolution ladders — detailed reference

Used by `guided-infra`. Ladders are ordered: detect the current rung from concrete
signals, then recommend the next 1–2 rungs. Never jump without signals.

Each rung lists: **signal** (what you observe), **pattern** (the named technique),
**guard** (when NOT to move up).

---

## 1. Architecture ladder

### Rung 0 — Flat MVC
- Signal: controllers/routes contain business logic + DB queries.
- Next: **Service layer** — extract business operations into service classes.
- Guard: trivial CRUD-only apps can stay here.

### Rung 1 — Service layer
- Signal: controllers thin, but services still query the DB directly.
- Next: **Repository layer** — persistence behind interfaces; services depend on abstractions.
- Guard: one-datastore, one-team apps can defer.

### Rung 2 — Layered (controller → service → repository)
- Signal: layers exist; persistence entities cross the API boundary.
- Next: **DTOs at boundaries** — request/response shapes decoupled from entities.
- Guard: internal APIs consumed only by the same repo may defer DTOs.

### Rung 3 — DTOs added
- Signal: business rules still import framework/ORM types; domain hard to test.
- Next: **Domain layer (framework-free)** — entities, value objects, ports; adapters at the edge (hexagonal).
- Guard: CRUD-with-validation apps rarely need a full domain layer.

### Rung 4 — Domain layer
- Signal: services grow into multi-purpose classes; “god services”.
- Next: **Actions / Use cases** — one class per operation, single reason to change.
- Guard: avoid class explosion for tiny operation sets.

### Rung 5 — Growing domains
- Signal: coupling across business areas; unclear ownership; merge conflicts.
- Next: **Modular monolith** — bounded contexts as modules with enforced boundaries (arch tests / deptrac / dependency-cruiser).
- Guard: do not split into services yet — modules first.

### Rung 6 — Event side-effects
- Signal: a DB write followed by an event publish / queue push (dual-write crash window).
- Next: **Transactional outbox** + relay/worker; idempotent consumers.
- Guard: read-only or single-writer flows don't need it.

### Rung 7 — Read-heavy
- Signal: repeated expensive reads; same DB serves reads + writes.
- Next: **Cache layer / read models** — cache-aside or projections, with invalidation defined.
- Guard: premature caching without a measured hot path adds bugs, not speed.

### Rung 8 — Real team + deploy pressure
- Signal: independent teams blocked on one deploy; scaling needs differ per capability.
- Next: **Strangler fig** — peel one capability at a time behind the existing API.
- Guard: services multiply operational cost; only with signals.

---

## 2. Infrastructure ladder

### Rung 0 — Nothing
- Signal: no Dockerfile, environment-specific setup scripts.
- Next: **Containerize** — Dockerfile + compose (app + db), env via variables.
- Guard: static sites can go straight to a platform/CDN.

### Rung 1 — Single compose
- Signal: compose exists; services use image defaults.
- Next: **Reliability baseline** — healthchecks, restart policies, resource limits, non-root user, multi-stage builds.
- Guard: none — this is the minimum for anything long-running.

### Rung 2 — Secrets hygiene
- Signal: literal secrets in compose/env; `.env` tracked in git.
- Next: **Secret management** — untrack, rotate, inject via environment/secret manager.
- Guard: none — always act on exposed secrets.

### Rung 3 — Backups
- Signal: DB service present, no backup asset / restore runbook.
- Next: **Backups + tested restore** — scheduled dump/snapshot; documented restore drill.
- Guard: none once data matters.

### Rung 4 — Observability
- Signal: no logs/metrics/error tracking; failures discovered by users.
- Next: **Structured logs + error tracking + health endpoint** (+ metrics when traffic grows).
- Guard: hobby apps can start with logging only.

### Rung 5 — Edge / Cloudflare
- Signal: origin directly exposed; assets served by app; no WAF/CDN.
- Next: **Cloudflare in front** — DNS + TLS, WAF rules, cache; R2 for large/static assets; Workers for edge logic when it truly belongs at the edge.
- Guard: keep business logic in the app; edge is for delivery and protection.

### Rung 6 — Async
- Signal: request handlers doing slow/blocking side work; cron scripts on the app host.
- Next: **Queue workers + scheduler** as separate services (compose service → platform worker), with retries and dead-letter.
- Guard: fire-and-forget without retries recreates the dual-write problem.

### Rung 7 — Data scale
- Signal: data volume/query latency growth; connection pressure.
- Next: **Indexes + pooling**, then **replicas / read models**, then partitioning/archival.
- Guard: measure first; replicas without read routing solve nothing.

### Rung 8 — Orchestration / HA
- Signal: uptime requirements, multiple nodes, real ops capacity.
- Next: **Managed platform first** (Railway/Fly/Cloud Run/etc. or Cloudflare Containers), k8s only with a team that can run it.
- Guard: k8s without ops capacity is a downgrade.

### Rung 9 — Zero-downtime migrations
- Signal: schema changes ship with downtime or deploy freezes.
- Next: **Expand–contract** — add new shape, backfill, dual-write/read, switch, remove old. Pairs with a migration gate in CI.
- Guard: single-instance hobby apps can keep simple migrations.

---

## 3. Data growth sub-ladder

1. Add indexes for real query patterns (EXPLAIN evidence).
2. Connection pooling (proxy or driver-level).
3. Read replicas for read-heavy endpoints.
4. Cache/read models for hot paths.
5. Partition or archive cold data.
6. Split stores only when access patterns demonstrably differ.

---

## 4. Security hardening sub-ladder

1. Secrets out of source (untrack, rotate, env/manager).
2. Least-privilege DB users; no root DB in the app service.
3. Edge protection (WAF/rate limiting) when public.
4. Dependency audits in CI (language SCA + react-doctor/supply chain for Node).
5. Backup encryption + access review.
6. AuthZ checks at server boundaries (guided-review verifies).

---

## 5. Decision gates — when to use this vs that

Starter criteria only. **Always re-verify against the current official docs at audit
time** — the docs are the standard, this table is the checklist of what to look up.

| Decision | Prefer this when | Prefer that when | Verify in |
|----------|------------------|------------------|-----------|
| Queue vs cron vs in-request | Retries, ordering, backpressure, or dead-letter matter; work outlives the request | Fixed schedule, idempotent, short, no ordering needs → cron; fast + critical to the response → in-request | Queue lib docs (delivery guarantees), framework scheduler docs |
| Cache vs read replica vs index | Repeated identical reads, tolerance for staleness, invalidation defined | Fresh reads or write-heavy → replica; slow single query → index first (EXPLAIN) | Cache docs (invalidation), DB docs (replication, indexing) |
| Object storage vs local disk vs app-served | User uploads, large/static assets, multi-instance deploys | Ephemeral or single-node scratch → local disk; never serve large files from the app process | Storage provider docs (durability, egress), framework filesystem docs |
| Edge/WAF/CDN vs origin hardening | Public traffic, bots, global users, static cacheability | Internal app, no public surface — harden the origin instead | Edge provider docs (WAF, cache rules, TLS) |
| Managed DB vs self-hosted | No DBA capacity, backups/HA needed fast | Regulatory pinning, exotic tuning, existing ops team | Managed DB docs (SLA, backup, failover terms) |
| Containers vs serverless vs plain VM | Reproducible envs, multi-service, portable deploys | Event-driven spiky work → serverless; single static site → platform/VM | Runtime docs (cold starts, limits, pricing model) |
| Monorepo vs single app vs split repos | Shared code + atomic cross-cutting changes, one team | Independent deploy cadences and ownership → split (with versioned contracts) | Tooling docs (workspaces, CI partitioning) |
| Multi-stage vs single-stage build | Slow installs, large base images, secret-free final layers | Tiny interpreted app with no build step — keep it simple | Docker docs (build cache, layer best practices) |

Rule: state the criterion, cite the doc, then apply it to the observed signal.
“No criterion found” means the item stays out of Now.

---

## When to recommend a migration (“this → that”)

Migrate only when the current rung is actively blocking (latency, cost, reliability,
team) — never for novelty:

- **Hosting**: single VM → managed platform (when ops burden > platform cost).
- **DB**: SQLite → server DB (when multi-writer/concurrency), single DB → replicas (read scale), self-managed → managed (ops burden).
- **Assets**: served by app → object storage/CDN (bandwidth, cache).
- **Edge**: no protection → Cloudflare (WAF/CDN/TLS).
- **Async**: in-request → queue (latency, reliability).

Each migration gets: current signal, target, migration pattern (often **strangler fig**
or **expand–contract**), rollback path, and a cost note. Large migrations go to
`guided-plan` first.

---

## 6. Vanilla / framework-less starters

Vanilla projects (plain PHP scripts, no composer, flat files) enter every ladder at
rung 0. First rungs are cheap and high-leverage:

- **Packaging**: no manifest → adopt the ecosystem manager (Composer + PSR-4
  autoloading for PHP, npm/pip/gomod elsewhere). Signal: `packaging: []`.
- **DB access**: raw `mysqli_*` / concatenated queries → PDO with prepared statements,
  then the repository rung. Signal: read-code fact (the harness can't see this).
- **Schema**: `.sql` dumps → a migration runner (Phinx / Doctrine Migrations for PHP,
  framework-native elsewhere). Signal: `schema_assets > 0`, `migrations == 0`.
- **Entry**: scattered public scripts → single front controller (`public/index.php`)
  with routing. Signal: read-code fact.
- **Tests**: no runner → PHPUnit/Pest + `tests/` dir before any refactor rung.
  Signal: `ops.no-tests-detected`.

Same rules apply: evidence first, next rung only, doc-backed criteria.
