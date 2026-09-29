"""Static contracts for the OpenCode guided primary-agent runtime."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agents" / "opencode"
TASK_ALLOWLISTS = {
    "guided-plan.md": ("explore", "guided-architect"),
    "guided-coding.md": ("explore", "guided-tdd", "guided-reviewer"),
    "guided-refactoring.md": ("explore", "guided-reviewer"),
    "guided-review.md": ("guided-reviewer",),
    "guided-verify.md": (),
}
AUTOMATION_PRIMARIES = tuple(TASK_ALLOWLISTS)

SPECIALISTS = (
    "guided-architect.md",
    "guided-tdd.md",
    "guided-reviewer.md",
)


def read_agent(name):
    return (AGENT_DIR / name).read_text(encoding="utf-8")


def frontmatter(text):
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    return match.group(1) if match else ""


def task_rules(text):
    match = re.search(
        r"(?ms)^  task:\r?\n(?P<body>(?:    .*(?:\r?\n|$))+)", frontmatter(text)
    )
    if not match:
        return {}
    rules = {}
    for line in match.group("body").splitlines():
        parts = line.strip().split(": ", 1)
        if len(parts) == 2:
            name, action = parts
            rules[name.strip().strip('"')] = action
    return rules


class OpenCodeAgentContractTest(unittest.TestCase):
    def test_automation_primaries_are_runtime_contracts_not_skill_wrappers(self):
        for name in AUTOMATION_PRIMARIES:
            with self.subTest(agent=name):
                text = read_agent(name)
                self.assertRegex(frontmatter(text), r"(?m)^mode: primary$")
                self.assertIn("## Agent loop", text)
                self.assertIn("## Delegation policy", text)
                self.assertIn("## Phase boundary", text)
                self.assertNotIn("On every session start, load", text)
                self.assertNotIn(
                    "Never delegate to other guided agents", text
                )

    def test_primary_task_permissions_use_explicit_allowlists(self):
        for name, allowed in TASK_ALLOWLISTS.items():
            with self.subTest(agent=name):
                expected = {"*": "deny"}
                expected.update({specialist: "allow" for specialist in allowed})
                self.assertEqual(task_rules(read_agent(name)), expected)

    def test_specialists_are_read_only_and_non_recursive(self):
        for name in SPECIALISTS:
            with self.subTest(agent=name):
                text = read_agent(name)
                meta = frontmatter(text)
                self.assertRegex(meta, r"(?m)^mode: subagent$")
                self.assertRegex(meta, r"(?m)^  edit: deny$")
                self.assertRegex(meta, r"(?m)^  task: deny$")
                self.assertRegex(meta, r"(?m)^  lsp: allow$")
                self.assertIn("Do not delegate", text)
                self.assertIn("## Return contract", text)

    def test_read_only_agents_cannot_write_through_bash_permissions(self):
        read_only = (
            "guided-plan.md",
            "guided-architect.md",
            "guided-reviewer.md",
            "guided-tdd.md",
        )
        for name in read_only:
            with self.subTest(agent=name):
                meta = frontmatter(read_agent(name))
                self.assertNotRegex(meta, r"(?m)^    \"git .*\": allow$")
                self.assertNotIn("  bash: allow", meta)
        for name in (
            "guided-architect.md",
            "guided-reviewer.md",
            "guided-tdd.md",
        ):
            with self.subTest(agent=name):
                self.assertIn(
                    "  bash: deny", frontmatter(read_agent(name))
        )
        plan = frontmatter(read_agent("guided-plan.md"))
        self.assertIn("    \"*\": deny", plan)
        self.assertIn(
            "    \"python ~/.guided/scripts/guided_run.py "
            "validate-plan *\": allow",
            plan,
        )
        self.assertIn(
            "    \"python */.guided/scripts/guided_run.py "
            "validate-plan *\": allow",
            plan,
        )
        self.assertIn(
            "    \"python *guided_run.py validate-plan*\": ask", plan
        )

    def test_readme_documents_runtime_model_and_restart_boundary(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "Primary-agent orchestrators",
            "optional, on-demand skill guidance",
            "read-only specialist subagents",
            "Quit and restart OpenCode",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, readme)


if __name__ == "__main__":
    unittest.main()
