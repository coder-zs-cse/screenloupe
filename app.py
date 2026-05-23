"""PyInstaller entry point. Build with:
    pyinstaller --noconfirm --onefile --windowed --name ScreenLoupe app.py
"""
from screenloupe.cli import main

if __name__ == "__main__":
    main()
