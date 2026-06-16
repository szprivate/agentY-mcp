"""Workflow-template registry tools — register / unregister custom templates.

In-process equivalents of ``scripts/add_workflow.ps1`` and
``scripts/remove_workflow.ps1``. They parse a ComfyUI workflow JSON into the
custom-templates ``index.json``, keep ``config/workflow_templates.json`` (the
``{name: description}`` catalog surfaced by ``get_workflow_catalog``) in sync,
and — on removal — delete the matching ``skills/<kebab>`` directory. No
PowerShell or subprocess is involved.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from src.tools._compat import tool
from src.utils.workflow_parser import (
    _custom_index_path,
    _project_root,
    parse_workflow,
    workflow_remove,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def _catalog_path() -> Path:
    """Path to config/workflow_templates.json (the {name: description} catalog)."""
    return _project_root() / "config" / "workflow_templates.json"


def _name_in_index(name: str, index_path: Path) -> bool:
    """Return True if a template called *name* already exists in *index_path*."""
    if not index_path.exists():
        return False
    try:
        raw = index_path.read_text(encoding="utf-8").strip()
        index = json.loads(raw) if raw else []
    except Exception:
        return False
    for group in index or []:
        for tpl in group.get("templates", []):
            if tpl.get("name") == name:
                return True
    return False


def _load_catalog(path: Path) -> dict:
    if path.exists():
        raw = path.read_text(encoding="utf-8").strip()
        return json.loads(raw) if raw else {}
    return {}


def _write_catalog(path: Path, obj: dict) -> None:
    """Write the catalog preserving its on-disk style: 4-space indent, literal
    unicode (ensure_ascii=False), UTF-8 (no BOM), trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")


# ── Tools ────────────────────────────────────────────────────────────────────

@tool
def register_workflow_template(workflow_file: str, index_path: str = "") -> str:
    """Register a custom ComfyUI workflow JSON as a reusable template.

    In-process equivalent of ``scripts/add_workflow.ps1``. It:
      1. Parses the workflow file and appends/updates its entry (name, models,
         io) in the custom-templates ``index.json``.
      2. Adds the template name — the workflow file's stem — as a key in
         ``config/workflow_templates.json`` (the catalog) with an empty
         description, so it appears in ``get_workflow_catalog()``.

    The template name is always the file stem (e.g. ``my_flow`` for
    ``my_flow.json``). Registering a name that already exists is refused, exactly
    like the script. The workflow JSON file itself is **not** copied — place it in
    the custom-templates directory so ``get_workflow_template`` can load it later.

    Args:
        workflow_file: Path to the ComfyUI workflow ``.json`` (API or graph
            format). Relative paths resolve against the repository root.
        index_path: Optional override for the ``index.json`` path. Empty (default)
            uses the configured custom-templates index.

    Returns:
        JSON summary with the parsed entry, the index path written, and whether
        the catalog was updated — or ``{"error": ...}``.
    """
    try:
        root = _project_root()
        p = Path(workflow_file)
        if not p.is_absolute():
            p = root / workflow_file
        if not p.exists():
            return json.dumps({"error": f"Workflow file not found: {workflow_file}"})

        name = p.stem
        idx = Path(index_path) if index_path else _custom_index_path()

        # Pre-check: refuse duplicates (mirrors workflow_parser._main / the script).
        if _name_in_index(name, idx):
            return json.dumps({"error": f"Template '{name}' already exists in {idx}"})

        try:
            with open(p, encoding="utf-8") as f:
                workflow = json.load(f)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid workflow JSON: {e}"})

        entry = parse_workflow(
            workflow,
            name=name,
            update_index=True,
            index_path=index_path or None,
        )

        # Keep config/workflow_templates.json in sync.
        catalog_path = _catalog_path()
        catalog = _load_catalog(catalog_path)
        catalog_updated = False
        if name not in catalog:
            catalog[name] = ""
            _write_catalog(catalog_path, catalog)
            catalog_updated = True

        return json.dumps(
            {
                "registered": name,
                "index_path": str(idx),
                "entry": entry,
                "catalog_updated": catalog_updated,
                "catalog_path": str(catalog_path),
                "message": (
                    f"Registered '{name}'. "
                    + (
                        "Added to catalog with an empty description — set a description in "
                        "config/workflow_templates.json so get_workflow_catalog() describes it."
                        if catalog_updated
                        else "Catalog entry already existed."
                    )
                ),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def unregister_workflow_template(name: str, index_path: str = "") -> str:
    """Unregister a custom workflow template by name.

    In-process equivalent of ``scripts/remove_workflow.ps1``. It:
      1. Removes every template named *name* from the custom-templates
         ``index.json`` (dropping a group that becomes empty).
      2. Removes the *name* key from ``config/workflow_templates.json``.
      3. Deletes the matching skill directory ``skills/<kebab>`` where ``<kebab>``
         is *name* lowercased with underscores turned into hyphens.

    Args:
        name: The template name (file stem) to remove, e.g. ``my_flow``.
        index_path: Optional override for the ``index.json`` path. Empty (default)
            uses the configured custom-templates index.

    Returns:
        JSON summary of what was removed — or ``{"error": ...}``.
    """
    try:
        if not name:
            return json.dumps({"error": "Template name is required"})

        root = _project_root()
        idx_written = workflow_remove(name, index_path=index_path or None)

        # Remove the catalog key.
        catalog_path = _catalog_path()
        catalog = _load_catalog(catalog_path)
        catalog_updated = False
        if name in catalog:
            del catalog[name]
            _write_catalog(catalog_path, catalog)
            catalog_updated = True

        # Remove the skill directory (kebab-case derived from the name).
        kebab = name.lower().replace("_", "-")
        skill_dir = root / "skills" / kebab
        skill_removed = False
        if skill_dir.is_dir():
            shutil.rmtree(skill_dir)
            skill_removed = True

        return json.dumps(
            {
                "removed": name,
                "index_path": str(idx_written),
                "catalog_updated": catalog_updated,
                "catalog_path": str(catalog_path),
                "skill_dir": str(skill_dir),
                "skill_dir_removed": skill_removed,
                "message": (
                    f"Unregistered '{name}'. Index updated; "
                    f"catalog {'updated' if catalog_updated else 'unchanged'}; "
                    f"skill dir {'removed' if skill_removed else 'not found'}."
                ),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})
