"""Create the TURN THE PAGE application icon for desktop release bundles."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "packaging"
SIZE = 1024


def font(size: int):
    candidates = (
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def render():
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    ink = (43, 43, 49, 255)
    paper = (246, 238, 207, 255)
    edge = (128, 112, 78, 255)
    rule = (176, 207, 217, 255)
    red = (185, 91, 86, 255)

    draw.rounded_rectangle((54, 52, 970, 974), radius=150, fill=ink)
    draw.rounded_rectangle((92, 84, 932, 934), radius=112, fill=paper,
                           outline=edge, width=7)
    for y in range(245, 890, 85):
        draw.line((118, y, 908, y), fill=rule, width=4)
    draw.line((224, 105, 224, 895), fill=(198, 123, 116, 255), width=5)
    draw.polygon(((797, 85), (932, 218), (797, 218)), fill=(229, 219, 183, 255),
                 outline=edge)
    draw.line((797, 85, 797, 218, 932, 218), fill=edge, width=5)

    title_font = font(84)
    for text, y in (("TURN THE", 115), ("PAGE", 202)):
        box = draw.textbbox((0, 0), text, font=title_font)
        x = (SIZE - (box[2] - box[0])) // 2 + 45
        draw.text((x, y), text, font=title_font, fill=ink)

    # Stick figure and katana remain readable even at taskbar size.
    draw.ellipse((420, 385, 542, 507), outline=ink, width=17)
    draw.line((481, 507, 475, 674), fill=ink, width=18)
    draw.line((476, 550, 371, 610), fill=ink, width=17)
    draw.line((371, 610, 304, 548), fill=ink, width=17)
    draw.line((480, 550, 594, 610), fill=ink, width=17)
    draw.line((594, 610, 653, 522), fill=ink, width=17)
    draw.line((475, 674, 364, 835), fill=ink, width=19)
    draw.line((475, 674, 593, 820), fill=ink, width=19)
    draw.line((658, 527, 826, 329), fill=ink, width=17)
    draw.line((665, 516, 833, 324), fill=(210, 151, 61, 255), width=8)
    draw.line((638, 496, 697, 546), fill=red, width=15)
    draw.line((352, 421, 380, 444, 421, 432, 535, 434), fill=red, width=14)
    draw.line((278, 860, 766, 856), fill=edge, width=5)

    OUT.mkdir(parents=True, exist_ok=True)
    png = OUT / "app-icon.png"
    image.save(png)
    image.save(OUT / "app-icon.ico", sizes=[(16, 16), (32, 32), (48, 48),
                                             (64, 64), (128, 128), (256, 256)])
    image.save(OUT / "app-icon.icns", sizes=[(16, 16), (32, 32), (64, 64),
                                              (128, 128), (256, 256),
                                              (512, 512), (1024, 1024)])


if __name__ == "__main__":
    render()
