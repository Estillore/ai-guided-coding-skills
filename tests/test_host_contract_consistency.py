"""Skill text, OpenCode agents, and Zed profiles must describe one phase.

These checks fail when a slash skill tells the model to do something the
matching agent permission or Zed profile cannot do, or the reverse.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

MEMORY_SKILLS = (
    "guided-plan",
    "guided-planner",
    "guided-coding",
    "guided-tdd",
    "guided-review",
    "guided-code-reviewer",
    "guided-docs",
    "guided-refactoring",
    "guided-verify",
    "guided-infra",
)

# Sentences that append a growing memory block into the always-on file.
MEMORY_WRITE_FORBIDDEN = (
    "Project Memory section in `AGENTS.md`",
    "Project Memory section to `AGENTS.md`",
    "Prefer writing into `AGENTS.md`",
    "update findings that become permanent conventions into `AGENTS.md`",
    "Update memory into `AGENTS.md`",
    "Update project memory into `AGENTS.md`",
    "Update project knowledge into `AGENTS.md`",
    "prefer `AGENTS.md` when running in OpenCode",
    "prefer a Project Memory section in `AGENTS.md`",
    "Prefer updating `AGENTS.md`",
)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


class HostContractConsistencyTest(unittest.TestCase):
    def test_project_memory_is_a_dedicated_file(self):
        for skill in MEMORY_SKILLS:
            text = read("skills/%s/SKILL.md" % skill)
            with self.subTest(skill=skill):
                self.assertIn("docs/guided-memory.md", text)
                for phrase in MEMORY_WRITE_FORBIDDEN:
                    self.assertNotIn(phrase, text)

    def test_plan_stops_and_zed_plan_profile_does_not_require_the_gate(self):
        text = read("skills/guided-plan/SKILL.md")
        self.assertIn(
            "Stop after the plan. Do not implement and do not invoke "
            "another guided phase.",
            text,
        )
        self.assertIn(
            "On the Zed Guided Plan profile, deliver the plan in chat and "
            "stop. That profile cannot write files or run a terminal, so it "
            "does not run validate-plan.",
            text,
        )
        self.assertIn(
            "When the host can write `docs/plans/*.json` and run a shell, "
            "write the Plan IR and run validate-plan until it prints "
            "`PLAN IR: PASS`.",
            text,
        )
        self.assertNotIn("without waiting", text)
        self.assertNotIn("proceed directly to `guided-coding`", text)
        self.assertNotIn(
            "Editing the codebase or creating files without explicit request",
            text,
        )

    def test_planner_skill_points_at_guided_plan(self):
        text = read("skills/guided-planner/SKILL.md")
        self.assertIn("Use `guided-plan` full mode.", text)
        self.assertNotIn("Never write the plan file yourself.", text)
        self.assertNotIn("chain to Build", text)
        self.assertNotIn("proceed directly to implementation", text)
        self.assertNotIn("chains to implementation", text)

    def test_tdd_skill_writes_and_runs(self):
        text = read("skills/guided-tdd/SKILL.md")
        self.assertIn("Write the failing test to disk and run it.", text)
        self.assertNotIn(
            "Never run `Write`, `Edit`, or create files yourself.", text
        )
        self.assertNotIn("human must type", text)

    def test_coding_skill_matches_opencode_and_zed_hosts(self):
        text = read("skills/guided-coding/SKILL.md")
        self.assertIn("Manual Mode is `guided-buddy`.", text)
        self.assertIn("references/quality-rules.md", text)
        self.assertNotIn("## Quality Layer", text)
        self.assertNotIn("the `guided` agent", text)
        self.assertNotIn("the human should type", text)
        self.assertNotIn("| **Build** |", text)
        self.assertIn("`guided-coding`", text)
        self.assertIn("`guided-test-design`", text)

    def test_review_skill_autofixes_only_on_a_writer(self):
        review = read("skills/guided-review/SKILL.md")
        self.assertIn(
            "Auto-fix CRITICAL and HIGH only when the active host can edit.",
            review,
        )
        self.assertIn(
            "The `guided-reviewer` subagent is read-only and does not edit.",
            review,
        )
        self.assertIn("recommend `guided-verify` and stop", review)
        self.assertNotIn("chain to `guided-verify`", review)
        self.assertNotIn("| **Build** |", review)

        companion = read("skills/guided-code-reviewer/SKILL.md")
        self.assertIn("Use `guided-review`.", companion)
        self.assertNotIn("the human should type", companion)

    def test_quality_reference_does_not_coach_typing(self):
        text = read("skills/guided-coding/references/quality-rules.md")
        self.assertNotIn("the human should type", text)

    def test_opencode_test_designer_is_not_named_guided_tdd(self):
        self.assertFalse(
            (ROOT / "agents" / "opencode" / "guided-tdd.md").exists()
        )
        text = read("agents/opencode/guided-test-design.md")
        self.assertIn("name: guided-test-design", text)
        self.assertRegex(text, r"(?m)^mode: subagent$")
        self.assertRegex(text, r"(?m)^  edit: deny$")
        self.assertRegex(text, r"(?m)^  bash: deny$")
        coding = read("agents/opencode/guided-coding.md")
        self.assertIn("guided-test-design: allow", coding)
        self.assertNotIn("guided-tdd:", coding)

    def test_plan_agent_keeps_memory_and_portable_validator(self):
        text = read("agents/opencode/guided-plan.md")
        self.assertIn('"docs/guided-memory.md": allow', text)
        self.assertIn("py -3", text)
        self.assertIn("python3", text)
        self.assertIn("Do not implement", text)

    def test_readme_has_one_host_phase_contract(self):
        text = read("README.md")
        self.assertIn("## Host phase contract", text)
        self.assertIn("does not auto-chain", text)
        self.assertIn("guided-test-design", text)
        self.assertIn(
            "OpenCode loads skills from both `~/.config/opencode/skills` "
            "and `~/.agents/skills`.",
            text,
        )

    def test_installers_remove_the_retired_tdd_agent_name(self):
        ps1 = read("install.ps1")
        sh = read("install.sh")
        self.assertIn("guided-tdd.md", ps1)
        self.assertIn("Remove-Item", ps1)
        self.assertIn(
            'rm -f "$HOME/.config/opencode/agent/guided-tdd.md"', sh
        )


if __name__ == "__main__":
    unittest.main()
