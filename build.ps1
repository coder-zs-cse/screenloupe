# build.ps1 — produce a standalone ScreenLoupe.exe that needs no Python.
# Run from the project root (the folder containing pyproject.toml):
#   powershell -ExecutionPolicy Bypass -File build.ps1

py -m pip install --upgrade pip pyinstaller

# --onefile   : single self-contained .exe (bundles the Python interpreter)
# --windowed  : no console window (subsystem = GUI) for both daemon and panel
# tkinter is picked up automatically by PyInstaller's hooks.
py -m PyInstaller --noconfirm --onefile --windowed --name ScreenLoupe `
    --version-file=version.txt app.py 2>$null
if (-not (Test-Path dist\ScreenLoupe.exe)) {
    # version.txt is optional; retry without it.
    py -m PyInstaller --noconfirm --onefile --windowed --name ScreenLoupe app.py
}

Write-Host ""
Write-Host "Built: dist\ScreenLoupe.exe"
Write-Host "Run 'dist\ScreenLoupe.exe' for the background magnifier,"
Write-Host "or  'dist\ScreenLoupe.exe --settings' for the settings panel."
