"""Every tool the MCP server offers masks secrets in what it returns."""
import asyncio
import os
import tempfile
import unittest


class RedactedTools(unittest.TestCase):

    def test_a_token_in_a_tool_result_leaves_masked(self):
        from src import mcp_server as m
        secret = "hf_" + "R" * 34
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "notes.txt")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(f"token {secret}\n")
            out = asyncio.run(m.mcp.call_tool("read_text_file", {"path": p}))
        self.assertNotIn(secret, str(out))
        self.assertIn("hf_R", str(out))

    def test_wrapping_keeps_each_tools_parameters(self):
        from src import mcp_server as m
        tools = {t.name: t for t in asyncio.run(m.mcp.list_tools())}
        self.assertIn("path", tools["read_text_file"].inputSchema["properties"])


if __name__ == "__main__":
    unittest.main()
