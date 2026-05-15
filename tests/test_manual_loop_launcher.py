from __future__ import annotations

import builtins
from pathlib import Path

import pytest
import yaml

from dume import manual_loop_launcher as launcher


VALID_MAPPING = {
    "THUMBS_UP": "advance",
    "TWO_FINGERS": "repeat",
    "FIST": "quit",
    "PALM": "none",
    "ONE_FINGER": "none",
    "THREE_FINGERS": "none",
    "NONE": "none",
}


def test_default_config_contains_canonical_safe_wait_mode() -> None:
    data = yaml.safe_load(Path("configs/manual_loop.default.yaml").read_text())

    assert data["manual"]["wait_mode"] == "enter"
    assert "wait" not in data


def test_manual_wait_mode_loads_correctly(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {"manual": {"wait_mode": "gesture"}, "gesture": {"source": "fake"}},
    )

    loaded = launcher.load_config(tmp_path)

    assert loaded.config.manual.wait_mode == "gesture"
    assert loaded.config.manual.loop_mode == "gesture"


def test_old_wait_mode_alias_is_accepted(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {"wait": {"mode": "gesture"}, "gesture": {"source": "fake"}},
    )

    loaded = launcher.load_config(tmp_path)

    assert loaded.config.manual.wait_mode == "gesture"


def test_no_local_config_uses_safe_defaults(tmp_path: Path) -> None:
    loaded = launcher.load_config(tmp_path)

    assert loaded.config.manual.loop_mode == "enter"
    assert loaded.config.gesture.source == "webcam"
    assert not loaded.local_loaded


def test_local_config_overrides_default_config(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "configs" / "manual_loop.default.yaml",
        {"manual": {"input_dir": "data/manuals/raw", "wait_mode": "enter"}},
    )
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {"manual": {"input_dir": "data/manuals/raw2"}},
    )

    loaded = launcher.load_config(tmp_path)

    assert loaded.config.manual.input_dir == "data/manuals/raw2"


def test_cli_overrides_local_config(tmp_path: Path) -> None:
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {
            "manual": {"input_dir": "data/manuals/raw2", "wait_mode": "gesture"},
            "gesture": {"source": "webcam", "timeout_s": 1},
        },
    )

    loaded = launcher.load_config(
        tmp_path,
        {
            "manual": {"input_dir": "data/manuals/raw3", "wait_mode": "enter"},
            "gesture": {"source": "fake", "timeout_s": 5},
        },
    )

    assert loaded.config.manual.input_dir == "data/manuals/raw3"
    assert loaded.config.manual.loop_mode == "enter"
    assert loaded.config.gesture.source == "fake"
    assert loaded.config.gesture.timeout_s == 5


def test_explicit_config_is_loaded_by_config_option(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "my-local.yaml"
    _write_yaml(
        config_path,
        {"manual": {"wait_mode": "enter"}, "gesture": {"source": "fake"}},
    )

    result = launcher.main(["--project-root", str(tmp_path), "--config", str(config_path), "check"])

    output = capsys.readouterr().out
    assert result == 0
    assert f"explicit_config: {config_path}" in output


@pytest.mark.parametrize(
    "mapping",
    [
        VALID_MAPPING,
        {
            "thumbs_up": "advance",
            "two_fingers": "repeat",
            "fist": "quit",
            "palm": "none",
            "one_finger": "none",
            "three_fingers": "none",
            "none": "none",
        },
        {"PALM": "advance"},
        {"THUMBS_UP": "none"},
    ],
)
def test_valid_gesture_mappings_load(tmp_path: Path, mapping: dict[str, str]) -> None:
    _write_yaml(tmp_path / "configs" / "manual_loop.local.yaml", {"gesture": {"mapping": mapping}})

    loaded = launcher.load_config(tmp_path)

    assert loaded.config.gesture.mapping["PALM"] in {"advance", "none"}
    assert "NONE" in loaded.config.gesture.mapping


@pytest.mark.parametrize(
    ("mapping", "message"),
    [
        ({"FIST": "move_forward"}, "Invalid gesture mapping action"),
        ({"WAVE": "advance"}, "Invalid gesture mapping key"),
        ({"PALM": "stop_robot"}, "Invalid gesture mapping action"),
        ({"PALM": ""}, "must not be empty"),
        ({1: "advance"}, "keys must be strings"),
        ({"PALM": 1}, "actions must be strings"),
    ],
)
def test_invalid_gesture_mapping_fails_fast(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    mapping: dict[object, object],
    message: str,
) -> None:
    _write_yaml(tmp_path / "configs" / "manual_loop.local.yaml", {"gesture": {"mapping": mapping}})

    result = launcher.main(["--project-root", str(tmp_path), "check"])

    output = capsys.readouterr().out
    assert result == 1
    assert message in output


def test_none_mapping_is_removed_from_runtime_actions() -> None:
    mapping = launcher.runtime_action_mapping({"THUMBS_UP": "none", "PALM": "advance"})

    assert mapping == {"PALM": "advance"}


def test_missing_model_path_fails_in_gesture_mode(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {
            "manual": {"wait_mode": "gesture"},
            "gesture": {"source": "fake", "model_path": "missing.task"},
        },
    )

    result = launcher.main(["--project-root", str(tmp_path), "check"])

    output = capsys.readouterr().out
    assert result == 1
    assert "Gesture model path not found" in output


def test_missing_camera_fails_fast_unless_fallback_enabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    model_path = tmp_path / "model.task"
    model_path.write_bytes(b"model")
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {
            "manual": {"wait_mode": "gesture"},
            "gesture": {"source": "webcam", "model_path": str(model_path), "fallback": None},
        },
    )
    monkeypatch.setattr(
        launcher,
        "_verify_gesture_source",
        lambda config, project_root: "camera missing",
    )

    failed = launcher.main(["--project-root", str(tmp_path), "check"])
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {
            "manual": {"wait_mode": "gesture"},
            "gesture": {
                "source": "webcam",
                "model_path": str(model_path),
                "fallback": "enter",
            },
        },
    )
    passed_with_fallback = launcher.main(["--project-root", str(tmp_path), "check"])

    output = capsys.readouterr().out
    assert failed == 1
    assert passed_with_fallback == 0
    assert "Gesture source unavailable" in output
    assert "keyboard fallback is enabled" in output


def test_check_exits_successfully_for_keyboard_mode_without_camera(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fail_if_called(config: object, project_root: Path) -> str | None:
        raise AssertionError("keyboard mode must not verify camera sources")

    monkeypatch.setattr(launcher, "_verify_gesture_source", fail_if_called)

    result = launcher.main(["--project-root", str(tmp_path), "check"])

    output = capsys.readouterr().out
    assert result == 0
    assert "source: webcam" in output
    assert "timeout_s: 30" in output
    assert "fallback: none" in output
    assert "THUMBS_UP" in output
    assert "camera_check: skipped because wait_mode=enter" in output
    assert "robot_control_enabled: false" in output
    assert "lerobot_env_step: not used" in output


def test_gesture_mode_summary_includes_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    model_path = tmp_path / "model.task"
    model_path.write_bytes(b"model")
    _write_yaml(
        tmp_path / "configs" / "manual_loop.local.yaml",
        {
            "manual": {"wait_mode": "gesture"},
            "gesture": {"source": "fake", "model_path": str(model_path), "timeout_s": 7},
        },
    )
    monkeypatch.setattr(launcher, "_verify_gesture_source", lambda config, project_root: None)

    result = launcher.main(["--project-root", str(tmp_path), "check"])

    output = capsys.readouterr().out
    assert result == 0
    assert "enabled: true" in output
    assert "timeout_s: 7" in output


def test_default_run_does_not_start_camera_dependencies(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Path] = []

    def fail_if_called(config: object, project_root: Path) -> str | None:
        raise AssertionError("keyboard default must not verify camera sources")

    def fake_run_loop(input_dir: Path, **kwargs: object) -> int:
        calls.append(input_dir)
        assert kwargs["wait_mode"] == "enter"
        return 0

    monkeypatch.setattr(launcher, "_verify_gesture_source", fail_if_called)
    monkeypatch.setattr(launcher.loop_cli, "run_loop", fake_run_loop)

    result = launcher.main(["--project-root", str(tmp_path)])

    assert result == 0
    assert calls == [(tmp_path / "data" / "manuals" / "raw").resolve()]


def test_setup_writes_canonical_schema_and_timeout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    answers = iter(
        [
            "data/manuals/raw2",
            "gesture",
            "new-pieces",
            "fake",
            "model.task",
            "12",
            "enter",
            "default",
        ]
    )
    default_before = Path("configs/manual_loop.default.yaml").read_text(encoding="utf-8")
    monkeypatch.setattr(builtins, "input", lambda prompt: next(answers))

    result = launcher.main(["--project-root", str(tmp_path), "setup"])

    payload = yaml.safe_load((tmp_path / "configs" / "manual_loop.local.yaml").read_text())
    assert result == 0
    assert payload["manual"]["wait_mode"] == "gesture"
    assert "wait" not in payload
    assert payload["gesture"]["timeout_s"] == 12
    assert payload["gesture"]["mapping"] == VALID_MAPPING
    assert Path("configs/manual_loop.default.yaml").read_text(encoding="utf-8") == default_before


def _write_yaml(path: Path, payload: dict[object, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
