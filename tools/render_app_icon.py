"""Build desktop icons from the game's Baby Face signature encounter."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packaging"
SOURCE = ROOT / "store" / "screenshots" / "baby-face-signature.png"
SIZE = 1024


def scene_crop(source: Image.Image) -> Image.Image:
    """Frame the real hero/boss encounter as a square without redrawing it."""
    # Coordinates target the deterministic 1120x700 gameplay capture. The
    # frame retains the hero, moustached Baby Face, ruled paper, and arena
    # line. The crop starts below the scene's long notes so no partial words
    # survive at taskbar size.
    return source.crop((340, 260, 800, 700)).resize(
        (SIZE, SIZE), Image.Resampling.LANCZOS
    ).convert("RGBA")


def render():
    scene = scene_crop(Image.open(SOURCE).convert("RGB"))
    radius = 146
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (28, 28, SIZE - 28, SIZE - 28), radius, fill=255
    )

    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    image.paste(scene, (0, 0), mask)
    draw = ImageDraw.Draw(image)
    # Slightly mismatched outlines preserve the game's imperfect ink language.
    draw.rounded_rectangle(
        (28, 28, SIZE - 28, SIZE - 28), radius,
        outline=(42, 40, 40, 255), width=18,
    )
    draw.rounded_rectangle(
        (39, 35, SIZE - 35, SIZE - 39), radius - 8,
        outline=(77, 73, 69, 210), width=4,
    )

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
