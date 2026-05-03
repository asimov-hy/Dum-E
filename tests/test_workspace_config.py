from pathlib import Path

from dume.config import (
    WorkspaceConfig,
    default_workspace_config,
    load_workspace_config,
    save_workspace_config,
)
from dume.control.session import ControlSession


def test_default_workspace_config_shape() -> None:
    workspace = default_workspace_config()

    assert len(workspace.bin_positions) == 3
    assert workspace.loadout_area.capacity == 2
    assert workspace.safety_margin_m == 0.05


def test_session_load_creates_workspace_config(tmp_path: Path) -> None:
    session = ControlSession.load(tmp_path)

    assert session.paths.workspace_config.exists()
    assert len(session.workspace.bin_positions) == 3
    assert session.status_summary()["bin_position_count"] == 3
    assert session.status_summary()["loadout_capacity"] == 2


def test_workspace_config_save_and_reload(tmp_path: Path) -> None:
    path = tmp_path / "workspace.yaml"
    workspace = WorkspaceConfig(camera_serial="test-camera")

    save_workspace_config(path, workspace)
    loaded = load_workspace_config(path)

    assert loaded.camera_serial == "test-camera"
