"""Bob assets (`.bob`) that travel to each workspace, with permissions scoped to that workspace.

Deterministic guarantees that do not depend on the model's judgment:

- Bob matches a mode's `fileRegex` against the file's ABSOLUTE PATH. In the repository, the modes that
  edit carry the `__WORK_ROOT__` marker: unsubstituted, it matches no path (fails closed). When the
  assets are installed it is replaced with the absolute root of THIS workspace, so Bob only writes inside it.
- Only read-only subagents travel: a mode that delegates cannot invoke one that edits or executes,
  even if an uploaded repository tries to talk it into it (prompt injection).
- Bob is launched without the application's secrets (`bob_adapter.bob_child_env`).
"""

import re
import shutil
from pathlib import Path

import yaml

from app.adapters.bob_adapter import CUSTOM_MODES_FILE

WORK_ROOT_TOKEN = "__WORK_ROOT__"
READ_ONLY_GROUPS = frozenset({"read", "skill", "todo"})
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)


def agent_groups(text: str) -> frozenset[str] | None:
    """Groups declared by an agent's frontmatter; None when they cannot be determined."""
    match = _FRONTMATTER.match(text)
    if not match:
        return None
    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    groups = data.get("groups") if isinstance(data, dict) else None
    if not isinstance(groups, list) or not groups:
        return None
    names: set[str] = set()
    for group in groups:
        if isinstance(group, str):
            names.add(group)
        elif isinstance(group, list) and group and isinstance(group[0], str):
            names.add(group[0])
        else:
            return None
    return frozenset(names)


def _is_read_only(agent: Path) -> bool:
    groups = agent_groups(agent.read_text(encoding="utf-8", errors="replace"))
    return groups is not None and groups <= READ_ONLY_GROUPS


def workspace_root_pattern(workspace: Path) -> str:
    """Workspace root as a regex: the path as given to Bob and its real path (symlinks)."""
    roots = sorted({str(workspace.absolute()), str(workspace.resolve())})
    return "(?:" + "|".join(re.escape(root) for root in roots) + ")"


def render_modes(text: str, workspace: Path) -> str:
    """Replaces the marker with the workspace root, escaped for a double-quoted YAML string."""
    return text.replace(WORK_ROOT_TOKEN, workspace_root_pattern(workspace).replace("\\", "\\\\"))


def install_bob_assets(workspace: Path, source: Path = CUSTOM_MODES_FILE.parent) -> None:
    """Copies the project's modes, skills and rules, and only the read-only subagents."""
    destination = workspace / ".bob"
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("agents"))
    agents = destination / "agents"
    agents.mkdir(exist_ok=True)
    for agent in sorted((source / "agents").glob("*.md")):
        if _is_read_only(agent):
            shutil.copy2(agent, agents / agent.name)
    modes = destination / CUSTOM_MODES_FILE.name
    if modes.is_file():
        modes.write_text(render_modes(modes.read_text(encoding="utf-8"), workspace), encoding="utf-8")
