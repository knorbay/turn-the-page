"""Store artwork built from TURN THE PAGE's real runtime drawings."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFilter, ImageFont

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


def hero_sprite() -> Image.Image:
    """Draw the protagonist's runtime silhouette as a crisp large mark."""
    image = Image.new("RGBA", (900, 900), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    ink = INK + (255,)
    light_ink = (63, 61, 63, 255)
    red = RED + (255,)
    paper = PAPER + (255,)

    # Pencil Blade, using the same wood, graphite, eraser, and red binding
    # language as the in-game weapon. It sits behind the gripping hand.
    blade = [(470, 385), (823, 666), (789, 718), (436, 438)]
    draw.polygon(blade, fill=(216, 185, 92, 255))
    draw.line(blade + [blade[0]], fill=ink, width=22, joint="curve")
    draw.line((490, 414, 798, 661), fill=(246, 219, 126, 255), width=13)
    draw.polygon([(823, 666), (872, 748), (789, 718)], fill=ink)
    draw.line([(823, 666), (872, 748), (789, 718)], fill=ink, width=11, joint="curve")
    draw.polygon([(435, 357), (484, 397), (445, 449), (395, 409)],
                 fill=(213, 151, 144, 255))
    draw.line([(435, 357), (484, 397), (445, 449), (395, 409), (435, 357)],
              fill=ink, width=17, joint="curve")
    for shift in (0, 24, 48):
        draw.line((408 + shift, 391 + shift, 449 + shift, 367 + shift),
                  fill=red, width=11)

    # The same circle-head, single face tick, and stick anatomy used in play.
    draw.ellipse((225, 65, 435, 275), fill=paper, outline=ink, width=27)
    draw.ellipse((230, 69, 432, 272), outline=light_ink, width=5)
    draw.line((345, 170, 394, 170), fill=ink, width=13)
    draw.line((330, 276, 343, 573), fill=ink, width=31)
    draw.line((337, 557, 202, 807), fill=ink, width=31)
    draw.line((337, 557, 493, 816), fill=ink, width=31)
    draw.line((330, 321, 210, 462, 143, 402), fill=ink, width=24, joint="curve")
    draw.line((332, 324, 421, 413, 454, 409), fill=ink, width=24, joint="curve")
    draw.ellipse((430, 386, 475, 431), fill=paper, outline=ink, width=11)
    # A few doubled strokes retain the handmade wobble at full resolution.
    draw.line((346, 286, 352, 555), fill=light_ink, width=5)
    draw.line((347, 567, 486, 807), fill=light_ink, width=5)
    return _trim(image, 12)


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


def _contain(image: Image.Image, size, resample=Image.Resampling.LANCZOS) -> Image.Image:
    """Fit an actor inside a box, including intentional poster-size upscaling."""
    ratio = min(size[0] / image.width, size[1] / image.height)
    return image.resize((max(1, round(image.width * ratio)),
                         max(1, round(image.height * ratio))), resample)


def _shadowed_paste(canvas, layer, pos, shadow=13):
    alpha = layer.getchannel("A")
    shade = Image.new("RGBA", layer.size, (0, 0, 0, 150))
    shade.putalpha(alpha.filter(ImageFilter.GaussianBlur(shadow)))
    canvas.alpha_composite(shade, (pos[0] + 8, pos[1] + 12))
    canvas.alpha_composite(layer, pos)


def render_key_art(size) -> Image.Image:
    """Compose clean key art around the game's actual stickman protagonist."""
    pygame.init()
    width, height = size
    scale = height / 500
    canvas = Image.new("RGBA", size, (29, 28, 31, 255))
    draw = ImageDraw.Draw(canvas)

    # One clean sheet makes the protagonist readable at storefront size.
    inset = round(18 * scale)
    sheet = Image.new("RGBA", (width - inset * 2, height - inset * 2), PAPER + (255,))
    sheet_draw = ImageDraw.Draw(sheet)
    rule_width = max(1, round(2 * scale))
    for y in range(round(height * .18), sheet.height, round(height * .13)):
        sheet_draw.line((0, y, sheet.width, y), fill=BLUE + (190,), width=rule_width)
    margin_x = round(sheet.width * .11)
    sheet_draw.line((margin_x, 0, margin_x, sheet.height),
                    fill=(201, 103, 103, 230), width=max(2, round(3 * scale)))
    # Slightly uneven lower edge keeps this a physical page, not a UI card.
    mask = Image.new("L", sheet.size, 0)
    ImageDraw.Draw(mask).polygon([
        (0, 0), (sheet.width, 0), (sheet.width, sheet.height - round(8 * scale)),
        (round(sheet.width * .82), sheet.height - round(3 * scale)),
        (round(sheet.width * .63), sheet.height - round(10 * scale)),
        (round(sheet.width * .43), sheet.height - round(4 * scale)),
        (round(sheet.width * .22), sheet.height - round(11 * scale)), (0, sheet.height)
    ], fill=255)
    sheet.putalpha(mask)
    _shadowed_paste(canvas, sheet, (inset, inset), max(5, round(10 * scale)))

    # The real runtime stickman is the undisputed subject of the cover.
    hero = _contain(hero_sprite(), (round(width * .43), round(height * .57)))
    hx = round(width * .53)
    hy = round(height * .34)
    _shadowed_paste(canvas, hero, (hx, hy), max(4, round(7 * scale)))

    # The Artist enters from beyond the page, aimed at the character it made.
    hand = artist_sprite()
    hand = _contain(hand, (round(width * .37), round(height * .34)))
    canvas.alpha_composite(hand, (width - hand.width + round(width * .035),
                                  -round(height * .045)))

    draw = ImageDraw.Draw(canvas)
    # One hand-drawn action stroke gives motion without adding another subject.
    arc = (round(width * .46), round(height * .29),
           round(width * .95), round(height * .91))
    draw.arc(arc, 197, 329, fill=(231, 204, 96, 245),
             width=max(4, round(8 * scale)))
    draw.arc((arc[0] - round(4 * scale), arc[1] + round(5 * scale),
              arc[2] - round(7 * scale), arc[3] + round(8 * scale)),
             197, 329, fill=RED + (245,), width=max(2, round(3 * scale)))

    tx, ty = round(width * .065), round(height * .08)
    top_font = _font(round(height * .073), True)
    page_font = _font(round(height * .178), True)
    draw.text((tx, ty), "TURN THE",
              font=top_font, fill=INK + (255,))
    draw.text((tx - round(3 * scale), ty + round(34 * scale)), "PAGE",
              font=page_font, fill=INK + (255,))
    underline = ty + round(124 * scale)
    draw.line((tx, underline, tx + round(width * .36), underline - round(3 * scale)),
              fill=RED + (255,), width=max(3, round(6 * scale)))

    label_font = _font(round(height * .034), True)
    lx = round(width * .066)
    ly = height - round(height * .15)
    draw.text((lx, ly), "THE ARTIST DRAWS.", font=label_font, fill=INK + (255,))
    draw.text((lx, ly + round(21 * scale)), "YOU FIGHT BACK.",
              font=label_font, fill=RED + (255,))
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

    hero = _contain(hero_sprite(), (round(size * .76), round(size * .67)))
    _shadowed_paste(plate, hero, (round(size * .13), round(size * .28)), size // 75)

    draw = ImageDraw.Draw(plate)
    draw.arc((round(size * .10), round(size * .16), round(size * .91), round(size * .91)),
             201, 333, fill=(232, 208, 110, 255), width=max(8, size // 58))
    draw.arc((round(size * .08), round(size * .19), round(size * .89), round(size * .94)),
             201, 333, fill=RED + (255,), width=max(3, size // 170))

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
