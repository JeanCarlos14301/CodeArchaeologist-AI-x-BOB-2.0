"""Validates `.bob/` with the same rules Bob Shell 2.x applies when it loads it.

Bob silently drops a subagent with `model:` or malformed frontmatter, and
regenerates `.bob/skills/<name>` from `.bob/commands/*.md` (overwriting skills
with the same name). These tests keep that from happening again without anyone noticing.
"""

import re
from pathlib import Path

import pytest
import yaml

from app.adapters.bob_adapter import REPO_ROOT

BOB_DIR = REPO_ROOT / ".bob"
VALID_GROUPS = {"read", "edit", "execute", "browser", "mcp", "skill", "todo", "subagent", "mode"}
SUBAGENT_KEYS = {"name", "description", "groups", "modelTier", "maxTurns", "rawPrompt",
                 "allowForkContext", "allowTools", "denyTools"}
MODEL_TIERS = {"fast", "premium", "ultra", "explorer"}
SKILL_NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Subagents that read untrusted code: never with a shell (AGENTS.md).
READ_ONLY_AUDITORS = {"legacy-archaeologist", "legacy-sql-auditor", "legacy-route-mapper",
                      "legacy-security-scanner", "legacy-dependency-tracer", "legacy-db-inspector"}
_FRONTMATTER = re.compile(r"^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$")


def _parse_like_bob(frontmatter: str) -> dict[str, object]:
    """Replica of the line-by-line parser Bob uses for `.bob/agents/*.md`."""
    data: dict[str, object] = {}
    key = ""
    for line in frontmatter.split("\n"):
        item = re.match(r"^\s+-\s+(.+)", line)
        if item and key:
            current = data.get(key)
            data[key] = [*current, item[1].strip()] if isinstance(current, list) else [item[1].strip()]
            continue
        pair = re.match(r"^(\w+):\s*(.*)", line)
        if not pair:
            continue
        key, value = pair[1], pair[2].strip()
        if value:
            data[key] = value
    return data


AGENT_FILES = sorted((BOB_DIR / "agents").glob("*.md"))
SKILL_FILES = sorted((BOB_DIR / "skills").glob("*/SKILL.md"))


def test_bob_assets_exist() -> None:
    assert len(AGENT_FILES) >= 16
    assert len(SKILL_FILES) >= 13


def test_no_commands_dir_that_bob_would_regenerate_into_skills() -> None:
    assert not (BOB_DIR / "commands").exists()


@pytest.mark.parametrize("path", AGENT_FILES, ids=lambda p: p.stem)
def test_subagent_frontmatter_is_loadable_by_bob(path: Path) -> None:
    match = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match, "the --- frontmatter block is missing"
    data = _parse_like_bob(match[1])
    assert "model" not in data, "Bob rejects 'model'; use 'modelTier'"
    assert set(data) <= SUBAGENT_KEYS, f"claves no soportadas: {set(data) - SUBAGENT_KEYS}"
    assert data.get("name") == path.stem
    description = data.get("description")
    assert isinstance(description, str) and len(description) > 20 and description not in {">", "|"}
    groups = data.get("groups")
    assert isinstance(groups, list) and set(groups) <= VALID_GROUPS
    assert "subagent" not in groups, "a subagent cannot launch subagents"
    if "modelTier" in data:
        assert data["modelTier"] in MODEL_TIERS
    if path.stem in READ_ONLY_AUDITORS:
        assert set(groups) == {"read"}, "auditors must not execute or edit"
    assert match[2].strip(), "the body (system prompt) is empty"


@pytest.mark.parametrize("path", SKILL_FILES, ids=lambda p: p.parent.name)
def test_skill_is_loadable_by_bob(path: Path) -> None:
    match = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
    assert match
    data = yaml.safe_load(match[1])
    folder = path.parent.name
    assert SKILL_NAME.match(folder) and len(folder) <= 64
    assert data.get("name") == folder
    assert isinstance(data.get("description"), str) and data["description"].strip()


def test_custom_modes_use_valid_groups_and_known_references() -> None:
    modes = yaml.safe_load((BOB_DIR / "custom_modes.yaml").read_text(encoding="utf-8"))["customModes"]
    agent_names = {p.stem for p in AGENT_FILES}
    skill_names = {p.parent.name for p in SKILL_FILES}
    for mode in modes:
        for group in mode["groups"]:
            name = group[0] if isinstance(group, list) else group
            assert name in VALID_GROUPS, f"{mode['slug']}: invalid group {name!r}"
            if isinstance(group, list):
                re.compile(group[1]["fileRegex"])
        text = mode.get("customInstructions", "")
        for ref in re.findall(r"\.bob/agents/([\w-]+)\.md", text):
            assert ref in agent_names, f"{mode['slug']}: agente inexistente {ref}"
        for ref in re.findall(r"\.bob/skills/([\w-]+)/SKILL\.md", text):
            assert ref in skill_names, f"{mode['slug']}: skill inexistente {ref}"


def test_edit_modes_are_path_restricted() -> None:
    modes = yaml.safe_load((BOB_DIR / "custom_modes.yaml").read_text(encoding="utf-8"))["customModes"]
    for mode in modes:
        assert "edit" not in mode["groups"], f"{mode['slug']}: 'edit' without fileRegex"
