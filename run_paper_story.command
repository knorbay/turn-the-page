#!/bin/zsh

# Double-click launcher for macOS.  It deliberately does not install anything
# behind the player's back; missing requirements get one clear command instead.
cd -- "${0:A:h}" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Paper Story needs Python 3.10 or newer."
    echo "Install Python, then open this launcher again."
    read -r "?Press Return to close..."
    exit 1
fi

if ! python3 -c "import pygame" >/dev/null 2>&1; then
    echo "Pygame is missing. In Terminal, run:"
    echo
    echo "  cd \"$PWD\""
    echo "  python3 -m pip install -r requirements.txt"
    echo
    read -r "?Press Return to close..."
    exit 1
fi

exec python3 main.py
