"""The ayon tools are offered by the MCP server and come from the shared layer.

    python -m unittest tests.test_ayon_offered
"""
import unittest

from src import tools as T

NAMES = ("ayon_context", "ayon_load", "ayon_mark_publish", "ayon_publish", "ayon_open_tool")


class Offered(unittest.TestCase):
    def test_in_the_server_tool_list(self):
        from src import mcp_server
        for name in NAMES:
            self.assertIn(getattr(T, name), mcp_server._TOOLS, name)

    def test_they_are_the_shared_core_functions(self):
        from agenty_core.tools import ayon
        for name in NAMES:
            self.assertIs(getattr(T, name), getattr(ayon, name))


if __name__ == "__main__":
    unittest.main()
