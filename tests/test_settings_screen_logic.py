from dataclasses import replace

from settings import default_settings, settings_to_dict
import pytest

from settings_screen import SettingsDraft, choose_settings_file, probe_arduino, resolve_settings_path


def test_editing_draft_does_not_mutate_accepted_settings():
    accepted = default_settings()
    editor = SettingsDraft(accepted)

    editor.set_text("serial_port", "COM9")
    editor.set_keybind("lane_0", "a")

    assert accepted == default_settings()
    assert accepted.keybinds["lane_0"] == "d"
    assert editor.draft_settings == replace(
        accepted,
        serial_port="COM9",
        keybinds={"lane_0": "a", "lane_1": "f", "lane_2": "j", "lane_3": "k"},
    )


def test_import_merges_with_the_current_draft_and_opens_complete_review():
    accepted = default_settings()
    editor = SettingsDraft(accepted)
    editor.set_text("fps", "120")

    reviewed = editor.begin_import(
        {"schema_version": 1, "screen_width": 1024, "future_option": "ignored"}
    )

    assert editor.is_reviewing
    assert reviewed == replace(accepted, fps=120, screen_width=1024)
    assert editor.review_settings == reviewed
    assert set(settings_to_dict(reviewed)) == {
        "schema_version",
        "serial_port",
        "baud_rate",
        "keybinds",
        "fps",
        "screen_width",
        "screen_height",
    }
    assert accepted == default_settings()


def test_apply_from_review_returns_candidate_without_changing_accepted_settings():
    accepted = default_settings()
    editor = SettingsDraft(accepted)
    candidate = editor.begin_import({"schema_version": 1, "baud_rate": 115200})

    result = editor.apply()

    assert result == {"action": "apply", "settings": candidate}
    assert accepted == default_settings()


def test_cancel_review_discards_import_and_keeps_preimport_draft():
    accepted = default_settings()
    editor = SettingsDraft(accepted)
    editor.set_text("fps", "90")
    editor.begin_import({"schema_version": 1, "fps": 144, "screen_height": 720})

    editor.cancel_review()

    assert not editor.is_reviewing
    assert editor.review_settings is None
    assert editor.draft_settings == replace(accepted, fps=90)
    assert editor.cancel() == {"action": "cancel"}
    assert accepted == default_settings()


def test_export_selects_visible_draft_in_editor_and_review_states():
    accepted = default_settings()
    editor = SettingsDraft(accepted)
    editor.set_text("screen_width", "800")

    assert editor.settings_for_export() == replace(accepted, screen_width=800)

    candidate = editor.begin_import({"schema_version": 1, "screen_height": 600})

    assert editor.settings_for_export() == candidate
    assert editor.settings_for_export() == replace(
        accepted,
        screen_width=800,
        screen_height=600,
    )


def test_file_import_and_export_use_the_review_candidate(tmp_path):
    source = tmp_path / "partial.json"
    source.write_text('{"schema_version": 1, "fps": 144}', encoding="utf-8")
    destination = tmp_path / "exported.json"
    editor = SettingsDraft(default_settings())

    editor.begin_import_file(source)
    editor.export_file(destination)

    assert destination.read_text(encoding="utf-8").endswith("\n")
    assert '"fps": 144' in destination.read_text(encoding="utf-8")
    assert '"serial_port": "COM4"' in destination.read_text(encoding="utf-8")


def test_typed_path_is_used_when_native_dialog_is_unavailable():
    def unavailable_dialog():
        raise RuntimeError("tk is unavailable")

    assert resolve_settings_path(" /tmp/settings.json ", unavailable_dialog) == "/tmp/settings.json"

    with pytest.raises(ValueError, match="enter a JSON path"):
        resolve_settings_path("", unavailable_dialog)


def test_native_dialog_selection_takes_priority_over_typed_path():
    assert resolve_settings_path(
        "/tmp/typed.json", lambda: "/tmp/chosen.json"
    ) == "/tmp/chosen.json"


def test_macos_file_dialog_uses_osascript_without_initializing_tk(monkeypatch):
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return type("Result", (), {"returncode": 0, "stdout": "/tmp/shared.json\n"})()

    monkeypatch.setattr("settings_screen.sys.platform", "darwin")

    assert choose_settings_file(runner=runner) == "/tmp/shared.json"
    assert calls[0][0][0] == "osascript"
    assert "choose file" in calls[0][0][-1]


def test_arduino_probe_closes_temporary_connection_and_never_raises():
    probes = []

    class Probe:
        connected = True

        def __init__(self, port, baud_rate):
            self.connection = (port, baud_rate)
            self.closed = False
            probes.append(self)

        def close(self):
            self.closed = True

    connected, message = probe_arduino(default_settings(), Probe)

    assert connected
    assert "connected" in message.lower()
    assert probes[0].connection == ("COM4", 9600)
    assert probes[0].closed

    connected, message = probe_arduino(
        default_settings(), lambda *_args: (_ for _ in ()).throw(OSError("busy"))
    )

    assert not connected
    assert "busy" in message
