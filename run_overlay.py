"""Launcher used by start scripts and PyInstaller (absolute import, so it works as a frozen entry point)."""
import sys

from endfield_pos_overlay.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
