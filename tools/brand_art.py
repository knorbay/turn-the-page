"""Store artwork built from TURN THE PAGE's real runtime drawings."""
from __future__ import annotations

import math
import os
from pathlib import Path
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from advanced_enemies import BabyFaceGiant
from player import Player
from scripted_events import ArtistDirector, ArtistTool


INK = (38, 38, 43)
RED = (153, 48, 45)
PAPER = (246, 239, 213)
BLUE = (176, 207, 217)


class StillCamera:
    offset_y = 0

    @staticmethod
    def screen_x(value):
        return round(value)


def _pil(surface: pygame.Surface) -> Image.Image:
    return Image.frombytes("RGBA", surface.get_size(),
                           pygame.image.tobytes(surface, "RGBA"))


def _trim(image: Image.Image, pad=5) -> Image.Image:
    box = image.getchannel("A").getbbox()
    if not box:
        return image
    return image.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                       min(image.width, box[2] + pad),
                       min(image.height, box[3] + pad)))


def baby_sprite() -> Image.Image:
    surface = pygame.Surface((360, 330), pygame.SRCALPHA)
    boss = BabyFaceGiant(178, 318, 4307)
    boss.state = "idle"
    boss.dead = False
    boss.empowered = True
    boss.moustache_progress = 1
    boss.facing = -1
    boss.draw(surface, StillCamera(), None)
    return _trim(_pil(surface))


def hero_sprite() -> Image.Image:
    surface = pygame.Surface((145, 130), pygame.SRCALPHA)
    player = Player(52, 64)
    player.facing = 1
    player.on_ground = True
    player.vx = 58
    player.anim_time = .42
    player.page_style = "astronaut"
    player.current_weapon = "excalibur"
    player.aim_angle = -.38
    player.draw(surface, StillCamera())
    return _trim(_pil(surface))


def artist_sprite() -> Image.Image:
    surface = pygame.Surface((570, 400), pygame.SRCALPHA)
    director = ArtistDirector()
    director.tool = ArtistTool("pencil", 85, 330, True, -.58, 1.0)
    director.draw(surface, StillCamera(), None)
    return _trim(_pil(surface), 2)


def _font(size, condensed=False):
    candidates = (
        Path("/System/Library/Fonts/Avenir Next Condensed.ttc") if condensed else
        Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _crop_fit(image: Image.Image, size, focus=(.5, .5)) -> Image.Image:
    ratio = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * ratio), round(image.height * ratio)),
                           Image.Resampling.LANCZOS)
    left = round((resized.width - size[0]) * focus[0])
    top = round((resized.height - size[1]) * focus[1])
    return resized.crop((left, top, left + size[0], top + size[1]))


def _contain(image: Image.Image, size, resample=Image.Resampling.LANCZOS) -> Image.Image:
    """Fit an actor inside a box, including intentional poster-size upscaling."""
    ratio = min(size[0] / image.width, size[1] / image.height)
    return image.resize((max(1, round(image.width * ratio)),
                         max(1, round(image.height * ratio))), resample)


def _paper_scrap(source: Image.Image, size, angle, focus, seed) -> Image.Image:
    image = _crop_fit(source, size, focus).convert("RGBA")
    mask = Image.new("L", size, 0)
    points = []
    rng = random.Random(seed)
    step = max(18, size[0] // 18)
    for x in range(0, size[0] + step, step):
        points.append((min(x, size[0]), rng.randrange(1, 8)))
    for y in range(step, size[1] + step, step):
        points.append((size[0] - rng.randrange(1, 8), min(y, size[1])))
    for x in range(size[0] - step, -step, -step):
        points.append((max(x, 0), size[1] - rng.randrange(1, 8)))
    for y in range(size[1] - step, 0, -step):
        points.append((rng.randrange(1, 8), y))
    ImageDraw.Draw(mask).polygon(points, fill=255)
    image.putalpha(mask)
    # A faint paper wash turns busy gameplay into supporting texture while
    # keeping the handwritten notes and distinct page themes recognizable.
    wash = Image.new("RGBA", image.size, PAPER + (42,))
    wash.putalpha(Image.eval(mask, lambda value: round(value * .24)))
    image = Image.alpha_composite(image, wash)
    return image.rotate(angle, Image.Resampling.BICUBIC, expand=True)


def _shadowed_paste(canvas, layer, pos, shadow=13):
    alpha = layer.getchannel("A")
    shade = Image.new("RGBA", layer.size, (0, 0, 0, 150))
    shade.putalpha(alpha.filter(ImageFilter.GaussianBlur(shadow)))
    canvas.alpha_composite(shade, (pos[0] + 8, pos[1] + 12))
    canvas.alpha_composite(layer, pos)


def render_key_art(size) -> Image.Image:
    """Compose store key art from screenshots and runtime actor renderers."""
    pygame.init()
    width, height = size
    scale = height / 500
    canvas = Image.new("RGBA", size, (29, 28, 31, 255))
    draw = ImageDraw.Draw(canvas)

    # Graphite scuffs keep the dark desk from reading as a flat UI panel.
    rng = random.Random(923)
    for _ in range(46):
        x = rng.randrange(width)
        y = rng.randrange(height)
        length = rng.randrange(round(18 * scale), round(90 * scale))
        draw.line((x, y, min(width, x + length), y + rng.randrange(-3, 4)),
                  fill=(59, 56, 59, 120), width=max(1, round(scale)))

    ronin = Image.open(ROOT / "store" / "screenshots" / "page-1.png").convert("RGB")
    western = Image.open(ROOT / "store" / "screenshots" / "page-2.png").convert("RGB")
    space = Image.open(ROOT / "store" / "screenshots" / "baby-face-signature.png").convert("RGB")

    left = _paper_scrap(ronin, (round(width * .48), round(height * .63)),
                        -7, (.34, .58), 41)
    right = _paper_scrap(western, (round(width * .44), round(height * .57)),
                         7, (.63, .58), 57)
    center = _paper_scrap(space, (round(width * .70), round(height * .77)),
                          -1.5, (.54, .54), 79)
    _shadowed_paste(canvas, left, (-round(width * .09), round(height * .24)))
    _shadowed_paste(canvas, right, (round(width * .67), round(height * .20)))
    _shadowed_paste(canvas, center, (round(width * .28), round(height * .17)))

    # Cover the screenshot actors with larger copies drawn by the real runtime.
    boss = _contain(baby_sprite(), (round(width * .34), round(height * .67)))
    bx, by = round(width * .57), round(height * .27)
    canvas.alpha_composite(boss, (bx, by))

    hero = _contain(hero_sprite(), (round(width * .25), round(height * .31)))
    hx, hy = round(width * .36), round(height * .62)
    canvas.alpha_composite(hero, (hx, hy))

    # The Artist enters from outside the key art and points at the encounter.
    hand = artist_sprite()
    hand.thumbnail((round(width * .48), round(height * .47)), Image.Resampling.LANCZOS)
    canvas.alpha_composite(hand, (width - hand.width + round(width * .05),
                                  -round(height * .10)))

    draw = ImageDraw.Draw(canvas)
    # Excalibur's impossible finishing arc ties the small hero to the giant.
    arc = (round(width * .32), round(height * .38),
           round(width * .77), round(height * .90))
    draw.arc(arc, 207, 331, fill=(231, 211, 130, 230),
             width=max(4, round(8 * scale)))
    draw.arc((arc[0] - 5, arc[1] + 4, arc[2] - 8, arc[3] + 8),
             207, 331, fill=(153, 48, 45, 225),
             width=max(2, round(3 * scale)))

    # A solid title block gives thumbnail legibility while preserving the
    # deliberately messy pages and runtime drawings beneath it.
    tx, ty = round(width * .035), round(height * .035)
    tw, th = round(width * .48), round(height * .27)
    draw.rectangle((tx + 7, ty + 8, tx + tw + 7, ty + th + 8), fill=(0, 0, 0, 180))
    draw.rectangle((tx, ty, tx + tw, ty + th), fill=(246, 239, 213, 255),
                   outline=INK + (255,), width=max(2, round(3 * scale)))
    top_font = _font(round(height * .074), True)
    page_font = _font(round(height * .142), True)
    draw.text((tx + round(15 * scale), ty + round(7 * scale)), "TURN THE",
              font=top_font, fill=INK + (255,))
    draw.text((tx + round(12 * scale), ty + round(38 * scale)), "PAGE",
              font=page_font, fill=INK + (255,))
    underline = ty + th - round(15 * scale)
    draw.line((tx + round(14 * scale), underline,
               tx + tw - round(13 * scale), underline - round(4 * scale)),
              fill=RED + (255,), width=max(3, round(6 * scale)))

    label_font = _font(round(height * .034), True)
    label = "THE ARTIST DRAWS.  YOU FIGHT BACK."
    label_box = draw.textbbox((0, 0), label, font=label_font)
    lx = round(width * .04)
    ly = height - round(height * .075)
    pad = round(8 * scale)
    draw.rectangle((lx - pad, ly - pad,
                    lx + label_box[2] + pad, ly + label_box[3] + pad),
                   fill=(29, 28, 31, 225))
    draw.text((lx, ly), label, font=label_font, fill=(246, 239, 213, 255))
    pygame.quit()
    return canvas.convert("RGB")


def render_icon(size=1024) -> Image.Image:
    """Create a readable app icon from the same real actor drawings."""
    pygame.init()
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    plate = Image.new("RGBA", (size, size), PAPER + (255,))
    draw = ImageDraw.Draw(plate)
    for y in range(round(size * .17), size, round(size * .14)):
        draw.line((0, y, size, y), fill=BLUE + (255,), width=max(2, size // 250))
    draw.line((round(size * .12), 0, round(size * .12), size),
              fill=(201, 103, 103, 255), width=max(3, size // 170))

    boss = _contain(baby_sprite(), (round(size * .69), round(size * .70)))
    _shadowed_paste(plate, boss, (round(size * .29), round(size * .14)), size // 80)
    hero = _contain(hero_sprite(), (round(size * .33), round(size * .34)))
    _shadowed_paste(plate, hero, (round(size * .055), round(size * .61)), size // 95)

    draw = ImageDraw.Draw(plate)
    draw.arc((round(size * .04), round(size * .20), round(size * .80), round(size * .93)),
             209, 334, fill=(232, 208, 110, 255), width=max(8, size // 58))
    draw.arc((round(size * .03), round(size * .22), round(size * .78), round(size * .95)),
             209, 334, fill=RED + (255,), width=max(3, size // 170))

    radius = round(size * .16)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((24, 24, size - 24, size - 24),
                                           radius, fill=255)
    canvas.paste(plate, (0, 0), mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, size - 24, size - 24), radius,
                           outline=(34, 33, 36, 255), width=max(8, size // 55))
    # Folded corner: a page is always about to turn.
    corner = [(round(size * .78), 25), (size - 24, round(size * .23)),
              (round(size * .78), round(size * .23))]
    draw.polygon(corner, fill=(222, 216, 193, 255))
    draw.line(corner + [corner[0]], fill=(65, 61, 60, 255), width=max(3, size // 150))
    pygame.quit()
    return canvas
