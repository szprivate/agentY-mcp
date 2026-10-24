"""Skills over MCP: list_skills, read_skill and the skills as MCP prompts.

    python -m unittest tests.test_skills_mcp
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from src import skills_mcp


def _make(root: Path):
    a = root / "alpha"
    (a / "references").mkdir(parents=True)
    (a / "SKILL.md").write_text(
        '---\nname: alpha\ndescription: Does the alpha thing. Activate when the user asks for alpha.\n'
        'allowed-tools: get_node_schema, update_workflow\n---\n# Alpha\nbody\n', encoding="utf-8")
    (a / "references" / "x.md").write_text("extra", encoding="utf-8")
    b = root / "beta"
    b.mkdir()
    (b / "SKILL.md").write_text('---\nname: beta\ndescription: >\n  Folded text\n  continues here.\n---\nbeta body\n', encoding="utf-8")
    (root / "no-skill").mkdir()          # no SKILL.md -> not a skill


class Functions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _make(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_load_skills_reads_frontmatter(self):
        skills = {s["name"]: s for s in skills_mcp.load_skills(self.root)}
        self.assertEqual(set(skills), {"alpha", "beta"})
        self.assertEqual(skills["alpha"]["summary"], "Does the alpha thing")
        self.assertTrue(skills["alpha"]["when_to_use"].startswith("Activate when"))
        self.assertEqual(skills["alpha"]["allowed_tools"], ["get_node_schema", "update_workflow"])
        self.assertEqual(skills["beta"]["description"], "Folded text continues here.")

    def test_read_skill_gives_text_and_extra_files(self):
        out = json.loads(skills_mcp._read_skill("alpha", "", self.root))
        self.assertIn("# Alpha", out["skill_md"])
        self.assertEqual(out["files"], ["references/x.md"])

    def test_read_extra_file(self):
        self.assertEqual(skills_mcp._read_skill("alpha", "references/x.md", self.root), "extra")

    def test_read_cannot_leave_the_skill_folder(self):
        out = json.loads(skills_mcp._read_skill("alpha", "../beta/SKILL.md", self.root))
        self.assertIn("error", out)

    def test_unknown_skill_lists_the_available_ones(self):
        out = json.loads(skills_mcp._read_skill("nope", "", self.root))
        self.assertEqual(out["available"], ["alpha", "beta"])

    def test_prompts_registered(self):
        from mcp.server.fastmcp import FastMCP
        m = FastMCP("t")
        self.assertEqual(skills_mcp.register_prompts(m, self.root), 2)
        names = {p.name for p in asyncio.run(m.list_prompts())}
        self.assertEqual(names, {"alpha", "beta"})
        got = asyncio.run(m.get_prompt("alpha"))
        self.assertIn("# Alpha", got.messages[0].content.text)


class Server(unittest.TestCase):
    def test_tools_offered_and_instructed(self):
        from src import mcp_server
        self.assertIn(skills_mcp.list_skills, mcp_server._TOOLS)
        self.assertIn(skills_mcp.read_skill, mcp_server._TOOLS)
        self.assertIn("list_skills", mcp_server.INSTRUCTIONS)
        self.assertIn("read_skill", mcp_server.INSTRUCTIONS)

    def test_the_real_skills_are_listed_and_readable(self):
        skills = json.loads(skills_mcp.list_skills())
        names = [s["name"] for s in skills]
        self.assertIn("prompting", names)
        for s in skills:
            self.assertTrue(s["summary"] or s["when_to_use"], s["name"])
            self.assertIn("skill_md", json.loads(skills_mcp.read_skill(s["name"])))

    def test_real_skills_are_prompts_of_the_server(self):
        from src import mcp_server
        prompts = {p.name for p in asyncio.run(mcp_server.mcp.list_prompts())}
        self.assertIn("prompting", prompts)
        self.assertEqual(len(prompts), mcp_server._N_SKILL_PROMPTS)


if __name__ == "__main__":
    unittest.main()
