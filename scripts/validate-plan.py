#!/usr/bin/env python3
"""Validate a Guided Plan IR JSON file against the plan schema rules.

Usage:
    python scripts/validate-plan.py <plan.json> [--changed <file>...]

Checks (stdlib only, no dependencies):
  1. Valid JSON object with all required keys and correct types.
     Unknown top-level keys FAIL (strict IR, archify-style).
  2. >=1 step, each with file + action; every step file must sit
     inside blast_radius (composition check).
  3. Blast radius: >=1 file; >3 files requires a justification string.
  4. Test strategy with >=1 test; done_criteria non-empty.
  5. Slice size: >7 steps warns (split into smaller slices).
  6. Optional blast-radius gate: --changed files must all be inside
     blast_radius.files (prefix match allows planned dirs).

Exit 0 + "PLAN IR: PASS" on success, exit 1 + errors otherwise.
"""
import json
import sys

REQUIRED = ["goal", "blast_radius", "steps", "test_strategy",
            "done_criteria", "source_of_standards"]
ALLOWED_TOP = set(REQUIRED) | {"non_goals", "key_decisions", "invariants",
                               "events", "accuracy"}
DEFAULT_BLAST_RADIUS = 3
MAX_STEPS_PER_SLICE = 7


def err(errors, msg):
    errors.append(msg)


def in_radius(path, files):
    return any(path == f or path.startswith(f.rstrip("/") + "/")
               for f in files)


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__.strip())
        return 0
    plan_path = args[0]
    changed = []
    if "--changed" in args:
        changed = args[args.index("--changed") + 1:]

    errors = []
    warnings = []
    try:
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
    except FileNotFoundError:
        print(f"PLAN IR: FAIL\n- file not found: {plan_path}")
        return 1
    except json.JSONDecodeError as e:
        print(f"PLAN IR: FAIL\n- invalid JSON: {e}")
        return 1

    if not isinstance(plan, dict):
        print("PLAN IR: FAIL\n- top level must be a JSON object")
        return 1

    for key in REQUIRED:
        if key not in plan:
            err(errors, f"missing required key: {key}")
    for key in plan:
        if key not in ALLOWED_TOP:
            err(errors, f"unknown top-level key: {key} "
                        "(strict IR, no extra keys)")

    goal = plan.get("goal", "")
    if goal and (not isinstance(goal, str) or len(goal) < 10):
        err(errors, "goal must be a string of >=10 chars")

    br = plan.get("blast_radius", {})
    files = br.get("files", []) if isinstance(br, dict) else []
    if not isinstance(files, list) or not files or \
            not all(isinstance(x, str) and x for x in files):
        err(errors, "blast_radius.files must be a non-empty string array")
        files = []
    if len(files) > DEFAULT_BLAST_RADIUS and not (
            isinstance(br, dict) and br.get("justification")):
        err(errors, f"blast radius {len(files)} > {DEFAULT_BLAST_RADIUS} "
                    "requires blast_radius.justification")

    steps = plan.get("steps", [])
    if not isinstance(steps, list) or not steps:
        err(errors, "steps must be a non-empty array")
    else:
        for i, s in enumerate(steps):
            if not isinstance(s, dict) or not s.get("file") \
                    or not s.get("action"):
                err(errors, f"steps[{i}] needs file + action")
            elif s["file"] not in files and not in_radius(s["file"], files):
                err(errors, f"steps[{i}] file {s['file']} outside "
                            "blast_radius (composition error)")
        if len(steps) > MAX_STEPS_PER_SLICE:
            warnings.append(f"{len(steps)} steps > {MAX_STEPS_PER_SLICE}: "
                            "split into smaller slices")

    ts = plan.get("test_strategy", {})
    tests = ts.get("tests", []) if isinstance(ts, dict) else []
    if not isinstance(tests, list) or not tests:
        err(errors, "test_strategy.tests must be a non-empty array")

    dc = plan.get("done_criteria", [])
    if not isinstance(dc, list) or not dc:
        err(errors, "done_criteria must be a non-empty array")

    for inv in plan.get("invariants", []) or []:
        if not isinstance(inv, dict) or not inv.get("rule") \
                or not inv.get("enforcement"):
            err(errors, "each invariant needs rule + enforcement")

    for ev in plan.get("events", []) or []:
        if not isinstance(ev, dict) or not ev.get("name") \
                or not isinstance(ev.get("outbox"), bool):
            err(errors, "each event needs name + outbox bool")

    acc = plan.get("accuracy", None)
    if acc is not None:
        if not isinstance(acc, dict):
            err(errors, "accuracy must be an object")
        else:
            for k in ("mutation_min_backend", "mutation_min_frontend"):
                v = acc.get(k, None)
                if v is not None and (not isinstance(v, (int, float))
                                      or not 0 <= v <= 100):
                    err(errors, f"accuracy.{k} must be 0-100")
            for k in ("mutation_scope", "contract_tests", "arch_rules"):
                v = acc.get(k, [])
                if not isinstance(v, list) or not all(
                        isinstance(x, str) and x for x in v):
                    err(errors, f"accuracy.{k} must be a string array")

    for c in changed:
        if not in_radius(c, files):
            err(errors, f"blast-radius drift: {c} not in planned files")

    if errors:
        print("PLAN IR: FAIL")
        for e in errors:
            print(f"- {e}")
        return 1
    for w in warnings:
        print(f"WARNING: {w}")
    extra = f" (+{len(changed)} changed files in radius)" if changed else ""
    print(f"PLAN IR: PASS ({len(files)} files, {len(steps)} steps{extra})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
