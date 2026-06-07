#!/usr/bin/env python3
"""Check workflows from config/workflow_templates.json for missing custom nodes and install them.

Steps:
  1. Load the list of workflow templates from ./config/workflow_templates.json
  2. Extract all ``class_type`` values from the corresponding JSON template files under
     ./comfyui_workflow_templates_custom/templates/
  3. Identify which types belong to a custom-node package by looking them up in
     the ComfyUI-Manager extension-node-map.json (fetched from GitHub).
  4. Compare the required packages against the installed ones listed in
     config/custom_nodes.json.
  5. Install every missing package via the ComfyUI Manager REST API.
  6. Restart the ComfyUI server (only when at least one package was installed).

Run once at startup via run_agent.ps1.  Exits silently if ComfyUI is offline
or the Manager extension is not installed.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TEMPLATES_DIR = PROJECT_ROOT / "comfyui_workflow_templates_custom" / "templates"
WORKFLOW_TEMPLATES_CONFIG = PROJECT_ROOT / "config" / "workflow_templates.json"
CUSTOM_NODES_CONFIG = PROJECT_ROOT / "config" / "custom_nodes.json"
EXTENSION_NODE_MAP_URL = (
    "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/extension-node-map.json"
)

# How long to wait (seconds) for ComfyUI to come back up after a restart
RESTART_WAIT_TIMEOUT = 120
RESTART_POLL_INTERVAL = 5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_comfyui_base_url() -> str:
    """Read the ComfyUI base URL from settings.json (same logic as the client)."""
    settings_path = PROJECT_ROOT / "config" / "settings.json"
    if settings_path.exists():
        with open(settings_path, encoding="utf-8") as f:
            raw = "".join(ln for ln in f if not ln.lstrip().startswith("//"))
        try:
            cfg = json.loads(raw)
            return cfg.get("comfyui_url", "http://127.0.0.1:8188").rstrip("/")
        except json.JSONDecodeError:
            pass
    return "http://127.0.0.1:8188"


def _comfyui_headers(base_url: str) -> dict:
    """Build auth headers for ComfyUI requests."""
    from src.utils.secrets import get_secret
    api_key = get_secret("COMFYUI_API_KEY")
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def extract_node_types_from_templates() -> set[str]:
    """Return all unique ``class_type`` values from workflows listed in config/workflow_templates.json."""
    types: set[str] = set()
    
    if not WORKFLOW_TEMPLATES_CONFIG.exists():
        print(f"[check_nodes] Workflow config not found: {WORKFLOW_TEMPLATES_CONFIG}")
        return types
    
    try:
        with open(WORKFLOW_TEMPLATES_CONFIG, encoding="utf-8") as f:
            workflow_ids = json.load(f)
    except Exception as exc:
        print(f"[check_nodes] WARNING: Could not parse {WORKFLOW_TEMPLATES_CONFIG}: {exc}")
        return types
    
    if not workflow_ids:
        print(f"[check_nodes] No workflows found in {WORKFLOW_TEMPLATES_CONFIG}")
        return types
    
    for workflow_id in workflow_ids.keys():
        template_file = TEMPLATES_DIR / f"{workflow_id}.json"
        if not template_file.exists():
            print(f"[check_nodes] WARNING: Workflow template not found: {template_file.name}")
            continue
        
        try:
            with open(template_file, encoding="utf-8") as f:
                workflow = json.load(f)
        except Exception as exc:
            print(f"[check_nodes] WARNING: Could not parse {template_file.name}: {exc}")
            continue

        nodes = workflow.values() if isinstance(workflow, dict) else workflow
        for node in nodes:
            if isinstance(node, dict):
                ct = node.get("class_type")
                if ct:
                    types.add(ct)

    return types


def load_installed_custom_nodes() -> set[str]:
    """Return the set of installed custom-node folder names from config/custom_nodes.json."""
    if not CUSTOM_NODES_CONFIG.exists():
        return set()
    with open(CUSTOM_NODES_CONFIG, encoding="utf-8") as f:
        data = json.load(f)
    return set(data.get("custom_nodes", []))


def fetch_extension_node_map() -> dict:
    """Download the ComfyUI-Manager extension-node-map.json from GitHub.

    Returns a dict mapping git-URL → [list-of-node-types, metadata-dict].
    Returns an empty dict on failure.
    """
    try:
        resp = requests.get(EXTENSION_NODE_MAP_URL, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        print(f"[check_nodes] WARNING: Could not fetch extension-node-map: {exc}")
        return {}


# ComfyUI core repo – never a custom node
_CORE_REPO_SUBSTRINGS = {"comfyanonymous/comfyui"}


def _is_core_repo(url: str) -> bool:
    return any(s in url.lower() for s in _CORE_REPO_SUBSTRINGS)


def build_nodetype_to_repos(extension_map: dict) -> dict[str, set[str]]:
    """Invert the extension-node-map to get node-type → set of git-URLs.

    Unlike a single-url mapping, keeping *all* providers lets us correctly
    recognise a type as satisfied when any one of its providers is installed.
    """
    mapping: dict[str, set[str]] = {}
    for url, payload in extension_map.items():
        if _is_core_repo(url):
            continue
        if not isinstance(payload, list) or len(payload) < 1:
            continue
        node_types = payload[0]
        if not isinstance(node_types, list):
            continue
        for nt in node_types:
            if isinstance(nt, str):
                mapping.setdefault(nt, set()).add(url)
    return mapping


def repo_url_to_folder_name(url: str) -> str:
    """Best-effort: derive the expected custom-node folder name from a GitHub URL.

    E.g. ``https://github.com/ltdrdata/ComfyUI-Manager``  →  ``ComfyUI-Manager``
    """
    return url.rstrip("/").split("/")[-1]


def find_missing_packages(
    node_types: set[str],
    installed: set[str],
    nodetype_to_repos: dict[str, set[str]],
) -> dict[str, str]:
    """Return {git_url: folder_name} for packages that need to be installed.

    A node type is considered satisfied when *any* repo that provides it has a
    folder name appearing (case-insensitively) in the installed set.  This
    prevents false positives caused by multiple forks registering the same types.
    """
    installed_lower = {name.lower() for name in installed}

    missing: dict[str, str] = {}  # git_url -> folder_name
    for nt in node_types:
        repos = nodetype_to_repos.get(nt)
        if not repos:
            continue  # built-in ComfyUI node or unknown – skip

        # Satisfied if any provider is already installed
        if any(repo_url_to_folder_name(url).lower() in installed_lower for url in repos):
            continue

        # None installed – queue the first (alphabetically) as the canonical one
        for url in sorted(repos):
            if url not in missing:
                missing[url] = repo_url_to_folder_name(url)
                break

    return missing


def install_package(base_url: str, headers: dict, git_url: str) -> bool:
    """Ask ComfyUI Manager to install a package by its git URL.

    Uses POST /customnode/install/git_url with the URL as a plain-text body,
    as defined in the Manager OpenAPI spec.

    Returns True on success, False otherwise.
    """
    endpoint = f"{base_url}/customnode/install/git_url"
    install_headers = {**headers, "Content-Type": "text/plain"}
    try:
        resp = requests.post(endpoint, headers=install_headers, data=git_url, timeout=300)
        if resp.status_code == 200:
            return True
        print(f"[check_nodes]   Install returned HTTP {resp.status_code}: {resp.text[:200]}")
        return False
    except Exception as exc:
        print(f"[check_nodes]   Install request failed: {exc}")
        return False


def restart_comfyui(base_url: str, headers: dict) -> None:
    """POST /manager/reboot and wait for ComfyUI to come back online."""
    print("[check_nodes] Restarting ComfyUI server...")
    try:
        requests.post(f"{base_url}/manager/reboot", headers=headers, timeout=10)
    except Exception:
        pass  # Connection drop is expected during restart

    print(f"[check_nodes] Waiting for ComfyUI to restart (up to {RESTART_WAIT_TIMEOUT}s)...")
    elapsed = 0
    while elapsed < RESTART_WAIT_TIMEOUT:
        time.sleep(RESTART_POLL_INTERVAL)
        elapsed += RESTART_POLL_INTERVAL
        try:
            resp = requests.get(f"{base_url}/system_stats", headers=headers, timeout=5)
            if resp.status_code == 200:
                print(f"[check_nodes] ComfyUI is back online after {elapsed}s.")
                return
        except Exception:
            pass
        print(f"[check_nodes]   Still waiting... ({elapsed}s elapsed)")

    print("[check_nodes] WARNING: ComfyUI did not respond within the timeout after restart.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("[check_nodes] Checking workflow templates for missing custom nodes...")

    # 1. Extract all node types used in templates
    node_types = extract_node_types_from_templates()
    if not node_types:
        print("[check_nodes] No node types found in templates – nothing to check.")
        return
    print(f"[check_nodes] Found {len(node_types)} unique node types across all templates.")

    # 2. Load installed custom nodes
    installed = load_installed_custom_nodes()
    if not installed:
        print("[check_nodes] WARNING: config/custom_nodes.json is empty or missing – "
              "run refresh_models.py first to populate it if ComfyUI is already online.")

    # 3. Fetch extension-node-map
    extension_map = fetch_extension_node_map()
    if not extension_map:
        print("[check_nodes] Cannot proceed without the extension-node-map – skipping.")
        return
    print(f"[check_nodes] Extension-node-map loaded ({len(extension_map)} packages).")

    nodetype_to_repos = build_nodetype_to_repos(extension_map)

    # 4. Determine missing packages
    missing = find_missing_packages(node_types, installed, nodetype_to_repos)
    if not missing:
        print("[check_nodes] All required custom nodes are installed.")
        return

    print(f"[check_nodes] {len(missing)} missing custom node package(s) detected:")
    for url, folder in sorted(missing.items(), key=lambda x: x[1].lower()):
        print(f"  - {folder}  ({url})")

    # 5. Ensure ComfyUI + Manager are reachable
    base_url = _get_comfyui_base_url()
    try:
        headers = _comfyui_headers(base_url)
    except Exception as exc:
        print(f"[check_nodes] Could not build auth headers: {exc}")
        headers = {"Accept": "application/json"}

    # Quick connectivity check
    try:
        resp = requests.get(f"{base_url}/system_stats", headers=headers, timeout=10)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[check_nodes] ComfyUI is offline or unreachable ({exc}) – skipping install.")
        return

    # 6. Install missing packages
    installed_count = 0
    for git_url, folder in sorted(missing.items(), key=lambda x: x[1].lower()):
        print(f"[check_nodes] Installing {folder} ...")
        ok = install_package(base_url, headers, git_url)
        if ok:
            print(f"[check_nodes]   ✓ {folder} installed successfully.")
            installed_count += 1
        else:
            print(f"[check_nodes]   ✗ Failed to install {folder}.")

    if installed_count == 0:
        print("[check_nodes] No packages were installed – skipping restart.")
        return

    # 7. Restart ComfyUI
    print(f"[check_nodes] {installed_count} package(s) installed. Restarting ComfyUI...")
    restart_comfyui(base_url, headers)


if __name__ == "__main__":
    main()
