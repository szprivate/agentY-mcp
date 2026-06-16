"""
HTTP client wrapper for communicating with the ComfyUI server.

Provides a singleton client that handles authentication and base URL configuration.
The ComfyUI API key is read directly from the .env file.
"""

import json
import os
from pathlib import Path

import requests

from src.utils.secrets import get_secret


_DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"


def parse_argv_dir_flag(argv: list, flag: str) -> str | None:
    """Extract a directory value passed to ComfyUI as ``--flag=VALUE`` or ``--flag VALUE``.

    ``/system_stats`` echoes the server's ``sys.argv`` verbatim, so a
    space-separated flag arrives as two consecutive list elements
    (``["--input-directory", "W:\\..."]``) while the ``=`` form arrives as a
    single element (``["--input-directory=W:\\..."]``).  Earlier code only
    handled the ``=`` form, so space-separated launch flags were silently
    missed and callers fell back to ComfyUI's stock install defaults.  Handle
    both forms; return ``None`` when the flag is absent.
    """
    for i, arg in enumerate(argv):
        if not isinstance(arg, str):
            continue
        if arg.startswith(flag + "="):
            return arg.split("=", 1)[1]
        if arg == flag and i + 1 < len(argv) and isinstance(argv[i + 1], str):
            return argv[i + 1]
    return None


class ComfyUIClient:
    """HTTP client for the ComfyUI REST API."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = (base_url or self._load_base_url()).rstrip("/")
        self.api_key = api_key or get_secret("COMFYUI_API_KEY")

    @staticmethod
    def _load_base_url() -> str:
        # An MCP host / .mcpb bundle can inject the ComfyUI URL via env.
        env_url = os.environ.get("COMFYUI_URL")
        if env_url:
            return env_url
        config_path = Path(__file__).parent.parent / "config" / "settings.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.loads("".join(ln for ln in f if not ln.lstrip().startswith("//")))
            return config.get("comfyui_url", _DEFAULT_COMFYUI_URL)
        return _DEFAULT_COMFYUI_URL

    def _headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get(
        self,
        path: str,
        params: dict | None = None,
        stream: bool = False,
        raw: bool = False,
    ) -> requests.Response | dict | list | str:
        """Send a GET request. Returns parsed JSON unless raw=True."""
        url = f"{self.base_url}{path}"
        resp = requests.get(
            url, headers=self._headers(), params=params, stream=stream, timeout=120
        )
        resp.raise_for_status()
        if raw or stream:
            return resp
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def post(
        self,
        path: str,
        json_data: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> dict | str:
        """Send a POST request. Returns parsed JSON when possible."""
        url = f"{self.base_url}{path}"
        headers = self._headers()
        if files:
            # Let requests set content-type with boundary for multipart
            headers.pop("Accept", None)
        resp = requests.post(
            url, headers=headers, json=json_data, data=data, files=files, timeout=120
        )
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def delete(self, path: str) -> dict | str:
        """Send a DELETE request."""
        url = f"{self.base_url}{path}"
        resp = requests.delete(url, headers=self._headers(), timeout=120)
        resp.raise_for_status()
        try:
            return resp.json()
        except ValueError:
            return resp.text


# ── Singleton ──────────────────────────────────────────────────────────────────

_client: ComfyUIClient | None = None


def get_client() -> ComfyUIClient:
    """Return (and lazily create) the singleton ComfyUI client."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = ComfyUIClient()
    return _client
