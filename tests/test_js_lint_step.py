"""Unit suite for the js-lint lane in scripts/guided_run.py.

The subprocess-level contract (exit codes, receipt shape) lives in
test_guided_run_smoke.py. This file covers the decision logic that contract
cannot reach without a real linter on PATH: JSON parsing, severity
classification, the "tool could not start" vs "ran and stayed quiet" split,
and the inline-<script> coverage metric.

Every oxlint invocation is mocked, so these cases are hermetic -- no network,
no npx, no Node. Stdlib only.
"""
import importlib.util
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "guided_run.py"

_spec = importlib.util.spec_from_file_location("guided_run", SCRIPT)
gr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gr)


def _diag(severity="error", filename="a.js", line=5, column=1):
    return {"diagnostics": [{
        "message": "boom", "code": "eslint(no-debugger)",
        "severity": severity, "filename": filename,
        "labels": [{"span": {"line": line, "column": column}}]}]}


def stub_sh(rc, out):
    """Patch gr.sh with a canned (rc, out) for the duration of a `with`."""
    return mock.patch.object(gr, "sh", lambda cmd, cwd, timeout=600: (rc, out))


class StepOxlintTest(unittest.TestCase):
    def test_error_diagnostic_counts_as_error(self):
        with stub_sh(1, json.dumps(_diag("error"))):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s["errors"], 1, msg=s)
        self.assertEqual(s["warnings"], 0, msg=s)
        self.assertEqual(s["sample"][0].split()[0], "a.js:5:1")

    def test_warning_diagnostic_counts_as_warning(self):
        with stub_sh(0, json.dumps(_diag("warning", line=9))):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s["errors"], 0, msg=s)
        self.assertEqual(s["warnings"], 1, msg=s)
        self.assertIn("a.js:9:1", s["sample"][0])

    def test_empty_diagnostics_is_clean(self):
        with stub_sh(0, json.dumps({"diagnostics": [], "number_of_files": 2})):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s["errors"], 0, msg=s)
        self.assertEqual(s["out"], "clean")

    def test_blank_output_on_success_is_clean_not_unparseable(self):
        """A linter that prints nothing when it finds nothing is not broken."""
        with stub_sh(0, ""):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s["errors"], 0, msg=s)
        self.assertNotIn("error", s)
        self.assertNotIn("not_run", s)

    def test_tool_could_not_start_is_not_run(self):
        """Distinct from a run that produced findings: a missing linter is
        never evidence of clean code."""
        with stub_sh(gr.SH_NO_PROGRAM, "not found: oxlint"):
            s = gr.step_oxlint("/repo", "full")
        self.assertIn("not_run", s)
        self.assertEqual(s["errors"], 0, msg=s)
        self.assertEqual(s["warnings"], 0, msg=s)

    def test_non_json_output_is_unparseable(self):
        with stub_sh(1, "could not parse config file"):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s.get("error"), "unparseable output")

    def test_json_without_diagnostics_key_is_unparseable(self):
        with stub_sh(0, json.dumps({"totally": "different"})):
            s = gr.step_oxlint("/repo", "full")
        self.assertEqual(s.get("error"), "unparseable output")

    def test_findings_carry_a_no_edit_hint(self):
        with stub_sh(1, json.dumps(_diag())):
            s = gr.step_oxlint("/repo", "full")
        self.assertIn("--fix", s["hint"])


class OxlintArgvTest(unittest.TestCase):
    def test_project_binary_wins_over_npx(self):
        """The lockfile's version is the one CI already trusts."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp, "node_modules", "bin")
            d.mkdir(parents=True)
            (d / "oxlint").write_text("", encoding="utf-8")
            argv, source = gr.oxlint_argv(tmp)
        self.assertEqual(source, "project")
        self.assertTrue(argv[0].endswith("node_modules/bin/oxlint"), argv)

    def test_windows_cmd_shim_counts_as_a_local_binary(self):
        """npm ships the shim beside a .cmd on Windows; checking only the
        bare name would report 'no local oxlint' where one exists."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp, "node_modules", "bin")
            d.mkdir(parents=True)
            (d / "oxlint.cmd").write_text("", encoding="utf-8")
            found = gr.local_oxlint_path(tmp)
            argv, source = gr.oxlint_argv(tmp)
        self.assertTrue(found.endswith("node_modules/bin/oxlint.cmd"), found)
        self.assertEqual(source, "project", argv)

    def test_absent_local_binary_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(gr.local_oxlint_path(tmp))

    def test_falls_back_to_pinned_npx(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("GUIDED_OXLINT_VERSION", None)
                argv, source = gr.oxlint_argv(tmp)
        self.assertEqual(argv[:2], ["npx", "-y"], argv)
        self.assertEqual(argv[2], "oxlint@" + gr.OXLINT_VERSION, argv)
        self.assertTrue(source.startswith("pinned:"), source)

    def test_env_override_changes_the_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(os.environ,
                                 {"GUIDED_OXLINT_VERSION": "9.9.9"}):
                argv, source = gr.oxlint_argv(tmp)
        self.assertEqual(argv[2], "oxlint@9.9.9", argv)
        self.assertEqual(source, "pinned:9.9.9", source)


class InlineScriptAuditTest(unittest.TestCase):
    def test_counts_inline_bodies_and_ignores_src(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "view.php").write_text(
                "<html><script>var a = 1;</script>"
                "<script src='/static/x.js'></script></html>",
                encoding="utf-8")
            Path(tmp, "empty.php").write_text(
                "<html><script>   \n</script></html>", encoding="utf-8")
            Path(tmp, "clean.php").write_text(
                "<html><script src='/a.js'></script></html>", encoding="utf-8")
            cov = gr.inline_script_audit(tmp)
        self.assertEqual(cov["inline_script_blocks"], 1, msg=cov)
        self.assertEqual(cov["files_with_inline_js"], 1, msg=cov)
        self.assertEqual(cov["examples"][0]["file"], "view.php", msg=cov)
        self.assertFalse(cov["capped"], msg=cov)

    def test_no_inline_scripts_reports_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.php").write_text("<p>hi</p>", encoding="utf-8")
            cov = gr.inline_script_audit(tmp)
        self.assertEqual(cov["inline_script_blocks"], 0, msg=cov)
        self.assertEqual(cov["files_with_inline_js"], 0, msg=cov)

    def test_multiline_script_body_is_one_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.php").write_text(
                "<script>\nvar a=1;\nvar b=2;\n</script>", encoding="utf-8")
            cov = gr.inline_script_audit(tmp)
        self.assertEqual(cov["inline_script_blocks"], 1, msg=cov)


class FindOxlintConfigTest(unittest.TestCase):
    def test_finds_config_nested_under_an_asset_dir(self):
        """Nested configs are real; a root-only search would miss them."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp, "public")
            d.mkdir()
            (d / ".oxlintrc.json").write_text("{}", encoding="utf-8")
            found = gr.find_oxlint_config(tmp)
        self.assertEqual(found, ["public/.oxlintrc.json"])

    def test_absent_config_is_empty_list_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(gr.find_oxlint_config(tmp), [])


class HasJsSourcesTest(unittest.TestCase):
    def test_true_when_asset_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            found = gr.has_js_sources(tmp)
        self.assertTrue(found)

    def test_false_for_php_only_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "a.php").write_text("<?php echo 1;", encoding="utf-8")
            found = gr.has_js_sources(tmp)
        self.assertFalse(found)

    def test_skips_vendor_and_node_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            for sub in ("vendor", "node_modules"):
                d = Path(tmp, sub)
                d.mkdir()
                (d / "x.js").write_text("var a = 1;", encoding="utf-8")
            found = gr.has_js_sources(tmp)
        self.assertFalse(found)


class NodeFloorTest(unittest.TestCase):
    def test_missing_node_is_skip_not_failure(self):
        with mock.patch.object(gr.shutil, "which",
                               lambda name: None if name == "node" else "/x"):
            ok, reason = gr.node_floor_ok()
        self.assertFalse(ok)
        self.assertIn("SKIP", reason)

    def test_floor_rejects_old_node(self):
        with mock.patch.object(gr.shutil, "which", lambda name: "/x"), \
                mock.patch.object(gr, "node_version", lambda: (18, 19)):
            ok, reason = gr.node_floor_ok()
        self.assertFalse(ok)
        self.assertIn("below minimum", reason)

    def test_floor_accepts_supported_node(self):
        with mock.patch.object(gr.shutil, "which", lambda name: "/x"), \
                mock.patch.object(gr, "node_version", lambda: (22, 12)):
            ok, reason = gr.node_floor_ok()
        self.assertTrue(ok, reason)


class FailOpenTest(unittest.TestCase):
    """A scan that never ran must never read as a clean one.

    _not_run reports 0 errors, so a consumer that only branches on
    `skipped`/`error` derives PASS from a run that produced nothing. This is
    the fail-open the not_run/unparseable split exists to prevent, so it is
    pinned here rather than left to the next reader to reintroduce.
    """

    def test_command_reports_skip_when_the_linter_never_ran(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            with mock.patch.object(gr, "ensure_oxlint",
                                   lambda repo: (True, "ready", "1.80.0")), \
                    stub_sh(gr.SH_TIMEOUT, "TIMEOUT after 900s"):
                rc = gr.cmd_js_lint(["--repo", tmp, "--receipts", tmp])
            self.assertEqual(rc, 0, "a timed-out scan must not exit non-zero")
            receipt = json.loads(
                (Path(tmp) / "js-lint.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "SKIP", msg=receipt)

    def test_command_still_fails_on_a_real_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            with mock.patch.object(gr, "ensure_oxlint",
                                   lambda repo: (True, "ready", "1.80.0")), \
                    stub_sh(1, json.dumps(_diag("error"))):
                rc = gr.cmd_js_lint(["--repo", tmp, "--receipts", tmp])
            self.assertEqual(rc, 1, msg=rc)


class InlineScriptHardeningTest(unittest.TestCase):
    def test_repeated_opening_tag_without_terminator_is_fast(self):
        """ReDoS regression: '<script' x k with no '>' was Theta(k*n) under the
        old lookahead, and could hang the gate on one 512 KB file."""
        payload = "<script" * 75000
        started = time.monotonic()
        self.assertEqual(gr._inline_script_count(payload), 0)
        self.assertLess(time.monotonic() - started, 5.0,
                        "script-tag scan is not linear")

    def test_unterminated_tag_is_not_counted(self):
        self.assertEqual(gr._inline_script_count("<script>var a = 1;"), 0)

    def test_src_tag_with_body_is_excluded(self):
        self.assertEqual(
            gr._inline_script_count("<script src='/a.js'>var a=1;</script>"), 0)

    def test_inline_block_is_counted(self):
        self.assertEqual(
            gr._inline_script_count("<script>var a=1;</script>"), 1)

    def test_data_uri_is_still_a_src_tag(self):
        self.assertEqual(
            gr._inline_script_count(
                "<script data-x='1' src='data:,'>var a=1;</script>"), 0)

    def test_cap_is_authoritative_across_directories(self):
        """A cap that only breaks the inner loop lets os.walk keep appending
        past the number the field reports."""
        with tempfile.TemporaryDirectory() as tmp:
            for d in range(5):
                sub = Path(tmp, "v%d" % d)
                sub.mkdir()
                for n in range(10):
                    (sub / ("p%d.php" % n)).write_text(
                        "<script>var a=1;</script>", encoding="utf-8")
            cov = gr.inline_script_audit(tmp, cap=3)
        self.assertEqual(cov["files_with_inline_js"], 3, msg=cov)
        self.assertTrue(cov["capped"], msg=cov)

    @unittest.skipUnless(os.name != "nt",
                         "symlink creation needs a privilege Windows lacks "
                         "by default; the guard is lstat-based and "
                         "platform-independent")
    def test_symlink_to_a_character_device_is_not_read(self):
        with tempfile.TemporaryDirectory() as tmp:
            view = Path(tmp, "x.php")
            view.symlink_to("/dev/zero")
            cov = gr.inline_script_audit(tmp)
        self.assertEqual(cov["inline_script_blocks"], 0, msg=cov)


class OxlintTargetsTest(unittest.TestCase):
    def test_all_candidate_dirs_are_linted_not_just_the_first(self):
        """Laravel has public/ (bundles) and resources/js/ (sources). Stopping
        at index 0 would report 'full' over the wrong tree."""
        with tempfile.TemporaryDirectory() as tmp:
            for d in ("public", "resources", "src"):
                Path(tmp, d).mkdir()
            targets, used = gr._oxlint_targets(tmp, "full")
        self.assertEqual(used, "full")
        self.assertEqual(sorted(targets), ["public", "resources", "src"])

    def test_falls_back_to_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            targets, used = gr._oxlint_targets(tmp, "full")
        self.assertEqual(targets, ["."])
        self.assertEqual(used, "full")

    def test_receipt_records_what_was_linted(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            with stub_sh(0, json.dumps({"diagnostics": []})):
                s = gr.step_oxlint(tmp, "full")
        self.assertIn("targets", s, msg=s)
        self.assertTrue(s["targets"], msg=s)


class CodeConfigGuardTest(unittest.TestCase):
    def test_ts_config_is_refused_on_the_npx_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            Path(tmp, "oxlint.config.ts").write_text(
                "export default {}", encoding="utf-8")
            found = gr.oxlint_code_config_present(tmp)
        self.assertEqual(found, "oxlint.config.ts")

    def test_jsplugins_in_json_config_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".oxlintrc.json").write_text(
                '{"jsPlugins": ["./p.js"]}', encoding="utf-8")
            found = gr.oxlint_code_config_present(tmp)
        self.assertIn("jsPlugins", found)

    def test_plain_json_config_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".oxlintrc.json").write_text(
                '{"env": {"browser": true}}', encoding="utf-8")
            found = gr.oxlint_code_config_present(tmp)
        self.assertIsNone(found)


class OxlintVersionPinTest(unittest.TestCase):
    def test_plain_semver_is_accepted(self):
        with mock.patch.dict(os.environ,
                             {"GUIDED_OXLINT_VERSION": "1.80.0"}):
            version, err = gr._oxlint_version_pin()
        self.assertEqual(version, "1.80.0")
        self.assertIsNone(err)

    def test_injection_shaped_value_is_rejected(self):
        for bad in ("1.80.0\nJS-LINT: PASS (sha deadbeef)",
                    "1.80.0 --registry=http://evil", "../evil", ""):
            with mock.patch.dict(os.environ,
                                 {"GUIDED_OXLINT_VERSION": bad}):
                if bad == "":
                    continue
                version, err = gr._oxlint_version_pin()
            self.assertIsNone(version, bad)
            self.assertIn("invalid", err, bad)


class OneLineTest(unittest.TestCase):
    def test_newline_cannot_forge_a_second_output_line(self):
        out = gr._one_line('a.js", "status": "PASS\nJS-LINT: PASS')
        self.assertNotIn("\n", out)
        self.assertNotIn("JS-LINT: PASS\n", out)

    def test_control_characters_are_stripped(self):
        self.assertNotIn("\x00", gr._one_line("a\x00b"))

    def test_length_is_bounded(self):
        self.assertLessEqual(len(gr._one_line("x" * 5000)), 300)


class DocumentationConsistencyTest(unittest.TestCase):
    """The lane's docs are part of its contract: an agent reads the SKILL.md,
    not the source. A command the README omits is a command nobody invokes."""

    def _readme(self):
        return (ROOT / "README.md").read_text(encoding="utf-8")

    def test_readme_documents_the_command_and_its_guarantees(self):
        readme = self._readme()
        self.assertIn("js-lint", readme, "js-lint missing from the README")
        row = [ln for ln in readme.splitlines() if "js-lint" in ln
               and ln.strip().startswith("|")]
        self.assertTrue(row, "js-lint is not a row in the harness table")
        self.assertIn("Never installs", row[0])
        self.assertIn("--fix", row[0])
        self.assertIn("inline_js_coverage", row[0])

    def test_repo_map_convention_lists_the_gate(self):
        rmap = json.loads((ROOT / "docs" / "repo-map.json")
                          .read_text(encoding="utf-8"))
        gates = [c for c in rmap.get("conventions", []) if "may exit 1" in c]
        self.assertTrue(gates, "no exit-1 convention in repo-map")
        self.assertIn("js-lint", gates[0], msg=gates[0])

    def test_skill_docs_state_that_skip_is_not_clean(self):
        """The fail-open the review caught is re-opened by an agent that reads
        'SKIP' as 'nothing to report'."""
        for skill in ("guided-verify", "guided-review"):
            with self.subTest(skill=skill):
                text = (ROOT / "skills" / skill / "SKILL.md") \
                    .read_text(encoding="utf-8")
                self.assertIn("js-lint", text)
                self.assertIn("did not run", text)


class InitConfigTest(unittest.TestCase):
    """The one file this lane is allowed to write. Everything below is about
    that write being safe."""

    def test_creates_config_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            created, path, note = gr.init_oxlint_config(tmp)
            self.assertTrue(created, note)
            self.assertTrue(os.path.isfile(path), path)
            with open(path, encoding="utf-8") as f:
                config = json.load(f)
        self.assertTrue(config["env"]["browser"])
        self.assertEqual(sorted(config["plugins"]),
                         ["eslint", "oxc", "typescript", "unicorn"])

    def test_never_overwrites_an_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp, ".oxlintrc.json")
            original = '{"rules":{"no-alert":"error"}}'
            existing.write_text(original, encoding="utf-8")
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            created, path, note = gr.init_oxlint_config(tmp)
            self.assertFalse(created, note)
            self.assertIn("untouched", note)
            self.assertEqual(existing.read_text(encoding="utf-8"), original)

    def test_respects_a_jsonc_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, ".oxlintrc.jsonc").write_text("{}", encoding="utf-8")
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            created, _, note = gr.init_oxlint_config(tmp)
        self.assertFalse(created)
        self.assertIn("untouched", note)

    def test_no_init_config_opt_out_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            created, path, note = gr.init_oxlint_config(tmp, enabled=False)
            self.assertFalse(created)
            self.assertIsNone(path)
            self.assertIn("no-init-config", note)
            self.assertFalse(
                os.path.isfile(os.path.join(tmp, ".oxlintrc.json")))

    def test_unwritable_repo_reports_and_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            with mock.patch("builtins.open",
                            side_effect=PermissionError("denied")):
                created, path, note = gr.init_oxlint_config(tmp)
        self.assertFalse(created)
        self.assertIsNone(path)
        self.assertIn("could not write", note)

    def test_written_config_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "app.js").write_text("var a = 1;", encoding="utf-8")
            _, path, _ = gr.init_oxlint_config(tmp)
            with open(path, encoding="utf-8") as f:
                json.load(f)


class DiscoverRootsTest(unittest.TestCase):
    def _project(self, base, name, marker="composer.json"):
        d = Path(base, name)
        d.mkdir(parents=True)
        (d / marker).write_text("{}", encoding="utf-8")
        return d

    def test_finds_projects_by_composer_or_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self._project(tmp, "phpapp")
            b = self._project(tmp, "nodeapp", marker="package.json")
            found = gr.discover_project_roots([tmp])
        self.assertEqual(len(found), 2, msg=found)
        self.assertIn(str(a), found)
        self.assertIn(str(b), found)

    def test_skips_vendor_and_node_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, "app")
            self._project(tmp, "vendor")
            self._project(tmp, "node_modules")
            found = [os.path.basename(p) for p in
                     gr.discover_project_roots([tmp])]
        self.assertEqual(found, ["app"], msg=found)

    def test_a_project_root_is_not_descended(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp, "monorepo")
            (Path(root, "packages")).mkdir()
            (Path(root, "packages", "composer.json")).write_text(
                "{}", encoding="utf-8")
            found = gr.discover_project_roots([tmp])
        self.assertEqual(found, [str(root)], msg=found)

    def test_missing_root_is_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            found = gr.discover_project_roots(
                [tmp, os.path.join(tmp, "nope")])
        self.assertIsInstance(found, list)

    def test_discover_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._project(tmp, "app")
            before = sorted(os.listdir(tmp))
            rc = gr.cmd_js_lint_all(["--discover", "--roots", tmp])
            after = sorted(os.listdir(tmp))
        self.assertEqual(rc, 0)
        self.assertEqual(before, after, msg="discover must not write")
        self.assertFalse(os.path.isfile(
            os.path.join(tmp, "app", ".oxlintrc.json")))


class SweepTest(unittest.TestCase):
    def test_all_flag_runs_every_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("a", "b"):
                d = Path(tmp, name)
                d.mkdir()
                (d / "composer.json").write_text("{}", encoding="utf-8")
            rc = gr.cmd_js_lint_all(["--all", "--roots", tmp,
                                     "--receipts", tmp])
            self.assertEqual(rc, 0, "SKIP projects must not fail the sweep")
            summary_path = next(Path(tmp).glob("guided-receipts/*/js-lint-all.json"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["scanned"], 2, msg=summary)
        self.assertEqual(summary["failing"], 0, msg=summary)

    def test_sweep_rejects_bad_blocking(self):
        self.assertEqual(
            gr.cmd_js_lint_all(["--all", "--blocking", "maybe"]), 1)


if __name__ == "__main__":
    unittest.main()

class SweepRegressionTest(unittest.TestCase):
    """One test per defect found in review. Each names the failure it stops."""

    def _js_project(self, base, name):
        d = Path(base, name)
        d.mkdir(parents=True)
        (d / "composer.json").write_text("{}", encoding="utf-8")
        (d / "app.js").write_text("var a = 1;", encoding="utf-8")
        return d

    def test_per_project_receipts_do_not_collide(self):
        """--receipts used to forward one dir to every project, so N-1
        receipts were silently destroyed by the same constant filename."""
        with tempfile.TemporaryDirectory() as tmp:
            a = self._js_project(tmp, "a")
            b = self._js_project(tmp, "b")
            out = Path(tmp, "out")
            out.mkdir()
            gr.cmd_js_lint_all(["--all", "--roots", tmp, "--receipts",
                                str(out)])
            # Evidence must live in each project, not in one shared dir.
            for proj in (a, b):
                self.assertTrue(
                    list(proj.glob("guided-receipts/*/js-lint.json")),
                    msg="no per-project receipt in %s" % proj)

    def test_discover_beats_all(self):
        """`--all --discover` used to run the full sweep, writing configs
        into every project, because discover_only was derived from --all."""
        with tempfile.TemporaryDirectory() as tmp:
            p = self._js_project(tmp, "a")
            before = sorted(os.listdir(p))
            rc = gr.cmd_js_lint_all(["--all", "--discover", "--roots", tmp])
            after = sorted(os.listdir(p))
        self.assertEqual(rc, 0)
        self.assertEqual(before, after, msg="--discover must write nothing")
        self.assertFalse(os.path.isfile(str(p / ".oxlintrc.json")))

    def test_bad_explicit_root_fails_instead_of_passing(self):
        """A typo in --roots used to scan nothing and exit 0: a gate that
        scanned nothing must never report green."""
        with tempfile.TemporaryDirectory() as tmp:
            rc = gr.cmd_js_lint_all(
                ["--all", "--roots", os.path.join(tmp, "Proejcts")])
        self.assertEqual(rc, 1, msg="a nonexistent --roots must fail")

    def test_empty_but_real_root_still_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = gr.cmd_js_lint_all(["--all", "--roots", tmp])
        self.assertEqual(rc, 0, msg="a real but empty root is not a failure")

    def test_one_broken_project_does_not_abort_the_sweep(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._js_project(tmp, "a")
            self._js_project(tmp, "boom")
            with mock.patch.object(
                    gr, "cmd_js_lint",
                    side_effect=[0, RuntimeError("unreadable")]):
                rc = gr.cmd_js_lint_all(["--all", "--roots", tmp,
                                         "--receipts", tmp])
            summary_path = next(
                Path(tmp).glob("guided-receipts/*/js-lint-all.json"))
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        # Both projects are still scanned, and the broken one is recorded as a
        # failure rather than aborting the machine-wide run.
        self.assertEqual(summary["scanned"], 2, msg=summary)
        self.assertEqual(summary["failing"], 1, msg=summary)
        self.assertEqual(rc, 1, "the broken project must surface as a failure")

    def test_summary_receipt_avoids_landing_in_a_scanned_project(self):
        """Run from inside a project, the summary must not be deposited in
        it. Uses a real chdir: os.path.abspath(".") on Windows resolves via
        the Win32 API, so mocking os.getcwd does NOT change it and the test
        would pass without ever reaching the branch."""
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            proj = self._js_project(tmp, "site")
            try:
                os.chdir(proj)
                with mock.patch.object(gr, "cmd_js_lint", return_value=0):
                    gr.cmd_js_lint_all(["--all", "--roots", tmp])
            finally:
                os.chdir(cwd)
            leaked = list(proj.glob("guided-receipts/*/js-lint-all.json"))
        self.assertEqual(leaked, [], msg=leaked)

    def test_config_is_not_written_to_a_project_with_no_js(self):
        """A sweep matches on composer.json, so a pure-PHP repo would collect
        a config for a linter that can never run there."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp, "pure-php")
            d.mkdir()
            (d / "composer.json").write_text("{}", encoding="utf-8")
            created, path, note = gr.init_oxlint_config(d)
        self.assertFalse(created, note)
        self.assertIn("no JS assets", note)

    def test_ensure_reason_is_single_line(self):
        """Repo-controlled path text reaches `reason`; unsanitised it could
        forge the gate's own verdict line on stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp, "a")
            d.mkdir()
            (d / "app.js").write_text("var a = 1;", encoding="utf-8")
            (d / "oxlint.config.ts").write_text("x", encoding="utf-8")
            with mock.patch.object(gr.shutil, "which", lambda n: "/x"), \
                    mock.patch.object(gr, "node_version", lambda: (22, 12)), \
                    stub_sh(0, "1.80.0"):
                _, reason, _ = gr.ensure_oxlint(d)
            self.assertNotIn("\n", reason)
            self.assertNotIn("\r", reason)

    def test_default_scan_dirs_exclude_bare_documents(self):
        """A stray package.json under $HOME/Documents must not make the
        sweep write into a tree the user never named."""
        self.assertNotIn("Documents", gr.DEFAULT_SCAN_DIRS)
        self.assertIn("Documents/GitHub", gr.DEFAULT_SCAN_DIRS)