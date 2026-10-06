"""Smoke suite for scripts/guided_run.py.

Contract-level checks only: every command's exit code + key output, run as a
real subprocess. Stdlib-only, no network, no side effects outside temp dirs.

This contract is why it has no mocked cases: a gate's branching logic
(JSON parsing, "tool never started" vs "ran and stayed quiet", severity
classification) cannot be reached from a subprocess without a real linter on
PATH. That logic is unit-tested separately, in-process and hermetic, in
test_js_lint_step.py. Do not widen this file to import the module.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "guided_run.py"
SERVERS = ("phpstan", "phpcs", "php-composer", "laravel-boost")


def run_guided(*args, cwd=None, home=None, timeout=120):
    """Run guided_run.py as a subprocess. `home` isolates ~/.guided/mcp."""
    env = None
    if home is not None:
        env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        cwd=str(cwd or ROOT), capture_output=True,
        encoding="utf-8", errors="replace", timeout=timeout, env=env)


class CliBasicsTest(unittest.TestCase):
    def test_no_args_prints_usage(self):
        r = run_guided()
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("Commands:", r.stdout)

    def test_unknown_command_fails(self):
        r = run_guided("frobnicate")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("unknown command", r.stdout)


class ValidatePlanTest(unittest.TestCase):
    def test_shipped_example_passes(self):
        r = run_guided("validate-plan",
                       "skills/guided-plan/examples/plan-ir.example.json")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        self.assertIn("PLAN IR: PASS", r.stdout)

    def test_invalid_plan_fails_with_reasons(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{}", encoding="utf-8")
            r = run_guided("validate-plan", bad)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("PLAN IR: FAIL", r.stdout)
            self.assertIn("missing required key: goal", r.stdout)


def minimal_plan(**overrides):
    plan = {
        "goal": "Cancel a pending order and release reserved stock.",
        "blast_radius": {"files": ["src/orders/cancel.ts"]},
        "steps": [{"file": "src/orders/cancel.ts", "action": "Add guard"}],
        "test_strategy": {"tests": ["cancel.test.ts"]},
        "done_criteria": ["Tests green"],
        "source_of_standards": "project convention",
    }
    plan.update(overrides)
    return plan


def run_plan(tmp, name, plan):
    path = Path(tmp) / name
    path.write_text(json.dumps(plan), encoding="utf-8")
    return run_guided("validate-plan", path)


class NonFunctionalRequirementsTest(unittest.TestCase):
    def test_nfr_block_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "plain.json", minimal_plan())
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("PLAN IR: PASS", r.stdout)
            self.assertNotIn("nfr missing", r.stdout)

    def test_well_formed_nfr_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "nfr.json", minimal_plan(nfr={
                "growth_horizon": "200 -> 20k orders/day in 12 months",
                "latency": "p95 < 300ms",
                "assumptions": ["No platform team"],
            }))
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("PLAN IR: PASS", r.stdout)
            self.assertNotIn("nfr missing", r.stdout)

    def test_malformed_nfr_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "bad-nfr.json", minimal_plan(nfr={
                "latency": 300,
                "assumptions": "no platform team",
            }))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("nfr.latency must be a string", r.stdout)
            self.assertIn("nfr.assumptions must be a string array", r.stdout)

    def test_large_change_without_nfr_warns_but_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = minimal_plan()
            plan["blast_radius"] = {
                "files": ["a.ts", "b.ts", "c.ts", "d.ts"],
                "justification": "Splitting the service",
            }
            plan["steps"] = [
                {"file": f, "action": "Refactor"} for f in
                ("a.ts", "b.ts", "c.ts", "d.ts")
            ]
            r = run_plan(tmp, "large.json", plan)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("PLAN IR: PASS", r.stdout)
            self.assertIn("nfr missing on a large change", r.stdout)

    def test_key_decision_without_why_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "kd.json", minimal_plan(
                key_decisions=[{"decision": "Use the outbox"}],
            ))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn(
                "each key_decision needs decision + why", r.stdout
            )

    def test_key_decision_exit_cost_must_be_a_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "kd2.json", minimal_plan(
                key_decisions=[{
                    "decision": "Use the outbox",
                    "why": "Prevents dual writes",
                    "exit_cost": 3,
                }],
            ))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn(
                "key_decision.exit_cost must be a string", r.stdout
            )

    def test_key_decisions_must_be_an_array_of_strings(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "kd3.json", minimal_plan(key_decisions=0))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("key_decisions must be an array", r.stdout)
            r = run_plan(tmp, "kd4.json", minimal_plan(
                key_decisions=[{"decision": ["a"], "why": 1}]))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn(
                "each key_decision needs decision + why as non-empty strings",
                r.stdout,
            )

    def test_empty_nfr_does_not_suppress_the_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = minimal_plan()
            plan["blast_radius"] = {
                "files": ["a.ts", "b.ts", "c.ts", "d.ts"],
                "justification": "Splitting the service",
            }
            plan["steps"] = [
                {"file": f, "action": "Refactor"} for f in
                ("a.ts", "b.ts", "c.ts", "d.ts")
            ]
            r = run_plan(tmp, "empty-nfr.json", dict(plan, nfr={}))
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("PLAN IR: PASS", r.stdout)
            self.assertIn("nfr missing on a large change", r.stdout)

    def test_unknown_nfr_key_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_plan(tmp, "typo.json", minimal_plan(nfr={
                "scalabilty": "20k/day",
            }))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("unknown nfr key: scalabilty", r.stdout)

    def test_optional_blocks_must_be_arrays(self):
        """A falsy non-array used to slip through `or []` unvalidated."""
        for field in ("invariants", "events", "key_decisions"):
            for value in (0, False, ""):
                with self.subTest(field=field, value=value):
                    with tempfile.TemporaryDirectory() as tmp:
                        r = run_plan(tmp, "arr.json",
                                     minimal_plan(**{field: value}))
                        self.assertEqual(
                            r.returncode, 1, msg=r.stdout + r.stderr)
                        self.assertIn(
                            "%s must be an array" % field, r.stdout)

    def test_optional_blocks_accept_null(self):
        for field in ("invariants", "events", "key_decisions", "nfr"):
            with self.subTest(field=field):
                with tempfile.TemporaryDirectory() as tmp:
                    r = run_plan(tmp, "null.json",
                                 minimal_plan(**{field: None}))
                    self.assertEqual(
                        r.returncode, 0, msg=r.stdout + r.stderr)
                    self.assertIn("PLAN IR: PASS", r.stdout)


class McpTest(unittest.TestCase):
    def test_snippets_are_valid_json_for_all_platforms(self):
        for platform, top_key in (("opencode", "mcp"),
                                  ("kiro", "mcpServers"),
                                  ("zed", "context_servers"),
                                  ("grok", "mcpServers")):
            with self.subTest(platform=platform):
                r = run_guided("mcp", "--print-snippet", platform)
                self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
                data = json.loads(r.stdout)
                self.assertTrue(
                    all(s in data[top_key] for s in SERVERS),
                    msg="missing servers in %s: %r" % (platform, data))

    def test_bad_platform_fails(self):
        r = run_guided("mcp", "--print-snippet", "not-a-platform")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("unknown platform", r.stdout)

    def test_advisory_run_exits_zero_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("mcp", "--repo", tmp, home=tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("MCP: ", r.stdout)
            receipts = list(Path(tmp).glob("guided-receipts/*/mcp.json"))
            self.assertEqual(len(receipts), 1, msg=r.stdout)


class LspTest(unittest.TestCase):
    def test_opencode_snippet_is_valid_json(self):
        r = run_guided("lsp", "--print-snippet", "opencode")
        self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
        data = json.loads(r.stdout)
        self.assertIs(data["lsp"], True)
        self.assertEqual(data["permission"]["lsp"], "allow")

    def test_bad_platform_fails(self):
        r = run_guided("lsp", "--print-snippet", "not-a-platform")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("unknown platform", r.stdout)

    def test_advisory_run_exits_zero_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("lsp", "--repo", tmp, home=tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("LSP: ", r.stdout)
            receipts = list(Path(tmp).glob("guided-receipts/*/lsp.json"))
            self.assertEqual(len(receipts), 1, msg=r.stdout)


class AdvisoryCommandsTest(unittest.TestCase):
    def test_orchestrator_exits_zero_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("orchestrator", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("ORCHESTRATOR: ", r.stdout)
            receipts = list(
                Path(tmp).glob("guided-receipts/*/orchestrator.json"))
            self.assertEqual(len(receipts), 1, msg=r.stdout)

    def test_init_scaffolds_repo_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("init", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            rmap = Path(tmp) / "docs" / "repo-map.json"
            self.assertTrue(rmap.is_file(), msg=r.stdout)
            self.assertIn("test_commands", json.loads(
                rmap.read_text(encoding="utf-8")))

    def test_php_audit_skips_non_php(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("php-audit", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("PHP-AUDIT: SKIP", r.stdout)

    def test_react_doctor_skips_non_react(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("react-doctor", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("REACT-DOCTOR: SKIP", r.stdout)

    def test_js_lint_skips_repo_without_js_sources(self):
        """No .js asset in the fixture: SKIP without ever reaching npx."""
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("js-lint", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("JS-LINT: SKIP", r.stdout)
            receipts = list(Path(tmp).glob("guided-receipts/*/js-lint.json"))
            self.assertEqual(len(receipts), 1, msg=r.stdout)

    def test_js_lint_receipt_carries_inline_js_coverage(self):
        """The coverage metric is reported even when the lane SKIPs."""
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "view.php").write_text(
                "<html><script>var a = 1;</script>"
                "<script src='/static/x.js'></script></html>",
                encoding="utf-8")
            r = run_guided("js-lint", "--repo", tmp)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            receipts = list(Path(tmp).glob("guided-receipts/*/js-lint.json"))
            self.assertEqual(len(receipts), 1, msg=r.stdout)
            data = json.loads(receipts[0].read_text(encoding="utf-8"))
            cov = data["inline_js_coverage"]
            self.assertEqual(cov["inline_script_blocks"], 1, msg=data)
            self.assertEqual(cov["files_with_inline_js"], 1, msg=data)
            # No linter ran, so no version may be claimed.
            self.assertIsNone(data["oxlint_version"], msg=data)
            self.assertIsNone(data["oxlint_source"], msg=data)

    def test_js_lint_rejects_bad_scope(self):
        r = run_guided("js-lint", "--scope", "sideways")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("bad --scope", r.stdout)

    def test_js_lint_rejects_bad_blocking(self):
        r = run_guided("js-lint", "--blocking", "sometimes")
        self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
        self.assertIn("bad --blocking", r.stdout)

    def test_growth_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_guided("growth", "--repo", tmp, "--no-memory")
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("GROWTH: ", r.stdout)


if __name__ == "__main__":
    unittest.main()
