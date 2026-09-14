from dataclasses import replace
from pathlib import Path

import pygame
import pytest

import config
import main
from arduino_handler import ArduinoHandler
from game import GameScreen
from settings import Settings, default_settings


@pytest.fixture(autouse=True)
def restore_default_runtime_config():
    yield
    config.apply_settings(default_settings())


def test_resource_path_uses_source_tree_when_working_directory_changes(monkeypatch, tmp_path):
    monkeypatch.delattr(config.sys, "_MEIPASS", raising=False)
    monkeypatch.chdir(tmp_path)

    resolved = config.resource_path("assets/img/background.png")

    expected = Path(config.__file__).resolve().parent / "assets" / "img" / "background.png"
    assert Path(resolved) == expected


def test_resource_path_uses_pyinstaller_bundle_root(monkeypatch, tmp_path):
    bundle_root = tmp_path / "bundle"
    monkeypatch.setattr(config.sys, "_MEIPASS", str(bundle_root), raising=False)

    resolved = config.resource_path("assets/fonts/game.ttf")

    assert Path(resolved) == bundle_root / "assets" / "fonts" / "game.ttf"


def test_arduino_handler_requires_explicit_runtime_connection_values(monkeypatch):
    monkeypatch.setattr(ArduinoHandler, "connect", lambda self: None)

    with pytest.raises(TypeError):
        ArduinoHandler()


def test_arduino_handler_resolves_omitted_baud_from_current_runtime_config(monkeypatch):
    monkeypatch.setattr(ArduinoHandler, "connect", lambda self: None)
    config.apply_settings(replace(default_settings(), baud_rate=57600))

    handler = ArduinoHandler(port="COM8")

    assert handler.baud_rate == 57600


def test_config_apply_settings_accepts_portable_punctuation_keybinds():
    updated = replace(
        default_settings(),
        keybinds={"lane_0": "a", "lane_1": "s", "lane_2": "l", "lane_3": ";"},
    )

    config.apply_settings(updated)

    assert config.KEYBINDS[pygame.K_SEMICOLON] == 3


class _Surface:
    def __init__(self, size):
        self.size = size


class _Arduino:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.connected = False
        self.close_count = 0

    def close(self):
        self.close_count += 1


class _Screen:
    def __init__(self, surface, *dependencies):
        self.surface = surface
        self.dependencies = dependencies

    def update_buttons(self):
        pass


class _GameScreen(_Screen):
    def __init__(self, surface, arduino):
        super().__init__(surface, arduino)
        self.arduino = arduino
        self.keybinds = dict(config.KEYBINDS)

    def update_arduino_handler(self, arduino):
        self.arduino = arduino

    def update_keybinds(self, keybinds):
        self.keybinds = dict(keybinds)


def _build_app(monkeypatch, loaded_settings, saved_settings):
    monkeypatch.setattr(main, "load_settings", lambda: loaded_settings, raising=False)
    monkeypatch.setattr(main, "save_settings", saved_settings.append, raising=False)
    monkeypatch.setattr(main.pygame, "init", lambda: None)
    monkeypatch.setattr(main.pygame.display, "set_caption", lambda caption: None)
    monkeypatch.setattr(main.pygame.display, "set_mode", lambda size: _Surface(size))
    monkeypatch.setattr(main.pygame.time, "Clock", object)
    monkeypatch.setattr(main, "ArduinoHandler", _Arduino)
    monkeypatch.setattr(main, "LoadingScreen", _Screen)
    monkeypatch.setattr(main, "TitleScreen", _Screen)
    monkeypatch.setattr(main, "MainMenuScreen", _Screen)
    monkeypatch.setattr(main, "GameScreen", _GameScreen)
    monkeypatch.setattr(main, "SettingsScreen", _Screen)
    return main.GameApp()


def test_game_app_loads_settings_before_creating_runtime_consumers(monkeypatch):
    loaded = Settings(
        "COM12",
        115200,
        {"lane_0": "q", "lane_1": "w", "lane_2": "o", "lane_3": "p"},
        144,
        1024,
        768,
    )
    saved = []

    app = _build_app(monkeypatch, loaded, saved)

    assert app.settings == loaded
    assert app.screen.size == (1024, 768)
    assert (app.arduino.port, app.arduino.baud_rate) == ("COM12", 115200)
    assert app.game_screen.keybinds == {
        pygame.K_q: 0,
        pygame.K_w: 1,
        pygame.K_o: 2,
        pygame.K_p: 3,
    }
    assert saved == []


def test_apply_settings_recreates_serial_consumer_and_persists(monkeypatch):
    saved = []
    app = _build_app(monkeypatch, default_settings(), saved)
    original_arduino = app.arduino
    original_screen = app.screen
    updated = replace(default_settings(), serial_port="COM9", baud_rate=57600, fps=120)

    app.apply_settings(updated)

    assert app.settings == updated
    assert original_arduino.close_count == 1
    assert app.arduino is app.game_screen.arduino
    assert (app.arduino.port, app.arduino.baud_rate) == ("COM9", 57600)
    assert app.screen is original_screen
    assert saved == [updated]


def test_apply_settings_updates_keybinds_without_recreating_serial(monkeypatch):
    saved = []
    app = _build_app(monkeypatch, default_settings(), saved)
    original_arduino = app.arduino
    updated = replace(
        default_settings(),
        keybinds={"lane_0": "z", "lane_1": "x", "lane_2": "n", "lane_3": "m"},
    )

    app.apply_settings(updated)

    assert app.arduino is original_arduino
    assert original_arduino.close_count == 0
    assert app.game_screen.keybinds == {
        pygame.K_z: 0,
        pygame.K_x: 1,
        pygame.K_n: 2,
        pygame.K_m: 3,
    }
    assert saved == [updated]


def test_apply_settings_recreates_background_dependent_screens_for_window_size(monkeypatch):
    saved = []
    app = _build_app(monkeypatch, default_settings(), saved)
    app.menu_screen = _Screen(app.screen)
    original_screen = app.screen
    original_arduino = app.arduino
    original_components = (
        app.loading_screen,
        app.title_screen,
        app.menu_screen,
        app.game_screen,
        app.settings_screen,
    )
    updated = replace(default_settings(), screen_width=1280, screen_height=720)

    app.apply_settings(updated)

    assert app.screen is not original_screen
    assert app.screen.size == (1280, 720)
    assert app.arduino is original_arduino
    assert all(
        component.surface is app.screen
        for component in (
            app.loading_screen,
            app.title_screen,
            app.menu_screen,
            app.game_screen,
            app.settings_screen,
        )
    )
    assert all(
        replacement is not original
        for replacement, original in zip(
            (
                app.loading_screen,
                app.title_screen,
                app.menu_screen,
                app.game_screen,
                app.settings_screen,
            ),
            original_components,
        )
    )
    assert app.game_screen.arduino is original_arduino


def test_apply_settings_keeps_accepted_values_when_persistence_fails(monkeypatch):
    def fail_to_save(_settings):
        raise OSError("disk full")

    app = _build_app(monkeypatch, default_settings(), [])
    monkeypatch.setattr(main, "save_settings", fail_to_save)
    updated = replace(default_settings(), fps=90)

    app.apply_settings(updated)

    assert app.settings == updated


def test_settings_cancel_returns_to_title_without_applying_changes():
    app = object.__new__(main.GameApp)
    app.state = "settings"

    assert app.handle_settings_result({"action": "cancel"}) is True
    assert app.state == "title"
    assert config.FPS == 90


def test_game_screen_uses_its_updated_keybinds_for_input():
    game = GameScreen.__new__(GameScreen)
    game.autoplay = False
    game.game_time = 1.25
    game.keybinds = {pygame.K_z: 2}
    processed = []
    game._process_tap = lambda lane, hit_time: processed.append((lane, hit_time))

    game._handle_input(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z))

    assert processed == [(2, 1.25)]
