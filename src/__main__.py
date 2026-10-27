"""Entry point so the agentY MCP server runs via ``python -m src``."""

from src import sync_deps

sync_deps.ensure()  # before the server imports its dependencies; stderr only

from src.mcp_server import main  # noqa: E402

if __name__ == "__main__":
    main()
