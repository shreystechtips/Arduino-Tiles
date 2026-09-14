import pygame
import config
import utils
from game import GameScreen
from title_screen import TitleScreen
from main_menu import MainMenuScreen
from settings_screen import SettingsScreen
from loading_screen import LoadingScreen
from arduino_handler import ArduinoHandler
from settings import Settings, default_settings, load_settings, save_settings

class GameApp:
    def __init__(self):
        pygame.init()
        self.settings = self._load_settings()
        config.apply_settings(self.settings)
        self.screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        pygame.display.set_caption(config.GAME_NAME)
        self.clock = pygame.time.Clock()
        self.arduino = ArduinoHandler(self.settings.serial_port, self.settings.baud_rate)
        self.state = 'loading'
        self._recreate_screens(include_menu=False)

    @staticmethod
    def _load_settings():
        try:
            return load_settings()
        except (OSError, ValueError) as exc:
            print(f"Could not load settings; using defaults: {exc}")
            return default_settings()

    def _recreate_screens(self, include_menu):
        self.loading_screen = LoadingScreen(self.screen)
        self.title_screen = TitleScreen(self.screen)
        self.menu_screen = MainMenuScreen(self.screen) if include_menu else None
        self.game_screen = GameScreen(self.screen, self.arduino)
        self.settings_screen = SettingsScreen(self.screen, self.arduino, self.settings)

    def apply_settings(self, settings):
        """Apply and persist accepted settings across live runtime consumers."""
        if not isinstance(settings, Settings):
            raise TypeError("settings must be a Settings instance")

        serial_changed = (
            settings.serial_port != self.settings.serial_port
            or settings.baud_rate != self.settings.baud_rate
        )
        size_changed = (
            settings.screen_width != self.settings.screen_width
            or settings.screen_height != self.settings.screen_height
        )
        had_menu = self.menu_screen is not None

        config.apply_settings(settings)
        self.settings = settings

        if serial_changed:
            old_arduino = self.arduino
            self.arduino = ArduinoHandler(settings.serial_port, settings.baud_rate)
            old_arduino.close()

        if size_changed:
            self.screen = pygame.display.set_mode((settings.screen_width, settings.screen_height))
            self._recreate_screens(include_menu=had_menu)
        else:
            if serial_changed:
                self.game_screen.update_arduino_handler(self.arduino)
                self.settings_screen.arduino_handler = self.arduino
            self.game_screen.update_keybinds(config.KEYBINDS)
            if hasattr(self.settings_screen, "draft"):
                self.settings_screen.accepted_settings = settings
                self.settings_screen.draft.reset(settings)

        try:
            save_settings(settings)
        except (OSError, ValueError) as exc:
            print(f"Could not save settings: {exc}")

    def run(self):
        """Main application loop."""
        running = True
        while running:
            if self.state == 'loading':
                result = self.loading_screen.run(self.clock)
                if result:
                    if result['action'] == 'quit':
                        running = False
                    elif result['action'] == 'go_to_menu':
                        self.menu_screen = result['menu_screen']
                        self.state = 'title'
            elif self.state == 'title':
                result = self.title_screen.run(self.clock)
                if result:
                    if result['action'] == 'quit':
                        running = False
                    elif result['action'] == 'go_to_menu':
                        self.state = 'menu'
                    elif result['action'] == 'go_to_settings':
                        self.state = 'settings'
            elif self.state == 'menu':
                result = self.menu_screen.run(self.clock)
                if result:
                    if result['action'] == 'quit':
                        running = False
                    elif result['action'] == 'back':
                        self.state = 'title'
                    elif result['action'] == 'play_song':
                        self.game_screen.load_song(result['filename'])
                        self.state = 'game'
            elif self.state == 'game':
                self.game_screen.run(self.clock)
                self.state = 'menu'
            elif self.state == 'settings':
                result = self.settings_screen.run(self.clock)
                if result:
                    if result['action'] == 'quit':
                        running = False
                    elif result['action'] == 'apply':
                        self.apply_settings(result['settings'])
                        self.state = 'title'
                    elif result['action'] == 'back':
                        # Update GameScreen with new ArduinoHandler and keybinds
                        self.arduino = result.get('arduino_handler', self.arduino)
                        self.game_screen.update_arduino_handler(self.arduino)
                        self.game_screen.update_keybinds(result.get('keybinds', config.KEYBINDS))
                        self.state = 'title'

        self.arduino.close()
        pygame.quit()

if __name__ == '__main__':
    import platform
    import asyncio

    async def main():
        app = GameApp()
        app.run()

    if platform.system() == "Emscripten":
        asyncio.ensure_future(main())
    else:
        asyncio.run(main())
