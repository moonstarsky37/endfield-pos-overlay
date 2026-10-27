#!/bin/sh
# macOS: double-click to start the overlay from source. Needs python3 with tkinter
# (python.org installer includes it; Homebrew: brew install python-tk).
cd "$(dirname "$0")" || exit 1
exec python3 run_overlay.py "$@"
