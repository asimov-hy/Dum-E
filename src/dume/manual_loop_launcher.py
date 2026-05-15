from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from scripts.manuals import run_manual_loop as loop_cli


VALID_MAPPING_ACTIONS = {"advance", "repeat", "quit", "none"}
GESTURE_ORDER = (
    "THUMBS_UP",
    "TWO_FINGERS",
    "FIST",
    "PALM",
    "ONE_FINGER",
    "THREE_FINGERS",
    "NONE",
)
GESTURE_NAME_ALIASES = {name: name for name in GESTURE_ORDER}
GESTURE_NAME_ALIASES.update({name.lower(): name for name in GESTURE_ORDER})
DEFAULT_MAPPING = {
    "THUMBS_UP": "advance",
    "TWO_FINGERS": "repeat",
    "FIST": "quit",
    "PALM": "none",
    "ONE_FINGER": "none",
    "THREE_FINGERS": "none",
    "NONE": "none",
}


class ManualReaderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input_dir: str = "data/manuals/raw"
    wait_mode: Literal["enter", "keyboard", "gesture"] = "enter"
    mode: Literal["new-pieces", "visible-blocks"] = "new-pieces"
    preview_dir: str | None = None
    open_preview: bool = False
    debug_components: bool = False
    open_image: bool = False
    stop_after: int | None = None
    repeat_on_fail: bool = False

    @model_validator(mode="after")
    def validate_stop_after(self) -> "ManualReaderConfig":
        if self.stop_after is not None and self.stop_after < 1:
            raise ValueError("manual.stop_after must be positive")
        return self

    @property
    def loop_mode(self) -> str:
        if self.wait_mode in {"keyboard", "enter"}:
            return "enter"
        return "gesture"

    @property
    def display_mode(self) -> str:
        if self.loop_mode == "enter":
            return "keyboard"
        return "gesture"


class GestureConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["fake", "webcam", "realsense", "video"] = "webcam"
    device: int | str | None = None
    video_path: str | None = None
    model_path: str = "data/mediapipe/models/gesture_recognizer.task"
    timeout_s: float | None = 30.0
    fallback: Literal["keyboard", "enter"] | None = None
    mapping: dict[Any, Any] = Field(default_factory=lambda: dict(DEFAULT_MAPPING))

    @model_validator(mode="after")
    def validate_gesture_config(self) -> "GestureConfig":
        if self.timeout_s is not None and self.timeout_s < 0:
            raise ValueError("gesture.timeout_s must not be negative")
        self.mapping = normalize_mapping(self.mapping)
        return self

    @property
    def fallback_loop_mode(self) -> str | None:
        if self.fallback is None:
            return None
        return "enter"


class ManualLoopConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manual: ManualReaderConfig = Field(default_factory=ManualReaderConfig)
    gesture: GestureConfig = Field(default_factory=GestureConfig)

    @model_validator(mode="before")
    @classmethod
    def migrate_wait_alias(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        payload = dict(data)
        wait = payload.pop("wait", None)
        if wait is not None:
            if not isinstance(wait, dict):
                raise ValueError("wait alias must be a mapping when provided")
            unsupported = set(wait) - {"mode"}
            if unsupported:
                names = ", ".join(sorted(unsupported))
                raise ValueError(f"Unsupported wait alias field(s): {names}")
            manual = dict(payload.get("manual") or {})
            if "mode" in wait:
                manual["wait_mode"] = wait["mode"]
            payload["manual"] = manual
        return payload

    @model_validator(mode="after")
    def validate_runtime_shape(self) -> "ManualLoopConfig":
        if self.manual.loop_mode == "gesture" and not self.gesture.mapping:
            raise ValueError("gesture.mapping must not be empty in gesture mode")
        return self


@dataclass(frozen=True)
class ConfigPaths:
    project_root: Path
    config_dir: Path
    default_config: Path
    local_config: Path
    explicit_config: Path | None


@dataclass(frozen=True)
class LoadedConfig:
    config: ManualLoopConfig
    paths: ConfigPaths
    default_loaded: bool
    local_loaded: bool


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


class ConfigLoadError(ValueError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Dum-E manual page loop launcher")
    parser.add_argument(
        "--project-root",
        default=".",
        help="Project root containing configs/ and data/ directories.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Explicit manual-loop config file. Replaces configs/manual_loop.local.yaml.",
    )
    _add_runtime_arguments(parser)

    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("run", help="Run the manual page loop")
    subparsers.add_parser("check", help="Validate config and print setup summary")
    setup_parser = subparsers.add_parser(
        "setup",
        help="Create or update configs/manual_loop.local.yaml",
    )
    setup_parser.add_argument(
        "--yes",
        action="store_true",
        help="Write the safe default local config without prompting.",
    )
    return parser


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--input", dest="input_dir", help="Manual image directory.")
    parser.add_argument(
        "--mode",
        choices=("new-pieces", "visible-blocks"),
        help="Manual reader mode.",
    )
    parser.add_argument("--preview-dir", help="Directory for per-page debug previews.")
    parser.add_argument(
        "--open-preview",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Open per-page debug previews.",
    )
    parser.add_argument(
        "--debug-components",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Print manual-reader component details.",
    )
    parser.add_argument(
        "--open-image",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Open each source image while waiting.",
    )
    parser.add_argument("--stop-after", type=int, help="Stop after N pages.")
    parser.add_argument(
        "--repeat-on-fail",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Stay on the page when parsing fails.",
    )
    parser.add_argument(
        "--wait-mode",
        choices=("keyboard", "enter", "gesture"),
        help="Wait strategy for the page loop.",
    )
    parser.add_argument(
        "--gesture-source",
        choices=("fake", "webcam", "realsense", "video"),
        help="Frame source for gesture mode.",
    )
    parser.add_argument("--gesture-device", help="Webcam device for gesture mode.")
    parser.add_argument("--gesture-video-path", help="Video file path for gesture mode.")
    parser.add_argument("--gesture-model-path", help="MediaPipe gesture model path.")
    parser.add_argument("--gesture-timeout-s", type=float, help="Gesture wait timeout.")
    parser.add_argument(
        "--gesture-fallback",
        choices=("keyboard", "enter", "none"),
        help="Fallback behavior when gesture startup or timeout fails.",
    )
    parser.add_argument(
        "--gesture-map",
        action="append",
        default=None,
        metavar="GESTURE=ACTION",
        help="Override gesture mapping. Actions: advance, repeat, quit, none.",
    )
    parser.add_argument(
        "--confirm-config",
        action="store_true",
        help="Print selected config and ask before running.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation prompts for scripts and CI.",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project_root = Path(args.project_root)
    command = args.command or "run"
    explicit_config = Path(args.config) if args.config else None

    if command == "setup":
        try:
            loaded = load_config(project_root, _cli_overrides(args), explicit_config)
            setup_local_config(loaded, yes=args.yes)
            return 0
        except (ConfigLoadError, ValidationError, ValueError) as exc:
            print(f"Config error: {_format_error(exc)}")
            return 1

    try:
        loaded = load_config(project_root, _cli_overrides(args), explicit_config)
    except (ConfigLoadError, ValidationError, ValueError) as exc:
        print(f"Config error: {_format_error(exc)}")
        return 1

    check = validate_config(loaded.config, loaded.paths.project_root)

    if command == "check":
        print_setup_summary(loaded, check)
        return 0 if check.ok else 1

    if not loaded.local_loaded:
        if loaded.paths.explicit_config is None:
            print(
                f"No local manual-loop config found at {loaded.paths.local_config}; "
                "using safe keyboard defaults."
            )

    if not check.ok:
        print_setup_summary(loaded, check)
        return 1

    if args.confirm_config:
        print_selected_config(loaded.config)
        if not args.yes and not _confirm("Run manual loop with this config?"):
            print("Manual loop cancelled.")
            return 1

    return run_manual_loop(loaded.config, loaded.paths.project_root)


def load_config(
    project_root: Path,
    cli_overrides: Mapping[str, Any] | None = None,
    explicit_config: Path | None = None,
) -> LoadedConfig:
    paths = _config_paths(project_root, explicit_config)
    payload: dict[str, Any] = ManualLoopConfig().model_dump(mode="python")

    default_loaded = paths.default_config.is_file()
    if default_loaded:
        payload = _deep_merge(payload, _load_yaml(paths.default_config))

    user_config = paths.explicit_config or paths.local_config
    local_loaded = user_config.is_file()
    if local_loaded:
        payload = _deep_merge(payload, _load_yaml(user_config))
    elif paths.explicit_config is not None:
        raise ConfigLoadError(f"Explicit config file not found: {paths.explicit_config}")

    if cli_overrides:
        payload = _deep_merge(payload, dict(cli_overrides))

    return LoadedConfig(
        config=ManualLoopConfig.model_validate(payload),
        paths=paths,
        default_loaded=default_loaded,
        local_loaded=local_loaded,
    )


def validate_config(config: ManualLoopConfig, project_root: Path) -> CheckResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        _validate_mapping(config.gesture.mapping)
    except ValueError as exc:
        errors.append(str(exc))

    if config.manual.loop_mode == "gesture":
        model_path = _resolve_path(project_root, config.gesture.model_path)
        if not model_path.is_file():
            errors.append(f"Gesture model path not found: {model_path}")

        source_error = _verify_gesture_source(config, project_root)
        if source_error is not None:
            message = f"Gesture source unavailable: {source_error}"
            if config.gesture.fallback_loop_mode == "enter":
                warnings.append(f"{message}; keyboard fallback is enabled.")
            else:
                errors.append(message)

    return CheckResult(ok=not errors, errors=tuple(errors), warnings=tuple(warnings))


def run_manual_loop(config: ManualLoopConfig, project_root: Path) -> int:
    wait_mode = config.manual.loop_mode
    wait_func = loop_cli.wait_for_confirmation
    gesture_wait = None

    if wait_mode == "gesture":
        try:
            from scripts.manuals.gesture_wait import build_gesture_wait

            gesture_wait = build_gesture_wait(
                source_name=config.gesture.source,
                device=config.gesture.device,
                video_path=_optional_resolved_str(project_root, config.gesture.video_path),
                model_path=str(_resolve_path(project_root, config.gesture.model_path)),
                timeout_s=config.gesture.timeout_s,
                fallback_wait_func=loop_cli.wait_for_confirmation
                if config.gesture.fallback_loop_mode == "enter"
                else None,
                action_mapping=runtime_action_mapping(config.gesture.mapping),
            )
            gesture_wait.start()
            wait_func = gesture_wait
        except Exception as exc:
            if config.gesture.fallback_loop_mode == "enter":
                print(f"Gesture wait unavailable ({exc}); falling back to keyboard input.")
                wait_mode = "enter"
                wait_func = loop_cli.wait_for_confirmation
                if gesture_wait is not None:
                    gesture_wait.close()
                    gesture_wait = None
            else:
                print(f"Manual loop error: could not start gesture wait: {exc}")
                if gesture_wait is not None:
                    gesture_wait.close()
                return 1

    manual = config.manual
    try:
        return loop_cli.run_loop(
            _resolve_path(project_root, manual.input_dir),
            mode=manual.mode,
            preview_dir=_resolve_path(project_root, manual.preview_dir)
            if manual.preview_dir
            else None,
            open_preview_flag=manual.open_preview,
            debug_components=manual.debug_components,
            open_image_flag=manual.open_image,
            stop_after=manual.stop_after,
            repeat_on_fail=manual.repeat_on_fail,
            wait_mode=wait_mode,
            wait_func=wait_func,
        )
    finally:
        if gesture_wait is not None:
            gesture_wait.close()


def print_setup_summary(loaded: LoadedConfig, check: CheckResult) -> None:
    config = loaded.config
    enabled = config.manual.loop_mode == "gesture"
    print("Dum-E manual loop configuration")
    print("")
    print("Manual:")
    print(f"  input_dir: {_resolve_path(loaded.paths.project_root, config.manual.input_dir)}")
    print(f"  reader_mode: {config.manual.mode}")
    print(f"  wait_mode: {config.manual.loop_mode}")
    print("")
    print("Gesture:")
    print(f"  enabled: {str(enabled).lower()}")
    print(f"  source: {config.gesture.source}")
    print(f"  device: {config.gesture.device}")
    print(f"  model_path: {_resolve_path(loaded.paths.project_root, config.gesture.model_path)}")
    video_path = _optional_resolved_str(loaded.paths.project_root, config.gesture.video_path)
    print(f"  video_path: {video_path}")
    print(f"  timeout_s: {config.gesture.timeout_s}")
    print(f"  fallback: {config.gesture.fallback or 'none'}")
    print("")
    print("Gesture mapping:")
    for gesture_name in GESTURE_ORDER:
        print(f"  {gesture_name:<14} -> {config.gesture.mapping.get(gesture_name, 'none')}")
    print("")
    print("Config:")
    print(f"  default_config: {_loaded_label(loaded.paths.default_config, loaded.default_loaded)}")
    print(f"  local_config: {_loaded_label(loaded.paths.local_config, loaded.local_loaded)}")
    explicit = str(loaded.paths.explicit_config) if loaded.paths.explicit_config else "null"
    print(f"  explicit_config: {explicit}")
    print("")
    print("Runtime:")
    if enabled:
        print("  camera_check: enabled for gesture mode")
    else:
        print("  camera_check: skipped because wait_mode=enter")
    print("  robot_control_enabled: false")
    print("  lerobot_env_step: not used")

    for warning in check.warnings:
        print(f"Warning: {warning}")
    for error in check.errors:
        print(f"Error: {error}")
    print(f"Status: {'ok' if check.ok else 'failed'}")


def print_selected_config(config: ManualLoopConfig) -> None:
    print("Selected manual-loop config:")
    print(yaml.safe_dump(config.model_dump(mode="python"), sort_keys=False).rstrip())


def setup_local_config(loaded: LoadedConfig, *, yes: bool = False) -> None:
    config = loaded.config
    if not yes:
        print("Configure the manual page loop. Press Enter to keep each default.")
        config = _prompt_for_config(config)

    loaded.paths.local_config.parent.mkdir(parents=True, exist_ok=True)
    with loaded.paths.local_config.open("w", encoding="utf-8") as file:
        yaml.safe_dump(config.model_dump(mode="python"), file, sort_keys=False)
    print(f"Wrote local manual-loop config: {loaded.paths.local_config}")


def _prompt_for_config(config: ManualLoopConfig) -> ManualLoopConfig:
    manual = config.manual.model_copy(
        update={
            "input_dir": _ask("Manual image directory", config.manual.input_dir),
            "wait_mode": _ask_choice(
                "Wait mode",
                ("enter", "gesture"),
                config.manual.loop_mode,
            ),
            "mode": _ask_choice(
                "Reader mode",
                ("new-pieces", "visible-blocks"),
                config.manual.mode,
            ),
        }
    )
    gesture = config.gesture

    if manual.loop_mode == "gesture":
        gesture = gesture.model_copy(
            update={
                "source": _ask_choice(
                    "Gesture source",
                    ("fake", "webcam", "realsense", "video"),
                    gesture.source,
                )
            }
        )
        updates: dict[str, Any] = {
            "model_path": _ask("Gesture model path", gesture.model_path),
            "timeout_s": _ask_optional_float("Gesture timeout seconds", gesture.timeout_s),
            "fallback": _ask_choice(
                "Gesture fallback",
                ("none", "enter"),
                gesture.fallback or "none",
            ),
        }
        if updates["fallback"] == "none":
            updates["fallback"] = None
        if gesture.source == "video":
            updates["video_path"] = _ask("Gesture video path", gesture.video_path or "")
        elif gesture.source == "webcam":
            device = _ask("Webcam device", "" if gesture.device is None else str(gesture.device))
            updates["device"] = device or None

        use_default_mapping = _ask_choice("Gesture mapping", ("default", "custom"), "default")
        if use_default_mapping == "default":
            updates["mapping"] = dict(DEFAULT_MAPPING)
        else:
            updates["mapping"] = _prompt_mapping(gesture.mapping)
        gesture = gesture.model_copy(update=updates)

    return ManualLoopConfig(manual=manual, gesture=gesture)


def _prompt_mapping(current: Mapping[str, str]) -> dict[str, str]:
    print("Enter gesture mappings as action names. Leave blank to keep current values.")
    mapping: dict[str, str] = {}
    for gesture_name in GESTURE_ORDER:
        default = current.get(gesture_name, "")
        raw = _ask(f"{gesture_name}", default)
        if raw:
            mapping[gesture_name] = raw
    if not mapping:
        mapping = dict(DEFAULT_MAPPING)
    _validate_mapping(mapping)
    return mapping


def _verify_gesture_source(config: ManualLoopConfig, project_root: Path) -> str | None:
    source = None
    try:
        from camera.source import create_source

        kwargs: dict[str, object] = {}
        if config.gesture.source == "video":
            if not config.gesture.video_path:
                return "gesture.video_path is required when gesture.source is video"
            kwargs["path"] = str(_resolve_path(project_root, config.gesture.video_path))
        if config.gesture.source == "webcam" and config.gesture.device is not None:
            kwargs["device"] = config.gesture.device
        source = create_source(config.gesture.source, **kwargs)
        source.start()
        return None
    except Exception as exc:
        return str(exc)
    finally:
        if source is not None:
            try:
                source.stop()
            except Exception:
                pass


def _cli_overrides(args: argparse.Namespace) -> dict[str, Any]:
    overrides: dict[str, Any] = {}

    manual: dict[str, Any] = {}
    for name in (
        "input_dir",
        "mode",
        "preview_dir",
        "open_preview",
        "debug_components",
        "open_image",
        "stop_after",
        "repeat_on_fail",
    ):
        value = getattr(args, name, None)
        if value is not None:
            manual[name] = value
    if manual:
        overrides["manual"] = manual

    wait_mode = getattr(args, "wait_mode", None)
    if wait_mode is not None:
        overrides.setdefault("manual", {})["wait_mode"] = wait_mode

    gesture: dict[str, Any] = {}
    gesture_fields = {
        "gesture_source": "source",
        "gesture_device": "device",
        "gesture_video_path": "video_path",
        "gesture_model_path": "model_path",
        "gesture_timeout_s": "timeout_s",
    }
    for arg_name, config_name in gesture_fields.items():
        value = getattr(args, arg_name, None)
        if value is not None:
            gesture[config_name] = value
    if getattr(args, "gesture_fallback", None) is not None:
        gesture["fallback"] = None if args.gesture_fallback == "none" else args.gesture_fallback
    if getattr(args, "gesture_map", None):
        gesture["mapping"] = _parse_mapping_args(args.gesture_map)
    if gesture:
        overrides["gesture"] = gesture

    return overrides


def _parse_mapping_args(raw_mappings: Sequence[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for raw in raw_mappings:
        if "=" not in raw:
            raise ValueError("--gesture-map must use GESTURE=ACTION form")
        key, value = raw.split("=", 1)
        mapping[key.strip()] = value.strip()
    return normalize_mapping(mapping)


def _validate_mapping(mapping: Mapping[Any, Any]) -> None:
    normalize_mapping(mapping)


def normalize_mapping(mapping: Mapping[Any, Any]) -> dict[str, str]:
    if not mapping:
        raise ValueError("gesture.mapping must not be empty")

    normalized: dict[str, str] = {}
    for gesture_name, action_name in mapping.items():
        canonical_gesture = normalize_gesture_name(gesture_name)
        normalized[canonical_gesture] = normalize_mapping_action(action_name)

    for gesture_name in GESTURE_ORDER:
        normalized.setdefault(gesture_name, "none")
    return {gesture_name: normalized[gesture_name] for gesture_name in GESTURE_ORDER}


def normalize_gesture_name(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Gesture mapping keys must be strings")
    normalized = value.strip()
    if normalized not in GESTURE_NAME_ALIASES:
        expected = ", ".join(GESTURE_ORDER)
        raise ValueError(
            f"Invalid gesture mapping key '{value}'. Expected one of: {expected}"
        )
    return GESTURE_NAME_ALIASES[normalized]


def normalize_mapping_action(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Gesture mapping actions must be strings")
    normalized = value.strip().lower()
    if not normalized:
        raise ValueError("Gesture mapping actions must not be empty")
    if normalized not in VALID_MAPPING_ACTIONS:
        expected = ", ".join(sorted(VALID_MAPPING_ACTIONS))
        raise ValueError(
            f"Invalid gesture mapping action '{value}'. Expected one of: {expected}"
        )
    return normalized


def runtime_action_mapping(mapping: Mapping[Any, Any]) -> dict[str, str]:
    normalized = normalize_mapping(mapping)
    return {
        gesture_name: action_name
        for gesture_name, action_name in normalized.items()
        if action_name != "none"
    }


def _config_paths(project_root: Path, explicit_config: Path | None = None) -> ConfigPaths:
    resolved_root = project_root.resolve()
    config_dir = resolved_root / "configs"
    resolved_explicit = None
    if explicit_config is not None:
        resolved_explicit = _resolve_path(resolved_root, explicit_config)
    return ConfigPaths(
        project_root=resolved_root,
        config_dir=config_dir,
        default_config=config_dir / "manual_loop.default.yaml",
        local_config=config_dir / "manual_loop.local.yaml",
        explicit_config=resolved_explicit,
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
    except OSError as exc:
        raise ConfigLoadError(f"Could not read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigLoadError(f"Expected mapping in YAML file: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_path(project_root: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def _optional_resolved_str(project_root: Path, raw_path: str | None) -> str | None:
    if raw_path is None or raw_path == "":
        return None
    return str(_resolve_path(project_root, raw_path))


def _loaded_label(path: Path, loaded: bool) -> str:
    return f"{path} ({'loaded' if loaded else 'missing'})"


def _format_error(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        return "; ".join(error["msg"] for error in exc.errors())
    return str(exc)


def _ask(prompt: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    try:
        raw = input(f"{prompt}{suffix}: ").strip()
    except EOFError:
        raw = ""
    return raw or default


def _ask_optional_float(prompt: str, default: float | None) -> float | None:
    default_text = "" if default is None else str(default)
    raw = _ask(prompt, default_text)
    if raw == "":
        return None
    value = float(raw)
    if value < 0:
        raise ValueError(f"{prompt} must not be negative")
    return value


def _ask_choice(prompt: str, choices: Sequence[str], default: str) -> str:
    choice_list = "/".join(choices)
    while True:
        value = _ask(f"{prompt} ({choice_list})", default)
        if value in choices:
            return value
        print(f"Choose one of: {choice_list}")


def _confirm(prompt: str) -> bool:
    try:
        raw = input(f"{prompt} [y/N]: ").strip().lower()
    except EOFError:
        return False
    return raw in {"y", "yes"}
