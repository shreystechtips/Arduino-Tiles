# Arduino Tiles

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python)
![Pygame](https://img.shields.io/badge/Pygame--CE-2.5.8-orange?logo=pygame)
![Arduino](https://img.shields.io/badge/Arduino-1.8.19-red?logo=arduino)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC_BY--NC_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc/4.0/)
[![made-with-love](https://img.shields.io/badge/Made%20with-❤️-red.svg)](https://shields.io/)

**Arduino Tiles** is a feature-complete clone of *Piano Tiles 2*, a rhythm-based game built using Python with Pygame for the front-end and Arduino for optional hardware input. Players can tap tiles in sync with music using a keyboard, mouse, or four IR proximity sensors connected to an Arduino. The game supports JSON-based song files, dynamic difficulty calculation, and a player-synced audio engine for an immersive experience.

<video src="https://github.com/Aieda1l/Arduino-Tiles/raw/refs/heads/master/media/demo.mp4"></video>

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Hardware Setup](#hardware-setup)
- [Directory Structure](#directory-structure)
- [Contributing](#contributing)
- [License](#license)

## Features
- **Gameplay**: Tap or hold tiles in four lanes to match the rhythm of songs, with support for normal, long, dual, and special tiles.
- **Input Options**: Play using keyboard (keys 1-4), mouse, or IR proximity sensors via Arduino.
- **Song Parsing**: Loads songs from JSON files in `assets/songs/`, with support for multiple difficulty levels (1-3 stars) and seamless level transitions.
- **Dynamic Difficulty**: Calculates song difficulty based on tile types, sequences, and speed (TPS).
- **Audio Engine**: Background accompaniment syncs with player hits, not a fixed timer, for a dynamic music experience.
- **UI**: Polished main menu with a scrollable song list, search bar, difficulty indicators, and song previews.
- **Visuals**: Includes particle effects, rounded rectangles, and gradient-filled long notes for a professional look.

## Installation

### Prerequisites
- **Python 3.13** or later
- **uv** for dependency and virtual-environment management
- **Arduino IDE** (1.8.19 or later) for uploading the Arduino sketch
- **Arduino Board** (e.g., Uno) with 4 IR proximity sensors (e.g., FC-51) for hardware input (optional)

### Steps
1. Clone or download the repository:
   ```bash
   git clone https://github.com/yourusername/arduino-tiles.git
   cd arduino-tiles
   ```
2. Create the project environment and install locked dependencies:
   ```bash
   uv sync
   ```
3. Ensure the `assets/` directory contains:
   - `songs/` with `.json` song files (e.g., `Havana.json`)
   - `snd/` with `.mp3` sound files (e.g., `c1.mp3`, `#a.mp3`)
   - `img/` with images (`background.png`, `circle_light.png`, `crazy_circle.png`, `dot_light.png`)
   - `fonts/` with `Futura condensed.ttf` and `StarThings-DLZx.ttf`
4. For Arduino input:
   - Open `arduino_sketch.ino` in the Arduino IDE.
   - Connect IR sensors to pins 2, 3, 4, and 5 (see [Hardware Setup](#hardware-setup)).
   - Upload the sketch to your Arduino board.

### Building a Standalone Executable
The checked-in `arduino_tiles.spec` bundles the complete `assets/` tree and produces a
windowed PyInstaller onedir application. Install the project dependencies, including
PyInstaller, in the active `uv` environment before building.

Build each release on its target operating system; PyInstaller does not produce a
portable Windows artifact when run on macOS, or a portable macOS artifact when run on
Windows.

On Windows PowerShell, from the repository root:

```powershell
uv run pyinstaller --version
powershell -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

On macOS, from the repository root:

```bash
uv run pyinstaller --version
bash scripts/build_macos.sh
```

The scripts clean only the project-local `build/` and `dist/` directories and invoke
the checked-in spec. The resulting platform-named onedir bundle is under `dist/`.

### GitHub Actions builds

Every push to `main`/`master`, pull request, or manually started workflow runs
native Windows and macOS builds. Open the workflow run in the repository's
Actions tab and download `ArduinoTiles-Windows` or `ArduinoTiles-macOS` from
the Artifacts section. Each artifact is a self-contained onedir application;
extract it before launching.

### Settings and Sharing

Run the application with `uv run python main.py`. Editable settings are stored in the
per-user application-data directory rather than inside the installed or bundled
application. The settings screen can export the portable JSON settings and import a
file into a review draft; values are applied only after confirmation.

## Usage
1. Run the game:
   ```bash
   uv run python main.py
   ```
2. In the main menu:
   - Use the search bar to filter songs.
   - Click a song to select it, or the play button (▶) for a preview.
   - Click the "Play" button to start the selected song.
3. Gameplay controls:
   - **Keyboard**: Press 1, 2, 3, 4 for lanes 1-4.
   - **Mouse**: Click tiles in the lanes.
   - **Arduino**: Tap over IR sensors aligned with the lanes.
   - Press ESC to return to the main menu.
   - Press 'A' to toggle autoplay (for testing).
4. Objective: Tap or hold tiles as they reach the strike line to score points. Earn up to 3 stars per song based on completion.

## Hardware Setup
For Arduino input:
- **Components**:
  - Arduino board (e.g., Uno)
  - 4 IR proximity sensors (e.g., FC-51 or E18-D80NK)
- **Wiring**:
  - Sensor 1 (Lane 1): OUT to pin 2, VCC to 5V, GND to GND
  - Sensor 2 (Lane 2): OUT to pin 3, VCC to 5V, GND to GND
  - Sensor 3 (Lane 3): OUT to pin 4, VCC to 5V, GND to GND
  - Sensor 4 (Lane 4): OUT to pin 5, VCC to 5V, GND to GND
- **Setup**:
  - Position sensors in a row under a surface (e.g., a table) to detect hand taps.
  - Adjust sensor sensitivity (if applicable) to detect proximity reliably.
  - Connect the Arduino to your computer via USB (update `SERIAL_PORT` in `config.py` if not `COM3`).
- Upload the Arduino sketch (`arduino_sketch.ino`) using the Arduino IDE.

## Directory Structure
```
arduino-tiles/
├── assets/
│   ├── songs/              # JSON song files (e.g., Havana.json)
│   ├── snd/                # MP3 sound files (e.g., c1.mp3)
│   ├── img/                # PNG images (background.png, etc.)
│   ├── fonts/              # TTF fonts
├── arduino/
│   ├── arduino_sketch.ino  # Arduino code for IR sensors
├── config.py               # Game constants and settings
├── utils.py                # Helper functions (drawing, buttons)
├── arduino_handler.py      # Arduino serial communication
├── tile.py                 # Tile and particle classes
├── song_parser.py          # JSON song parsing logic
├── game.py                 # Main game loop and logic
├── main_menu.py            # Main menu with song selection
├── main.py                 # Application entry point
├── arduino_tiles.spec      # PyInstaller onedir/windowed build definition
├── scripts/
│   ├── build_windows.ps1   # Windows release build
│   └── build_macos.sh      # macOS release build
├── pyproject.toml          # Project metadata and dependencies
├── uv.lock                 # Locked dependency versions
├── README.md               # This file
└── LICENSE
```

## Contributing
Contributions are welcome! To contribute:
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

Please ensure code follows PEP 8 style guidelines and includes tests where applicable.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
