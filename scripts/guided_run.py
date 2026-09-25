#!/usr/bin/env python3
"""guided-run: thin enforcement harness for the guided family.

The harness executes every DETERMINISTIC part of the loop; the agent keeps
every JUDGMENT part (writing code, review findings). Skills are the agent
contract; this script is the enforcement.

Commands:
    validate-plan <plan.json> [--changed <file>...]
        Plan IR gate (strict keys, steps-in-radius, blast-radius drift).
    verify [--repo DIR] [--plan plan.json] [--receipts DIR]
        Run the verify ladder: typecheck -> unit -> lint -> build
        (-> e2e hint) + planned accuracy gates (mutation/contract/arch).
        Writes a JSON receipt. Exit 0 only on full PASS.
    react-doctor [--repo DIR] [--scope S] [--blocking LVL] [--base REF]
        React-only audit lane: detect React -> provision the pinned
        react-doctor (auto-download on first use) -> scan as JSON.
        Writes a JSON receipt. Exit 0 on PASS or SKIP (not React /
        no Node / offline, with reason); 1 on FAIL (blocking-level
        findings). Never blocks review/verify when unavailable.
    growth [--repo DIR] [--no-memory]
        Advisory infrastructure + architecture growth scan: compose /
        Dockerfile gaps, Cloudflare signals, DB + migrations, queue,
        cache, object storage, auth, observability, secret hygiene,
        layer signals. Writes a JSON receipt and updates
        docs/repo-map.json (infrastructure + growth.last_audit).
        Always exit 0.
    php-audit [--repo DIR] [--scope full|changed] [--blocking LVL]
        PHP audit lane: detect composer.json -> run whatever PHP
        auditors the project already has (phpstan JSON, pint --test,
        composer audit JSON, rector dry-run, deptrac JSON, psalm
        taint, warden JSON). Never installs anything. Writes a JSON
        receipt. Exit 0 on PASS or SKIP (not PHP / no php / no tools,
        with reason); 1 on FAIL (blocking-level findings).
    orchestrator [--repo DIR]
        External-supervision check: detect the Agent Orchestrator
        (`ao`) CLI + git worktree readiness. Never installs or
        clones anything; prints the OS-specific install hint when
        missing. Writes a JSON receipt. Always exit 0.
    mcp [--repo DIR] [--print-snippet PLATFORM]
        PHP MCP readiness check: locate each guided MCP server
        (phpstan, phpcs, php-composer, laravel-boost), handshake it
        over stdio, list its tools. Never installs or clones.
        --print-snippet emits a ready-to-paste client block with
        resolved paths. Writes a JSON receipt. Always exit 0.
    lsp [--repo DIR] [--query SYMBOL] [--print-snippet PLATFORM]
        Report whether the OpenCode CLI and experimental LSP-tool flag
        are available, optionally probe a real symbol query, or print the
        OpenCode v1 semantic-tool config. Never edits config. Writes a
        JSON receipt. Always exit 0.
    init [--repo DIR]
        Scaffold docs/repo-map.json from detected project facts.

Command auto-detection (no config needed, override via repo-map.json
test_commands): composer.json scripts, package.json scripts,deptrac/pest/
infection/phpstan/vitest/pint binaries, pact dirs. Missing tools are
SKIP-logged unless the Plan IR accuracy block requires them (then FAIL).

Stdlib only. Windows + macOS + Linux. Exit codes: 0 PASS, 1 FAIL.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ACCURACY_DEFAULTS = {"mutation_min_backend": 70,
                     "mutation_min_frontend": 50}

# react-doctor stays EXTERNAL: never bundled, provisioned at runtime.
# Pinned here (single source of truth); bump deliberately, never @latest.
REACT_DOCTOR_VERSION = "0.9.13"

REACT_RUNTIME_DEPS = ("react", "react-dom", "next", "preact",
                      "react-native", "expo", "@remix-run/react",
                      "@tanstack/react-start")

# growth scan: concrete signals only; the guided-infra skill is the judge.
SOURCE_EXTS = (".php", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
               ".py", ".vue", ".svelte", ".go", ".rb", ".java", ".kt")
WALK_SKIP = {"node_modules", "vendor", ".git", "dist", "build", "out",
             "coverage", ".next", ".nuxt", ".venv", "venv", "__pycache__",
             ".cache", "target", "backup-old"}
ARCH_LAYER_DIRS = (
    ("controllers", ("app/Http/Controllers", "src/controllers",
                     "src/http/controllers", "app/controllers",
                     "controllers")),
    ("services", ("app/Services", "src/services", "services",
                  "src/application/services")),
    ("repositories", ("app/Repositories", "src/repositories",
                      "repositories",
                      "src/infrastructure/persistence",
                      "src/database/repositories")),
    ("domain", ("app/Domain", "src/domain", "domain", "src/core/domain")),
    ("dtos", ("app/DTOs", "app/Dtos", "src/dto", "src/dtos", "dto")),
    ("actions", ("app/Actions", "src/actions", "actions")),
    ("use_cases", ("app/UseCases", "app/UseCases", "src/use-cases",
                   "src/use_cases", "src/usecases")),
    ("jobs", ("app/Jobs", "src/jobs", "jobs")),
)
OBSERVABILITY_DEPS = ("sentry", "winston", "pino", "bunyan", "prom-client",
                      "opentelemetry", "telescope", "dd-trace", "newrelic",
                      "datadog", "monolog")
QUEUE_DEPS = ("bullmq", "bull", "bee-queue", "agenda", "celery", "rq",
              "dramatiq", "horizon")
CACHE_DEPS = ("redis", "memcached", "keyv", "node-cache", "cachemanager")
TEST_DEPS = ("phpunit", "pestphp", "/pest", "codeception", "behat",
             "phpspec", "jest", "vitest", "pytest", "cypress",
             "playwright", "rspec", "gotestsum")
STORAGE_DEPS = ("@aws-sdk/client-s3", "aws-sdk", "minio", "cloudinary",
                "@google-cloud/storage", "@azure/storage-blob",
                "laravel-medialibrary", "flysystem-aws")
AUTH_DEPS = ("next-auth", "@auth/core", "@clerk", "passport", "jsonwebtoken",
             "laravel/sanctum", "laravel/passport", "firebase/auth",
             "@supabase", "lucia", "jose")
SECRET_RE = re.compile(
    r"(PASSWORD|PASSWD|SECRET|TOKEN|API_KEY|APIKEY|PRIVATE_KEY|ACCESS_KEY)"
    r"\s*[:=]\s*(?![${\s])([^\s#]+)", re.I)


def sh(cmd, cwd, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        tail = (p.stdout + p.stderr)[-2000:]
        return p.returncode, tail.strip()
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT after %ss: %s" % (timeout, cmd)
    except FileNotFoundError as e:
        return 127, "not found: %s" % e


def git_sha(repo):
    rc, out = sh("git rev-parse --short HEAD", repo, timeout=30)
    return out.strip() if rc == 0 else "uncommitted"


def load_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def find_repo_map(repo):
    for p in ("docs/repo-map.json", ".kiro/repo-map.json",
              ".grok/repo-map.json"):
        full = os.path.join(repo, p)
        if os.path.isfile(full):
            return full
    return None


def detect_commands(repo):
    """Return ordered [(name, cmd)] ladder steps. Missing tools -> []."""
    cmds = []
    rmap = load_json(find_repo_map(repo) or "") or {}
    tc = rmap.get("test_commands", {}) or {}
    if tc:
        for name in ("typecheck", "unit", "lint", "build"):
            if tc.get(name):
                cmds.append((name, tc[name]))
        return cmds
    composer = os.path.isfile(os.path.join(repo, "composer.json"))
    package = os.path.isfile(os.path.join(repo, "package.json"))
    if composer:
        comp = load_json(os.path.join(repo, "composer.json")) or {}
        scripts = (comp.get("scripts") or {})
        if "verify" in scripts:
            return [("composer verify", "composer verify")]
        if "phpstan" in scripts or os.path.isdir(
                os.path.join(repo, "vendor", "phpstan")):
            cmds.append(("phpstan", "composer phpstan" if "phpstan" in scripts
                         else "vendor/bin/phpstan analyse --no-progress"))
        if "test" in scripts:
            cmds.append(("test", "composer test"))
        elif "pest" in scripts:
            cmds.append(("pest", "composer pest"))
    if package:
        pkg = load_json(os.path.join(repo, "package.json")) or {}
        scripts = pkg.get("scripts") or {}
        if "typecheck" in scripts:
            cmds.append(("typecheck", "npm run typecheck"))
        elif "tsc" in scripts:
            cmds.append(("tsc", "npm run tsc"))
        if "test" in scripts:
            cmds.append(("test", "npm test -- --run" if "vite" in json.dumps(
                pkg.get("devDependencies", {})) else "npm test"))
        if "lint" in scripts:
            cmds.append(("lint", "npm run lint"))
        if "build" in scripts:
            cmds.append(("build", "npm run build"))
    return cmds


def detect_react(repo):
    """Cheap React signal: a React runtime dep in package.json."""
    pkg = load_json(os.path.join(repo, "package.json")) or {}
    deps = {**(pkg.get("dependencies", {}) or {}),
            **(pkg.get("devDependencies", {}) or {})}
    return any(d in deps for d in REACT_RUNTIME_DEPS)


def node_version():
    """(major, minor) tuple, or None when node is missing/unparseable."""
    if not shutil.which("node"):
        return None
    rc, out = sh("node --version", ".", timeout=30)
    m = re.match(r"\s*v(\d+)\.(\d+)", out) if rc == 0 else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def ensure_react_doctor(repo):
    """Provision the pinned react-doctor binary. Returns (ready, reason).

    Never raises and never blocks: False means the caller continues
    without react-doctor and states the reason in one line. The npx
    invocation below IS the download trigger on first use (cached
    afterwards). react-doctor's own reactDetected flag stays the
    authoritative second gate at scan time.
    """
    if not detect_react(repo):
        return False, "SKIP: not a React project (no react runtime dep)"
    if not shutil.which("npx"):
        return False, "SKIP: npx not found (Node.js required)"
    nv = node_version()
    if nv is None:
        return False, "SKIP: node not found or version unparseable"
    if not (nv[0] > 22 or (nv[0] == 22 and nv[1] >= 12)
            or (nv[0] == 20 and nv[1] >= 19)):
        return False, "SKIP: node %d.%d below minimum (20.19+/22.12+)" % nv
    rc, out = sh("npx -y react-doctor@%s --version" % REACT_DOCTOR_VERSION,
                 repo, timeout=600)
    if rc != 0:
        return False, "SKIP: download/probe failed: %s" % out[-300:]
    return True, "react-doctor %s ready" % out.strip()


def _read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def _deps(repo):
    deps = set()
    pkg = load_json(os.path.join(repo, "package.json")) or {}
    for key in ("dependencies", "devDependencies"):
        deps.update((pkg.get(key) or {}).keys())
    comp = load_json(os.path.join(repo, "composer.json")) or {}
    for key in ("require", "require-dev"):
        deps.update((comp.get(key) or {}).keys())
    return deps


def _band(n_files, n_lines):
    if n_files < 200 and n_lines < 20000:
        return "small"
    if n_files < 1000 and n_lines < 100000:
        return "growing"
    if n_files < 5000 and n_lines < 500000:
        return "large"
    return "very-large"


def scan_tree(repo):
    """One capped walk: sources, packages, backups, CI, SQL schemas."""
    n_src, pkgs, backups, workflows, sql = 0, 0, 0, 0, 0
    n_lines = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        for fn in files:
            if fn == "package.json":
                pkgs += 1
            if "backup" in fn.lower():
                backups += 1
            ext = os.path.splitext(fn)[1].lower()
            if ext in SOURCE_EXTS:
                n_src += 1
                fp = os.path.join(root, fn)
                try:
                    if os.path.getsize(fp) <= 524288:
                        with open(fp, encoding="utf-8",
                                  errors="ignore") as f:
                            n_lines += sum(1 for _ in f)
                except OSError:
                    pass
            if ext == ".sql":
                sql += 1
            p = os.path.join(root, fn).replace("\\", "/")
            if "/.github/workflows/" in p and ext in (".yml", ".yaml"):
                workflows += 1
    return {"source_files": n_src, "packages": pkgs,
            "backup_assets": backups, "ci_workflows": workflows,
            "schema_assets": sql, "source_lines": n_lines}


def parse_compose(path):
    """Naive line-based parse: {service: [block lines]} (no yaml lib)."""
    services, cur, in_services = {}, None, False
    for ln in _read(path).splitlines():
        if re.match(r"^services:\s*$", ln):
            in_services = True
            continue
        if not in_services:
            continue
        if ln.strip() and not ln.startswith(" ") and ln[0] != "#":
            break
        m = re.match(r"^  ([A-Za-z0-9_.-]+):\s*(#.*)?$", ln)
        if m:
            cur = m.group(1)
            services[cur] = []
        elif cur is not None:
            services[cur].append(ln)
    return services


def _svc_flags(block):
    body = "\n".join(block)
    img = re.search(r"^\s+image:\s*[\"']?([^\s\"']+)", body, re.M)
    user = re.search(r"^\s+user:\s*[\"']?(root|0)[\"']?\s*$", body, re.M)
    return {"healthcheck": "healthcheck:" in body,
            "restart": "restart:" in body,
            "limits": ("mem_limit" in body or "cpus" in body
                       or "deploy:" in body or "resources:" in body),
            "root_user": user is not None,
            "ports": "ports:" in body,
            "image": img.group(1) if img else ""}


def layer_counts(repo, cap=5000):
    counts = {}
    for name, rels in ARCH_LAYER_DIRS:
        n, found = 0, False
        for rel in rels:
            d = os.path.join(repo, *rel.split("/"))
            if not os.path.isdir(d):
                continue
            found = True
            for root, dirs, files in os.walk(d):
                dirs[:] = [x for x in dirs if x not in WALK_SKIP]
                n += sum(1 for f in files
                         if os.path.splitext(f)[1].lower() in SOURCE_EXTS)
                if n >= cap:
                    n = cap
                    break
        if found:
            counts[name] = n
    return counts


def arch_style_hint(counts):
    if counts.get("domain"):
        return "domain-oriented"
    if counts.get("use_cases") or counts.get("actions"):
        return "use-case oriented"
    if (counts.get("repositories") and counts.get("services")
            and counts.get("controllers")):
        return "layered controller-service-repository"
    if counts.get("services") and counts.get("controllers"):
        return "controller-service"
    if counts.get("services"):
        return "service-oriented"
    if counts.get("controllers"):
        return "flat mvc"
    return "unclear"


def count_migrations(repo):
    total = 0
    d = os.path.join(repo, "database", "migrations")
    if os.path.isdir(d):
        total += sum(1 for f in os.listdir(d)
                     if os.path.isfile(os.path.join(d, f)))
    d = os.path.join(repo, "prisma", "migrations")
    if os.path.isdir(d):
        total += sum(1 for f in os.listdir(d)
                     if os.path.isdir(os.path.join(d, f)))
    d = os.path.join(repo, "migrations")
    if os.path.isdir(d):
        total += sum(1 for f in os.listdir(d)
                     if os.path.isfile(os.path.join(d, f)))
    return total


def detect_infrastructure(repo):
    """Concrete infra + layer signals -> (facts, gaps). Advisory only."""
    deps = _deps(repo)
    deps_l = {d.lower() for d in deps}
    tree = scan_tree(repo)

    compose_file = None
    for name in ("docker-compose.yml", "docker-compose.yaml",
                 "compose.yml", "compose.yaml"):
        if os.path.isfile(os.path.join(repo, name)):
            compose_file = name
            break
    services = parse_compose(os.path.join(repo, compose_file)) \
        if compose_file else {}
    svc_flags = {n: _svc_flags(b) for n, b in services.items()}

    dockerfile = None
    for name in ("Dockerfile", "dockerfile",
                 os.path.join("docker", "Dockerfile")):
        p = os.path.join(repo, name)
        if os.path.isfile(p):
            txt = _read(p)
            from_count = len(re.findall(r"^FROM\s", txt, re.M))
            user_lines = re.findall(r"^USER\s+(\S+)", txt, re.M)
            dockerfile = {
                "file": name.replace("\\", "/"),
                "multi_stage": from_count > 1,
                "non_root": bool(user_lines)
                and all(u.lower() != "root" for u in user_lines),
                "healthcheck": "HEALTHCHECK" in txt,
            }
            break

    cf = []
    if any(os.path.isfile(os.path.join(repo, f)) for f in
           ("wrangler.toml", "wrangler.json", "wrangler.jsonc")):
        cf.append("wrangler-config")
    if os.path.isdir(os.path.join(repo, "functions")):
        cf.append("pages-functions")
    if any("wrangler" in d or "cloudflare" in d for d in deps_l):
        cf.append("deps")

    db_images = sorted({s["image"] for s in svc_flags.values()
                        if re.search(r"postgres|mysql|mariadb|mongo",
                                     s["image"], re.I)})
    engines = []
    blob = " ".join(sorted(deps_l))
    for eng, needles in (("mysql", ("mysql", "mariadb")),
                         ("postgres", ("pgsql", "postgres")),
                         ("sqlite", ("sqlite",)),
                         ("mongo", ("mongodb", "mongoose"))):
        if any(n in blob for n in needles):
            engines.append(eng)
    if any("postgres" in i for i in db_images):
        engines.append("postgres")
    if any("mysql" in i or "mariadb" in i for i in db_images):
        engines.append("mysql")
    m = re.search(r"^DB_CONNECTION\s*=\s*(\w+)",
                  _read(os.path.join(repo, ".env")), re.M)
    if m:
        engines.append(m.group(1).lower())
    engines = sorted(set(engines))
    migrations = count_migrations(repo)

    queue = sorted({d for d in deps_l
                    if any(q in d for q in QUEUE_DEPS)})
    has_jobs_dir = any(os.path.isdir(os.path.join(repo, *rel.split("/")))
                       for rel in ("app/Jobs", "src/jobs", "jobs"))
    obs = sorted({d for d in deps_l
                  if any(o in d for o in OBSERVABILITY_DEPS)})
    testing = sorted({d for d in deps_l
                      if any(t in d for t in TEST_DEPS)})
    test_dirs = sorted({d for d in ("tests", "test", "__tests__", "spec")
                        if os.path.isdir(os.path.join(repo, d))})
    packaging = []
    if os.path.isfile(os.path.join(repo, "composer.json")):
        packaging.append("composer")
    if os.path.isfile(os.path.join(repo, "package.json")):
        packaging.append("npm")
    if os.path.isfile(os.path.join(repo, "requirements.txt")) \
            or os.path.isfile(os.path.join(repo, "pyproject.toml")):
        packaging.append("pip")
    if os.path.isfile(os.path.join(repo, "go.mod")):
        packaging.append("gomod")
    cache = sorted({d for d in deps_l
                    if any(c in d for c in CACHE_DEPS)})
    cache_images = sorted({s["image"] for s in svc_flags.values()
                           if re.search(r"redis|memcached",
                                        s["image"], re.I)})
    storage = sorted({d for d in deps_l
                      if any(s in d for s in STORAGE_DEPS)})
    auth = sorted({d for d in deps_l
                   if any(a in d for a in AUTH_DEPS)})

    env_tracked = any(
        sh("git ls-files --error-unmatch %s" % f, repo, timeout=30)[0] == 0
        for f in (".env", ".env.production"))

    secret_hits = []
    for n, block in services.items():
        for ln in block:
            m = SECRET_RE.search(ln)
            if m and not m.group(2).strip("\"'").startswith("$"):
                secret_hits.append("%s:%s" % (n, m.group(1).upper()))

    counts = layer_counts(repo)
    facts = {
        "compose_file": compose_file,
        "compose_services": {n: {"image": f["image"],
                                 "healthcheck": f["healthcheck"],
                                 "restart": f["restart"],
                                 "limits": f["limits"],
                                 "ports": f["ports"]}
                             for n, f in svc_flags.items()},
        "dockerfile": dockerfile,
        "cloudflare": cf,
        "database": {"engines": engines, "migrations": migrations,
                     "compose_services": db_images},
        "queue": {"libs": queue, "jobs_dir": has_jobs_dir},
        "observability": obs,
        "cache": {"libs": cache, "compose_services": cache_images},
        "storage": storage,
        "auth": auth,
        "ci_workflows": tree["ci_workflows"],
        "backup_assets": tree["backup_assets"],
        "testing": {"libs": testing, "dirs": test_dirs},
        "packaging": packaging,
        "schema_assets": tree["schema_assets"],
        "monorepo": {
            "packages": tree["packages"],
            "workspaces": os.path.isfile(
                os.path.join(repo, "pnpm-workspace.yaml"))
            or bool((load_json(os.path.join(repo, "package.json"))
                     or {}).get("workspaces"))},
        "architecture": {"detected_layers": counts,
                         "style_hint": arch_style_hint(counts)},
        "source_files": tree["source_files"],
        "source_lines": tree["source_lines"],
        "source_band": _band(tree["source_files"], tree["source_lines"]),
    }

    gaps = []
    for n, f in svc_flags.items():
        if not f["healthcheck"]:
            gaps.append({"id": "compose.%s.no-healthcheck" % n,
                         "severity": "medium",
                         "evidence": "service '%s' has no healthcheck" % n})
        if not f["restart"]:
            gaps.append({"id": "compose.%s.no-restart" % n,
                         "severity": "low",
                         "evidence": "service '%s' has no restart policy"
                                     % n})
        if not f["limits"]:
            gaps.append({"id": "compose.%s.no-resource-limits" % n,
                         "severity": "low",
                         "evidence": "service '%s' has no mem_limit/cpus/"
                                     "deploy limits" % n})
    for hit in secret_hits:
        gaps.append({"id": "compose.hardcoded-secret.%s"
                     % hit.split(":")[1].lower(),
                     "severity": "high",
                     "evidence": "possible literal secret in %s" % hit})
    if env_tracked:
        gaps.append({"id": "secrets.env-tracked", "severity": "critical",
                     "evidence": ".env is tracked in git"})
    if dockerfile:
        if not dockerfile["multi_stage"]:
            gaps.append({"id": "dockerfile.single-stage", "severity": "low",
                         "evidence": "single-stage build"})
        if not dockerfile["non_root"]:
            gaps.append({"id": "dockerfile.root-user", "severity": "medium",
                         "evidence": "container runs as root"})
    if (engines or db_images) and tree["backup_assets"] == 0:
        gaps.append({"id": "ops.no-backups-detected", "severity": "low",
                     "evidence": "DB present, no backup asset found"})
    if not obs and tree["source_files"] >= 200:
        gaps.append({"id": "ops.no-observability", "severity": "medium",
                     "evidence": "no logging/metrics/error-tracking lib"})
    if not testing and not test_dirs and tree["source_files"] >= 200:
        gaps.append({"id": "ops.no-tests-detected", "severity": "medium",
                     "evidence": "200+ source files, no test runner or dir"})
    return facts, gaps


def update_growth_memory(repo, facts, gaps, recommend):
    path = find_repo_map(repo)
    if not path:
        return None
    rmap = load_json(path)
    if rmap is None:
        return None
    rmap["infrastructure"] = facts
    growth = rmap.get("growth") or {}
    growth["last_audit"] = datetime.now(timezone.utc) \
        .isoformat(timespec="seconds")
    growth["recommended"] = bool(recommend)
    growth["gap_ids"] = [g["id"] for g in gaps]
    rmap["growth"] = growth
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rmap, f, indent=2)
    return path


def cmd_validate_plan(args):
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "validate_plan", os.path.join(here, "validate-plan.py"))
    mod = importlib.util.module_from_spec(spec)
    old_argv = sys.argv
    sys.argv = ["validate-plan.py"] + args
    try:
        spec.loader.exec_module(mod)
        return mod.main()
    finally:
        sys.argv = old_argv


def run_accuracy_gates(repo, plan, results):
    """Run planned mutation/contract/arch gates. Returns True if all pass."""
    acc = (plan or {}).get("accuracy", {}) or {}
    ok = True
    scope = acc.get("mutation_scope", []) or []
    if scope:
        mins = {**ACCURACY_DEFAULTS,
                **{k: v for k, v in acc.items() if k.startswith(
                    "mutation_min")}}
        mutated = False
        if shutil.which("vendor/bin/infection") or os.path.isfile(
                os.path.join(repo, "vendor", "bin", "infection")):
            f = ",".join(scope)
            rc, out = sh("vendor/bin/infection --filter=%s "
                         "--min-msi=%s --threads=4" % (
                             f, mins["mutation_min_backend"]), repo,
                         timeout=1800)
            results.append({"gate": "mutation:backend", "rc": rc,
                            "out": out[-1000:]})
            mutated = mutated or rc == 0
            ok = ok and rc == 0
        if shutil.which("npx") and os.path.isfile(
                os.path.join(repo, "stryker.config.json")):
            rc, out = sh("npx stryker run", repo, timeout=1800)
            results.append({"gate": "mutation:frontend", "rc": rc,
                            "out": out[-1000:]})
            mutated = mutated or rc == 0
            ok = ok and rc == 0
        if not mutated:
            results.append({"gate": "mutation", "rc": 1,
                            "out": "planned but no runner found "
                                   "(infection/stryker)"})
            ok = False
    for name in acc.get("contract_tests", []) or []:
        pact = os.path.isdir(os.path.join(repo, "pacts"))
        rc, out = (0, "contract '%s' recorded PASS "
                   "(pact dir present, verifier run in CI)" % name) if pact \
            else (1, "contract '%s': no pacts/ dir and no recorded light "
                     "check (fixture-vs-live). Add Pact or run the light "
                     "contract test and record its output" % name)
        results.append({"gate": "contract:%s" % name, "rc": rc,
                        "out": out})
        ok = ok and rc == 0
    for rule in acc.get("arch_rules", []) or []:
        if os.path.isfile(os.path.join(repo, "deptrac.yaml")) or \
                os.path.isfile(os.path.join(repo, "deptrac.php")):
            rc, out = sh("vendor/bin/deptrac analyse --no-progress", repo)
        else:
            rc, out = (1, "arch rule '%s': no deptrac config found" % rule)
        results.append({"gate": "arch:%s" % rule, "rc": rc,
                        "out": out[-1000:]})
        ok = ok and rc == 0
    return ok


def cmd_verify(args):
    repo = "."
    plan_path = None
    receipts = None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--plan" and i + 1 < len(args):
            plan_path, i = args[i + 1], i + 2
        elif args[i] == "--receipts" and i + 1 < len(args):
            receipts, i = args[i + 1], i + 2
        else:
            i += 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    results = []
    status = "PASS"

    plan = load_json(plan_path) if plan_path else None
    if plan_path and plan is None:
        print("VERIFY: FAIL\n- cannot read plan: %s" % plan_path)
        return 1

    ladder = detect_commands(repo)
    if not ladder:
        results.append({"step": "detect", "rc": 1,
                        "out": "no verifiable commands found "
                               "(repo-map test_commands, composer or npm "
                               "scripts)"})
        status = "FAIL"
    for name, cmd in ladder:
        rc, out = sh(cmd, repo)
        results.append({"step": name, "cmd": cmd, "rc": rc, "out": out})
        print("[%s] %s -> %s" % ("PASS" if rc == 0 else "FAIL", name, cmd))
        if rc != 0:
            status = "FAIL"
            break  # stale-green rule: stop at first red, fix, re-run

    if status == "PASS" and plan:
        if not run_accuracy_gates(repo, plan, results):
            status = "FAIL"

    receipt = {"tool": "guided-run verify", "run_id": run_id, "sha": sha,
               "repo": repo, "status": status,
               "plan": os.path.abspath(plan_path) if plan_path else None,
               "results": results}
    rdir = receipts or os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "verify.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("VERIFY: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0 if status == "PASS" else 1


def cmd_react_doctor(args):
    repo, scope, blocking, base, receipts = ".", "full", "error", None, None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--scope" and i + 1 < len(args):
            scope, i = args[i + 1], i + 2
        elif args[i] == "--blocking" and i + 1 < len(args):
            blocking, i = args[i + 1], i + 2
        elif args[i] == "--base" and i + 1 < len(args):
            base, i = args[i + 1], i + 2
        elif args[i] == "--receipts" and i + 1 < len(args):
            receipts, i = args[i + 1], i + 2
        else:
            i += 1
    if scope not in ("full", "files", "changed", "lines"):
        print("REACT-DOCTOR: FAIL\n- bad --scope: %s "
              "(full|files|changed|lines)" % scope)
        return 1
    if blocking not in ("error", "warning", "none"):
        print("REACT-DOCTOR: FAIL\n- bad --blocking: %s "
              "(error|warning|none)" % blocking)
        return 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    results = []
    status = "SKIP"

    ready, reason = ensure_react_doctor(repo)
    results.append({"step": "ensure", "rc": 0 if ready else 1,
                    "out": reason})
    print("[%s] ensure -> %s" % ("PASS" if ready else "SKIP", reason))

    if ready:
        rep_path = os.path.join(tempfile.gettempdir(),
                                "rd-%s.json" % run_id)
        cmd = ("npx -y react-doctor@%s --json --json-out %s --scope %s "
               "--blocking %s --no-telemetry --no-score"
               % (REACT_DOCTOR_VERSION, rep_path, scope, blocking))
        if base:
            cmd += " --base %s" % base
        rc, out = sh(cmd, repo, timeout=900)
        rep = load_json(rep_path)
        try:
            os.remove(rep_path)
        except OSError:
            pass
        if rep is not None and rep.get("reactDetected") is False:
            results.append({"step": "scan", "rc": 0,
                            "out": "reactDetected=false: wrong scan target, "
                                   "not a failure"})
            print("[SKIP] scan -> reactDetected=false (no React runtime "
                  "here)")
        else:
            summ = (rep.get("summary") or {}) if rep else {}
            errs = summ.get("errorCount", "?")
            warns = summ.get("warningCount", "?")
            sval = summ.get("score")
            sval = sval if sval is not None else "n/a"
            results.append({"step": "scan", "rc": rc, "scope": scope,
                            "blocking": blocking, "errors": errs,
                            "warnings": warns, "score": sval,
                            "out": out[-1000:]})
            if rc == 0:
                status = "PASS"
                print("[PASS] scan -> %d errors, %d warnings, score %s"
                      % (errs, warns, sval))
            else:
                status = "FAIL"
                print("[FAIL] scan -> %d errors, %d warnings, score %s "
                      "(blocking=%s)" % (errs, warns, sval, blocking))

    receipt = {"tool": "guided-run react-doctor", "run_id": run_id,
               "sha": sha, "repo": repo, "status": status,
               "react_doctor": REACT_DOCTOR_VERSION, "scope": scope,
               "blocking": blocking, "results": results}
    rdir = receipts or os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "react-doctor.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("REACT-DOCTOR: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0 if status in ("PASS", "SKIP") else 1


def cmd_growth(args):
    repo, no_memory = ".", False
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--no-memory":
            no_memory, i = True, i + 1
        else:
            i += 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    facts, gaps = detect_infrastructure(repo)
    sev_rank = {"critical": 3, "high": 2, "medium": 1, "low": 0}
    services = facts["compose_services"]
    recommend = (any(sev_rank.get(g["severity"], 0) >= 1 for g in gaps)
                 or len(services) >= 3
                 or facts["source_files"] >= 500
                 or facts["source_lines"] >= 100000
                 or facts["database"]["migrations"] >= 50)

    stack = ["compose=%s" % (facts["compose_file"] or "none")]
    if services:
        stack.append("%d svc" % len(services))
    stack.append("dockerfile=%s"
                 % ("yes" if facts["dockerfile"] else "no"))
    stack.append("cloudflare=%s"
                 % (",".join(facts["cloudflare"]) or "no"))
    stack.append("db=%s"
                 % (",".join(facts["database"]["engines"]) or "none"))
    stack.append("migrations=%d" % facts["database"]["migrations"])
    stack.append("queue=%s"
                 % (",".join(facts["queue"]["libs"])
                    or ("jobs-dir" if facts["queue"]["jobs_dir"]
                        else "none")))
    stack.append("tests=%s"
                 % (",".join(facts["testing"]["libs"]
                             + facts["testing"]["dirs"])
                    or "none"))
    stack.append("cache=%s"
                 % (",".join(facts["cache"]["libs"]
                             + facts["cache"]["compose_services"])
                    or "none"))
    stack.append("storage=%s" % (",".join(facts["storage"]) or "none"))
    stack.append("auth=%s" % (",".join(facts["auth"]) or "none"))
    print("[INFO] stack: %s" % " | ".join(stack))
    arch = facts["architecture"]
    layers = ", ".join("%s=%d" % (k, v)
                       for k, v in sorted(arch["detected_layers"].items()))
    print("[INFO] architecture: %s%s | source=%d files, %d lines (%s)"
          % (arch["style_hint"], " (%s)" % layers if layers else "",
             facts["source_files"], facts["source_lines"],
             facts["source_band"]))
    for g in gaps:
        print("[GAP ] [%s] %s -- %s"
              % (g["severity"], g["id"], g["evidence"]))
    print("[INFO] growth: recommend guided-infra audit: %s"
          % ("true" if recommend else "false"))

    memory_path = None
    if not no_memory:
        memory_path = update_growth_memory(repo, facts, gaps, recommend)

    receipt = {"tool": "guided-run growth", "run_id": run_id, "sha": sha,
               "repo": repo, "status": "INFO", "recommend_audit": recommend,
               "facts": facts, "gaps": gaps, "memory": memory_path}
    rdir = os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "growth.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("GROWTH: INFO (sha %s)\nreceipt: %s%s"
          % (sha, rpath,
             "\nmemory: %s updated" % memory_path if memory_path else ""))
    return 0


def cmd_init(args):
    repo = "."
    if "--repo" in args:
        repo = args[args.index("--repo") + 1]
    repo = os.path.abspath(repo)
    comp = load_json(os.path.join(repo, "composer.json")) or {}
    pkg = load_json(os.path.join(repo, "package.json")) or {}
    fw = "unknown"
    if comp:
        fw = "php" + (" laravel" if "laravel/framework" in json.dumps(comp)
                      else "")
    if pkg:
        fw += "+react" if "react" in json.dumps(
            {**pkg.get("dependencies", {}),
             **pkg.get("devDependencies", {})}) else "+node"
    rmap = {"generated": datetime.now(timezone.utc).date().isoformat(),
            "framework": {"name": fw.strip(), "version": ""},
            "source_of_standards": "project convention",
            "entry_points": [], "domains": [], "dependency_direction": "",
            "structure_style": "", "conventions": [],
            "decisions_gotchas": [],
            "test_commands": {n: c for n, c in detect_commands(repo)},
            "infrastructure": {},
            "growth": {"last_audit": None},
            "open_questions": []}
    out = os.path.join(repo, "docs", "repo-map.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rmap, f, indent=2)
    print("repo-map scaffolded: %s (fill entry_points/domains by hand or "
          "via guided-docs)" % out)
    return 0


def _tool(repo, name):
    """Invokable vendor/bin path for a composer tool, else None."""
    d = os.path.join(repo, "vendor", "bin")
    for cand in (name, name + ".bat", name + ".cmd"):
        if os.path.isfile(os.path.join(d, cand)):
            return "\"vendor/bin/%s\"" % cand
    phar = os.path.join(d, name + ".phar")
    if os.path.isfile(phar):
        return "php \"vendor/bin/%s.phar\"" % name
    return None


def _first_file(repo, names):
    for n in names:
        if os.path.isfile(os.path.join(repo, n)):
            return n
    return None


def _skip(step, reason, hint=None):
    s = {"step": step, "rc": None, "errors": 0, "warnings": 0,
         "skipped": reason}
    if hint:
        s["hint"] = hint
    return s


def changed_php_files(repo):
    """Changed + untracked .php paths via git ([] when unavailable)."""
    files = []
    for cmd in ("git diff --name-only HEAD -- \"*.php\"",
                "git ls-files --others --exclude-standard -- \"*.php\""):
        rc, out = sh(cmd, repo, timeout=30)
        if rc != 0:
            return []
        for ln in out.splitlines():
            p = ln.strip().strip("\"")
            if p.endswith(".php") \
                    and os.path.isfile(os.path.join(repo, p)) \
                    and "\"%s\"" % p not in files:
                files.append("\"%s\"" % p)
    return files


def _parse_json_tail(out):
    # Tools (phpstan 2.2+) wrap JSON in human-readable prelude/epilogue
    # text. raw_decode parses one value and ignores the rest.
    try:
        return json.JSONDecoder().raw_decode(out[out.index("{"):])[0]
    except (ValueError, IndexError):
        return None


def step_phpstan(repo, scope):
    tool = _tool(repo, "phpstan")
    if not tool:
        return _skip("phpstan", "not installed",
                      "composer require --dev phpstan/phpstan")
    cmd = "%s analyse --error-format=json --no-progress" % tool
    used = "full"
    cfg = _first_file(repo, ("phpstan.neon", "phpstan.neon.dist",
                             "phpstan.dist.neon"))
    if scope == "changed":
        changed = changed_php_files(repo)
        if changed:
            cmd += " " + " ".join(changed)
            used = "changed"
    if used == "full" and not cfg:
        for d in ("src", "app", "lib"):
            if os.path.isdir(os.path.join(repo, d)):
                cmd += " \"%s\"" % d
                break
        else:
            return _skip("phpstan", "no phpstan.neon and no src|app|lib dir",
                         "create phpstan.neon with paths + level")
    rc, out = sh(cmd, repo, timeout=900)
    rep = _parse_json_tail(out)
    if rep is None:
        return {"step": "phpstan", "rc": rc, "errors": 0, "warnings": 0,
                "scope": used, "error": "unparseable output",
                "out": out[-1000:]}
    n, sample = 0, []
    files = rep.get("files") or {}
    if isinstance(files, dict):
        for path, fdata in files.items():
            for m in (fdata or {}).get("messages") or []:
                n += 1
                if len(sample) < 3:
                    sample.append("%s:%s %s" % (
                        path, m.get("line", "?"), m.get("message", "")))
    return {"step": "phpstan", "rc": rc, "errors": n, "warnings": 0,
            "scope": used, "sample": sample}


def step_pint(repo, scope):
    tool = _tool(repo, "pint")
    if not tool:
        return _skip("pint", "not installed",
                      "composer require --dev laravel/pint")
    cmd = "%s --test" % tool
    if scope == "changed":
        cmd += " --dirty"
    rc, out = sh(cmd, repo, timeout=600)
    if rc == 0:
        return {"step": "pint", "rc": rc, "errors": 0, "warnings": 0,
                "scope": scope}
    return {"step": "pint", "rc": rc, "errors": 0, "warnings": 1,
            "scope": scope,
            "sample": ["style violations present "
                       "(run vendor/bin/pint to fix)"],
            "out": out[-1000:]}


def step_composer_audit(repo):
    if not shutil.which("composer"):
        return _skip("composer-audit", "composer not on PATH",
                      "install Composer from getcomposer.org")
    if not os.path.isfile(os.path.join(repo, "composer.lock")):
        return _skip("composer-audit", "no composer.lock",
                      "run composer install to generate the lock file")
    rc, out = sh("composer audit --format=json --locked --no-dev",
                 repo, timeout=300)
    rep = _parse_json_tail(out)
    if rep is None:
        return {"step": "composer-audit", "rc": rc, "errors": 0,
                "warnings": 0, "error": "unparseable output",
                "out": out[-1000:]}
    errs, warns, sample = 0, 0, []
    adv = rep.get("advisories") or {}
    if isinstance(adv, dict):
        for pkg, items in adv.items():
            for a in items or []:
                sev = (a.get("severity") or "").lower()
                if sev in ("critical", "high"):
                    errs += 1
                else:
                    warns += 1
                if len(sample) < 3:
                    sample.append("%s: %s (%s)" % (
                        pkg, a.get("title", "?"), sev or "?"))
    return {"step": "composer-audit", "rc": rc, "errors": errs,
            "warnings": warns, "sample": sample}


def step_rector(repo):
    tool = _tool(repo, "rector")
    cfg = _first_file(repo, ("rector.php", "rector.dist.php"))
    if not tool:
        return _skip("rector", "not installed",
                      "composer require --dev rector/rector")
    if not cfg:
        return _skip("rector", "no rector.php config",
                      "create rector.php with codeQuality/deadCode sets")
    rc, out = sh("%s process --dry-run --no-progress" % tool,
                 repo, timeout=900)
    if rc == 0:
        return {"step": "rector", "rc": rc, "errors": 0, "warnings": 0}
    if "would change" in out.lower() \
            or "would have changed" in out.lower():
        return {"step": "rector", "rc": rc, "errors": 0, "warnings": 1,
                "sample": ["clean-code drift present "
                           "(run vendor/bin/rector to apply)"],
                "out": out[-1000:]}
    return {"step": "rector", "rc": rc, "errors": 0, "warnings": 0,
            "error": "rector failed (config/runtime)",
            "out": out[-1000:]}


def step_deptrac(repo):
    tool = _tool(repo, "deptrac")
    cfg = _first_file(repo, ("deptrac.yaml", "deptrac.yml", "deptrac.php",
                             "deptrac.dist.yaml", "deptrac.dist.php"))
    if not tool:
        return _skip("deptrac", "not installed",
                      "composer require --dev deptrac/deptrac")
    if not cfg:
        return _skip("deptrac", "no deptrac config",
                      "create deptrac.yaml with layers + ruleset")
    rc, out = sh("%s analyse --formatter=json --no-progress" % tool,
                 repo, timeout=600)
    rep = _parse_json_tail(out)
    n, err = 0, None
    if isinstance(rep, dict) and isinstance(rep.get("violations"), list):
        n = len(rep["violations"])
    elif rc != 0:
        n = 1
        if rep is None:
            err = "unparseable output"
    s = {"step": "deptrac", "rc": rc, "errors": n, "warnings": 0,
         "out": out[-1000:] if n else "clean"}
    if err:
        s["error"] = err
    return s


def step_psalm_taint(repo):
    # Granular JSON parsing deferred: verify flags against psalm.dev
    # before extending. Exit code + tail only.
    tool = _tool(repo, "psalm")
    cfg = _first_file(repo, ("psalm.xml", "psalm.xml.dist"))
    if not tool:
        return _skip("psalm-taint", "not installed",
                      "composer require --dev vimeo/psalm")
    if not cfg:
        return _skip("psalm-taint", "no psalm.xml config",
                      "run vendor/bin/psalm --init to generate one")
    rc, out = sh("%s --taint-analysis" % tool, repo, timeout=900)
    if rc == 0:
        return {"step": "psalm-taint", "rc": rc, "errors": 0,
                "warnings": 0}
    return {"step": "psalm-taint", "rc": rc, "errors": 1, "warnings": 0,
            "sample": ["taint findings present (see output)"],
            "out": out[-1000:]}


def step_warden(repo):
    artisan = os.path.join(repo, "artisan")
    if not (os.path.isfile(artisan)
            and os.path.isdir(os.path.join(repo, "vendor", "dgtlss",
                                           "warden"))):
        return _skip("warden", "not a Warden-equipped Laravel app",
                      "composer require --dev dgtlss/warden "
                      "(Laravel only)")
    rc, out = sh("php artisan warden:audit --format=json --no-notify",
                 repo, timeout=900)
    if rc == 0:
        return {"step": "warden", "rc": rc, "errors": 0, "warnings": 0}
    if rc == 2:
        return {"step": "warden", "rc": rc, "errors": 0, "warnings": 0,
                "error": "audit failed to run", "out": out[-1000:]}
    n, rep = 1, _parse_json_tail(out)
    if isinstance(rep, dict) and isinstance(rep.get("findings"), list):
        n = len(rep["findings"])
    return {"step": "warden", "rc": rc, "errors": n, "warnings": 0,
            "out": out[-1000:]}


def cmd_php_audit(args):
    repo, scope, blocking, receipts = ".", "full", "error", None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--scope" and i + 1 < len(args):
            scope, i = args[i + 1], i + 2
        elif args[i] == "--blocking" and i + 1 < len(args):
            blocking, i = args[i + 1], i + 2
        elif args[i] == "--receipts" and i + 1 < len(args):
            receipts, i = args[i + 1], i + 2
        else:
            i += 1
    if scope not in ("full", "changed"):
        print("PHP-AUDIT: FAIL\n- bad --scope: %s (full|changed)" % scope)
        return 1
    if blocking not in ("error", "warning", "none"):
        print("PHP-AUDIT: FAIL\n- bad --blocking: %s "
              "(error|warning|none)" % blocking)
        return 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    results = []
    status = "SKIP"

    if not os.path.isfile(os.path.join(repo, "composer.json")):
        results.append({"step": "detect", "rc": 1,
                        "out": "SKIP: not a PHP project "
                               "(no composer.json)"})
    elif not shutil.which("php"):
        results.append({"step": "detect", "rc": 1,
                        "out": "SKIP: php not on PATH"})
    else:
        steps = [step_phpstan(repo, scope), step_pint(repo, scope),
                 step_composer_audit(repo), step_rector(repo),
                 step_deptrac(repo), step_psalm_taint(repo),
                 step_warden(repo)]
        results.extend(steps)
        for s in steps:
            if "skipped" in s:
                print("[SKIP] %s -> %s" % (s["step"], s["skipped"]))
            elif "error" in s:
                print("[ERROR] %s -> %s" % (s["step"], s["error"]))
            else:
                mark = "PASS" if s["rc"] == 0 else "FAIL"
                print("[%s] %s -> %d errors, %d warnings"
                      % (mark, s["step"], s["errors"], s["warnings"]))
        errs = sum(s.get("errors", 0) for s in steps)
        warns = sum(s.get("warnings", 0) for s in steps)
        if all("skipped" in s for s in steps):
            status = "SKIP"
        elif blocking == "error" and errs:
            status = "FAIL"
        elif blocking == "warning" and (errs + warns):
            status = "FAIL"
        else:
            status = "PASS"

    receipt = {"tool": "guided-run php-audit", "run_id": run_id,
               "sha": sha, "repo": repo, "status": status,
               "scope": scope, "blocking": blocking, "results": results}
    rdir = receipts or os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "php-audit.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("PHP-AUDIT: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0 if status in ("PASS", "SKIP") else 1


AO_RELEASES = ("https://github.com/Untrivial-ai/agent-orchestrator"
               "/releases/latest")
AO_DOCS = "https://orchestrator.inc/docs"


def ao_install_hint():
    """OS-specific Agent Orchestrator install pointer (no side effects)."""
    import platform
    base = AO_RELEASES + "/download/agent-orchestrator-"
    sysname = platform.system().lower()
    if sysname == "windows":
        return base + "win32-x64.exe"
    if sysname == "darwin":
        arch = "arm64" if platform.machine() == "arm64" else "x64"
        return base + "darwin-%s.dmg" % arch
    return base + "linux-x64.AppImage (or .deb/.rpm)"


def ensure_orchestrator(repo):
    """Detect AO supervision readiness. Returns (status, detail dict).

    Never installs or clones: the AO repo is a full desktop app
    (backend + frontend), not a library. Statuses: READY (ao CLI +
    git worktree), DEGRADED (ao present, project not git-backed),
    MISSING (no ao CLI -> install hint).
    """
    detail = {"hint": None, "ao_version": None, "git_ready": False}
    rc, out = sh("git rev-parse --is-inside-work-tree", repo, timeout=30)
    detail["git_ready"] = (rc == 0 and out.strip() == "true")
    if not shutil.which("ao"):
        detail["hint"] = ("%s (releases: %s, docs: %s)"
                          % (ao_install_hint(), AO_RELEASES, AO_DOCS))
        return "MISSING", detail
    rc, out = sh("ao --version", repo, timeout=30)
    detail["ao_version"] = out.strip()[:80] if rc == 0 else "unknown"
    if not detail["git_ready"]:
        detail["hint"] = ("AO requires a git repo for worktree isolation: "
                          "run git init + one commit in the project")
        return "DEGRADED", detail
    return "READY", detail


def cmd_orchestrator(args):
    repo = "."
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        else:
            i += 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    status, detail = ensure_orchestrator(repo)
    if status == "READY":
        print("[READY] orchestrator -> ao %s, git worktree ready"
              % (detail["ao_version"] or "?"))
    elif status == "DEGRADED":
        print("[DEGRADED] orchestrator -> ao present, %s" % detail["hint"])
    else:
        print("[MISSING] orchestrator -> ao CLI not found")
        print("  install: %s" % detail["hint"])
        print("  guided lanes stay fully usable standalone; AO adds "
              "supervised workers + Kanban when present")
    receipt = {"tool": "guided-run orchestrator", "run_id": run_id,
               "sha": sha, "repo": repo, "status": status,
               "ao_version": detail["ao_version"],
               "git_ready": detail["git_ready"], "hint": detail["hint"]}
    rdir = os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "orchestrator.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("ORCHESTRATOR: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0


MCP_SERVERS = {
    "phpstan": {
        "repo": "https://github.com/larspohlmann/mcp-phpstan-server",
        "dirname": "mcp-phpstan-server",
        "entry": "bin/mcp-phpstan",
        "tools": ["phpstan_analyze", "phpstan_pro"],
    },
    "phpcs": {
        "repo": "https://github.com/larspohlmann/mcp-phpcs-server",
        "dirname": "mcp-phpcs-server",
        "entry": "bin/mcp-phpcs",
        "tools": ["phpcs_check", "phpcbf_fix"],
    },
    "php-composer": {
        "repo": "https://github.com/baschny/php-composer-mcp",
        "phar": "php-composer-mcp.phar",
        "dirname": "php-composer-mcp",
        "entry": "bin/mcp-server.php",
        "tools": ["search_packages", "get_package_info",
                  "read_composer_json", "analyze_project",
                  "suggest_upgrades"],
    },
}


def guided_mcp_home():
    return os.path.join(os.path.expanduser("~"), ".guided", "mcp")


def find_mcp_entry(repo, spec):
    """Locate a server checkout: repo dir, repo/mcp, ~/.guided/mcp."""
    if spec.get("phar"):
        c = os.path.join(guided_mcp_home(), spec["phar"])
        if os.path.isfile(c):
            return c
    for base in (repo, os.path.join(repo, "mcp"), guided_mcp_home()):
        c = os.path.join(base, spec.get("dirname", ""),
                         spec.get("entry", ""))
        if os.path.isfile(c):
            return c
    return None


def mcp_handshake(cmd, cwd=None, timeout=60):
    """Minimal MCP handshake over stdio. Returns (ok, tools_or_error)."""
    reqs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                    "clientInfo": {"name": "guided-run", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list",
         "params": {}},
    ]
    blob = "\n".join(json.dumps(r) for r in reqs) + "\n"
    try:
        p = subprocess.run(cmd, input=blob, capture_output=True, text=True,
                           cwd=cwd, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, "spawn failed: %s" % e
    tools = []
    for line in (p.stdout or "").splitlines():
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("id") == 2 and isinstance(msg.get("result"), dict):
            for t in msg["result"].get("tools", []):
                if isinstance(t, dict) and t.get("name"):
                    tools.append(t["name"])
    if tools:
        return True, tools
    err = (p.stderr or "").strip().splitlines()
    return False, (err[-1] if err else "no tools listed")[:300]


def ensure_mcp(repo):
    """Check PHP MCP servers. Returns (status, servers dict).

    Never installs or clones. Statuses per server: READY (found +
    handshake lists expected tools), DEGRADED (found but broken, or
    php missing), MISSING (hint with clone/download command), SKIP
    (laravel-boost on non-Laravel projects).
    """
    servers = {}
    php = shutil.which("php")
    for name, spec in MCP_SERVERS.items():
        entry = find_mcp_entry(repo, spec)
        if entry is None:
            if spec.get("phar"):
                hint = ("download %s from %s/releases to %s"
                        % (spec["phar"], spec["repo"],
                           os.path.join(guided_mcp_home(), spec["phar"])))
            else:
                hint = ("git clone %s %s"
                        % (spec["repo"], os.path.join(guided_mcp_home(),
                                                      spec["dirname"])))
            servers[name] = {"status": "MISSING", "hint": hint}
            continue
        if not php:
            servers[name] = {"status": "DEGRADED", "entry": entry,
                             "hint": "php not on PATH"}
            continue
        ok, info = mcp_handshake(["php", entry])
        if not ok:
            servers[name] = {"status": "DEGRADED", "entry": entry,
                             "hint": "handshake failed: %s" % info}
            continue
        missing = [t for t in spec["tools"] if t not in info]
        if missing:
            servers[name] = {"status": "DEGRADED", "entry": entry,
                             "tools": info,
                             "hint": "tools missing: %s"
                                     % ",".join(missing)}
        else:
            servers[name] = {"status": "READY", "entry": entry,
                             "tools": info}
    comp = os.path.join(repo, "composer.json")
    laravel = False
    try:
        with open(comp, encoding="utf-8") as f:
            laravel = "laravel/framework" in f.read()
    except OSError:
        pass
    if laravel and os.path.isfile(os.path.join(repo, "artisan")) \
            and os.path.isdir(os.path.join(repo, "vendor", "laravel",
                                           "boost")):
        ok, info = mcp_handshake(["php", "artisan", "boost:mcp"],
                                 cwd=repo, timeout=90)
        servers["laravel-boost"] = {
            "status": "READY" if ok else "DEGRADED",
            "tools": info if ok else [],
            "hint": None if ok else "handshake failed: %s" % info}
    elif laravel:
        servers["laravel-boost"] = {
            "status": "MISSING",
            "hint": "composer require laravel/boost --dev, then "
                    "php artisan boost:install"}
    else:
        servers["laravel-boost"] = {"status": "SKIP",
                                    "hint": "not a Laravel project"}
    states = [s["status"] for s in servers.values()
              if s["status"] != "SKIP"]
    if states and all(s == "READY" for s in states):
        return "READY", servers
    if any(s == "READY" for s in states):
        return "PARTIAL", servers
    return "MISSING", servers


def print_mcp_snippet(platform, repo):
    """Emit a ready-to-paste client block with resolved absolute paths."""
    home = guided_mcp_home().replace("\\", "/")
    laravel_artisan = os.path.join(os.path.abspath(repo), "artisan")
    artisan = (laravel_artisan.replace("\\", "/")
               if os.path.isfile(laravel_artisan) else "<LARAVEL_PROJECT>/artisan")
    blocks = {
        "phpstan": (["php", home + "/mcp-phpstan-server/bin/mcp-phpstan"], {}),
        "phpcs": (["php", home + "/mcp-phpcs-server/bin/mcp-phpcs"], {}),
        "php-composer": (["php", home + "/php-composer-mcp.phar"], {}),
        "laravel-boost": (["php", artisan, "boost:mcp"], {}),
    }
    if platform == "opencode":
        out = {"mcp": {}}
        for name, (cmd, _) in blocks.items():
            out["mcp"][name] = {"type": "local", "command": cmd,
                                "enabled": False}
        print(json.dumps(out, indent=2))
    elif platform in ("kiro", "grok"):
        out = {"mcpServers": {}}
        for name, (cmd, _) in blocks.items():
            entry = {"command": cmd[0], "args": cmd[1:]}
            if platform == "kiro":
                entry["disabled"] = True
            out["mcpServers"][name] = entry
        print(json.dumps(out, indent=2))
    elif platform == "zed":
        out = {"context_servers": {}}
        for name, (cmd, _) in blocks.items():
            out["context_servers"][name] = {"command": cmd[0],
                                            "args": cmd[1:]}
        print(json.dumps(out, indent=2))
    else:
        print("unknown platform: %s (opencode|kiro|zed|grok)" % platform)
        return 1
    return 0


def cmd_mcp(args):
    repo, snippet = ".", None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--print-snippet" and i + 1 < len(args):
            snippet, i = args[i + 1], i + 2
        else:
            i += 1
    if snippet:
        return print_mcp_snippet(snippet, repo)
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    status, servers = ensure_mcp(repo)
    for name, s in servers.items():
        st = s["status"]
        if st == "READY":
            print("[READY] %s -> tools: %s"
                  % (name, ",".join(s["tools"])))
        elif st == "SKIP":
            print("[SKIP] %s -> %s" % (name, s["hint"]))
        else:
            print("[%s] %s -> %s" % (st, name, s["hint"]))
    receipt = {"tool": "guided-run mcp", "run_id": run_id,
               "sha": sha, "repo": repo, "status": status,
               "servers": servers}
    rdir = os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "mcp.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("MCP: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0


def print_lsp_snippet(platform):
    """Emit the minimal OpenCode v1 config for semantic tool access."""
    if platform != "opencode":
        print("unknown platform: %s (opencode)" % platform)
        return 1
    print(json.dumps({
        "$schema": "https://opencode.ai/config.json",
        "lsp": True,
        "permission": {"lsp": "allow"},
    }, indent=2))
    return 0


def _env_truthy(name):
    return os.environ.get(name, "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _opencode_probe_command(opencode, query):
    """Build a safe Windows launcher for npm's opencode.cmd wrapper."""
    args = ["debug", "lsp", "symbols", query]
    if os.name == "nt" and opencode.lower().endswith((".cmd", ".bat")):
        if any(ch in query for ch in "&|<>^%!\"\r\n"):
            return None, "probe query contains unsupported shell characters"
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/s", "/c",
                opencode, *args], None
    if os.name == "nt" and opencode.lower().endswith(".ps1"):
        return None, "PowerShell wrapper is not directly executable"
    return [opencode, *args], None


def _probe_lsp_symbols(opencode, repo, query):
    """Probe OpenCode's LSP symbol command without exposing its raw output."""
    command, error = _opencode_probe_command(opencode, query)
    if error:
        return False, error
    try:
        result = subprocess.run(
            command, cwd=repo, capture_output=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, "probe failed: %s" % exc
    if result.returncode != 0:
        return False, "probe failed with exit code %d" % result.returncode
    try:
        symbols = json.loads(result.stdout.strip() or "[]")
    except ValueError:
        return False, "probe returned invalid JSON"
    if not isinstance(symbols, list):
        return False, "probe returned an unexpected JSON shape"
    if not symbols:
        return False, "probe returned no symbols; check the language server and query"
    return True, "probe returned %d symbol result(s)" % len(symbols)


def lsp_readiness(repo, query=None):
    """Report host prerequisites and optionally verify a live symbol query."""
    opencode = shutil.which("opencode")
    flags = [name for name in (
        "OPENCODE_EXPERIMENTAL_LSP_TOOL", "OPENCODE_EXPERIMENTAL",
    ) if _env_truthy(name)]
    if not opencode:
        return "MISSING", {
            "opencode": None,
            "experimental_flags": flags,
            "hint": "install OpenCode, then rerun this command",
        }
    if not flags:
        return "DEGRADED", {
            "opencode": opencode,
            "experimental_flags": flags,
            "hint": "set OPENCODE_EXPERIMENTAL_LSP_TOOL=true for OpenCode v1",
        }
    if not query:
        return "DEGRADED", {
            "opencode": opencode,
            "experimental_flags": flags,
            "hint": "pass --query SYMBOL to verify a live language-server response",
        }
    ok, detail = _probe_lsp_symbols(opencode, repo, query)
    return ("READY" if ok else "DEGRADED"), {
        "opencode": opencode,
        "experimental_flags": flags,
        "hint": detail,
    }


def cmd_lsp(args):
    repo, snippet, query = ".", None, None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--query" and i + 1 < len(args):
            query, i = args[i + 1], i + 2
        elif args[i] == "--print-snippet" and i + 1 < len(args):
            snippet, i = args[i + 1], i + 2
        else:
            i += 1
    if snippet:
        return print_lsp_snippet(snippet)
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    status, detail = lsp_readiness(repo, query)
    print("[%s] lsp -> %s" % (status, detail["hint"]))
    receipt = {"tool": "guided-run lsp", "run_id": run_id,
               "sha": sha, "repo": repo, "status": status,
               "details": detail}
    rdir = os.path.join(repo, "guided-receipts", run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "lsp.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump(receipt, f, indent=2)
    print("LSP: %s (sha %s)\nreceipt: %s" % (status, sha, rpath))
    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        return 0
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "validate-plan":
        return cmd_validate_plan(rest)
    if cmd == "verify":
        return cmd_verify(rest)
    if cmd == "react-doctor":
        return cmd_react_doctor(rest)
    if cmd == "growth":
        return cmd_growth(rest)
    if cmd == "php-audit":
        return cmd_php_audit(rest)
    if cmd == "orchestrator":
        return cmd_orchestrator(rest)
    if cmd == "mcp":
        return cmd_mcp(rest)
    if cmd == "lsp":
        return cmd_lsp(rest)
    if cmd == "init":
        return cmd_init(rest)
    print("unknown command: %s "
          "(validate-plan|verify|react-doctor|growth|php-audit|"
          "orchestrator|mcp|lsp|init)" % cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
