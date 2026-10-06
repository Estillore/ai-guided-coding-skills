"""Static contracts for the OpenCode guided primary-agent runtime."""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AGENT_DIR = ROOT / "agents" / "opencode"
TASK_ALLOWLISTS = {
    "guided-plan.md": ("explore", "guided-architect"),
    "guided-coding.md": ("explore", "guided-test-design", "guided-reviewer"),
    "guided-refactoring.md": ("explore", "guided-reviewer"),
    "guided-review.md": ("guided-reviewer",),
    "guided-verify.md": (),
}
AUTOMATION_PRIMARIES = tuple(TASK_ALLOWLISTS)

SPECIALISTS = (
    "guided-architect.md",
    "guided-test-design.md",
    "guided-reviewer.md",
)


def read_agent(name):
    return (AGENT_DIR / name).read_text(encoding="utf-8")


def frontmatter(text):
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    return match.group(1) if match else ""


def permission_pairs(text, key):
    """Ordered [(pattern, action)] for an object-syntax permission block.

    No re.S: `.` must not cross newlines, or a non-final key such as `bash`
    swallows every following 2-space key in the frontmatter. Returns a list, not
    a dict, because OpenCode resolves duplicate patterns by last match and a
    dict would silently collapse them back to their first position.
    """
    match = re.search(
        r"(?m)^  %s:\r?\n(?P<body>(?:    .*(?:\r?\n|$))+)" % re.escape(key),
        frontmatter(text),
    )
    if not match:
        return []
    pairs = []
    for line in match.group("body").splitlines():
        parts = line.strip().split(": ", 1)
        if len(parts) == 2:
            pairs.append((parts[0].strip().strip('"'), parts[1]))
    return pairs


def permission_rules(text, key):
    return dict(permission_pairs(text, key))


def task_rules(text):
    return permission_rules(text, "task")


def bash_pairs(text):
    return permission_pairs(text, "bash")


def bash_rules(text):
    return permission_rules(text, "bash")


def resolve_bash(pairs, command):
    """Resolve one command the way OpenCode does: wildcard, last match wins.

    `*` becomes `.*` under re.S, so it crosses `/` and spaces, matching the
    upstream Wildcard matcher.
    """
    action = None
    for pattern, act in pairs:
        rx = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        if re.match(rx, command, re.S):
            action = act
    return action


MUTATING_GIT = (
    r'(?m)^    "git (commit|push|reset|checkout|restore|clean|merge|rebase'
    r'|stash|branch|tag|add|rm|mv|config|fetch|pull|apply|init|clone|switch'
    r'|cherry-pick|revert|am|worktree|update-ref|update-index|read-tree'
    r'|write-tree|commit-tree|hash-object|notes|bisect|gc|remote|filter-branch'
    r')\b[^"]*": allow$'
)

SHELL_AGENTS = ("guided-plan.md", "guided-architect.md")

# Commands that write, delete, or execute. Each must resolve to deny or ask.
DANGEROUS_COMMANDS = (
    "find . -delete",
    "fd -x rm",
    "rg --pre sh -c id pattern",
    "git diff --output=src/x.ts HEAD",
    "git log --output=/tmp/out.txt --oneline",
    "git show --output=src/x.ts HEAD",
    "git grep -O 'sh -c id' pattern",
    "git commit -m wip",
    "git push origin main",
    "git reset --hard HEAD~1",
    "git checkout main",
    "git branch -d feature",
    "git stash",
    "rm -rf src",
    "mv src/app src/old",
    "cp secrets.json public/",
    "tee out.txt",
    "npm install left-pad",
    "pip install requests",
    "python -c 'import os'",
    "python -m pip install x",
    "npx tsx script.ts",
    "curl https://example.com",
    "bash -c 'id'",
    "sh -c 'id'",
    "eval 'id'",
    "node -e 'require(1)'",
    "bun run script.ts",
    "php -r 'echo 1;'",
    "perl -e 'print 1;'",
)

# Commands the planner and architect need. Each must resolve to allow.
INSPECTION_COMMANDS = (
    "git status",
    "git status --porcelain",
    "git log --oneline -20",
    "git show HEAD --stat",
    "git diff --stat",
    "git grep -n TODO",
    "git blame src/x.ts",
    "git ls-files",
    "git rev-parse --show-toplevel",
    "git describe --tags --always",
    "git shortlog -sn",
    "rg -n TODO",
    "rg --files",
    "grep -rn TODO .",
    "ls -la",
    "Get-ChildItem -Recurse",
    "Test-Path docs/plans",
    "wc -l src/x.ts",
    "head -20 src/x.ts",
    "tail -50 build.log",
    "jq '.version' package.json",
)


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
            "guided-test-design.md",
        )
        for name in read_only:
            with self.subTest(agent=name):
                meta = frontmatter(read_agent(name))
                self.assertNotRegex(meta, MUTATING_GIT)
                self.assertNotIn("  bash: allow", meta)
        for name in (
            "guided-reviewer.md",
            "guided-test-design.md",
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


    def test_shell_agents_share_one_bash_allowlist(self):
        """No include mechanism exists, so the two blocks must not drift."""
        blocks = {name: bash_rules(read_agent(name)) for name in SHELL_AGENTS}
        first = blocks[SHELL_AGENTS[0]]
        for name in SHELL_AGENTS[1:]:
            with self.subTest(agent=name):
                self.assertEqual(blocks[name], first)
        self.assertGreater(len(first), 20)

    def test_bash_allowlist_orders_catch_all_first_and_mutators_last(self):
        """OpenCode uses last-match-wins, so rule order is the whole design."""
        for name in SHELL_AGENTS:
            with self.subTest(agent=name):
                pairs = bash_pairs(read_agent(name))
                self.assertEqual(pairs[0], ("*", "deny"))
                self.assertEqual(
                    len(pairs), len(dict(pairs)),
                    "duplicate pattern: OpenCode resolves it by last match, "
                    "so the ordering invariant cannot be checked",
                )
                first_hard_deny = next(
                    (i for i, (p, a) in enumerate(pairs)
                     if a == "deny" and p != "*"),
                    len(pairs),
                )
                for pattern, action in pairs[first_hard_deny:]:
                    self.assertNotEqual(
                        action, "allow",
                        "%s: allow appears after a mutator deny" % pattern,
                    )

    def test_bash_allowlist_dangerous_commands_never_resolve_to_allow(self):
        """Resolve real commands, not pattern strings, through real semantics."""
        for name in SHELL_AGENTS:
            pairs = bash_pairs(read_agent(name))
            for command in DANGEROUS_COMMANDS:
                with self.subTest(agent=name, command=command):
                    self.assertNotEqual(
                        resolve_bash(pairs, command), "allow",
                        "%r resolves to allow" % command,
                    )

    def test_bash_allowlist_keeps_inspection_commands_allowed(self):
        """The read-only allowlist must still be useful, or nobody needs it."""
        for name in SHELL_AGENTS:
            pairs = bash_pairs(read_agent(name))
            for command in INSPECTION_COMMANDS:
                with self.subTest(agent=name, command=command):
                    self.assertEqual(
                        resolve_bash(pairs, command), "allow",
                        "%r should be allowed" % command,
                    )

    def test_bash_allowlist_gate_specific_forms_beat_the_loose_ask(self):
        """The loose ask must precede the narrow allows, or it shadows them."""
        for name in SHELL_AGENTS:
            pairs = bash_pairs(read_agent(name))
            for command in (
                "python ~/.guided/scripts/guided_run.py validate-plan "
                "docs/plans/x.json",
                "python ~/.guided/scripts/guided_run.py validate-plan x.json "
                "--changed a.ts",
            ):
                with self.subTest(agent=name, command=command):
                    self.assertEqual(resolve_bash(pairs, command), "allow")
            for command in (
                "python scripts/guided_run.py validate-plan x.json",
                "python -c 'import json'",
            ):
                with self.subTest(agent=name, command=command):
                    self.assertNotEqual(resolve_bash(pairs, command), "allow")

    def test_validate_plan_accepts_windows_and_rejects_shell_suffixes(self):
        """A trailing * on the allow rule must not authorize &&, ;, or |."""
        allowed = (
            "py -3 $env:USERPROFILE\\.guided\\scripts\\guided_run.py "
            "validate-plan docs/plans/x.json",
            "python3 $HOME/.guided/scripts/guided_run.py validate-plan "
            "docs/plans/x.json",
        )
        chained = (
            "python ~/.guided/scripts/guided_run.py validate-plan "
            "docs/plans/x.json && rm -rf src",
            "python ~/.guided/scripts/guided_run.py validate-plan "
            "docs/plans/x.json; rm -rf src",
            "python3 $HOME/.guided/scripts/guided_run.py validate-plan "
            "docs/plans/x.json | tee out.txt",
            "py -3 $env:USERPROFILE\\.guided\\scripts\\guided_run.py "
            "validate-plan docs/plans/x.json && del src",
        )
        for name in SHELL_AGENTS:
            pairs = bash_pairs(read_agent(name))
            for command in allowed:
                with self.subTest(agent=name, command=command):
                    self.assertEqual(resolve_bash(pairs, command), "allow")
            for command in chained:
                with self.subTest(agent=name, command=command):
                    self.assertNotEqual(
                        resolve_bash(pairs, command), "allow"
                    )

    def test_bash_allowlist_has_no_write_capable_readers(self):
        """find/fd/--pre/--output/-O turn readers into writers and runners."""
        for name in SHELL_AGENTS:
            rules = bash_rules(read_agent(name))
            for pattern in ("find", "find *", "fd", "fd *"):
                with self.subTest(agent=name, pattern=pattern):
                    self.assertNotIn(pattern, rules)
            for pattern, action in rules.items():
                if action != "allow":
                    continue
                for flag in ("--pre", "--output", "-O ", "-exec", "-delete",
                             "-x ", "-X "):
                    if flag in pattern:
                        with self.subTest(agent=name, pattern=pattern):
                            self.fail(
                                "%s allows %s" % (pattern, flag.strip())
                            )

    def test_planner_may_write_plan_artifacts_only(self):
        rules = permission_rules(read_agent("guided-plan.md"), "edit")
        self.assertEqual(rules.get("*"), "deny")
        self.assertEqual(rules.get("docs/plans/*.json"), "allow")
        self.assertEqual(rules.get("docs/guided-memory.md"), "allow")
        for pattern in rules:
            if pattern not in ("*", "docs/plans/*.json", "docs/guided-memory.md"):
                with self.subTest(pattern=pattern):
                    self.fail("unexpected extra write path: %s" % pattern)
        self.assertIn(
            "  edit: deny", frontmatter(read_agent("guided-architect.md"))
        )

    def test_architect_owns_the_decision_and_bounds_the_growth_lens(self):
        text = read_agent("guided-architect.md")
        for marker in (
            "## Role",
            "Make the decision defensible",
            "**Frame.**",
            "**Ground.**",
            "**Decide.**",
            "**Bind.**",
            "**Fit.**",
            "**Stop.**",
            "State exit cost",
            "Never silently assume",
            "You own the decision for your slice but never set scope",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, text)
        self.assertIn("## Growth lens", text)
        self.assertIn("at most 6 rows", text)
        self.assertIn("Otherwise omit", text)
        for section in (
            "Relevant boundary", "Recommended design", "Trade-off",
            "Blast radius", "Risks and unknowns",
        ):
            with self.subTest(section=section):
                self.assertIn(section, text)
        self.assertIn("at most 15 bullets", text)

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
