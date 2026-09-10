"""Build desktop icons from the game's real runtime drawings."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "tools"))

from brand_art import render_icon

OUT = ROOT / "packaging"
SIZE = 1024


def render():
    image = render_icon(SIZE)

    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "app-icon.png"
    image.save(png, optimize=True)
    image.save(
        OUT / "app-icon.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
               (128, 128), (256, 256)],
    )
    image.save(
        OUT / "app-icon.icns",
        sizes=[(16, 16), (32, 32), (64, 64), (128, 128), (256, 256),
               (512, 512), (1024, 1024)],
    )


if __name__ == "__main__":
    render()
