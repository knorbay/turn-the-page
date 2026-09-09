"""Lost drawings that teach persistent, optional combat techniques.

The save's existing secret IDs are the only source of truth. Deriving every
modifier afresh makes old collections work immediately and prevents retries,
page changes or repeated pickups from stacking a reward.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import pygame


@dataclass(frozen=True)
class Sketch:
    secret_id: str
    page: int
    title: str
    technique: str
    benefit: str
    detail: str
    icon: str
    attribute: str
    value: float
    weapons: tuple[str, ...] = ()


SKETCHES = (
    Sketch("old_first_figure", 0, "THE FIRST FIGURE", "SECOND THOUGHT",
           "Jump a little later after leaving an edge.",
           "+0.06 seconds of edge-jump grace.", "figure", "sketch_coyote_bonus", .06),
    Sketch("practice_monster", 0, "PRACTICE MONSTER", "FOLLOW THROUGH",
           "Your blade finisher reaches farther.",
           "+12 reach on the third blade strike.", "monster", "sketch_finisher_reach", 12,
           ("pencil_blade",)),
    Sketch("shrine_roof", 0, "THE KITE RONIN", "PAPER KITE",
           "Change direction faster in the air.",
           "+20% air control; jump height stays the same.", "kite", "sketch_air_control", 1.20),
    Sketch("beyond_red", 1, "THE MARGIN HOUSE", "QUICK DRAW",
           "Reload your sidearm faster.",
           "Sidearm reloads take 15% less time.", "house", "sketch_pistol_reload", .85,
           ("ink_pistol",)),
    Sketch("coffee_secret", 1, "COFFEE UMBRELLA", "TIGHT FOLD",
           "Your scattergun keeps a tighter spread.",
           "18% narrower pellet spread.", "umbrella", "sketch_shotgun_spread", .82,
           ("marker_shotgun",)),
    Sketch("margin_battle_note", 1, "THE VICTORY POSE", "MAKE SOME ROOM",
           "Scattergun hits push enemies farther.",
           "+20% scattergun knockback.", "victory", "sketch_shotgun_knockback", 1.20,
           ("marker_shotgun",)),
    Sketch("water_tower", 1, "THE UNUSED TICKET", "THROUGH TICKET",
           "Sidearm shots pass through one enemy.",
           "One extra target per sidearm bullet.", "ticket", "sketch_pistol_pierce", 1,
           ("ink_pistol",)),
    Sketch("bad_draft", 2, "THE APOLOGETIC BEAST", "ELASTIC MEMORY",
           "Ricochet shots bounce one more time.",
           "One extra rebound for Orbit Pulse / Rubber Band.", "beast", "sketch_rubber_bounces", 1,
           ("rubber_band",)),
    Sketch("eraser_survivor_sketch", 2, "THE ERASER SURVIVOR", "CLEAN SLATE",
           "Reload your heavy cannon faster.",
           "Null / Eraser Cannon reloads take 15% less time.", "patchwork", "sketch_eraser_reload", .85,
           ("eraser_cannon",)),
    Sketch("orbit_observatory", 2, "THE SECOND MOON", "LOW ORBIT",
           "Ricochet shots stay in flight longer.",
           "+25% Orbit Pulse / Rubber Band projectile lifetime.", "moon", "sketch_rubber_lifetime", 1.25,
           ("rubber_band",)),
    Sketch("agent_badge", 3, "THE FORGED BADGE", "FAST INK",
           "Sidearm bullets reach their target faster.",
           "+20% sidearm projectile speed.", "badge", "sketch_pistol_velocity", 1.20,
           ("ink_pistol",)),
    Sketch("last_homework", 4, "THE LAST HOMEWORK", "REVISION RHYTHM",
           "Your dash becomes ready sooner.",
           "Dash recovery is 0.10 seconds shorter.", "homework", "sketch_dash_recovery", .10),
)

SKETCH_BY_ID = {sketch.secret_id: sketch for sketch in SKETCHES}
PAGE_NAMES = ("THE RONIN", "HIGH NOON", "LOW ORBIT", "THE AGENT", "THE LAST DRAFT")
_ADDITIVE = {"sketch_coyote_bonus", "sketch_finisher_reach", "sketch_pistol_pierce",
             "sketch_rubber_bounces", "sketch_dash_recovery"}


def sketch_for(secret_id):
    return SKETCH_BY_ID.get(secret_id)


def derive_modifiers(discovered):
    """Return a complete baseline plus owned techniques; unknown IDs are inert."""
    owned = set(discovered or ())
    return {sketch.attribute: (sketch.value if sketch.secret_id in owned else
                              0 if sketch.attribute in _ADDITIVE else 1)
            for sketch in SKETCHES}


def apply_sketch_rewards(player, discovered):
    modifiers = derive_modifiers(discovered)
    for attribute, value in modifiers.items():
        setattr(player, attribute, value)
    return modifiers


def sketch_active(sketch, available_weapons=()):
    """Movement techniques always work; weapon techniques follow page tools."""
    return not sketch.weapons or bool(set(sketch.weapons).intersection(available_weapons))


def collection_message(secret_id):
    sketch = sketch_for(secret_id)
    return (f"TECHNIQUE LEARNED: {sketch.technique} — {sketch.benefit}"
            if sketch else "LOST SKETCH — clipped into the back pages.")


def draw_sketch_icon(surface, icon, center, size=42, color=(70, 66, 60), accent=(154, 64, 61)):
    """Twelve little authored drawings, shared by pickups and the back cover."""
    cx, cy = center
    scale = size / 48
    def p(x, y):
        return round(cx+x*scale), round(cy+y*scale)
    def line(points, ink=color, width=2, closed=False):
        pygame.draw.lines(surface, ink, closed, [p(x,y) for x,y in points],
                          max(1, round(width*scale)))
    def circle(x, y, radius, ink=color, width=2):
        pygame.draw.circle(surface, ink, p(x,y), max(1,round(radius*scale)),
                           max(1,round(width*scale)))
    def rect(x, y, w, h, ink=color, width=2):
        pygame.draw.rect(surface, ink, (*p(x,y), round(w*scale), round(h*scale)),
                         max(1,round(width*scale)))
    if icon in ("figure", "victory"):
        circle(0,-14,6);line([(0,-8),(-1,8),(-11,21)])
        line([(-1,8),(11,20)])
        line([(-15,-1),(0,-4),(13,4)] if icon == "figure" else
             [(-15,-18),(-7,-3),(0,-4),(10,-18)],accent)
        if icon == "figure":
            line([(-18,23),(-4,23)]);line([(6,23),(22,23)])
            line([(-17,-20),(-9,-24),(-3,-21)],accent,1)
        else:
            line([(13,-17),(21,-25)],accent);circle(-18,-22,2,accent,1)
    elif icon in ("monster", "beast"):
        line([(-19,15),(-19,-2),(-12,-12),(-18,-22),(-5,-14),
              (8,-14),(18,-24),(16,-7),(23,4),(17,18),(-19,15)],closed=True)
        circle(-5,-4,3);circle(9,-4,3)
        line([(-7,8),(1,11),(10,7)] if icon == "beast" else
             [(-8,7),(-3,3),(1,8),(6,3),(12,7)],accent,1)
        if icon == "beast":
            line([(23,-18),(28,-23),(24,-26)],accent,1)
    elif icon == "kite":
        line([(0,-23),(18,-5),(0,14),(-18,-5)],closed=True)
        line([(0,-23),(0,14)],accent,1);line([(-18,-5),(18,-5)],accent,1)
        line([(0,14),(6,20),(1,26),(11,29)],accent,1)
        line([(-5,20),(7,25),(-5,25),(6,20)],width=1)
    elif icon == "house":
        line([(-23,-2),(0,-23),(24,-2)],accent)
        line([(-17,-6),(-17,21),(18,21),(18,-6)])
        rect(-11,2,9,8);line([(5,21),(5,7),(13,7),(13,21)])
        line([(-25,24),(-6,24)],accent,1);line([(17,-13),(17,-23),(23,-23),(23,-8)],width=1)
    elif icon == "umbrella":
        pts=[(math.cos(math.pi+i*math.pi/12)*24,math.sin(math.pi+i*math.pi/12)*19-1)
             for i in range(13)]
        line(pts,accent);line([(-24,-1),(-12,-5),(0,-1),(12,-5),(24,-1)],accent,1)
        line([(0,-22),(0,17),(5,22),(11,20),(12,14)])
        for x in (-16,15):line([(x,12),(x-3,17)],accent,1)
    elif icon == "ticket":
        line([(-26,-15),(21,-15),(26,-10),(21,-5),(26,0),(21,5),(26,10),
              (21,15),(-26,15),(-21,9),(-26,3),(-21,-4),(-26,-9)],closed=True)
        for y in range(-11,13,6):line([(10,y),(10,y+2)],accent,1)
        line([(-17,0),(5,0)],accent);line([(0,-5),(5,0),(0,5)],accent)
    elif icon == "patchwork":
        rect(-18,-19,33,37);line([(-18,-3),(15,-3)],accent)
        line([(-1,-19),(-1,18)],accent)
        for y in (-13,7):line([(-6,y),(4,y+3)],width=1)
        circle(-9,-10,3);line([(5,-10),(10,-10)],width=1)
        line([(-9,9),(1,12),(10,6)]);line([(-22,21),(-14,19)],accent,1)
    elif icon == "moon":
        circle(0,0,20);circle(11,-6,5,accent,1);circle(-3,10,4,accent,1)
        ellipse=pygame.Rect(*p(-28,-8),round(56*scale),round(17*scale))
        pygame.draw.ellipse(surface,accent,ellipse,max(1,round(scale)))
        circle(-26,0,3,accent,1)
        line([(-8,-12),(-5,-15),(-1,-12)],width=1)
    elif icon == "badge":
        line([(-8,-20),(-7,-27),(7,-27),(8,-20)],accent)
        rect(-21,-20,42,43);circle(-9,-7,6);line([(-17,12),(-14,2),(-5,2),(0,13)])
        line([(-14,-7),(-4,-7)],accent)
        for y in (-10,-2,6):line([(5,y),(15,y)],width=1)
        line([(5,15),(11,20),(20,9)],accent)
    else:
        line([(-19,-25),(10,-25),(21,-14),(21,24),(-19,24)],closed=True)
        line([(10,-25),(10,-14),(21,-14)],accent,1)
        for y in (-10,-3,4):line([(-12,y),(6,y)],width=1)
        line([(-10,14),(-3,19),(13,6)],accent,3)


def wrap_text(text, font, width):
    lines = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def draw_sketch_card(surface, rect, sketch, renderer, discovered=True, available_weapons=()):
    """Compact back-page card. Use rectangles at least 315 by 100 pixels."""
    ink = (65, 62, 56) if discovered else (151, 145, 128)
    accent = (138, 65, 59) if discovered else (169, 160, 139)
    pygame.draw.rect(surface, (242, 235, 210) if discovered else (232, 226, 210), rect)
    renderer.rough_rect(surface, ink, rect, 1, 2500+sketch.page*91+len(sketch.secret_id))
    draw_sketch_icon(surface, sketch.icon, (rect.x+30,rect.y+33), 36, ink, accent)
    font = renderer.font_small
    label = sketch.technique if discovered else "UNDISCOVERED SKETCH"
    surface.blit(font.render(label,True,ink),(rect.x+56,rect.y+9))
    if discovered:
        status = "ACTIVE" if sketch_active(sketch,available_weapons) else "SAVED / NEEDS ITS WEAPON"
        surface.blit(font.render(status,True,accent),(rect.x+56,rect.y+31))
        for index,line in enumerate(wrap_text(sketch.benefit,font,rect.width-24)):
            surface.blit(font.render(line,True,ink),(rect.x+12,rect.y+58+index*19))
    else:
        surface.blit(font.render(PAGE_NAMES[sketch.page],True,accent),(rect.x+56,rect.y+31))
        surface.blit(font.render("A rejected drawing. A useful idea.",True,ink),(rect.x+12,rect.y+65))
