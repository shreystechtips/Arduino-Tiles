import os
import pygame
import sys

from settings import Settings

def resource_path(relative_path):
    """Return an absolute resource path for source and PyInstaller runs."""
    root = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, relative_path)

# Screen dimensions
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800
ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
LIGHT_BLUE = (173, 216, 230)
GRAY = (128, 128, 128)
PERFECT_COLOR = (0, 255, 0)
GREAT_COLOR = (255, 255, 0)
GOOD_COLOR = (255, 165, 0)
MISS_COLOR = (255, 0, 0)

# Game settings
GAME_NAME = "Arduino Tiles"
FPS = 60
STRIKE_LINE_Y = SCREEN_HEIGHT - 200
TILE_WIDTH = SCREEN_WIDTH // 4
BEATS_AHEAD = 4

# Paths
ASSETS_DIR = resource_path('assets')
SONGS_DIR = os.path.join(ASSETS_DIR, "songs")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "snd")
FONTS_DIR = os.path.join(ASSETS_DIR, "fonts")
IMAGES_DIR = os.path.join(ASSETS_DIR, "img")

FONT_PATH = os.path.join(FONTS_DIR, "Futura condensed.ttf")
SYMBOL_FONT_PATH = os.path.join(FONTS_DIR, "Segoe UI Symbol.ttf")

BACKGROUND_IMG = os.path.join(IMAGES_DIR, "background.png")
CIRCLE_LIGHT_IMG = os.path.join(IMAGES_DIR, "circle_light.png")
CRAZY_CIRCLE_IMG = os.path.join(IMAGES_DIR, "crazy_circle.png")
DOT_LIGHT_IMG = os.path.join(IMAGES_DIR, "dot_light.png")

# Arduino settings
SERIAL_PORT = "COM4"  # Default, can be changed in settings
BAUD_RATE = 9600

# Keybinds (default, can be changed in settings)
KEYBINDS = {
    pygame.K_d: 0,  # Lane 0
    pygame.K_f: 1,  # Lane 1
    pygame.K_j: 2,  # Lane 2
    pygame.K_k: 3   # Lane 3
}


def apply_settings(settings: Settings):
    """Update legacy module-level consumers from a validated Settings value."""
    global SERIAL_PORT, BAUD_RATE, FPS, SCREEN_WIDTH, SCREEN_HEIGHT
    global ASPECT_RATIO, STRIKE_LINE_Y, TILE_WIDTH, KEYBINDS

    if not isinstance(settings, Settings):
        raise TypeError("settings must be a Settings instance")
    SERIAL_PORT = settings.serial_port
    BAUD_RATE = settings.baud_rate
    FPS = settings.fps
    SCREEN_WIDTH = settings.screen_width
    SCREEN_HEIGHT = settings.screen_height
    ASPECT_RATIO = SCREEN_WIDTH / SCREEN_HEIGHT
    STRIKE_LINE_Y = SCREEN_HEIGHT - 200
    TILE_WIDTH = SCREEN_WIDTH // 4
    KEYBINDS = {
        ord(key.lower()): int(lane.rsplit("_", 1)[1])
        for lane, key in settings.keybinds.items()
    }


def current_settings() -> Settings:
    """Return the current legacy values as a typed Settings value."""
    keybinds = {
        f"lane_{lane}": pygame.key.name(key)
        for key, lane in KEYBINDS.items()
    }
    return Settings(SERIAL_PORT, BAUD_RATE, keybinds, FPS, SCREEN_WIDTH, SCREEN_HEIGHT)

# Tile properties
BEAT_MAP = {
    'H': 8, 'I': 4, 'J': 2, 'K': 1, 'L': 0.5, 'M': 0.25,
    'N': 0.125, 'O': 0.0625, 'P': 0.03125
}

SPACE_MAP = {
    'Q': 8, 'R': 4, 'S': 2, 'T': 1, 'U': 0.5, 'V': 0.25,
    'W': 0.125, 'X': 0.0625, 'Y': 0.03125
}

# Scoring
PERFECT_TIMING = 0.1
GREAT_TIMING = 0.15
GOOD_TIMING = 0.2
HOLD_POINTS_PER_BEAT = 10
COMBO_MULTIPLIER = 1.1
