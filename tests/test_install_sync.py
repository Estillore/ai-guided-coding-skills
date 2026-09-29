"""Contract tests for the install-sync drift gate.

`guided_run.py sync --check` diffs skills/ against every installed tool path.
These tests build throwaway HOMEs so they never touch the real ones and
never depend on the machine's current install state.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "guided_run.py"

# The install contract: every tool resolves its skills to this path under $HOME.
SKILL_ROOTS = {
    "kiro": Path(".kiro") / "skills",
    "grok": Path(".grok") / "skills",
    "opencode": Path(".config") / "opencode" / "skills",
    "zed": Path(".agents") / "skills",
}


def run_sync(home, receipts, *extra, repo=ROOT, timeout=120):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "sync", "--check",
         "--repo", str(repo), "--home", str(home), "--receipts", str(receipts),
         *map(str, extra)],
        cwd=str(ROOT), capture_output=True, encoding="utf-8",
        errors="replace", timeout=timeout)


def install_into(home, tool):
    """Copy the repo's skills/ into one tool root, as the installer would."""
    dest = Path(home) / SKILL_ROOTS[tool]
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "skills", dest)
    return dest


def skill_names():
    return sorted(p.name for p in (ROOT / "skills").iterdir()
                  if (p / "SKILL.md").is_file())


def last_receipt(receipts):
    runs = sorted(p for p in Path(receipts).iterdir() if p.is_dir())
    return json.loads((runs[-1] / "sync.json").read_text(encoding="utf-8"))


def run_record(home, *extra, repo=ROOT, timeout=60):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "record-install",
         "--repo", str(repo), "--home", str(home), *map(str, extra)],
        cwd=str(ROOT), capture_output=True, encoding="utf-8",
        errors="replace", timeout=timeout)


def manifest_path(home):
    return Path(home) / ".guided" / "installed.json"


def write_manifest(home, names):
    path = manifest_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 1, "skills": list(names)}),
                    encoding="utf-8")
    return path


def make_source(base, names=("guided-plan",), stray=()):
    """A minimal skills/ tree: real skills, plus optional stray dirs."""
    src = Path(base) / "skills"
    for name in names:
        d = src / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("---\nname: %s\n---\n" % name,
                                   encoding="utf-8")
    for name in stray:
        d = src / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "notes.md").write_text("no SKILL.md here\n", encoding="utf-8")
    return Path(base)


class SyncPassTest(unittest.TestCase):
    def test_fresh_install_reports_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            install_into(home, "zed")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("SYNC: PASS (0 drifted)", r.stdout)
            self.assertEqual(last_receipt(receipts)["status"], "PASS")

    def test_absent_tool_roots_are_not_drift(self):
        """~/.kiro may simply be absent; that is not drift."""
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            install_into(home, "kiro")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("not-installed", r.stdout)

    def test_every_tool_root_is_compared(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            for tool in SKILL_ROOTS:
                install_into(home, tool)
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            detail = last_receipt(receipts)["details"]
            self.assertEqual(set(detail["tools"]), set(SKILL_ROOTS))
            for info in detail["tools"].values():
                self.assertEqual(info["state"], "checked")
                self.assertEqual(len(info["skills"]), len(skill_names()))


class SyncDriftTest(unittest.TestCase):
    def test_edited_skill_fails_and_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            dest = install_into(home, "zed")
            target = dest / "guided-plan" / "SKILL.md"
            target.write_text(target.read_text(encoding="utf-8")
                              + "\ndrifted\n", encoding="utf-8")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("stale", r.stdout)
            self.assertIn("guided-plan", r.stdout)
            receipt = last_receipt(receipts)
            self.assertEqual(receipt["status"], "FAIL")
            self.assertEqual(
                receipt["details"]["tools"]["zed"]["drifted"], ["guided-plan"])

    def test_changed_bundled_reference_also_counts_as_drift(self):
        """A whole-folder digest must catch edits below SKILL.md too."""
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            dest = install_into(home, "opencode")
            ref = next((dest / "guided-coding" / "references").glob("*.md"))
            ref.write_text("changed\n", encoding="utf-8")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("guided-coding", r.stdout)

    def test_missing_skill_is_reported_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            dest = install_into(home, "zed")
            shutil.rmtree(dest / "guided-buddy")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("missing", r.stdout)
            self.assertIn("guided-buddy", r.stdout)

    def test_foreign_skills_in_a_shared_root_are_ignored(self):
        """~/.agents/skills legitimately holds other agents' skills."""
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            dest = install_into(home, "zed")
            (dest / "some-other-skill").mkdir()
            (dest / "some-other-skill" / "SKILL.md").write_text(
                "name: other\n", encoding="utf-8")
            r = run_sync(home, receipts)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertNotIn("some-other-skill", r.stdout)


@unittest.skipIf(os.name == "nt", "POSIX permission bits; chmod is a no-op on NT")
class UnreadableFileTest(unittest.TestCase):
    """An unreadable file must be reported, never crash the gate."""

    def test_gate_reports_rather_than_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            dest = install_into(home, "zed")
            locked = dest / "guided-plan" / "SKILL.md"
            locked.chmod(0)
            try:
                r = run_sync(home, receipts)
            finally:
                locked.chmod(0o600)
            self.assertNotIn("Traceback", r.stderr, msg=r.stdout + r.stderr)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("stale", r.stdout)
            self.assertIn("guided-plan", r.stdout)


class RecordInstallTest(unittest.TestCase):
    def test_records_every_shipped_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            r = run_record(home)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("manifest ->", r.stdout)
            self.assertEqual(
                json.loads(manifest_path(home).read_text(encoding="utf-8"))
                ["skills"], skill_names())

    def test_stray_dir_is_not_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_source(tmp, stray=("stray",))
            home = Path(tmp) / "home"
            r = run_record(home, repo=repo)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertEqual(
                json.loads(manifest_path(home).read_text(encoding="utf-8"))
                ["skills"], ["guided-plan"])

    def test_unknown_option_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_record(Path(tmp) / "home", "--frobnicate")
            self.assertEqual(r.returncode, 1)
            self.assertIn("unknown option for record-install", r.stdout)

    def test_repo_without_skills_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_record(Path(tmp) / "home", repo=Path(tmp))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("skills/ not found", r.stdout)


class SourceHygieneTest(unittest.TestCase):
    """Follow-up #2: a skills/ dir with no SKILL.md must not be invisible."""

    def test_stray_dir_in_source_fails_the_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_source(tmp, stray=("stray",))
            home, receipts = Path(tmp) / "home", Path(tmp) / "receipts"
            r = run_sync(home, receipts, repo=repo)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("invalid", r.stdout)
            self.assertIn("stray", r.stdout)
            detail = last_receipt(receipts)["details"]
            self.assertEqual(detail["invalid"], ["stray"])
            self.assertEqual(detail["orphans"], [])

    def test_invalid_hint_names_the_fix(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = make_source(tmp, stray=("stray",))
            r = run_sync(Path(tmp) / "home", Path(tmp) / "receipts", repo=repo)
            self.assertIn("add a SKILL.md to skills/stray", r.stdout)


class OrphanTest(unittest.TestCase):
    """Follow-up #1: a guided skill removed from source must not live on."""

    def _installed(self, tmp, names=("guided-plan",)):
        repo = make_source(tmp, names=names)
        home = Path(tmp) / "home"
        shutil.copytree(repo / "skills", home / SKILL_ROOTS["zed"])
        write_manifest(home, names)
        return repo, home

    def test_clean_install_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

    def test_removed_skill_left_in_root_is_orphaned(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            shutil.rmtree(repo / "skills" / "guided-plan")
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("orphaned", r.stdout)
            self.assertIn("guided-plan", r.stdout)
            detail = last_receipt(Path(tmp) / "receipts")["details"]
            self.assertEqual(detail["orphans"], ["guided-plan"])

    def test_removed_skill_also_deleted_from_root_is_not_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            shutil.rmtree(repo / "skills" / "guided-plan")
            shutil.rmtree(home / SKILL_ROOTS["zed"] / "guided-plan")
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)

    def test_foreign_skill_in_shared_root_is_never_an_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            other = home / SKILL_ROOTS["zed"] / "some-other-skill"
            other.mkdir()
            (other / "SKILL.md").write_text("name: other\n", encoding="utf-8")
            shutil.rmtree(repo / "skills" / "guided-plan")
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            # guided-plan is gone from source AND from the manifest? no: it is
            # in the manifest, so it is an orphan -- but the foreign skill is
            # never named.
            self.assertNotIn("some-other-skill", r.stdout)
            self.assertNotIn("some-other-skill",
                             last_receipt(Path(tmp) / "receipts")
                             ["details"]["orphans"])

    def test_absent_manifest_reports_orphan_detection_is_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            manifest_path(home).unlink()
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("orphan detection is off", r.stdout)

    def test_corrupt_manifest_is_ignored_not_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, home = self._installed(tmp)
            manifest_path(home).write_text("{not json", encoding="utf-8")
            r = run_sync(home, Path(tmp) / "receipts", repo=repo)
            self.assertEqual(r.returncode, 0, msg=r.stdout + r.stderr)
            self.assertIn("orphan detection is off", r.stdout)



class SyncCliTest(unittest.TestCase):
    def test_unknown_option_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_sync(Path(tmp) / "home", Path(tmp) / "receipts",
                         "--frobnicate")
            self.assertEqual(r.returncode, 1)
            self.assertIn("unknown option for sync", r.stdout)

    def test_repo_without_skills_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = run_sync(Path(tmp) / "home", Path(tmp) / "receipts",
                         repo=Path(tmp))
            self.assertEqual(r.returncode, 1, msg=r.stdout + r.stderr)
            self.assertIn("skills/ not found", r.stdout)


class InstallerContractTest(unittest.TestCase):
    """The installers must both drive the same four tool roots."""

    INSTALLERS = (ROOT / "install.ps1", ROOT / "install.sh")

    def test_installers_cover_every_sync_target(self):
        for script in self.INSTALLERS:
            text = script.read_text(encoding="utf-8")
            for tool, rel in SKILL_ROOTS.items():
                with self.subTest(script=script.name, tool=tool):
                    self.assertIn(str(rel).replace("\\", "/").lower(),
                                  text.lower().replace("\\", "/"))

    def test_installers_run_the_sync_gate(self):
        for script in self.INSTALLERS:
            text = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertIn("guided_run.py", text)
                self.assertIn("sync --check", text)

    def test_zed_install_points_at_the_profile_snippet(self):
        for script in self.INSTALLERS:
            text = script.read_text(encoding="utf-8")
            with self.subTest(script=script.name):
                self.assertIn("agents/zed/profiles.snippet.jsonc",
                              text.replace("\\", "/"))
                self.assertTrue((ROOT / "agents" / "zed" / "profiles.snippet.jsonc")
                                .is_file())


if __name__ == "__main__":
    unittest.main()
