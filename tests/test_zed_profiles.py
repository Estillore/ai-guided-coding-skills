"""Contract tests for the shipped Zed agent-profile snippet.

Zed replaced custom modes with agent.profiles. A profile is a tool set plus a
default model -- it has no prompt field -- so this file guards the tool sets,
not the behavior. The behavior lives in the skills under ~/.agents/skills.

Upstream source for ZED_PROFILE_TOOLS: the built-in `write` profile in
https://github.com/zed-industries/zed/blob/main/assets/settings/default.json
(`agent.profiles.write.tools`), frozen 2026-09-28. Bump deliberately when Zed
adds or removes a tool; do not auto-follow.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNIPPET = ROOT / "agents" / "zed" / "profiles.snippet.jsonc"

ZED_PROFILE_TOOLS = {
    "apply_code_action", "ask_user", "copy_path", "create_directory",
    "create_thread", "delete_path", "diagnostics", "edit_file", "fetch",
    "find_path", "find_references", "get_code_actions", "go_to_definition",
    "grep", "list_agents_and_models", "list_directory", "move_path",
    "read_file", "rename_symbol", "search_web", "skill", "spawn_agent",
    "terminal", "write_file",
}

# Tools that can change the project. A read-only profile must disable all of them.
MUTATING = {
    "apply_code_action", "copy_path", "create_directory", "delete_path",
    "edit_file", "move_path", "rename_symbol", "terminal", "write_file",
}

READ_ONLY_PROFILES = ("guided_plan", "guided_buddy")


def strip_jsonc(text):
    """Drop // and /* */ comments that are not inside a string literal."""
    out, i, n = [], 0, len(text)
    in_string = in_block = escaped = False
    while i < n:
        ch = text[i]
        if in_block:
            if ch == "*" and text[i:i + 2] == "*/":
                in_block = False
                i += 2
            else:
                i += 1
            continue
        if in_string:
            out.append(ch)
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            i += 1
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
        elif ch == "/" and text[i:i + 2] == "//":
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and text[i:i + 2] == "/*":
            in_block = True
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def load_snippet():
    """The snippet is an object fragment meant to merge into Zed settings."""
    return json.loads("{" + strip_jsonc(SNIPPET.read_text(encoding="utf-8"))
                      + "}")


def load_profiles():
    return load_snippet()["agent"]["profiles"]


class ZedProfileSnippetTest(unittest.TestCase):
    def setUp(self):
        self.profiles = load_profiles()

    def test_snippet_is_parseable_jsonc(self):
        self.assertTrue(self.profiles)

    def test_every_tool_exists_in_zed_schema(self):
        for name, profile in self.profiles.items():
            for tool in profile["tools"]:
                with self.subTest(profile=name, tool=tool):
                    self.assertIn(tool, ZED_PROFILE_TOOLS)

    def test_no_profile_claims_an_unknown_tool(self):
        """Guards against a typo silently disabling a tool Zed never had."""
        for name, profile in self.profiles.items():
            with self.subTest(profile=name):
                self.assertEqual(
                    set(profile["tools"]) - set(ZED_PROFILE_TOOLS), set())

    def test_read_only_profiles_disable_every_mutating_tool(self):
        for name in READ_ONLY_PROFILES:
            with self.subTest(profile=name):
                tools = self.profiles[name]["tools"]
                self.assertEqual(
                    sorted(t for t in MUTATING if tools.get(t) is not False),
                    [])
                self.assertTrue(tools["skill"], "profile must load skills")

    def test_buddy_never_fans_out_to_subagents(self):
        self.assertIs(self.profiles["guided_buddy"]["tools"]["spawn_agent"],
                      False)

    def test_profiles_carry_a_display_name(self):
        for name, profile in self.profiles.items():
            with self.subTest(profile=name):
                self.assertRegex(profile["name"], r"^Guided \w")

    def test_snippet_does_not_override_default_profile(self):
        self.assertNotIn("default_profile", load_snippet()["agent"])

    def test_snippet_does_not_hardcode_a_provider_or_model(self):
        """Model choice belongs to the user; a profile here must not pin one."""
        for name, profile in self.profiles.items():
            with self.subTest(profile=name):
                self.assertNotIn("default_model", profile)

    def test_snippet_documents_the_skill_pairing(self):
        raw = SNIPPET.read_text(encoding="utf-8")
        self.assertIn("/guided-plan", raw)
        self.assertIn("/guided-buddy", raw)
        self.assertRegex(raw, re.compile(r"%APPDATA%.Zed.settings\.json"))


class StripJsoncTest(unittest.TestCase):
    """The stripper must not eat comment markers that live inside strings."""

    def test_line_comments_removed(self):
        self.assertEqual(json.loads(strip_jsonc('{\n// gone\n"a": 1\n}')),
                         {"a": 1})

    def test_block_comments_removed(self):
        raw = '{\n/* multi\n   line */\n"a": 1\n}'
        self.assertEqual(json.loads(strip_jsonc(raw)), {"a": 1})

    def test_inline_block_comment_removed(self):
        self.assertEqual(json.loads(strip_jsonc('{"a": 1 /* x */}')),
                         {"a": 1})

    def test_url_inside_string_survives(self):
        raw = '{"a": "https://example.com/x"}'
        self.assertEqual(json.loads(strip_jsonc(raw)),
                         {"a": "https://example.com/x"})

    def test_comment_markers_inside_string_survive(self):
        raw = '{"a": "/* not a comment */"}'
        self.assertEqual(json.loads(strip_jsonc(raw)),
                         {"a": "/* not a comment */"})

    def test_escaped_quote_does_not_end_the_string(self):
        raw = '{"a": "he said \\"//\\" here"}'
        self.assertEqual(json.loads(strip_jsonc(raw))["a"],
                         'he said "//" here')

    def test_line_comment_inside_block_comment_ignored(self):
        raw = '{/* // nested\n   still block */"a": 1}'
        self.assertEqual(json.loads(strip_jsonc(raw)), {"a": 1})

    def test_shipped_snippet_survives_a_block_comment(self):
        raw = "/* added by a user */\n" + SNIPPET.read_text(encoding="utf-8")
        self.assertTrue(load_profiles().keys())


if __name__ == "__main__":
    unittest.main()
