"""A short ink-stamp entrance that leaves the live fighting lane visible."""
from __future__ import annotations

import math
import pygame

from localization import translate
from paper_renderer import jitter_line


ENTRANCE_DURATION = 2.8
PORTRAIT_DURATION = 1.9
STAMP_SIZE = (660, 132)
PORTRAIT_STAMP_SIZE = (660, 174)
STAMP_TOP = 86
INK = (55, 51, 48)
SEAL = (130, 57, 53)

# These are drawing crops, not collision boxes. Long blade/pencil tips stay
# outside the portrait so a weapon cannot shrink the boss body to a thumbnail.
_BODY_CROPS = {
    "moon_compass": (-62, -176, 124, 180),
    "wanted_sketch": (-44, -125, 88, 132),
    "railroad_stapler": (-97, -115, 185, 120),
    "orbital_mistake": (-99, -136, 198, 140),
    "scissor_director": (-65, -140, 162, 144),
    "final_editor": (-71, -175, 171, 180),
    "baby_face_giant": (-110, -275, 225, 281),
    "cloud_kite": (-43, -82, 86, 116),
    "brass_tumbleweed": (-43, -79, 86, 89),
    "orbit_crab": (-68, -82, 136, 92),
    "carbon_hound": (-62, -76, 124, 86),
    "draft_moth": (-75, -99, 150, 109),
}


class _PortraitCamera:
    """Render-only view of the actual drawing; never touch the live camera."""

    def __init__(self, boss):
        self.x = float(boss.x) - 180
        self.offset_x = 0
        anchor_y = (getattr(boss, "ground_y", boss.y)
                    if getattr(boss, "kind", "") == "baby_face_giant" else boss.y)
        self.offset_y = 300 - anchor_y
        self.screen_width = 480

    def screen_x(self, world_x):
        return round(world_x - self.x)


def _draw_boss_portrait(surface, renderer, boss, slot):
    """Use the live enemy's draw function and current pose, with a body crop."""
    layer = pygame.Surface((480, 340), pygame.SRCALPHA)
    boss.draw(layer, _PortraitCamera(boss), renderer)
    kind = getattr(boss, "kind", "")
    dx, dy, width, height = _BODY_CROPS.get(kind,
        (-max(40, boss.width//2+8), -boss.height-12, boss.width+16, boss.height+20))
    if getattr(boss, "facing", 1) < 0:
        dx = -dx-width
    crop = pygame.Rect(180+dx, 300+dy, width, height).clip(layer.get_rect())
    if not crop.width or not crop.height:
        return
    drawing = layer.subsurface(crop)
    scale = min(slot.width/crop.width, slot.height/crop.height, 1.35)
    size = (max(1, round(crop.width*scale)), max(1, round(crop.height*scale)))
    # Nearest-neighbour sizing keeps the original sharp graphite pixels.
    drawing = pygame.transform.scale(drawing, size)
    surface.blit(drawing, drawing.get_rect(center=slot.center))


def entrance_alpha(elapsed, duration=ENTRANCE_DURATION):
    """The lettering, seal and paper share one entrance/fade envelope."""
    if duration <= 0 or elapsed <= 0 or elapsed >= duration:
        return 0.0
    return max(0.0, min(1.0, elapsed / .22, (duration - elapsed) / .34))


def _seal(surface, kind, center):
    x, y = center
    pygame.draw.circle(surface, SEAL, center, 31, 2)
    pygame.draw.arc(surface, SEAL, (x-34, y-33, 67, 66), -.2, 4.5, 1)
    line = lambda a, b, width=2: jitter_line(surface, SEAL,
        (x+a[0], y+a[1]), (x+b[0], y+b[1]), width, 413, 1, .55)
    if kind == "moon_compass":
        pygame.draw.arc(surface, SEAL, (x-20, y-20, 29, 29), .8, 5.7, 3)
        line((-12, 18), (18, -12), 3)
        line((1, 14), (-5, 8))
    elif kind == "wanted_sketch":
        pygame.draw.lines(surface, SEAL, False,
            [(x-23,y+5),(x-15,y+3),(x-12,y-13),(x+12,y-13),
             (x+16,y+3),(x+24,y+5)], 3)
        line((-14, 3), (15, 3))
        pygame.draw.circle(surface, SEAL, (x, y+17), 4, 2)
    elif kind == "railroad_stapler":
        pygame.draw.lines(surface, SEAL, False,
            [(x-20,y+11),(x-20,y-14),(x+20,y-14),(x+20,y+11)], 4)
        line((-22, 17), (22, 17))
        for wheel in (-12, 12):
            pygame.draw.circle(surface, SEAL, (x+wheel, y+11), 5, 2)
    elif kind == "orbital_mistake":
        pygame.draw.circle(surface, SEAL, center, 9, 2)
        pygame.draw.ellipse(surface, SEAL, (x-24, y-12, 48, 24), 2)
        pygame.draw.circle(surface, SEAL, (x+17, y-8), 4)
        line((-13, 21), (14, -21), 1)
    elif kind == "scissor_director":
        for side in (-1, 1):
            pygame.draw.circle(surface, SEAL, (x+side*12, y+15), 7, 2)
            line((side*8, 9), (-side*17, -21), 3)
        pygame.draw.circle(surface, SEAL, (x, y), 3, 1)
    elif kind == "final_editor":
        line((-18, 19), (17, -17), 5)
        line((-13, 21), (22, -14), 1)
        pygame.draw.lines(surface, SEAL, False,
            [(x-19,y-15),(x-6,y-2),(x+20,y-15)], 3)
        line((-21, 24), (17, 24), 1)
    elif kind == "baby_face_giant":
        pygame.draw.circle(surface, SEAL, (x, y-2), 18, 2)
        for side in (-1, 1):
            pygame.draw.circle(surface, SEAL, (x+side*6, y-6), 2)
        pygame.draw.arc(surface, SEAL, (x-8,y-2,16,10), 0, math.pi, 2)
        line((-20, 24), (-5, 24), 3)
        line((5, 24), (20, 24), 3)
    elif kind == "cloud_kite":
        pygame.draw.lines(surface, SEAL, True,
            [(x,y-24),(x+17,y-3),(x,y+13),(x-17,y-3)], 2)
        line((0, -24), (0, 13), 1)
        line((-17, -3), (17, -3), 1)
        pygame.draw.lines(surface, SEAL, False,
            [(x,y+13),(x-6,y+20),(x+4,y+26)], 2)
    elif kind == "brass_tumbleweed":
        pygame.draw.circle(surface, SEAL, center, 19, 2)
        for index in range(8):
            angle = index*math.pi/4
            line((math.cos(angle)*7, math.sin(angle)*7),
                 (math.cos(angle)*24, math.sin(angle)*24), 2)
        pygame.draw.circle(surface, SEAL, center, 5, 2)
    elif kind == "orbit_crab":
        pygame.draw.ellipse(surface, SEAL, (x-15,y-8,30,22), 2)
        for side in (-1, 1):
            pygame.draw.lines(surface, SEAL, False,
                [(x+side*11,y+5),(x+side*23,y-7),(x+side*15,y-19)], 2)
            line((side*8, 12), (side*17, 22), 2)
        pygame.draw.ellipse(surface, SEAL, (x-24,y-4,48,12), 1)
    elif kind == "carbon_hound":
        pygame.draw.lines(surface, SEAL, True,
            [(x-20,y+10),(x-17,y-6),(x+7,y-8),(x+12,y-21),
             (x+21,y-4),(x+26,y+1),(x+8,y+8)], 2)
        for side in (-1, 1):
            line((side*12, 9), (side*15, 23), 2)
        line((-19, -3), (-27, -14), 2)
    elif kind == "draft_moth":
        for side in (-1, 1):
            pygame.draw.lines(surface, SEAL, True,
                [(x,y-6),(x+side*24,y-22),(x+side*20,y+7),(x+side*8,y+20)], 2)
        line((0, -17), (0, 22), 3)
        line((-7, -25), (0, -17), 1)
        line((7, -25), (0, -17), 1)
    else:
        line((-15, -16), (15, 17), 3)
        line((15, -16), (-15, 17), 3)


def _wrap_rule(text, font, width):
    words = translate(str(text)).split()
    lines, current = [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if current and font.size(candidate)[0] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    # The content authors use one short combat rule. If an extension exceeds
    # two lines, keep the tip inside the stamp instead of covering the fight.
    if len(lines) > 2:
        lines = lines[:2]
        while lines[-1] and font.size(lines[-1] + "…")[0] > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
        lines[-1] += "…"
    return lines


def _reveal_text(surface, font, text, position, color, progress, max_width):
    image = font.render(text, True, color)
    if image.get_width() > max_width:
        # Scale only an unusually long localized title. Rules wrap instead.
        height = max(15, round(image.get_height() * max_width / image.get_width()))
        image = pygame.transform.smoothscale(image, (max_width, height))
    width = round(image.get_width() * max(0.0, min(1.0, progress)))
    if width:
        surface.blit(image, position, pygame.Rect(0, 0, width, image.get_height()))


def _focus_edges(surface, elapsed, alpha):
    # The top corners tighten briefly around the stamp. No full-screen tint,
    # centre vignette or line passes through the 300..640px combat band.
    strength = alpha * max(0.0, 1.0 - max(0.0, elapsed-.45) / 1.05)
    if strength <= 0:
        return
    overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    w = surface.get_width()
    color = (*INK, round(55 * strength))
    for side in (-1, 1):
        x = 8 if side < 0 else w-9
        jitter_line(overlay, color, (x, 5), (x+side*3, 258), 3, 671+side, 1, 2)
        for index in range(5):
            yy = 18 + index*39
            pygame.draw.line(overlay, color, (x, yy), (x-side*12, yy+24), 1)
        pygame.draw.line(overlay, color,
            (x, 7), (x-side*90, 7), 2)
    surface.blit(overlay, (0, 0))


def draw_boss_entrance(surface, renderer, kind, title, rule, elapsed,
                       duration=ENTRANCE_DURATION, boss=None):
    """Draw one localized entrance; caller owns its timer and encounter edge.

    ``elapsed`` counts from the actual boss drawing, never the room's previous
    wave. The helper is stateless and cannot move the camera or lock input.
    Pass the actual ``boss`` for its current drawing in a larger portrait
    slot. The live camera, controls and enemy state are untouched. Old callers
    without that optional argument retain the compact seal and 2.8s timing.
    Secret guardians use the same API as the six mandatory campaign duels.
    Returns the stamp rect when visible, or ``None`` at either silent edge.
    """
    portrait = boss is not None and not getattr(boss, "dead", False)
    visible_duration = min(duration, PORTRAIT_DURATION) if portrait else duration
    alpha = entrance_alpha(elapsed, visible_duration)
    if not alpha:
        return None
    _focus_edges(surface, elapsed, alpha)
    card = pygame.Surface(PORTRAIT_STAMP_SIZE if portrait else STAMP_SIZE, pygame.SRCALPHA)
    card.fill((246, 240, 219, 237))
    bottom = card.get_height()-7
    # A stamped frame and short proof lines suit the existing drawn notebook.
    for start, end, seed in (((4, 5), (654, 7), 921),
                             ((654, 7), (652, bottom), 922),
                             ((652, bottom), (7, bottom+3), 923),
                             ((7, bottom+3), (4, 5), 924)):
        jitter_line(card, SEAL, start, end, 2, seed, 2, 1.2)
    jitter_line(card, (170, 133, 110), (12, 11), (647, 12), 1, 928, 1, .7)
    title_progress = (elapsed-.07)/.43
    text_width = 472 if portrait else 520
    _reveal_text(card, renderer.font, translate(str(title)), (25, 18), INK,
                 title_progress, text_width)
    underline_width = round((454 if portrait else 509) * max(0, min(1, (elapsed-.13)/.43)))
    if underline_width:
        jitter_line(card, SEAL, (25, 53), (25+underline_width, 54),
                    2, 931, 1, .7)
    rule_width = 472 if portrait else 525
    for index, line in enumerate(_wrap_rule(rule, renderer.font_small, rule_width)):
        _reveal_text(card, renderer.font_small, line, (26, 65+index*25),
                     (104, 66, 60), (elapsed-.3-index*.1)/.4, rule_width)
    if portrait:
        _draw_boss_portrait(card, renderer, boss, pygame.Rect(521, 16, 128, 142))
    else:
        seal_clip = card.get_clip()
        progress = max(0, min(1, (elapsed-.18)/.4))
        card.set_clip(pygame.Rect(568, 10, round(80*progress), 112))
        _seal(card, kind, (607, 65))
        card.set_clip(seal_clip)
    # Applying alpha after all ink fixes the old floating opaque-title bug.
    card.set_alpha(round(255*alpha))
    rect = card.get_rect(midtop=(surface.get_width()//2, STAMP_TOP))
    surface.blit(card, rect)
    return rect


__all__ = ["draw_boss_entrance", "entrance_alpha", "ENTRANCE_DURATION", "PORTRAIT_DURATION"]
