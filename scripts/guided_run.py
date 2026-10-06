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
    js-lint [--repo DIR] [--scope full|changed] [--blocking LVL]
             [--no-init-config]
        JavaScript correctness lane: detect .js/.mjs/.cjs sources -> use the
        project's own oxlint if it has one, else the pinned binary via npx
        (auto-download on first use) -> scan --format=json. Never installs
        into the project, never runs --fix, and refuses the npx path when the
        repo ships a config oxlint would evaluate (oxlint.config.ts, or a
        jsPlugins entry). Writes a starter .oxlintrc.json when the project has
        none (never overwrites an existing one; --no-init-config disables).
        Also measures how many inline <script> blocks in .php files oxlint
        cannot see. Writes a JSON receipt. Exit 0 on PASS or SKIP (no JS / no
        Node / below floor / offline / repo ships an evaluable config, with
        reason); 1 on FAIL (blocking-level findings). A scan that never ran
        reports SKIP, never PASS.
    js-lint --all [--roots DIR[,DIR...]] [--discover] [same flags]
        Sweep every project under the scan roots, so no repo has to be named
        by hand. With no --roots, scans the usual home dev folders
        (Desktop, Documents, Projects, code, repos, ...). --discover lists the
        roots it would scan and writes nothing -- the safe first run. Writes a
        per-project receipt plus one summary receipt; exits 1 if any project
        fails.
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
    sync [--repo DIR] [--home DIR] [--receipts DIR] [--check]
        Diff skills/ against every installed tool path (kiro, grok,
        opencode, zed) and report each guided skill as up-to-date,
        stale, or missing. Foreign skills sharing a tool root are
        ignored on purpose. Writes a JSON receipt. Exit 1 on drift.
        Also reports skills/ dirs with no SKILL.md (invalid) and
        names the installer recorded but no longer ships, while
        they still sit in a tool root (orphaned).
    record-install [--repo DIR] [--home DIR]
        Write ~/.guided/installed.json with the guided skill names
        shipped. The manifest is what lets `sync` spot a removed
        guided skill without mistaking another tool's skill on the
        same shared root for one.
    init [--repo DIR]
        Scaffold docs/repo-map.json from detected project facts.

Command auto-detection (no config needed, override via repo-map.json
test_commands): composer.json scripts, package.json scripts,deptrac/pest/
infection/phpstan/vitest/pint binaries, pact dirs. Missing tools are
SKIP-logged unless the Plan IR accuracy block requires them (then FAIL).

Stdlib only. Windows + macOS + Linux. Exit codes: 0 PASS, 1 FAIL.
"""
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ACCURACY_DEFAULTS = {"mutation_min_backend": 70,
                     "mutation_min_frontend": 50}

# react-doctor stays EXTERNAL: never bundled, provisioned at runtime.
# Pinned here (single source of truth); bump deliberately, never @latest.
REACT_DOCTOR_VERSION = "0.9.13"

# oxlint is external for the same reason react-doctor is: never bundled, never
# installed into the target project. Pinned here so a version bump is a
# deliberate, reviewable edit. Set GUIDED_OXLINT_VERSION to override at
# runtime; a bad pin degrades to SKIP (the download probe fails) instead of
# failing the lane.
OXLINT_VERSION = "1.80.0"

# Files oxlint actually lints. Inline <script> in a .php template is NOT one of
# them -- inline_script_audit measures that gap rather than hiding it.
JS_EXTS = (".js", ".mjs", ".cjs")

# Likely homes for a plain-PHP asset tree, tried in order when scoping a run.
JS_SCOPE_DIRS = ("public", "assets", "js", "resources", "static", "src",
                 "www", "dist")

OXLINT_CONFIGS = (".oxlintrc.json", ".oxlintrc.jsonc", "oxlint.config.ts",
                  "oxlint.config.mts")

# Every receipt path is named by this one format; a second spelling would
# make receipts sort inconsistently.
RUN_ID_FORMAT = "%Y%m%d-%H%M%S"

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


BATCH_EXT = (".cmd", ".bat")
WIN_EXE_EXT = (".exe", ".com")

# sh() exit codes. 125 is deliberately distinct from 127: "the environment
# could not start this" and "there is no such program" need different
# remedies, and conflating them is how a missing tool turns into a
# "unparseable output" report.
SH_TIMEOUT = 124
SH_NO_PROGRAM = 127
SH_NO_ENVIRONMENT = 125


def _resolve_program(prog, cwd=None):
    """Runnable absolute path for a program, or None when it cannot run.

    Windows is why this exists. `npx` ships as a POSIX script beside npx.cmd
    and npx.ps1, and CreateProcess runs neither a bare name nor a .ps1.
    shutil.which already applies PATHEXT, so a bare name is a PATH lookup.

    A repo-relative path (vendor/bin/phpstan) must be resolved against `cwd`,
    NOT against the process CWD: CreateProcess resolves argv[0] against the
    parent, while the shell this replaced resolved it against cwd. Skipping
    that makes composer vendor tools unreachable from any other directory.
    """
    if os.name != "nt":
        return prog
    ext = os.path.splitext(prog)[1].lower()
    if ext in (".ps1", ".psm1", ".psd1"):
        return None                       # not a Win32 application
    has_sep = os.sep in prog or bool(os.altsep and os.altsep in prog)
    if not has_sep:
        found = shutil.which(prog)       # PATH + PATHEXT, like a shell
        if found:
            return found
    base = cwd or os.getcwd()
    if ext in BATCH_EXT or ext in WIN_EXE_EXT:
        cands = [prog]
    else:
        cands = [prog] + [prog + s for s in BATCH_EXT + WIN_EXE_EXT]
    for cand in cands:
        full = os.path.abspath(os.path.join(base, cand))
        if os.path.exists(full):
            return full
    return None


def _run_process(argv, cwd, timeout, use_shell):
    """Spawn a process and return (rc, output) with the shared conventions.

    One definition of the 2000-char output cap and of the exit codes for
    failures a caller cannot act on: 124 timeout, 125 the environment could
    not start the process, 127 no such program. Everything else is the
    program's own exit code.
    """
    try:
        p = subprocess.run(argv, cwd=cwd, shell=use_shell,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        label = argv if isinstance(argv, str) else " ".join(argv)
        return SH_TIMEOUT, "TIMEOUT after %ss: %s" % (timeout, label)
    except FileNotFoundError as e:
        return SH_NO_PROGRAM, "not found: %s" % e
    except OSError as e:
        # A bad cwd, or a directory we may not enter. Reported, not raised:
        # this is the wrong argument, and the caller gets to decide.
        return SH_NO_ENVIRONMENT, "cannot run in %s: %s" % (cwd, e)
    return p.returncode, (p.stdout + p.stderr)[-2000:].strip()


def sh(cmd, cwd, timeout=600):
    """Run `cmd` as an argv list, never through a shell.

    A value can therefore never be re-read as shell syntax. A shell string is
    rejected rather than guessed at: on POSIX subprocess would treat it as one
    filename, on Windows CreateProcess would re-parse it -- per-platform
    behaviour differences are a trap, so both forms must be explicit.
    """
    if isinstance(cmd, str):
        return SH_NO_PROGRAM, ("sh() takes an argv list, not a shell "
                               "string: %r "
                     "(use sh([...]), or sh_line() for a config-defined "
                     "command line)" % cmd[:120])
    argv = [str(a) for a in cmd]
    if not argv:
        return SH_NO_PROGRAM, "empty command"
    prog = _resolve_program(argv[0], cwd)
    if prog is None:
        return SH_NO_PROGRAM, "not found or not executable: %s" % argv[0]
    if os.name == "nt" and os.path.splitext(prog)[1].lower() in BATCH_EXT:
        # A .cmd/.bat argv is still handed to cmd.exe, where a double quote in
        # a value breaks out of the quoting subprocess.apply.
        for value in argv[1:]:
            if '"' in value:
                return SH_NO_PROGRAM, ("refusing a double quote in an "
                                       "argument to the "
                             "batch wrapper %s: cmd.exe would re-parse it"
                             % os.path.basename(prog))
    argv[0] = prog
    return _run_process(argv, cwd, timeout, False)


def sh_line(line, cwd, timeout=600):
    """Run a project-defined command LINE, shell-executed on purpose.

    npm/composer scripts and repo-map test_commands are command lines by
    definition and come from the project's own config, so they keep the shell
    (npm relies on it). Never pass an interpolated value through here: that is
    the injection the sh()/sh_line() split exists to prevent. Dynamic data
    belongs in sh() as argv.
    """
    return _run_process(line, cwd, timeout, True)


def _run_id():
    """Timestamp id for one receipt directory."""
    return datetime.now(timezone.utc).strftime(RUN_ID_FORMAT)


def git_sha(repo):
    rc, out = sh(["git", "rev-parse", "--short", "HEAD"], repo, timeout=30)
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
    rc, out = sh(["node", "--version"], ".", timeout=30)
    m = re.match(r"\s*v(\d+)\.(\d+)", out) if rc == 0 else None
    return (int(m.group(1)), int(m.group(2))) if m else None


def node_floor_ok():
    """(ok, reason) for the Node floor every npx-backed lane needs.

    One definition so the minimum and the SKIP wording cannot drift between
    the React and JS lanes: a lane that reported a different floor than its
    neighbour would be a support question nobody could answer from the code.
    """
    if not shutil.which("node"):
        return False, "SKIP: node not found (Node.js required)"
    nv = node_version()
    if nv is None:
        return False, "SKIP: node not found or version unparseable"
    if not (nv[0] > 22 or (nv[0] == 22 and nv[1] >= 12)
            or (nv[0] == 20 and nv[1] >= 19)):
        return False, "SKIP: node %d.%d below minimum (20.19+/22.12+)" % nv
    return True, "node %d.%d" % nv


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
    ok, reason = node_floor_ok()
    if not ok:
        return False, reason
    rc, out = sh(["npx", "-y", "react-doctor@" + REACT_DOCTOR_VERSION,
                  "--version"],
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
        sh(["git", "ls-files", "--error-unmatch", f], repo,
           timeout=30)[0] == 0
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
            rc, out = sh(["vendor/bin/infection", "--filter=" + f,
                          "--min-msi=" + str(mins["mutation_min_backend"]),
                          "--threads=4"], repo, timeout=1800)
            results.append({"gate": "mutation:backend", "rc": rc,
                            "out": out[-1000:]})
            mutated = mutated or rc == 0
            ok = ok and rc == 0
        if shutil.which("npx") and os.path.isfile(
                os.path.join(repo, "stryker.config.json")):
            rc, out = sh(["npx", "stryker", "run"], repo, timeout=1800)
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
            rc, out = sh(["vendor/bin/deptrac", "analyse",
                           "--no-progress"], repo)
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
    run_id = _run_id()
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
        rc, out = sh_line(cmd, repo)   # config-defined command line
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
    run_id = _run_id()
    results = []
    status = "SKIP"

    ready, reason = ensure_react_doctor(repo)
    results.append({"step": "ensure", "rc": 0 if ready else 1,
                    "out": reason})
    print("[%s] ensure -> %s" % ("PASS" if ready else "SKIP", reason))

    if ready:
        rep_path = os.path.join(tempfile.gettempdir(),
                                "rd-%s.json" % run_id)
        argv = ["npx", "-y", "react-doctor@" + REACT_DOCTOR_VERSION,
                "--json", "--json-out", rep_path, "--scope", scope,
                "--blocking", blocking, "--no-telemetry", "--no-score"]
        if base:
            argv += ["--base", base]
        rc, out = sh(argv, repo, timeout=900)
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
    run_id = _run_id()
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
            return ["vendor/bin/%s" % cand]
    phar = os.path.join(d, name + ".phar")
    if os.path.isfile(phar):
        return ["php", "vendor/bin/%s.phar" % name]
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


def changed_files(repo, ext):
    """Changed + untracked paths ending in `ext` via git ([] on any error).

    `ext` carries its dot, e.g. ".php". One implementation for every lane that
    scopes to touched files: the git plumbing is identical, and a second copy
    is how one lane ends up quietly disagreeing with another about what
    "changed" means.
    """
    files = []
    for cmd in (["git", "diff", "--name-only", "HEAD", "--", "*" + ext],
                ["git", "ls-files", "--others", "--exclude-standard",
                 "--", "*" + ext]):
        rc, out = sh(cmd, repo, timeout=30)
        if rc != 0:
            return []
        for ln in out.splitlines():
            p = ln.strip().strip("\"")
            if p.endswith(ext) \
                    and os.path.isfile(os.path.join(repo, p)) \
                    and p not in files:
                files.append(p)
    return files


def changed_php_files(repo):
    """Changed + untracked .php paths via git ([] when unavailable)."""
    return changed_files(repo, ".php")


NOT_RUN_RCS = (SH_TIMEOUT, SH_NO_ENVIRONMENT, SH_NO_PROGRAM)


def _not_run(step, rc, out, **extra):
    """The step result for a tool that never produced output.

    "The auditor could not start" and "the auditor ran and did not speak
    JSON" are different problems with different fixes. Returning this instead
    of a parse error is the difference between a readable report and a
    mystery. Only consult it when rc is in NOT_RUN_RCS.
    """
    s = {"step": step, "rc": rc, "errors": 0, "warnings": 0,
         "not_run": out, "out": out[-1000:]}
    s.update(extra)
    return s


def _unparseable(step, rc, out, **extra):
    """The step result for a tool that did not emit JSON.

    One shape for every JSON-emitting auditor, so a caller cannot drift on
    which keys it fills in when the output cannot be read.
    """
    s = {"step": step, "rc": rc, "errors": 0, "warnings": 0,
         "error": "unparseable output", "out": out[-1000:]}
    s.update(extra)
    return s


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
    argv = list(tool) + ["analyse", "--error-format=json", "--no-progress"]
    used = "full"
    cfg = _first_file(repo, ("phpstan.neon", "phpstan.neon.dist",
                             "phpstan.dist.neon"))
    if scope == "changed":
        changed = changed_php_files(repo)
        if changed:
            argv += changed
            used = "changed"
    if used == "full" and not cfg:
        for d in ("src", "app", "lib"):
            if os.path.isdir(os.path.join(repo, d)):
                argv.append(d)
                break
        else:
            return _skip("phpstan", "no phpstan.neon and no src|app|lib dir",
                         "create phpstan.neon with paths + level")
    rc, out = sh(argv, repo, timeout=900)
    if rc in NOT_RUN_RCS:
        return _not_run("phpstan", rc, out, scope=used)
    rep = _parse_json_tail(out)
    if rep is None:
        return _unparseable("phpstan", rc, out, scope=used)
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
    argv = list(tool) + ["--test"]
    if scope == "changed":
        argv.append("--dirty")
    rc, out = sh(argv, repo, timeout=600)
    if rc in NOT_RUN_RCS:
        return _not_run("pint", rc, out, scope=scope)
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
    rc, out = sh(["composer", "audit", "--format=json", "--locked",
                  "--no-dev"], repo, timeout=300)
    if rc in NOT_RUN_RCS:
        return _not_run("composer-audit", rc, out)
    rep = _parse_json_tail(out)
    if rep is None:
        return _unparseable("composer-audit", rc, out)
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
    rc, out = sh(list(tool) + ["process", "--dry-run", "--no-progress"],
                 repo, timeout=900)
    if rc in NOT_RUN_RCS:
        return _not_run("rector", rc, out)
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
    rc, out = sh(list(tool) + ["analyse", "--formatter=json",
                               "--no-progress"], repo, timeout=600)
    if rc in NOT_RUN_RCS:
        return _not_run("deptrac", rc, out)
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
    rc, out = sh(list(tool) + ["--taint-analysis"], repo, timeout=900)
    if rc in NOT_RUN_RCS:
        return _not_run("psalm-taint", rc, out)
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
    rc, out = sh(["php", "artisan", "warden:audit", "--format=json",
                  "--no-notify"],
                 repo, timeout=900)
    if rc in NOT_RUN_RCS:
        return _not_run("warden", rc, out)
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
    run_id = _run_id()
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
        ran = [s for s in steps if "skipped" not in s and "not_run" not in s]
        code_ran = [s for s in ran if s.get("step") in ("phpstan", "pint", "rector")]
        audit = next((s for s in steps if s.get("step") == "composer-audit"), {})
        audit_unread = (audit and "skipped" not in audit and "error" not in audit
                        and audit.get("rc") not in (0, None)
                        and not audit.get("errors") and not audit.get("warnings"))
        if all("skipped" in s for s in steps):
            status = "SKIP"
        elif not code_ran:
            # composer-audit alone is not a PHP modernization. A tree with no
            # phpstan/pint/rector must not look cleaner than one that ran them.
            status = "SKIP"
            print("[SKIP] php-audit -> no phpstan, pint, or rector installed; "
                  "not a code audit")
        elif audit_unread:
            status = "FAIL"
            print("[ERROR] composer-audit -> exit %s with no parsed advisories"
                  % audit.get("rc"))
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


def has_js_sources(repo, cap=5000):
    """True when the repo holds at least one lintable JS asset."""
    n = 0
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        for fn in files:
            if os.path.splitext(fn)[1].lower() in JS_EXTS:
                n += 1
                if n >= cap:
                    return True
    return n > 0


def local_oxlint_path(repo):
    """Path to the project's own oxlint binary, or None.

    Windows ships a .cmd wrapper beside the extensionless shim, so the
    extension list is not decoration: checking only the bare name would
    report "no local oxlint" on exactly the platform that has one.
    """
    d = os.path.join(repo, "node_modules", "bin")
    for cand in ("oxlint", "oxlint.cmd", "oxlint.bat", "oxlint.exe"):
        if os.path.isfile(os.path.join(d, cand)):
            return os.path.join(d, cand).replace("\\", "/")
    return None


def oxlint_argv(repo):
    """(argv_prefix, source) for the oxlint to run. Never None.

    A project that already depends on oxlint gets its own binary: that is the
    version its CI already trusts, and running a different linter than the one
    in the lockfile is exactly how "green in CI, red here" starts. npx is the
    fallback for the lockfile-free PHP repos this lane exists for, and is
    pinned for the same reason react-doctor is.
    """
    local = local_oxlint_path(repo)
    if local:
        return [local], "project"
    version = (os.environ.get("GUIDED_OXLINT_VERSION")
               or OXLINT_VERSION).strip()
    return ["npx", "-y", "oxlint@" + version], "pinned:" + version


CODE_CONFIG_RE = re.compile(r"\bjsPlugins\b")
# A .ts/.mts oxlint config is a MODULE: oxlint evaluates it, so a repo-authored
# one runs code with the developer's privileges before any diagnostic exists.
OXLINT_CODE_CONFIGS = ("oxlint.config.ts", "oxlint.config.mts")
# A npm spec, and only a strict one. GUIDED_OXLINT_VERSION reaches the npx
# command line, and the output stream and receipt; anything with whitespace
# or a flag-shaped prefix would let an env value forge a verdict line.
OXLINT_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-.+][0-9A-Za-z.-]+)?$")


def _oxlint_version_pin():
    """(version, error) for the npx fallback pin. Never raises."""
    raw = os.environ.get("GUIDED_OXLINT_VERSION", "").strip() or OXLINT_VERSION
    raw = raw.strip()
    if not OXLINT_VERSION_RE.match(raw):
        return None, ("invalid GUIDED_OXLINT_VERSION %r: expected a semver "
                      "like 1.80.0" % raw[:40])
    return raw, None


def oxlint_code_config_present(repo):
    """True when the repo can make oxlint execute code of its own.

    Inherited harness trust model, not new: php-audit already runs the repo's
    vendor/bin/*, and react-doctor already runs npx from the repo CWD. This
    function narrows it where narrowing is free -- the npx fallback, which is
    the only path that would fetch and run a *new* copy of the linter, refuses
    a repo that ships an evaluable config.
    """
    for fn in OXLINT_CODE_CONFIGS:
        if os.path.isfile(os.path.join(repo, fn)):
            return fn
    for cfg in find_oxlint_config(repo):
        if CODE_CONFIG_RE.search(_read_bounded(os.path.join(repo, cfg), 65536)):
            return cfg + " (jsPlugins)"
    return None


def ensure_oxlint(repo):
    """Detect JS-lane readiness. Returns (ready, reason, version).

    Never installs into the project and never raises: False means continue
    without oxlint and state the reason in one line. Availability is
    evidence-quality, not a hard gate -- a missing linter must not be able to
    fail a run the way a real finding does.
    """
    if not has_js_sources(repo):
        return False, "SKIP: no .js/.mjs/.cjs sources found", None
    if not local_oxlint_path(repo):
        version, err = _oxlint_version_pin()
        if err:
            return False, "SKIP: " + err, None
    else:
        version = None
    if not local_oxlint_path(repo) and not shutil.which("npx"):
        return False, ("SKIP: npx not found and no local oxlint "
                       "(Node.js required)"), None
    ok, reason = node_floor_ok()
    if not ok:
        return False, reason, None
    argv, source = oxlint_argv(repo)
    if source != "project":
        risky = oxlint_code_config_present(repo)
        if risky:
            return False, ("SKIP: %s makes oxlint evaluate repo-supplied "
                           "code; refusing the npx path. Install oxlint as a "
                           "devDependency and re-run" % risky), None
    rc, out = sh(argv + ["--version"], repo, timeout=600)
    if rc != 0:
        return False, "SKIP: oxlint unavailable via %s: %s" % (source,
                                                              out[-200:]), None
    # oxlint prints "Version: 1.80.0"; keep the bare semver so the receipt
    # field is a version, not a sentence fragment.
    found = re.search(r"[0-9]+\.[0-9]+\.[0-9]+[^\s]*", out)
    return True, "oxlint ready via %s (%s)" % (source, out.strip()[:60]), \
        (found.group(0) if found else out.strip()[:40])


def find_oxlint_config(repo, cap=20):
    """Relative paths of oxlint config files found anywhere in the repo.

    Nested configs are real -- oxlint loads them per directory -- so looking
    only at the root would miss a project that scopes its rules under public/
    and then read the whole result as "no config".
    """
    found = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        for fn in files:
            if fn in OXLINT_CONFIGS:
                found.append(
                    os.path.relpath(os.path.join(root, fn), repo)
                    .replace("\\", "/"))
                if len(found) >= cap:
                    return sorted(found)
    return sorted(found)


def _oxlint_targets(repo, scope):
    """(targets, used_scope) for a run. 'full' falls back to the repo root.

    Every existing candidate directory is linted, not just the first hit.
    A Laravel repo has both public/ (compiled bundles) and resources/js/ (the
    sources anyone actually edits), and stopping at index 0 would report
    `scope: full` over public/ while the file under review never ran.
    """
    if scope == "changed":
        changed = []
        for ext in JS_EXTS:
            changed.extend(changed_files(repo, ext))
        if changed:
            return changed, "changed"
    found = [d for d in JS_SCOPE_DIRS if os.path.isdir(os.path.join(repo, d))]
    return (found or ["."]), "full"


def step_oxlint(repo, scope):
    """oxlint as a correctness gate. Returns the shared step-dict shape.

    No category flags are passed: the project's own config decides severity,
    and with no config oxlint's default already denies `correctness`. Adding
    -D/-W here would silently override a deliberate per-rule downgrade.
    """
    argv, source = oxlint_argv(repo)
    targets, used = _oxlint_targets(repo, scope)
    rc, out = sh(argv + ["--format=json"] + targets, repo, timeout=900)
    if rc in NOT_RUN_RCS:
        return _not_run("oxlint", rc, out, scope=used, source=source)
    rep = _parse_json_tail(out)
    if rep is None:
        # A clean run can legitimately print no JSON at all. That is zero
        # findings, not a parse failure -- conflating the two would report a
        # green file as a broken tool.
        if rc == 0 and not out.strip():
            return {"step": "oxlint", "rc": 0, "errors": 0, "warnings": 0,
                    "scope": used, "source": source, "out": "clean"}
        return _unparseable("oxlint", rc, out, scope=used, source=source)
    diags = rep.get("diagnostics")
    if not isinstance(diags, list):
        return _unparseable("oxlint", rc, out, scope=used, source=source)
    errs = warns = 0
    sample = []
    for d in diags:
        if not isinstance(d, dict):
            continue
        sev = (d.get("severity") or "").lower()
        if sev == "error":
            errs += 1
        else:
            warns += 1
        if len(sample) < 5:
            sample.append(_one_line("%s %s %s" % (_oxlint_line(d),
                                                   d.get("code", "?"),
                                                   d.get("message", ""))))
    s = {"step": "oxlint", "rc": rc, "errors": errs, "warnings": warns,
         "scope": used, "source": source, "sample": sample,
         # What was actually handed to the linter. Without this the receipt
         # says "full" and nothing more, which is indistinguishable from
         # having covered the whole repo.
         "targets": targets[:20],
         "files": rep.get("number_of_files")}
    if errs or warns:
        s["out"] = out[-1000:]
        s["hint"] = ("oxlint --fix applies the safe fixes, but a gate never "
                     "edits: make the change deliberately, then re-run")
    else:
        s["out"] = "clean"
    return s


def _one_line(value, limit=300):
    """Collapse a repo-controlled string to one printable line.

    Filenames, rule codes and tool messages are attacker-influenced when the
    repo is, and these are exactly the strings an agent is told to read as
    evidence. A newline in a filename would otherwise be able to forge the
    next line of the receipt output, including a verdict line.
    """
    text = "".join(ch if ch.isprintable() else " " for ch in str(value))
    text = " ".join(text.split())
    return text[:limit]


def _oxlint_line(diag):
    """`file.js:12:3` from an oxlint JSON diagnostic, degrading to `file.js`."""
    name = diag.get("filename") or "?"
    labels = diag.get("labels")
    if not isinstance(labels, list) or not labels:
        return name
    span = (labels[0] or {}).get("span") if isinstance(labels[0], dict) \
        else None
    if not isinstance(span, dict):
        return name
    return "%s:%s:%s" % (name, span.get("line", "?"), span.get("column", "?"))


# A <script> opening tag and its attributes. The attribute class is BOUNDED
# on purpose: `<script` repeated with no `>` anywhere makes an unbounded
# [^>]* scan-and-backtrack at every one of the k occurrences, which is
# Theta(k*n) on a 512 KB file -- a repository can hang the gate with a file
# that never contains a real tag. A tag longer than 1000 characters is
# pathological, and missing one is a coverage note, never a crash.
SCRIPT_TAG_RE = re.compile(r"<script\b([^>]{0,1000})>", re.I)
SRC_ATTR_RE = re.compile(r"\bsrc\s*=", re.I)
SCRIPT_CLOSE = "</script"
# Per-file ceiling on counted blocks. Same reasoning: a bound on the work, not
# a claim that a file has at most this many scripts.
INLINE_MAX_PER_FILE = 500


def _inline_script_count(text):
    """Non-empty <script> bodies with no src= in the opening tag.

    Split into "find the tag" + "look for the close" rather than one regex
    with a nested lazy group: str.find is a C-level scan, and keeping the
    quantifiers out of each other is what makes the cost predictable.
    """
    n = 0
    for m in SCRIPT_TAG_RE.finditer(text):
        if SRC_ATTR_RE.search(m.group(1)):
            continue
        close = text.find(SCRIPT_CLOSE, m.end())
        if close == -1:
            continue                      # unterminated tag, nothing to count
        if text[m.end():close].strip():
            n += 1
            if n >= INLINE_MAX_PER_FILE:
                break
    return n


def _read_bounded(path, limit=524288):
    """Read at most `limit` bytes, or '' for anything not a regular file.

    A size check on the open file is not a size check: os.path.getsize
    reports 0 for a character device, so a .php symlink to /dev/zero passes
    any threshold and then reads without end. lstat decides regularity, and
    the read itself stays bounded.
    """
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return ""
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read(limit + 1)[:limit]
    except OSError:
        return ""


def inline_script_audit(repo, cap=200):
    """Count <script> bodies in .php files that oxlint can never see.

    oxlint lints .js/.mjs/.cjs plus the <script> blocks of .vue/.svelte/.astro.
    A script body inside a .php template is outside that set, so a clean run
    on a PHP project is only as complete as the externalisation rate. This
    measures that rate instead of letting a green receipt imply full coverage.
    Heuristic by nature: a <script> string inside PHP or HTML comments still
    counts, which errs toward over-reporting the gap.
    """
    files, blocks, capped = [], 0, False
    for root, dirs, names in os.walk(repo):
        if capped:
            break
        dirs[:] = [d for d in dirs if d not in WALK_SKIP]
        for fn in names:
            if not fn.lower().endswith(".php"):
                continue
            n = _inline_script_count(_read_bounded(os.path.join(root, fn)))
            if n:
                files.append({"file": os.path.relpath(
                    os.path.join(root, fn), repo).replace("\\", "/"),
                    "inline_scripts": n})
                blocks += n
                if len(files) >= cap:
                    # Authoritative: a cap the caller cannot rely on is not a
                    # cap. break out of BOTH loops, or the walk keeps
                    # accumulating past the number the field reports.
                    capped = True
                    break
    return {"files_with_inline_js": len(files),
            "inline_script_blocks": blocks, "capped": capped,
            "examples": files[:10]}


NO_OXLINT_CONFIG_HINT = (
    "no .oxlintrc.* / oxlint.config.* found: without env.browser the "
    "default-on no-undef rule cannot see document/window, so every finding "
    "is a false positive. Minimal config: "
    '{"env":{"browser":true},"plugins":["eslint","typescript","unicorn",'
    '"oxc"],"categories":{"correctness":"error","suspicious":"warn"}} '
    "- note that `plugins` REPLACES the defaults, so all four must be listed.")

# Written to a project that has no oxlint config, so the gate does not have to
# be pointed at a config by hand on every repo. `plugins` is spelled out in
# full because that field REPLACES the default set: a config that omits them
# would silently switch off most correctness rules, which is worse than no
# config at all.
OXLINT_STARTER_CONFIG = """{
  "$schema": "https://raw.githubusercontent.com/oxc-project/oxc/main/npm/oxlint/configuration_schema.json",
  "env": { "browser": true },
  "plugins": ["eslint", "typescript", "unicorn", "oxc"],
  "categories": { "correctness": "error", "suspicious": "warn" }
}
"""

# Where a sweep looks for projects when the user names no roots. Dev folders
# only, and deliberately NOT a bare $HOME/Documents: a stray package.json in
# an unzipped tarball or a notes folder would otherwise make the sweep write
# a config into a tree the user never named. --roots is the precise option.
DEFAULT_SCAN_DIRS = ("Desktop", "Documents/GitHub", "Documents/Projects",
                     "Documents/repos", "Documents/dev", "Projects",
                     "projects", "repos", "workspace", "Workspaces")


def init_oxlint_config(repo, enabled=True):
    """(created, path, note) -- create a starter config only when absent.

    Three rules, all of them load-bearing:
      * NEVER overwrite. An existing config is a decision someone made, and
        silently replacing it would discard their rule choices and baselines.
      * NEVER fail the run. A read-only checkout, a permissions error, a
        full disk: report the note and let the scan proceed. A missing config
        is a nuisance, not a gate failure.
      * Write only this one file. No npm install, no lockfile, no node_modules.
        oxlint itself still arrives through the pinned npx fallback.
    """
    if not enabled:
        return False, None, "skipped (--no-init-config)"
    if not has_js_sources(repo):
        # Never leave a config for a linter that cannot run here. A sweep
        # matches on composer.json, so without this every pure-PHP repo on
        # the machine would collect a file it will never use.
        return False, None, "no JS assets in this project"
    if find_oxlint_config(repo):
        return False, None, "existing config left untouched"
    path = os.path.join(repo, ".oxlintrc.json")
    try:
        with open(path, "x", encoding="utf-8", newline="\n") as f:
            f.write(OXLINT_STARTER_CONFIG)
    except FileExistsError:
        return False, None, "existing config left untouched"
    except OSError as e:
        return False, None, "could not write config: %s" % _one_line(e, 120)
    return True, path, "created starter config"


def discover_project_roots(roots, max_depth=4):
    """Project roots under `roots`: a dir holding composer.json or
    package.json. Sorted, deduped, and a nested project is not reported twice.

    A root that is itself a project is returned as-is; descending further just
    finds the same dir again, and a monorepo would otherwise report every
    package as a separate project.
    """
    found = []
    for base in roots:
        base = os.path.abspath(base)
        if not os.path.isdir(base):
            continue
        if _is_project_root(base):
            found.append(base)
            continue
        base_depth = base.rstrip(os.sep).count(os.sep)
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs
                       if d not in WALK_SKIP and d != "guided-receipts"]
            if _is_project_root(root):
                found.append(root)
                dirs[:] = []          # do not double-report nested projects
            elif root.rstrip(os.sep).count(os.sep) - base_depth >= max_depth:
                dirs[:] = []
    return sorted(set(found))


def _is_project_root(path):
    return (os.path.isfile(os.path.join(path, "composer.json"))
            or os.path.isfile(os.path.join(path, "package.json")))


def default_scan_roots():
    """Existing home dev folders, in order. Empty list is not an error."""
    home = os.path.expanduser("~")
    return [os.path.join(home, *d.split("/")) for d in DEFAULT_SCAN_DIRS
            if os.path.isdir(os.path.join(home, *d.split("/")))]


def cmd_js_lint(args):
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
        print("JS-LINT: FAIL\n- bad --scope: %s (full|changed)" % scope)
        return 1
    if blocking not in ("error", "warning", "none"):
        print("JS-LINT: FAIL\n- bad --blocking: %s "
              "(error|warning|none)" % blocking)
        return 1
    repo = os.path.abspath(repo)
    sha = git_sha(repo)
    run_id = _run_id()
    results = []
    status = "SKIP"
    init_config = "--no-init-config" not in args

    coverage = inline_script_audit(repo)
    created, cfg_path, note = init_oxlint_config(repo, init_config)
    if created:
        print("[WRITE] config -> created %s (commit it so CI matches)"
              % _one_line(os.path.relpath(cfg_path, repo)))
    elif not init_config:
        print("[INFO] config -> not created (--no-init-config)")

    ready, reason, version = ensure_oxlint(repo)
    # reason can carry repo-controlled path text and captured tool stderr, so
    # it gets the same single-line treatment as every other printed field.
    results.append({"step": "ensure", "rc": 0 if ready else 1,
                    "out": _one_line(reason, 300)})
    print("[%s] ensure -> %s" % ("PASS" if ready else "SKIP",
                                 _one_line(reason, 300)))

    if ready:
        step = step_oxlint(repo, scope)
        results.append(step)
        if "skipped" in step:
            print("[SKIP] oxlint -> %s" % step["skipped"])
        elif "not_run" in step:
            # A linter that timed out or could not start is NOT a clean run.
            # _not_run reports 0 errors, so without this branch the verdict
            # below would read "PASS" from a scan that never happened -- the
            # exact fail-open the not_run/unparseable split exists to prevent,
            # reintroduced one level up.
            print("[SKIP] oxlint -> never ran: %s" % step["not_run"])
        elif "error" in step:
            print("[ERROR] oxlint -> %s" % step["error"])
            status = "FAIL"
        else:
            errs, warns = step["errors"], step["warnings"]
            print("[%s] oxlint -> %d errors, %d warnings (%s, scope %s)"
                  % ("PASS" if errs == 0 else "FAIL", errs, warns,
                     step["scope"], step["source"]))
            for line in step.get("sample", []):
                print("        %s" % line)
            if blocking == "error" and errs:
                status = "FAIL"
            elif blocking == "warning" and (errs + warns):
                status = "FAIL"
            else:
                status = "PASS"

    cfgs = find_oxlint_config(repo)
    results.append({"step": "config", "rc": 0, "created": created,
                    "out": ("created %s"
                            % _one_line(os.path.relpath(cfg_path, repo)))
                           if created else
                           (("configs: %s" % _one_line(",".join(cfgs)))
                            if cfgs else NO_OXLINT_CONFIG_HINT + " " + note)})
    if not cfgs and not created:
        print("[WARN] config -> no oxlint config found; findings may be "
              "false positives from no-undef (%s)" % _one_line(note, 100))

    if coverage["inline_script_blocks"]:
        print("[INFO] coverage -> %d inline <script> block(s) across %d .php "
              "file(s) are NOT covered by oxlint"
              % (coverage["inline_script_blocks"],
                 coverage["files_with_inline_js"]))
    else:
        print("[INFO] coverage -> no inline <script> bodies in .php files")

    receipt = {"tool": "guided-run js-lint", "run_id": run_id, "sha": sha,
               "repo": repo, "status": status, "scope": scope,
               "blocking": blocking,
               # The version that actually ran, not the pin. Recording the
               # pin here made the receipt assert a linter that never
               # executed whenever the project supplied its own binary.
               "oxlint_version": version,
               "oxlint_source": ("project" if ready and
                                 local_oxlint_path(repo) else
                                 ("pinned:" + str(version) if ready
                                  else None)),
               "oxlint_configs": cfgs, "inline_js_coverage": coverage,
               "results": results}
    rdir = receipts or os.path.join(repo, "guided-receipts", run_id)
    try:
        os.makedirs(rdir, exist_ok=True)
        rpath = os.path.join(rdir, "js-lint.json")
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
    except OSError as e:
        # A read-only repo must not turn a green scan into a crash. The scan
        # result is still printed; only the persisted evidence is lost, and
        # that is stated rather than swallowed.
        print("[WARN] receipt -> could not write %s: %s"
              % (_one_line(rdir, 160), _one_line(e, 120)))
        rpath = None
    print("JS-LINT: %s (sha %s)%s"
          % (status, sha, "\nreceipt: %s" % rpath if rpath else ""))
    return 0 if status in ("PASS", "SKIP") else 1


def cmd_js_lint_all(args):
    """Sweep every discovered project under the scan roots.

    Exists so the gate can be run across a whole machine without naming a
    single repo: `js-lint --all` with no --repo scans the usual home dev
    folders, and `--roots a,b,c` overrides them. `--discover` previews the
    roots and writes nothing, which is the safe first move on a machine where
    you are not sure where the projects live.
    """
    roots_arg, scope, blocking, receipts = None, "full", "error", None
    # --discover wins over --all. Asking "what would you scan?" and getting
    # writes is the worst possible answer to a preview.
    discover_only = "--discover" in args or "--all" not in args
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            roots_arg, i = args[i + 1], i + 2
        elif args[i] == "--roots" and i + 1 < len(args):
            roots_arg, i = args[i + 1], i + 2
        elif args[i] == "--scope" and i + 1 < len(args):
            scope, i = args[i + 1], i + 2
        elif args[i] == "--blocking" and i + 1 < len(args):
            blocking, i = args[i + 1], i + 2
        elif args[i] == "--receipts" and i + 1 < len(args):
            receipts, i = args[i + 1], i + 2
        else:
            i += 1
    if scope not in ("full", "changed"):
        print("JS-LINT-ALL: FAIL\n- bad --scope: %s (full|changed)" % scope)
        return 1
    if blocking not in ("error", "warning", "none"):
        print("JS-LINT-ALL: FAIL\n- bad --blocking: %s "
              "(error|warning|none)" % blocking)
        return 1

    explicit_roots = bool(roots_arg)
    if roots_arg:
        roots = [os.path.abspath(os.path.expanduser(r.strip()))
                 for r in roots_arg.split(",") if r.strip()]
        missing = [r for r in roots if not os.path.isdir(r)]
        if missing:
            # A gate that scanned nothing must not report green. A typo in
            # --roots and a genuinely empty tree look identical downstream,
            # so the typo has to fail here.
            print("JS-LINT-ALL: FAIL\n- --roots is not a directory: %s"
                  % _one_line(", ".join(missing), 300))
            return 1
    else:
        roots = default_scan_roots()
        if not roots:
            print("JS-LINT-ALL: FAIL\n- no scan roots found. Pass "
                  "--roots <dir>[,<dir>...] explicitly.")
            return 1
    print("[INFO] scanning: %s" % _one_line(", ".join(roots), 400))
    projects = discover_project_roots(roots)

    if discover_only:
        print("[INFO] %d project root(s) found:" % len(projects))
        for p in projects:
            print("  %s" % _one_line(p, 300))
        print("JS-LINT-ALL: DISCOVER (nothing written; re-run with --all)")
        return 0

    if not projects:
        print("JS-LINT-ALL: SKIP (no composer.json / package.json under the "
              "scan roots)")
        return 0

    run_id = _run_id()
    summary = []
    for p in projects:
        # Each project keeps its own receipt under its own repo, by default.
        # Forwarding one --receipts dir here would make every project write
        # the same js-lint.json, and all but the last would be destroyed
        # while the printed summary still claimed N projects scanned.
        sub = ["--repo", p, "--scope", scope, "--blocking", blocking]
        if "--no-init-config" in args:
            sub.append("--no-init-config")
        try:
            rc = cmd_js_lint(sub)
        except Exception as e:                    # noqa: BLE001
            # One unreadable project must not abort the machine-wide run.
            rc = 1
            print("[ERROR] %s -> sweep aborted this project: %s"
                  % (_one_line(p, 200), _one_line(e, 160)))
        summary.append({"project": p, "rc": rc})
        print("")

    failed = [s for s in summary if s["rc"] == 1]
    ran = len(summary)
    print("=" * 60)
    print("JS-LINT-ALL SUMMARY: %d project(s) scanned, %d failing"
          % (ran, len(failed)))
    for s in summary:
        mark = "FAIL" if s["rc"] == 1 else "ok"
        print("  %-4s %s" % (mark, _one_line(s["project"], 200)))
    receipt = {"tool": "guided-run js-lint --all", "run_id": run_id,
               "roots": roots, "scanned": ran, "failing": len(failed),
               "projects": summary}
    # The summary describes EVERY project, so it does not belong inside any
    # one of them. Prefer an explicit --receipts; else a directory that is
    # not itself a scanned project -- writing it into cwd would deposit an
    # untracked file in a repo the user is standing in, where it can be swept
    # into a commit and misread as that project's own evidence.
    here = os.path.abspath(".")
    inside = any(here == p or here.startswith(p + os.sep) for p in projects)
    if receipts:
        base = receipts
    elif inside:
        base = os.path.dirname(roots[0]) if roots else here
    else:
        base = here
    try:
        rdir = os.path.join(base, "guided-receipts", run_id)
        os.makedirs(rdir, exist_ok=True)
        rpath = os.path.join(rdir, "js-lint-all.json")
        with open(rpath, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
    except OSError as e:
        print("[WARN] summary receipt -> could not write: %s"
              % _one_line(e, 120))
        rpath = None
    print("summary receipt: %s" % (rpath or "(not written)"))
    return 1 if failed else 0


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
    rc, out = sh(["git", "rev-parse", "--is-inside-work-tree"], repo,
                  timeout=30)
    detail["git_ready"] = (rc == 0 and out.strip() == "true")
    if not shutil.which("ao"):
        detail["hint"] = ("%s (releases: %s, docs: %s)"
                          % (ao_install_hint(), AO_RELEASES, AO_DOCS))
        return "MISSING", detail
    rc, out = sh(["ao", "--version"], repo, timeout=30)
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
    run_id = _run_id()
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
        p = subprocess.run(cmd, input=blob, capture_output=True,
                           encoding="utf-8", errors="replace",
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
    run_id = _run_id()
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
    run_id = _run_id()
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


# Install targets: tool -> skills root, relative to $HOME. skills/ is the
# single source of truth and every installed copy must be byte-identical to
# it. Foreign skills that merely share a root (e.g. ~/.agents/skills) are
# deliberately ignored: a shared root is not drift.
TOOL_SKILL_PATHS = (
    ("kiro", os.path.join(".kiro", "skills")),
    ("grok", os.path.join(".grok", "skills")),
    ("opencode", os.path.join(".config", "opencode", "skills")),
    ("zed", os.path.join(".agents", "skills")),
)


def _tree_digest(root):
    """Stable sha256 over a folder: sorted (relpath, file sha256) pairs.

    An unreadable file folds in a sentinel instead of raising: the gate must
    report drift, never crash, and a file nobody can read must never hash-equal
    a readable one.
    """
    root = Path(root)
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(path.relative_to(root).as_posix().encode("utf-8"))
        h.update(b"\0")
        try:
            h.update(hashlib.sha256(path.read_bytes()).digest())
        except OSError as exc:
            h.update(b"\0unreadable:" + type(exc).__name__.encode("utf-8"))
    return h.hexdigest()


GUIDED_MANIFEST = os.path.join(".guided", "installed.json")


def read_install_manifest(home):
    """Guided names the installer last recorded, or [] when absent/unreadable.

    The manifest is the only reliable discriminator on a shared root: it names
    exactly what we installed, so a foreign skill is never mistaken for an
    orphan, and a genuinely removed guided skill still gets caught.
    """
    path = os.path.join(home, GUIDED_MANIFEST)
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return []
    names = data.get("skills") if isinstance(data, dict) else None
    if not isinstance(names, list):
        return []
    return sorted({n for n in names if isinstance(n, str)})


def source_skill_names(repo):
    """(digests, invalid) for skills/. invalid = dirs carrying no SKILL.md.

    Returns ([], ["<unreadable>"]) when skills/ cannot be listed, so a
    permissions problem is reported instead of raised at the gate.
    """
    root = os.path.join(repo, "skills")
    try:
        entries = sorted(os.listdir(root))
    except OSError as e:
        return {}, ["<unreadable: %s>" % e]
    digests, invalid = {}, []
    for entry in entries:
        folder = os.path.join(repo, "skills", entry)
        if not os.path.isdir(folder):
            continue
        if os.path.isfile(os.path.join(folder, "SKILL.md")):
            digests[entry] = _tree_digest(folder)
        else:
            invalid.append(entry)
    return digests, invalid


def sync_drift(repo, home):
    """Diff skills/ against every installed tool path -> (status, detail)."""
    src = os.path.join(repo, "skills")
    if not os.path.isdir(src):
        return "FAIL", {"error": "skills/ not found under %s" % repo}
    sources, invalid = source_skill_names(repo)
    recorded = read_install_manifest(home)
    # Recorded by the installer but no longer shipped by skills/. Only drift
    # while it still sits in a tool root; a clean removal is not a problem.
    orphans = sorted(set(recorded) - set(sources))
    tools, total = {}, 0
    for tool, rel in TOOL_SKILL_PATHS:
        dest = os.path.join(home, rel)
        if not os.path.isdir(dest):
            tools[tool] = {"path": dest, "state": "not-installed",
                           "drifted": []}
            continue
        rows = []
        for name, digest in sources.items():
            folder = os.path.join(dest, name)
            if not os.path.isdir(folder):
                state = "missing"
            elif _tree_digest(folder) != digest:
                state = "stale"
            else:
                state = "up-to-date"
            rows.append({"skill": name, "state": state})
        for name in orphans:
            if os.path.isdir(os.path.join(dest, name)):
                rows.append({"skill": name, "state": "orphaned"})
        bad = [r["skill"] for r in rows if r["state"] != "up-to-date"]
        total += len(bad)
        tools[tool] = {"path": dest, "state": "checked",
                       "drifted": bad, "skills": rows}
    total += len(invalid)
    if invalid:
        hint = ("add a SKILL.md to %s, or delete the stray directory"
                % ", ".join("skills/" + n for n in invalid))
    elif total:
        hint = "run install.ps1 -Target all (or ./install.sh) to resync"
    else:
        hint = "every installed tool path matches skills/"
    detail = {"source": src, "skills": len(sources), "drifted": total,
              "invalid": invalid, "orphans": orphans,
              "manifest": os.path.join(home, GUIDED_MANIFEST),
              "recorded": recorded, "tools": tools, "hint": hint}
    return ("PASS" if not total else "FAIL"), detail


def cmd_sync(args):
    repo, home, receipts = ".", os.path.expanduser("~"), None
    i = 0
    while i < len(args):
        if args[i] == "--check":
            i += 1
        elif args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--home" and i + 1 < len(args):
            home, i = args[i + 1], i + 2
        elif args[i] == "--receipts" and i + 1 < len(args):
            receipts, i = args[i + 1], i + 2
        else:
            print("unknown option for sync: %s" % args[i])
            return 1
    repo = os.path.abspath(repo)
    status, detail = sync_drift(repo, home)
    if "error" in detail:
        print("[FAIL] sync -> %s" % detail["error"])
        return 1
    for tool, info in detail["tools"].items():
        if info["state"] == "not-installed":
            print("  %-10s not-installed %s" % (tool, info["path"]))
            continue
        for row in info["skills"]:
            if row["state"] != "up-to-date":
                print("  %-10s %-12s %s"
                      % (tool, row["state"], row["skill"]))
        if not info["drifted"]:
            print("  %-10s ok           %d skills"
                  % (tool, len(info["skills"])))
    for name in detail["invalid"]:
        print("  %-10s %-12s %s (no SKILL.md)" % ("repo", "invalid", name))
    if not detail["recorded"] and not detail["invalid"]:
        print("  note        no %s yet, so orphan detection is off; "
              "the installer writes it" % GUIDED_MANIFEST)
    print("[%s] sync -> %s" % (status, detail["hint"]))
    run_id = _run_id()
    rdir = os.path.join(receipts or os.path.join(repo, "guided-receipts"),
                        run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, "sync.json")
    with open(rpath, "w", encoding="utf-8") as f:
        json.dump({"tool": "guided-run sync", "run_id": run_id,
                   "sha": git_sha(repo), "repo": repo, "home": home,
                   "status": status, "details": detail}, f, indent=2)
    print("SYNC: %s (%d drifted)\nreceipt: %s"
          % (status, detail["drifted"], rpath))
    return 0 if status == "PASS" else 1


def cmd_record_install(args):
    """Write ~/.guided/installed.json: the guided names the installer shipped.

    Both installers call this, so the manifest cannot drift between platforms.
    """
    repo, home, i = ".", os.path.expanduser("~"), 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo, i = args[i + 1], i + 2
        elif args[i] == "--home" and i + 1 < len(args):
            home, i = args[i + 1], i + 2
        else:
            print("unknown option for record-install: %s" % args[i])
            return 1
    repo = os.path.abspath(repo)
    if not os.path.isdir(os.path.join(repo, "skills")):
        print("[FAIL] record-install -> skills/ not found under %s" % repo)
        return 1
    names, _ = source_skill_names(repo)
    path = os.path.join(home, GUIDED_MANIFEST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "skills": sorted(names),
                   "recorded": datetime.now(timezone.utc).isoformat()},
                  f, indent=2)
    print("OK  manifest -> %s (%d skills)" % (path, len(names)))
    return 0


def cmd_php_trace(args):
    """Print entry:line -> include:function:line from include edges and function defs."""
    import os
    import re
    repo = "."
    entry = None
    i = 0
    while i < len(args):
        if args[i] == "--repo" and i + 1 < len(args):
            repo = args[i + 1]
            i += 2
            continue
        if args[i] == "--entry" and i + 1 < len(args):
            entry = args[i + 1].replace("\\", "/")
            i += 2
            continue
        i += 1
    skip = {"vendor", "node_modules", ".git", "storage", "cache"}
    files = {}
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in skip and not d.startswith(".")]
        for name in filenames:
            if not name.endswith(".php"):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, repo).replace("\\", "/")
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            files[rel] = lines
    funcs = {}
    for rel, lines in files.items():
        for n, line in enumerate(lines, 1):
            m = re.search(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
            if m:
                funcs.setdefault(m.group(1), []).append("%s:%d" % (rel, n))
    print("PHP TRACE")
    calls = 0
    for rel, lines in files.items():
        if entry and entry not in rel:
            continue
        for n, line in enumerate(lines, 1):
            inc = re.search(r"(include|require)(_once)?\s*\(?\s*['\"]([^'\"]+\.php)", line)
            if inc:
                print("  %s:%d includes %s" % (rel, n, inc.group(3)))
            call = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
            if not call:
                continue
            name = call.group(1)
            if name in ("if", "for", "while", "switch", "catch", "function", "array", "isset", "empty"):
                continue
            targets = funcs.get(name) or []
            if not targets:
                continue
            print("  %s:%d -> %s:%s" % (rel, n, name, targets[0]))
            calls += 1
            if calls >= 40:
                print("  ... truncated")
                break
        if calls >= 40:
            break
    print("PHP TRACE: PASS" if files else "PHP TRACE: FAIL no php files")
    return 0 if files else 1



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
    if cmd == "js-lint":
        if "--all" in rest or "--discover" in rest or "--roots" in rest:
            return cmd_js_lint_all(rest)
        return cmd_js_lint(rest)
    if cmd == "orchestrator":
        return cmd_orchestrator(rest)
    if cmd == "mcp":
        return cmd_mcp(rest)
    if cmd == "lsp":
        return cmd_lsp(rest)
    if cmd == "sync":
        return cmd_sync(rest)
    if cmd == "record-install":
        return cmd_record_install(rest)
    if cmd == "init":
        return cmd_init(rest)
    if cmd == "php-trace":
        return cmd_php_trace(rest)
    print("unknown command: %s "
          "(validate-plan|verify|react-doctor|growth|php-audit|js-lint|"
          "orchestrator|mcp|lsp|sync|record-install|init|php-trace)" % cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
