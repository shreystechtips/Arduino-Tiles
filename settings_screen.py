from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping
import subprocess
import sys

import pygame

import config
import utils
from arduino_handler import ArduinoHandler
from settings import Settings, export_settings_file, import_settings_file, merge_settings

_TEXT_FIELDS = ("serial_port", "baud_rate", "fps", "screen_width", "screen_height")


def _copy_settings(settings: Settings) -> Settings:
    return Settings(settings.serial_port, settings.baud_rate, dict(settings.keybinds), settings.fps,
                    settings.screen_width, settings.screen_height)


def resolve_settings_path(typed_path: str, dialog):
    try:
        selected = dialog()
    except Exception:
        selected = ""
    selected = selected or typed_path.strip()
    if not selected:
        raise ValueError("enter a JSON path or choose a file")
    return selected


def choose_settings_file(save: bool = False, runner=subprocess.run) -> str:
    """Open an OS-native chooser without embedding another GUI toolkit in SDL."""
    if sys.platform == "darwin":
        action = "choose file name" if save else "choose file"
        label = "Export" if save else "Import"
        script = f'POSIX path of ({action} with prompt "{label} settings")'
        command = ["osascript", "-e", script]
    elif sys.platform == "win32":
        dialog = "SaveFileDialog" if save else "OpenFileDialog"
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            f"$d=New-Object System.Windows.Forms.{dialog}; "
            "$d.Filter='JSON settings (*.json)|*.json|All files (*.*)|*.*'; "
            "if($d.ShowDialog() -eq 'OK'){[Console]::Write($d.FileName)}"
        )
        command = ["powershell", "-NoProfile", "-STA", "-Command", script]
    else:
        command = ["zenity", "--file-selection"]
        if save:
            command.append("--save")
    try:
        result = runner(command, capture_output=True, text=True, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def probe_arduino(settings: Settings, handler_class=ArduinoHandler):
    handler = None
    try:
        handler = handler_class(settings.serial_port, settings.baud_rate)
        connected = bool(handler.connected)
        return connected, "Arduino connected." if connected else "Arduino not found."
    except Exception as exc:
        return False, f"Arduino unavailable: {exc}"
    finally:
        if handler is not None:
            try:
                handler.close()
            except Exception:
                pass


class SettingsDraft:
    """Display-independent draft/review state used by the Pygame screen."""

    def __init__(self, accepted_settings: Settings):
        self.reset(accepted_settings)

    def reset(self, accepted_settings: Settings) -> None:
        if not isinstance(accepted_settings, Settings):
            raise TypeError("accepted_settings must be a Settings instance")
        self._accepted_settings = accepted_settings
        self._text = {field: str(getattr(accepted_settings, field)) for field in _TEXT_FIELDS}
        self._keybinds = dict(accepted_settings.keybinds)
        self._review_settings = None

    def set_text(self, field: str, value: str) -> None:
        if field not in _TEXT_FIELDS:
            raise ValueError(f"unknown editable field: {field}")
        self._text[field] = value

    def text(self, field: str) -> str:
        if field not in _TEXT_FIELDS:
            raise ValueError(f"unknown editable field: {field}")
        return self._text[field]

    def set_keybind(self, lane: str, key: str) -> None:
        candidate = dict(self._keybinds)
        if lane not in candidate:
            raise ValueError(f"unknown lane: {lane}")
        candidate[lane] = key
        self._settings_from_values(self._text, candidate)
        self._keybinds = candidate

    @property
    def keybinds(self):
        return dict(self._keybinds)

    @property
    def draft_settings(self):
        return self._settings_from_values(self._text, self._keybinds)

    @property
    def review_settings(self):
        return _copy_settings(self._review_settings) if self._review_settings else None

    @property
    def is_reviewing(self):
        return self._review_settings is not None

    def begin_import(self, payload: Mapping[str, Any]):
        candidate = merge_settings(self.draft_settings, payload)
        self._review_settings = _copy_settings(candidate)
        return _copy_settings(candidate)

    def begin_import_file(self, path: str | Path):
        candidate = import_settings_file(self.draft_settings, path)
        self._review_settings = _copy_settings(candidate)
        return _copy_settings(candidate)

    def cancel_review(self):
        self._review_settings = None

    def settings_for_export(self):
        return self.review_settings or self.draft_settings

    def export_file(self, path: str | Path):
        export_settings_file(self.settings_for_export(), path)

    def apply(self):
        return {"action": "apply", "settings": self.settings_for_export()}

    @staticmethod
    def cancel():
        return {"action": "cancel"}

    @staticmethod
    def _settings_from_values(text, keybinds):
        try:
            return Settings(text["serial_port"], int(text["baud_rate"]), dict(keybinds),
                            int(text["fps"]), int(text["screen_width"]), int(text["screen_height"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid settings: {exc}") from exc


class SettingsScreen:
    def __init__(self, surface, arduino_handler, settings: Settings | None = None):
        self.surface = surface
        self.font_path = config.FONT_PATH
        self.arduino_handler = arduino_handler
        self.accepted_settings = settings or config.current_settings()
        self.draft = SettingsDraft(self.accepted_settings)
        self.background = pygame.transform.scale(utils.load_image(config.BACKGROUND_IMG),
                                                  (config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        self.active_field = None
        self.keybind_input = None
        self.feedback_message = ""
        self.feedback_timer = 0
        self.create_buttons()

    def create_buttons(self):
        self.buttons = [
            utils.Button((20, 500, 140, 42), "Import", self.import_settings),
            utils.Button((170, 500, 140, 42), "Export", self.export_settings),
            utils.Button((320, 500, 140, 42), "Test Arduino", self.test_arduino),
            utils.Button((config.SCREEN_WIDTH - 220, config.SCREEN_HEIGHT - 70, 100, 45), "Apply", self.apply),
            utils.Button((config.SCREEN_WIDTH - 110, config.SCREEN_HEIGHT - 70, 90, 45), "Cancel", self.cancel),
        ]

    def _dialog(self, save=False):
        return choose_settings_file(save=save)

    def import_settings(self):
        try:
            self.draft.begin_import_file(resolve_settings_path("", self._dialog))
            self.feedback_message = "Review imported settings, then Apply or Cancel."
        except (OSError, ValueError) as exc:
            self.feedback_message = f"Import failed: {exc}"
        self.feedback_timer = 5

    def export_settings(self):
        try:
            self.draft.export_file(resolve_settings_path("", lambda: self._dialog(save=True)))
            self.feedback_message = "Settings exported."
        except (OSError, ValueError) as exc:
            self.feedback_message = f"Export failed: {exc}"
        self.feedback_timer = 4

    def test_arduino(self):
        try:
            _, self.feedback_message = probe_arduino(self.draft.draft_settings)
        except ValueError as exc:
            self.feedback_message = str(exc)
        self.feedback_timer = 4

    def apply(self):
        try:
            return self.draft.apply()
        except ValueError as exc:
            self.feedback_message = str(exc)
            self.feedback_timer = 4
            return None

    def cancel(self):
        self.draft.reset(self.accepted_settings)
        return {"action": "cancel"}

    def _field_rect(self, index):
        return pygame.Rect(20 + (index % 2) * 230, 105 + (index // 2) * 65, 210, 42)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return {"action": "quit"}
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for index, field in enumerate(_TEXT_FIELDS):
                    if self._field_rect(index).collidepoint(event.pos):
                        self.active_field = field
                        self.keybind_input = None
                        break
                else:
                    for index, lane in enumerate(("lane_0", "lane_1", "lane_2", "lane_3")):
                        rect = pygame.Rect(20 + (index % 2) * 230, 380 + (index // 2) * 48, 210, 36)
                        if rect.collidepoint(event.pos):
                            self.keybind_input = lane
                            break
                    else:
                        for button in self.buttons:
                            result = button.handle_event(event)
                            if result:
                                return result
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return self.cancel()
                if self.keybind_input:
                    if event.unicode and len(event.unicode) == 1 and event.unicode.isprintable():
                        self.draft.set_keybind(self.keybind_input, event.unicode.lower())
                        self.feedback_message = f"{self.keybind_input} set to {event.unicode}"
                        self.feedback_timer = 3
                        self.keybind_input = None
                elif self.active_field:
                    if event.key == pygame.K_BACKSPACE:
                        self.draft.set_text(self.active_field, self.draft.text(self.active_field)[:-1])
                    elif event.key == pygame.K_RETURN:
                        self.active_field = None
                    elif event.unicode and event.unicode.isprintable():
                        self.draft.set_text(self.active_field, self.draft.text(self.active_field) + event.unicode)
        return None

    def update(self, dt):
        for button in self.buttons:
            button.update()
        self.feedback_timer = max(0, self.feedback_timer - dt)

    def draw(self):
        self.surface.blit(self.background, (0, 0))
        utils.draw_text(self.surface, "Settings", 52, config.SCREEN_WIDTH // 2, 38, config.WHITE, self.font_path, shadow=True)
        for index, field in enumerate(_TEXT_FIELDS):
            rect = self._field_rect(index)
            utils.draw_rounded_rect(self.surface, rect, config.LIGHT_BLUE if self.active_field == field else config.GRAY, 8)
            utils.draw_text(self.surface, f"{field.replace('_', ' ').title()}: {self.draft.text(field)}", 18,
                            rect.left + 8, rect.centery, config.WHITE, self.font_path, "midleft")
        for index, lane in enumerate(("lane_0", "lane_1", "lane_2", "lane_3")):
            rect = pygame.Rect(20 + (index % 2) * 230, 380 + (index // 2) * 48, 210, 36)
            utils.draw_rounded_rect(self.surface, rect, config.LIGHT_BLUE if self.keybind_input == lane else config.GRAY, 8)
            utils.draw_text(self.surface, f"{lane}: {self.draft.keybinds[lane]}", 18, rect.centerx, rect.centery,
                            config.WHITE, self.font_path, "center")
        if self.draft.is_reviewing:
            reviewed = self.draft.review_settings
            lines = ["IMPORT REVIEW", f"Port: {reviewed.serial_port}", f"Baud: {reviewed.baud_rate}",
                     f"FPS: {reviewed.fps}", f"Size: {reviewed.screen_width} x {reviewed.screen_height}",
                     "Press Apply to accept or Cancel to discard"]
            for index, line in enumerate(lines):
                utils.draw_text(self.surface, line, 18, config.SCREEN_WIDTH // 2, 575 + index * 22,
                                config.CYAN, self.font_path, "center")
        if self.feedback_message:
            utils.draw_text(self.surface, self.feedback_message, 17, config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT - 100,
                            config.CYAN, self.font_path, "center", shadow=True)
        for button in self.buttons:
            button.draw(self.surface)
        pygame.display.flip()

    def run(self, clock):
        while True:
            result = self.handle_events()
            if result:
                return result
            self.update(clock.tick(config.FPS) / 1000.0)
            self.draw()
