"""Contract tests for capability-aware semantic retrieval wiring.

These checks protect the static agent contract. The default checks do not
start language servers; the explicitly enabled live smoke test may start the
host's configured language server.
"""
import os
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "guided-docs",
    "guided-buddy",
    "guided-plan",
    "guided-coding",
    "guided-refactoring",
    "guided-review",
    "guided-verify",
)
OPENCODE_AGENTS = (
    "guided-plan.md",
    "guided-coding.md",
    "guided-refactoring.md",
    "guided-review.md",
    "guided-verify.md",
    "guided-buddy.md",
)


class SemanticRetrievalContractTest(unittest.TestCase):
    def test_skills_require_capability_aware_semantic_retrieval(self):
        for skill in SKILLS:
            with self.subTest(skill=skill):
                text = (ROOT / "skills" / skill / "SKILL.md").read_text(
                    encoding="utf-8"
                )
                self.assertIn("## Semantic retrieval (capability-aware)", text)
                self.assertIn("LSP", text)
                self.assertIn("ranged `read`", text)
                self.assertIn("never claim LSP was used", text)
                self.assertIn("navigation evidence, not verification", text)

    def test_opencode_agents_expose_read_only_lsp_permission(self):
        for agent in OPENCODE_AGENTS:
            with self.subTest(agent=agent):
                text = (ROOT / "agents" / "opencode" / agent).read_text(
                    encoding="utf-8"
                )
                self.assertRegex(text, re.compile(r"(?m)^  lsp: allow$"))

    def test_opencode_setup_and_version_fallback_are_documented(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "## Optional LSP retrieval",
            "OPENCODE_EXPERIMENTAL_LSP_TOOL=true",
            '"lsp": true',
            "OpenCode v2 currently preserves `lsp` configuration",
            "does not auto-install them",
            "guided_run.py lsp --repo .",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, readme)

    @unittest.skipUnless(
        os.environ.get("GUIDED_LSP_E2E") == "1",
        "set GUIDED_LSP_E2E=1 with a configured language server",
    )
    def test_live_opencode_lsp_symbol_lookup(self):
        query = os.environ.get("GUIDED_LSP_QUERY")
        if not query:
            self.skipTest("set GUIDED_LSP_QUERY to a symbol in the target project")
        repo = Path(os.environ.get("GUIDED_LSP_REPO", str(ROOT)))
        result = subprocess.run(
            ["opencode", "debug", "lsp", "symbols", query],
            cwd=repo, capture_output=True, encoding="utf-8",
            errors="replace", timeout=60,
        )
        self.assertEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertNotEqual(result.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
