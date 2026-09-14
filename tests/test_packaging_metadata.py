from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_pyinstaller_spec_bundles_assets_as_onedir_windowed_application():
    spec = (ROOT / "arduino_tiles.spec").read_text(encoding="utf-8")

    assert "datas" in spec
    assert "assets" in spec
    assert "Analysis(" in spec
    assert "EXE(" in spec
    assert "COLLECT(" in spec
    assert "console=False" in spec
    assert "name=" in spec
    assert "SPECPATH" in spec


def test_windows_build_script_cleans_local_outputs_and_uses_checked_in_spec():
    script = (ROOT / "scripts" / "build_windows.ps1").read_text(encoding="utf-8")

    assert "arduino_tiles.spec" in script
    assert "pyinstaller" in script.lower()
    assert "build" in script
    assert "dist" in script
    assert "--onedir" not in script


def test_macos_build_script_cleans_local_outputs_and_uses_checked_in_spec():
    script = (ROOT / "scripts" / "build_macos.sh").read_text(encoding="utf-8")

    assert "arduino_tiles.spec" in script
    assert "pyinstaller" in script.lower()
    assert "build" in script
    assert "dist" in script
    assert "--onedir" not in script


def test_readme_documents_uv_and_target_os_packaging_requirements():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "uv sync" in readme
    assert "uv run" in readme
    assert "build_windows.ps1" in readme
    assert "build_macos.sh" in readme
    assert "Windows" in readme
    assert "macOS" in readme
    assert "target operating system" in readme
