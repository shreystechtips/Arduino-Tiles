#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJECT_ROOT/build"
DIST_DIR="$PROJECT_ROOT/dist"
SPEC_FILE="$PROJECT_ROOT/arduino_tiles.spec"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is not installed. Install uv before building the macOS bundle." >&2
    exit 1
fi

rm -rf "$BUILD_DIR" "$DIST_DIR"
cd "$PROJECT_ROOT"
uv run pyinstaller --noconfirm --clean "$SPEC_FILE"

echo "macOS onedir bundle created under $DIST_DIR."
