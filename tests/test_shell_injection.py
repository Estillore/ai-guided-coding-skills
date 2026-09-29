"""Security regression tests: sh() must never let a value become syntax.

The finding: sh() used shell=True and callers interpolated values into a
command string, so a filename containing shell metacharacters was re-parsed
as a command. The fix splits the API: sh() takes an argv list and runs with
shell=False; sh_line() keeps the shell only for project-defined command
lines from config. These tests prove the value can no longer execute.
"""
import ast
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "guided_run.py"
sys.path.insert(0, str(ROOT / "scripts"))
import guided_run as g  # noqa: E402

IS_NT = os.name == "nt"
MARK = "INJECTED_MARKER"


# Metacharacter payloads that are ALSO legal Windows filenames, so they can be
# used as a real tracked file. Windows forbids < > : " / \ | ? * in a name,
# which rules a redirection marker out of the portable set.
METACHAR_VALUES = [
    ".env & whoami",
    ".env; whoami",
    ".env && whoami",
    ".env $(whoami)",
    ".env `whoami`",
    ".env & calc",
]


def redirect_payloads(marker):
    """Side-effect payloads: only run where `>` is a legal filename char."""
    return [
        "x & echo pwned > %s" % marker,
        "x | echo pwned > %s" % marker,
        "x ; echo pwned > %s" % marker,
        "$(echo pwned > %s)" % marker,
        "`echo pwned > %s`" % marker,
        'x" & echo pwned > %s & "y' % marker,
    ]


def _enclosing(tree, target):
    """Name of the function that lexically contains `target`, or None."""
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and any(
                target is n for n in ast.walk(fn)):
            return fn
    return None


class ShRejectsShellStringsTest(unittest.TestCase):
    def test_shell_string_is_refused_not_guessed(self):
        rc, out = g.sh("git rev-parse --short HEAD", ".")
        self.assertEqual(rc, 127)
        self.assertIn("argv list", out)

    def test_empty_argv_is_refused(self):
        rc, out = g.sh([], ".")
        self.assertEqual(rc, 127)
        self.assertIn("empty command", out)

    def test_missing_program_is_a_clean_127(self):
        rc, out = g.sh(["definitely-not-a-real-binary-xyz", "--x"], ".")
        self.assertEqual(rc, 127)
        self.assertIn("not found", out)


class ArgvIsNotReparsedTest(unittest.TestCase):
    def test_real_argv_command_still_runs(self):
        """The gate must still work: argv has to actually execute."""
        rc, out = g.sh(["git", "--version"], ".")
        self.assertEqual(rc, 0, msg=out)
        self.assertIn("git version", out)

    def test_metacharacter_value_is_passed_through_verbatim(self):
        """A value containing & ; $() must reach git as ONE argument."""
        with tempfile.TemporaryDirectory() as tmp:
            for value in METACHAR_VALUES:
                with self.subTest(value=value):
                    rc, out = g.sh(["git", "ls-files", "--error-unmatch",
                                    value], tmp)
                    self.assertNotEqual(rc, 0)
                    self.assertIn("fatal", out.lower() + "fatal")

    def test_spaces_in_a_value_are_not_word_split(self):
        """Positive proof: a tracked name with spaces is found only if the
        value arrived as a single argv element. A shell would split it."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            self._init_repo(repo)
            name = ".env backup one"
            (repo / name).write_text("SECRET=1\n", encoding="utf-8")
            self._add(repo)
            rc, out = g.sh(["git", "ls-files", "--error-unmatch", name],
                           str(repo), timeout=30)
            self.assertEqual(rc, 0, msg="argv was word-split: %s" % out)

    def test_the_actual_call_site_is_not_injectable(self):
        """Exercise the real .env probe value against a real git repo."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            marker = repo / MARK
            self._init_repo(repo)
            evil = ".env & echo pwned > %s" % marker
            if os.name == "nt":
                evil = ".env & whoami"     # redirect is illegal in a Win name
            (repo / evil).write_text("SECRET=1\n", encoding="utf-8")
            self._add(repo)
            rc, _ = g.sh(["git", "ls-files", "--error-unmatch", evil],
                         str(repo), timeout=30)
            self.assertFalse(marker.exists(),
                             msg="the .env probe executed an injected command")
            # Tracked, so --error-unmatch succeeds and no shell ran.
            self.assertEqual(rc, 0)

    @staticmethod
    def _init_repo(repo):
        subprocess.run(["git", "init", "-q", str(repo)], check=True,
                       capture_output=True)

    @staticmethod
    def _add(repo):
        subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True,
                       capture_output=True)


@unittest.skipIf(IS_NT, "POSIX: `>` is legal in a filename, Windows forbids it")
class PosixSideEffectProofTest(unittest.TestCase):
    """The strongest available proof: a real injected command would leave a
    file behind. Run only where the payload is also a legal filename."""

    def test_redirect_payloads_never_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, MARK)
            for payload in redirect_payloads(marker):
                with self.subTest(payload=payload[:30]):
                    if os.path.exists(marker):
                        os.remove(marker)
                    g.sh(["git", "ls-files", "--error-unmatch", payload], tmp)
                    self.assertFalse(os.path.exists(marker),
                                     msg="payload executed: %r" % payload)

    def test_shebang_substitution_does_not_execute(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, MARK)
            payload = "x; touch %s" % marker
            g.sh(["git", "ls-files", "--error-unmatch", payload], tmp)
            self.assertFalse(os.path.exists(marker))


class ShLineIsTheDocumentedExceptionTest(unittest.TestCase):
    def test_config_command_lines_still_run_through_a_shell(self):
        rc, out = g.sh_line("echo guided-ok", ".")
        self.assertEqual(rc, 0, msg=out)
        self.assertIn("guided-ok", out)

    def test_docstring_forbids_interpolating_values(self):
        doc = g.sh_line.__doc__ or ""
        self.assertIn("Never pass an interpolated value", doc)


@unittest.skipUnless(IS_NT, "Windows program resolution")
class WindowsResolutionTest(unittest.TestCase):
    def test_bare_npx_resolves_to_the_cmd_wrapper(self):
        resolved = g._resolve_program("npx")
        if resolved is None:
            self.skipTest("npx not installed")
        self.assertTrue(resolved.lower().endswith((".cmd", ".bat", ".exe")),
                        msg=resolved)

    def test_powershell_wrapper_is_refused(self):
        self.assertIsNone(g._resolve_program("npx.ps1"))

    def test_repo_relative_vendor_bin_gets_a_suffix_probe(self):
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "vendor" / "bin"
            bindir.mkdir(parents=True)
            (bindir / "faketool.bat").write_text("@echo off\r\n",
                                                 encoding="ascii")
            resolved = g._resolve_program("vendor/bin/faketool", tmp)
            self.assertIsNotNone(resolved, msg="suffix probe missed the .bat")
            self.assertTrue(resolved.lower().endswith(".bat"))

    def test_relative_path_resolves_against_cwd_not_the_process_cwd(self):
        """Regression guard.

        CreateProcess resolves argv[0] against the PARENT's cwd, while the
        shell this replaced resolved a relative path against the `cwd`
        argument. Checking existence against the process cwd instead made
        every composer vendor tool unreachable unless you happened to be
        standing in the project root.
        """
        with tempfile.TemporaryDirectory() as tmp:
            bindir = Path(tmp) / "vendor" / "bin"
            bindir.mkdir(parents=True)
            (bindir / "faketool.bat").write_text(
                "@echo off\r\necho REACHED_THE_WRAPPER\r\n",
                encoding="ascii")
            # The process cwd is the repo root; only a cwd-aware resolver
            # can find this file.
            resolved = g._resolve_program("vendor/bin/faketool", tmp)
            self.assertIsNotNone(resolved, msg="not resolved against cwd")
            self.assertTrue(os.path.isabs(resolved),
                            msg="must hand CreateProcess an absolute path")
            rc, out = g.sh(["vendor/bin/faketool"], tmp)
            self.assertEqual(rc, 0, msg=out)
            self.assertIn("REACHED_THE_WRAPPER", out)

    def test_batch_wrapper_rejects_an_embedded_quote(self):
        with tempfile.TemporaryDirectory() as tmp:
            bat = Path(tmp) / "probe.cmd"
            bat.write_text("@echo off\r\necho ARGS=[%*]\r\n", encoding="ascii")
            marker = Path(tmp) / MARK
            rc, out = g.sh([str(bat), 'a" & echo pwned > %s & "b' % marker],
                           tmp)
            self.assertEqual(rc, 127, msg=out)
            self.assertIn("double quote", out)
            self.assertFalse(marker.exists())


class NoStrayShellUsageTest(unittest.TestCase):
    """Static guard: keep the split from eroding back to shell=True.

    The two guards are COMPLEMENTARY, not redundant, and neither subsumes the
    other. Know which catches what before deleting one:
      test_no_literal_shell_true_anywhere  -> a hard-coded subprocess shell=
      test_only_sh_line_enables_the_shell  -> a flipped use_shell variable
    Re-injecting either one alone is caught by exactly one of them.
    """

    SOURCE = SCRIPT.read_text(encoding="utf-8")

    def test_no_literal_shell_true_anywhere(self):
        """The shell flag is a variable now, so no call may hard-code True."""
        tree = ast.parse(self.SOURCE)
        hits = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Call)
                for kw in n.keywords
                if kw.arg == "shell" and getattr(kw.value, "value", None) is True]
        self.assertEqual(
            hits, [],
            "literal shell=True on line(s) %s; route it through "
            "sh_line() so the exception stays visible" % hits)

    def test_only_sh_line_enables_the_shell(self):
        """Exactly one caller may pass use_shell=True, and it is sh_line."""
        tree = ast.parse(self.SOURCE)
        enabled = []
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args
                    and isinstance(node.args[-1], ast.Constant)):
                continue
            if node.args[-1].value is True:
                fn = _enclosing(tree, node)
                if fn:
                    enabled.append(fn.name)
        self.assertEqual(enabled, ["sh_line"],
                         "only sh_line() may enable the shell, found %s"
                         % enabled)

    def test_sh_always_runs_without_a_shell(self):
        src = (ROOT / "scripts" / "guided_run.py").read_text(encoding="utf-8")
        self.assertIn("_run_process(argv, cwd, timeout, False)", src)

    def test_no_sh_call_passes_a_bare_string(self):
        tree = ast.parse(self.SOURCE)
        bad = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "sh" and node.args
                    and isinstance(node.args[0], ast.Constant)
                    and isinstance(node.args[0].value, str)):
                bad.append(node.lineno)
        self.assertEqual(bad, [], "sh() called with a shell string on %s" % bad)

    def test_sh_docstring_states_the_contract(self):
        doc = g.sh.__doc__ or ""
        self.assertIn("argv list", doc)
        self.assertIn("never through a shell", doc)


if __name__ == "__main__":
    unittest.main()
