import json
from pathlib import Path

import pytest

import config
from settings import (
    Settings,
    default_settings,
    export_settings_file,
    import_settings_file,
    load_settings,
    merge_settings,
    save_settings,
    settings_to_dict,
)


def test_default_settings_match_the_documented_schema_defaults():
    settings = default_settings()

    assert settings == Settings(
        serial_port="COM4",
        baud_rate=9600,
        keybinds={"lane_0": "d", "lane_1": "f", "lane_2": "j", "lane_3": "k"},
        fps=60,
        screen_width=480,
        screen_height=800,
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("serial_port", ""),
        ("baud_rate", 0),
        ("baud_rate", True),
        ("fps", 0),
        ("fps", 241),
        ("screen_width", 319),
        ("screen_height", 319),
    ],
)
def test_settings_reject_invalid_values(field, value):
    values = settings_to_dict(default_settings())
    values.pop("schema_version")
    values[field] = value

    with pytest.raises(ValueError):
        Settings(**values)


def test_settings_reject_invalid_keybinds():
    values = settings_to_dict(default_settings())
    values.pop("schema_version")
    values["keybinds"] = {"lane_0": "d", "lane_1": "d", "lane_2": "j", "lane_3": "k"}

    with pytest.raises(ValueError):
        Settings(**values)


def test_merge_preserves_omitted_fields_and_ignores_unknown_fields():
    current = default_settings()

    merged = merge_settings(
        current,
        {"schema_version": 1, "fps": 120, "future_option": "ignored"},
    )

    assert merged.fps == 120
    assert merged.serial_port == current.serial_port
    assert merged.keybinds == current.keybinds


def test_merge_rejects_wrong_schema_version_and_malformed_types():
    with pytest.raises(ValueError):
        merge_settings(default_settings(), {"schema_version": 2})

    with pytest.raises(ValueError):
        merge_settings(default_settings(), {"fps": "60"})


def test_keybinds_are_serialized_as_portable_lane_names():
    payload = settings_to_dict(default_settings())

    assert payload["schema_version"] == 1
    assert payload["keybinds"] == {"lane_0": "d", "lane_1": "f", "lane_2": "j", "lane_3": "k"}


def test_export_and_import_round_trip(tmp_path):
    path = tmp_path / "shared-settings.json"
    original = Settings("/dev/ttyUSB0", 115200, {"lane_0": "a", "lane_1": "s", "lane_2": "l", "lane_3": ";"}, 144, 1024, 768)

    export_settings_file(original, path)
    imported = import_settings_file(default_settings(), path)

    assert imported == original
    assert json.loads(path.read_text()) == settings_to_dict(original)


def test_import_merges_file_without_mutating_current_settings(tmp_path):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"schema_version": 1, "screen_width": 1200}))
    current = default_settings()

    imported = import_settings_file(current, path)

    assert current.screen_width == 480
    assert imported.screen_width == 1200
    assert imported.screen_height == current.screen_height


@pytest.mark.parametrize(
    "contents",
    ["not json", "[]", '{"schema_version": 1, "keybinds": []}', '{"schema_version": 1, "fps": null}'],
)
def test_import_rejects_malformed_json_payloads(tmp_path, contents):
    path = tmp_path / "bad.json"
    path.write_text(contents)

    with pytest.raises(ValueError):
        import_settings_file(default_settings(), path)


def test_import_rejects_duplicate_lane_keys(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "keybinds": {"lane_0": "a", "lane_0": "b"}}')

    with pytest.raises(ValueError):
        import_settings_file(default_settings(), path)


def test_save_and_load_round_trip_uses_explicit_path(tmp_path):
    path = tmp_path / "nested" / "settings.json"
    expected = Settings("COM9", 57600, {"lane_0": "q", "lane_1": "w", "lane_2": "o", "lane_3": "p"}, 30, 640, 480)

    save_settings(expected, path)

    assert load_settings(path) == expected


def test_load_missing_explicit_path_returns_defaults(tmp_path):
    assert load_settings(tmp_path / "missing.json") == default_settings()


def test_save_replaces_existing_file_atomically(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("old")
    replacements = []
    real_replace = __import__("os").replace

    def recording_replace(source, destination):
        replacements.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr("settings.os.replace", recording_replace)
    save_settings(default_settings(), path)

    assert len(replacements) == 1
    assert replacements[0][1] == path
    assert json.loads(path.read_text())["schema_version"] == 1


def test_default_path_is_supplied_by_platformdirs(monkeypatch, tmp_path):
    monkeypatch.setattr("settings.user_config_dir", lambda app_name: str(tmp_path / app_name))

    save_settings(default_settings())

    assert (tmp_path / "Arduino Tiles" / "settings.json").exists()


def test_config_compatibility_bridge_applies_typed_settings():
    updated = Settings("COM7", 19200, {"lane_0": "z", "lane_1": "x", "lane_2": "n", "lane_3": "m"}, 120, 640, 480)

    config.apply_settings(updated)

    assert config.SERIAL_PORT == "COM7"
    assert config.BAUD_RATE == 19200
    assert config.FPS == 120
    assert config.SCREEN_WIDTH == 640
    assert config.SCREEN_HEIGHT == 480
    assert config.KEYBINDS == {config.pygame.K_z: 0, config.pygame.K_x: 1, config.pygame.K_n: 2, config.pygame.K_m: 3}

    config.apply_settings(default_settings())
