"""Build desktop icon formats from the TURN THE PAGE brand emblem."""
from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packaging"
SOURCE = OUT / "brand-emblem.png"
SIZE = 1024
MARK_SIZE = 944


def render():
    source = Image.open(SOURCE).convert("RGBA")
    alpha_box = source.getchannel("A").getbbox()
    if not alpha_box:
        raise ValueError(f"Brand emblem has no visible pixels: {SOURCE}")
    source = source.crop(alpha_box)
    source.thumbnail((MARK_SIZE, MARK_SIZE), Image.Resampling.LANCZOS)

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    position = ((SIZE - source.width) // 2, (SIZE - source.height) // 2)
    image.alpha_composite(source, position)

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
