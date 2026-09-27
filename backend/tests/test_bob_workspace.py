"""Isolation of each Bob session: which agents travel to the workspace, where it can write and with which environment.

Bob matches a mode's `fileRegex` against the file's ABSOLUTE PATH (verified with Bob Shell 2.0.5), so
the restriction is anchored here to the root of each workspace. Spends no bobcoins.
"""

import re
import sys
from pathlib import Path

import pytest
import yaml

from app.adapters.bob_adapter import CUSTOM_MODES_FILE, BobAdapter, BobRunSettings, bob_child_env
from app.adapters.bob_workspace import WORK_ROOT_TOKEN, agent_groups, install_bob_assets
from app.modernization.implement import prepare_work
from app.pipeline.evidence_audit import prepare_workspace

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = REPO_ROOT / "samples" / "facturaya-v1"


def _mode(workspace: Path, slug: str) -> dict:
    modes = yaml.safe_load((workspace / ".bob" / "custom_modes.yaml").read_text(encoding="utf-8"))["customModes"]
    return next(mode for mode in modes if mode["slug"] == slug)


def _edit_regex(mode: dict) -> re.Pattern[str]:
    edit = next(group for group in mode["groups"] if isinstance(group, list) and group[0] == "edit")
    return re.compile(edit[1]["fileRegex"])


# --- Subagentes -------------------------------------------------------------------------------

def test_only_read_only_agents_reach_a_workspace(tmp_path: Path) -> None:
    workspace = prepare_workspace(SAMPLE, tmp_path / "job")
    agents = {path.stem for path in (workspace / ".bob" / "agents").glob("*.md")}
    assert {"legacy-sql-auditor", "legacy-route-mapper", "legacy-security-scanner", "legacy-dependency-tracer"} <= agents
    for name in agents:
        groups = agent_groups((workspace / ".bob" / "agents" / f"{name}.md").read_text(encoding="utf-8"))
        assert groups is not None and groups <= {"read", "skill", "todo"}, name
    assert not {"strangler-surgeon", "contract-keeper", "legacy-test-writer", "git-archaeologist"} & agents, \
        "an uploaded repository must not be able to delegate to agents that edit or execute"


@pytest.mark.parametrize(("frontmatter", "expected"), [
    ("---\nname: a\ngroups:\n  - read\n---\n", frozenset({"read"})),
    ("---\nname: a\ngroups: [read, [edit, {fileRegex: x}]]\n---\n", frozenset({"read", "edit"})),
    ("---\nname: a\n---\n", None),  # no declared groups: unknown capabilities -> it does not travel
    ("no frontmatter", None),
])
def test_agent_groups_fail_closed(frontmatter: str, expected: frozenset[str] | None) -> None:
    assert agent_groups(frontmatter) == expected


# --- Writing anchored to the workspace -----------------------------------------------------------

def test_repository_modes_fail_closed_until_rendered() -> None:
    text = CUSTOM_MODES_FILE.read_text(encoding="utf-8")
    assert WORK_ROOT_TOKEN in text
    modes = yaml.safe_load(text)["customModes"]
    for mode in modes:
        for group in mode["groups"]:
            if isinstance(group, list) and group[0] == "edit":
                pattern = re.compile(group[1]["fileRegex"])
                for path in ("/etc/passwd", "/app/backend/app/main.py", "/app/artifacts/jobs/x/dossier.json", "app.py"):
                    assert not pattern.search(path), f"{mode['slug']} allows {path} without an anchor"


def test_surgeon_can_only_write_inside_its_own_copy(tmp_path: Path) -> None:
    work = tmp_path / "jobs" / "abc123" / "modernization" / "work"
    prepare_work(SAMPLE, work)
    pattern = _edit_regex(_mode(work, "modernization-surgeon"))
    root = str(work.resolve())
    assert pattern.search(f"{root}/app.py") and pattern.search(f"{root}/src/api/main.ts")
    for outside in (
        f"{root}/.bob/custom_modes.yaml",          # its own permissions
        f"{root}/.git/config",
        f"{root}-evil/app.py",                      # prefijo compartido
        f"{root}/../dossier.json",                  # unnormalized path that leaves the copy
        f"{root}/src/../../../../etc/passwd",
        str(tmp_path / "jobs" / "abc123" / "dossier.json"),  # dossier of the same analysis
        str(tmp_path / "jobs" / "other" / "source" / "app.py"),  # another analysis
        str(REPO_ROOT / "backend" / "app" / "main.py"),         # the application itself
        str(REPO_ROOT / "frontend" / "dist" / "index.html"),
        "/etc/passwd",
    ):
        assert not pattern.search(outside), outside


@pytest.mark.skipif(sys.platform == "win32", reason="Creating symlinks needs admin rights on Windows; runs in Linux CI.")
def test_rendered_regex_accepts_the_path_bob_is_given_and_its_real_path(tmp_path: Path) -> None:
    real = tmp_path / "real"
    (real / "src").mkdir(parents=True)
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)
    install_bob_assets(alias)
    pattern = _edit_regex(_mode(alias, "modernization-surgeon"))
    assert pattern.search(f"{alias.absolute()}/src/app.py")
    assert pattern.search(f"{real.resolve()}/src/app.py")


# --- Bob environment ---------------------------------------------------------------------------

def test_bob_never_receives_the_app_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOB_API_KEY", "bob-key")
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", "app-token")
    monkeypatch.setenv("IBM_CLOUD_API_KEY", "other-key")
    monkeypatch.setenv("DATABASE_PASSWORD", "x")
    monkeypatch.setenv("GITHUB_TOKEN", "y")
    env = bob_child_env()
    assert env["BOB_API_KEY"] == "bob-key", "Bob needs its own key"
    assert "PATH" in env
    for secret in ("LIVE_AUDIT_TOKEN", "IBM_CLOUD_API_KEY", "DATABASE_PASSWORD", "GITHUB_TOKEN"):
        assert secret not in env, secret


FAKE_BOB = r'''#!{python}
import json, os, sys
# Emits before reading stdin: with the prompt written from the main thread this used to block.
for index in range(2000):
    print(json.dumps({{"type": "message", "role": "assistant", "content": "x" * 60}}), flush=True)
prompt = sys.stdin.read()
secret = os.environ.get("LIVE_AUDIT_TOKEN")
print(json.dumps({{"type": "message", "role": "assistant", "content": f"len={{len(prompt)}} secret={{secret}}"}}), flush=True)
print(json.dumps({{"type": "result", "status": "success", "stats": {{"task_id": "t1", "duration_ms": 5, "session_costs": 0.01, "tool_calls": 0}}}}), flush=True)
'''


@pytest.mark.skipif(sys.platform == "win32", reason="The fake `bob` is a POSIX script Windows cannot execute; runs in Linux CI.")
def test_run_stream_feeds_large_prompts_without_blocking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "bob"
    fake.write_text(FAKE_BOB.format(python=sys.executable), encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.setenv("BOB_API_KEY", "test-key")
    monkeypatch.setenv("LIVE_AUDIT_TOKEN", "app-token")
    monkeypatch.setenv("BOB_LOG_DIR", str(tmp_path / "logs"))
    workspace = tmp_path / "ws"
    workspace.mkdir()
    adapter = BobAdapter(workspace, BobRunSettings(bob_binary=str(fake), timeout_s=20))
    prompt = "p" * 400_000  # several times a pipe's buffer
    result = adapter.run_stream("evidence-auditor", prompt, lambda _event: None)
    assert f"len={len(prompt)}" in result.last_message
    assert "secret=None" in result.last_message
