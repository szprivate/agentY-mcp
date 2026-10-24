"""The agentY skills, offered over MCP.

Claude Code loads ``skills/`` from the plugin by itself. Other MCP clients (Claude
Desktop, Cursor, ...) have no skill mechanism, so the server hands them out:

* ``list_skills()``  - every skill: name, description, when to use it
* ``read_skill(name)`` - the full SKILL.md plus the names of its extra files
  (``read_skill(name, file="references/x.md")`` reads one of those)
* every skill also as an MCP *prompt* (clients that show prompts list them)

``skills/`` is a mirror of agentY's skills, kept by agentY's
``scripts/sync_plugin_skills.py``; nothing here is edited by hand.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"
_SKIP = {"__pycache__"}


def _frontmatter(text: str) -> tuple[dict, str]:
    """(fields, body). Handles ``key: value`` lines, quoted values and a folded ``>`` value."""
    m = re.match(r"---\s*\r?\n(.*?)\r?\n---\s*\r?\n?", text, re.S)
    if not m:
        return {}, text
    fields: dict = {}
    key = None
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            val = kv.group(2).strip()
            fields[key] = "" if val in (">", "|", ">-", "|-") else val.strip("\"'")
        elif key and line.strip():
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, text[m.end():]


def _split_when(description: str) -> tuple[str, str]:
    """agentY descriptions say what a skill does, then 'Activate/Use when ...'. Split there."""
    m = re.search(r"\b(Activate (?:when|in|whenever|during)|Use (?:for|when|ONLY when)|Invoke when)\b", description)
    if not m or m.start() == 0:
        return description.strip(), ""
    return description[:m.start()].strip(" .-"), description[m.start():].strip()


def _skill_dirs(root: Path) -> list:
    root = Path(root)
    if not root.is_dir():
        return []
    return sorted(d for d in root.iterdir() if d.is_dir() and d.name not in _SKIP and (d / "SKILL.md").is_file())


def load_skills(root: Path | None = None) -> list:
    out = []
    for d in _skill_dirs(root or SKILLS_DIR):
        fields, _ = _frontmatter((d / "SKILL.md").read_text(encoding="utf-8-sig"))
        desc = fields.get("description", "")
        what, when = _split_when(desc)
        out.append({
            "name": d.name,
            "description": desc,
            "summary": what,
            "when_to_use": when or desc,
            "allowed_tools": [t for t in re.split(r"[,\s]+", fields.get("allowed-tools", "")) if t],
        })
    return out


def _extra_files(folder: Path) -> list:
    return sorted(p.relative_to(folder).as_posix() for p in folder.rglob("*")
                  if p.is_file() and p.name != "SKILL.md" and not (_SKIP & set(p.relative_to(folder).parts))
                  and p.suffix != ".pyc")


def list_skills() -> str:
    """List the agentY skills (procedures and know-how). Check this BEFORE a task: when a skill matches
    (template assembly, prompting a model family, partner nodes, upscaling, Atlas/3D, DCC, Deadline,
    storyboards ...) read it with read_skill and follow it.

    Returns JSON: [{"name", "summary", "when_to_use", "allowed_tools"}, ...].
    """
    skills = [{k: s[k] for k in ("name", "summary", "when_to_use", "allowed_tools")} for s in load_skills()]
    return json.dumps(skills, indent=1, ensure_ascii=False)


def read_skill(name: str, file: str = "") -> str:
    """Read one agentY skill: its full SKILL.md and the names of its extra files (references, scripts).

    Args:
        name: the skill name from list_skills.
        file: optional - an extra file of that skill (e.g. "references/flux.md") to read instead of SKILL.md.
    """
    return _read_skill(name, file, SKILLS_DIR)


def _read_skill(name: str, file: str, root: Path) -> str:
    known = {d.name: d for d in _skill_dirs(root)}
    if name not in known:
        return json.dumps({"error": f"no skill named '{name}'", "available": sorted(known)})
    folder = known[name]
    extras = _extra_files(folder)
    if file:
        target = (folder / file).resolve()
        if folder.resolve() not in target.parents or not target.is_file():
            return json.dumps({"error": f"'{file}' is not a file of skill '{name}'", "files": extras})
        return target.read_text(encoding="utf-8-sig")
    text = (folder / "SKILL.md").read_text(encoding="utf-8-sig")
    return json.dumps({"name": name, "skill_md": text, "files": extras,
                       "note": "Read an extra file with read_skill(name, file=<one of files>)."}, ensure_ascii=False)


def _prompt_fn(folder: Path):
    def skill_text() -> str:
        return (folder / "SKILL.md").read_text(encoding="utf-8-sig")
    return skill_text


def register_prompts(mcp, root: Path | None = None) -> int:
    """Expose every skill as an MCP prompt (name = skill name, text = its SKILL.md)."""
    from mcp.server.fastmcp.prompts import Prompt

    count = 0
    for s in load_skills(root):
        folder = Path(root or SKILLS_DIR) / s["name"]

        mcp.add_prompt(Prompt.from_function(_prompt_fn(folder), name=s["name"], description=(s["description"] or s["name"])[:1000]))
        count += 1
    return count
