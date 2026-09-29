"""Contract tests for the sh() exit-code contract and the not_run report.

Two follow-ups from review:
  M1  a bad cwd / unreadable path raised out of the gate instead of reporting
  M2  a tool that never ran was reported as "unparseable output"
"""
import ast
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import guided_run as g  # noqa: E402

IS_NT = os.name == "nt"


class ShExitCodeContractTest(unittest.TestCase):
    """124 timeout / 125 environment / 127 no program must stay distinct."""

    def test_codes_are_distinct(self):
        self.assertEqual(len({g.SH_TIMEOUT, g.SH_NO_ENVIRONMENT,
                              g.SH_NO_PROGRAM}), 3)

    def test_bad_cwd_is_reported_not_raised(self):
        """M1: this used to raise NotADirectoryError straight through."""
        rc, out = g.sh(["git", "--version"], "C:/no/such/dir")
        self.assertEqual(rc, g.SH_NO_ENVIRONMENT)
        self.assertIn("cannot run in", out)

    def test_missing_program_is_127_not_125(self):
        rc, out = g.sh(["definitely-not-a-real-binary-xyz"], ".")
        self.assertEqual(rc, g.SH_NO_PROGRAM)
        self.assertIn("not found", out)

    def test_timeout_is_124(self):
        rc, out = g.sh([sys.executable, "-c", "import time; time.sleep(5)"],
                       ".", timeout=1)
        self.assertEqual(rc, g.SH_TIMEOUT)
        self.assertIn("TIMEOUT", out)

    def test_a_real_command_is_untouched(self):
        rc, out = g.sh(["git", "--version"], ".")
        self.assertEqual(rc, 0, msg=out)


class UnreadableSourceTest(unittest.TestCase):
    """M1: a skills/ we cannot list must be reported, not raised."""

    def test_unlistable_skills_path_is_reported_not_raised(self):
        """A `skills` that is a FILE makes os.listdir raise on every OS, so
        the guard is exercisable without relying on POSIX permission bits."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "skills").write_text("not a directory", encoding="utf-8")
            digests, invalid = g.source_skill_names(str(repo))
            self.assertEqual(digests, {})
            self.assertEqual(len(invalid), 1)
            self.assertTrue(invalid[0].startswith("<unreadable:"), invalid)

    def test_a_readable_skills_dir_still_yields_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            skills = repo / "skills"
            (skills / "guided-plan").mkdir(parents=True)
            (skills / "guided-plan" / "SKILL.md").write_text("x",
                                                             encoding="utf-8")
            digests, invalid = g.source_skill_names(str(repo))
            self.assertEqual(list(digests), ["guided-plan"])
            self.assertEqual(invalid, [])

    def test_gate_reports_a_non_directory_source_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "skills").write_text("not a directory", encoding="utf-8")
            status, detail = g.sync_drift(str(repo), tmp)
            self.assertEqual(status, "FAIL")
            self.assertIn("skills/ not found", detail["error"])

    @unittest.skipIf(IS_NT, "POSIX: chmod is a no-op on NT")
    def test_gate_reports_a_permission_denied_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            skills = repo / "skills"
            skills.mkdir()
            (skills / "guided-plan").mkdir()
            (skills / "guided-plan" / "SKILL.md").write_text("x",
                                                             encoding="utf-8")
            os.chmod(skills, 0)
            try:
                status, detail = g.sync_drift(str(repo), tmp)
            finally:
                os.chmod(skills, 0o755)
            self.assertEqual(status, "FAIL")
            self.assertTrue(detail["invalid"], msg=detail)
            self.assertTrue(detail["invalid"][0].startswith("<unreadable:"),
                            detail["invalid"])


class NotRunReportTest(unittest.TestCase):
    """M2: a tool that never started must not read as a parse failure."""

    def test_not_run_carries_the_reason_not_a_parse_error(self):
        step = g._not_run("phpstan", g.SH_NO_PROGRAM, "not found: phpstan")
        self.assertIn("not_run", step)
        self.assertNotIn("error", step)
        self.assertEqual(step["errors"], 0)
        self.assertEqual(step["step"], "phpstan")

    def test_not_run_accepts_extra_scope(self):
        step = g._not_run("phpstan", g.SH_TIMEOUT, "TIMEOUT", scope="changed")
        self.assertEqual(step["scope"], "changed")

    def test_not_run_rcs_are_distinct_from_a_real_failure(self):
        for rc in (0, 1, 2, 255):
            self.assertNotIn(rc, g.NOT_RUN_RCS)

    def test_every_auditor_step_gates_on_not_run(self):
        """M2 guard: every step_* auditor must turn a tool that never started
        into `not_run`, never into a parse error.

        The auditor list is derived from the source instead of pinned as a
        count. A pinned count has to be hand-edited whenever an auditor is
        added -- which is exactly the moment you are least looking at this
        file -- and a guard that has to be maintained by hand is a guard that
        eventually reports a number nobody checked. Deriving it keeps the
        original strength (drop a gate and this fails) with no ongoing tax.
        """
        tree = ast.parse((ROOT / "scripts" / "guided_run.py")
                         .read_text(encoding="utf-8"))
        steps = [n for n in tree.body
                 if isinstance(n, ast.FunctionDef)
                 and n.name.startswith("step_")]
        self.assertTrue(steps, "no step_* auditors found; the scan is broken")
        ungated = []
        for n in steps:
            body = ast.dump(n)
            # Both halves matter. Checking only the `return _not_run(` node is
            # not enough: neutering the `if rc in NOT_RUN_RCS:` condition
            # leaves that return sitting in the tree, and the guard would go
            # quiet on exactly the regression it exists to catch.
            returns_not_run = any(
                isinstance(node, ast.Return) and "_not_run" in ast.dump(node)
                for node in ast.walk(n))
            if not (returns_not_run and "NOT_RUN_RCS" in body):
                ungated.append(n.name)
        self.assertEqual(ungated, [], "auditor lost its not_run gate")

    def test_unparseable_is_still_used_for_output_that_is_not_json(self):
        """The two conditions must not be conflated again."""
        step = g._unparseable("phpstan", 1, "not json")
        self.assertIn("error", step)
        self.assertNotIn("not_run", step)


class AuditStepNotRunTest(unittest.TestCase):
    """End to end: a phpstan that cannot start reports not_run."""

    def test_phpstan_reports_not_run_when_the_tool_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            bindir = repo / "vendor" / "bin"
            bindir.mkdir(parents=True)
            # A vendor phpstan that exists but is not executable as a program.
            (bindir / "phpstan").write_text("not a program", encoding="utf-8")
            (repo / "phpstan.neon").write_text("parameters: {}\n",
                                              encoding="utf-8")
            step = g.step_phpstan(str(repo), "full")
            if step.get("rc") in g.NOT_RUN_RCS:
                self.assertIn("not_run", step)
            else:
                # POSIX can exec a text file with a shebang; the tool then
                # fails for its own reasons, which is a different code path.
                self.assertNotIn("unparseable output",
                                 str(step.get("error", "")),
                                 msg="a not-runnable tool must not be "
                                     "reported as a parse failure")


if __name__ == "__main__":
    unittest.main()
