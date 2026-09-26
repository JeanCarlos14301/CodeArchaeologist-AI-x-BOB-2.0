"""Activos de Bob (`.bob`) que viajan a cada workspace, con permisos acotados a ese workspace.

Garantías deterministas, sin depender del criterio del modelo:

- Bob compara el `fileRegex` de un modo con la RUTA ABSOLUTA del archivo. En el repositorio, los modos que
  editan llevan el marcador `__WORK_ROOT__`: sin sustituir no coincide con ninguna ruta (falla cerrado). Al
  instalar los activos se sustituye por la raíz absoluta de ESTE workspace, así Bob solo escribe dentro de él.
- Solo viajan los subagentes de solo lectura: un modo que delega no puede invocar a uno que edita o ejecuta
  aunque un repositorio subido intente convencerlo (inyección de instrucciones).
- Bob se lanza sin los secretos de la aplicación (`bob_adapter.bob_child_env`).
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
    """Grupos que declara el frontmatter de un agente; None si no se pueden determinar."""
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
    """Raíz del workspace como regex: la ruta tal como se le da a Bob y su ruta real (enlaces simbólicos)."""
    roots = sorted({str(workspace.absolute()), str(workspace.resolve())})
    return "(?:" + "|".join(re.escape(root) for root in roots) + ")"


def render_modes(text: str, workspace: Path) -> str:
    """Sustituye el marcador por la raíz del workspace, escapada para una cadena YAML entre comillas dobles."""
    return text.replace(WORK_ROOT_TOKEN, workspace_root_pattern(workspace).replace("\\", "\\\\"))


def install_bob_assets(workspace: Path, source: Path = CUSTOM_MODES_FILE.parent) -> None:
    """Copia modos, skills y reglas del proyecto, y solo los subagentes de solo lectura."""
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
