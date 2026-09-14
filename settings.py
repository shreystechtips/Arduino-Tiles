"""Typed user settings, JSON sharing, and per-user persistence."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Union

from platformdirs import user_config_dir


SCHEMA_VERSION = 1
APP_NAME = "Arduino Tiles"
SETTINGS_FILENAME = "settings.json"
LANES = tuple(f"lane_{index}" for index in range(4))


@dataclass(frozen=True)
class Settings:
    serial_port: str
    baud_rate: int
    keybinds: dict[str, str]
    fps: int
    screen_width: int
    screen_height: int

    def __post_init__(self) -> None:
        if not isinstance(self.serial_port, str) or not self.serial_port.strip():
            raise ValueError("serial_port must be a non-empty string")
        _validate_int("baud_rate", self.baud_rate, minimum=1, maximum=1_000_000)
        _validate_int("fps", self.fps, minimum=1, maximum=240)
        _validate_int("screen_width", self.screen_width, minimum=320, maximum=7680)
        _validate_int("screen_height", self.screen_height, minimum=320, maximum=7680)

        if not isinstance(self.keybinds, Mapping):
            raise ValueError("keybinds must be an object")
        if set(self.keybinds) != set(LANES):
            raise ValueError(f"keybinds must contain exactly: {', '.join(LANES)}")
        if any(not isinstance(key, str) or len(key) != 1 for key in self.keybinds.values()):
            raise ValueError("each keybind must be a single-character string")
        if len(set(self.keybinds.values())) != len(LANES):
            raise ValueError("keybinds must not assign one key to multiple lanes")

        object.__setattr__(self, "serial_port", self.serial_port.strip())
        object.__setattr__(self, "keybinds", dict(self.keybinds))


def _validate_int(name: str, value: Any, *, minimum: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer between {minimum} and {maximum}")


def default_settings() -> Settings:
    return Settings(
        serial_port="COM4",
        baud_rate=9600,
        keybinds={"lane_0": "d", "lane_1": "f", "lane_2": "j", "lane_3": "k"},
        fps=60,
        screen_width=480,
        screen_height=800,
    )


def settings_to_dict(settings: Settings) -> dict[str, Any]:
    if not isinstance(settings, Settings):
        raise TypeError("settings must be a Settings instance")
    return {
        "schema_version": SCHEMA_VERSION,
        "serial_port": settings.serial_port,
        "baud_rate": settings.baud_rate,
        "keybinds": dict(settings.keybinds),
        "fps": settings.fps,
        "screen_width": settings.screen_width,
        "screen_height": settings.screen_height,
    }


def merge_settings(current: Settings, payload: Mapping[str, Any]) -> Settings:
    if not isinstance(current, Settings):
        raise TypeError("current must be a Settings instance")
    if not isinstance(payload, Mapping):
        raise ValueError("settings payload must be an object")

    if "schema_version" in payload:
        version = payload["schema_version"]
        if isinstance(version, bool) or not isinstance(version, int) or version != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema_version: {version!r}")

    values = settings_to_dict(current)
    values.update({key: payload[key] for key in values if key != "schema_version" and key in payload})
    values.pop("schema_version")
    return Settings(**values)


def settings_path() -> Path:
    return Path(user_config_dir(APP_NAME)) / SETTINGS_FILENAME


def load_settings(path: Optional[Union[os.PathLike, str]] = None) -> Settings:
    target = Path(path) if path is not None else settings_path()
    if not target.exists():
        return default_settings()
    try:
        payload = _read_json(target)
        return merge_settings(default_settings(), payload)
    except OSError as exc:
        raise ValueError(f"unable to read settings file {target}: {exc}") from exc


def save_settings(settings: Settings, path: Optional[Union[os.PathLike, str]] = None) -> None:
    if not isinstance(settings, Settings):
        raise TypeError("settings must be a Settings instance")
    target = Path(path) if path is not None else settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(settings_to_dict(settings), temporary, indent=2, sort_keys=True)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def import_settings_file(current: Settings, path: Union[os.PathLike, str]) -> Settings:
    try:
        return merge_settings(current, _read_json(Path(path)))
    except OSError as exc:
        raise ValueError(f"unable to read settings file {path}: {exc}") from exc


def export_settings_file(settings: Settings, path: Union[os.PathLike, str]) -> None:
    save_settings(settings, path)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as source:
            payload = json.load(source, object_pairs_hook=_object_pairs_without_duplicates)
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError(f"invalid settings JSON in {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("settings JSON must contain an object")
    return payload


def _object_pairs_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field: {key}")
        result[key] = value
    return result
