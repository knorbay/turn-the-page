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
    extra_effects: tuple[tuple[str, float], ...] = ()


SKETCHES = (
    Sketch("old_first_figure", 0, "THE FIRST FIGURE", "SECOND THOUGHT",
           "Jump a little later after leaving an edge.",
           "+0.08 seconds of edge-jump grace.", "figure", "sketch_coyote_bonus", .08),
    Sketch("practice_monster", 0, "PRACTICE MONSTER", "FOLLOW THROUGH",
           "Your blade finisher reaches farther.",
           "+18 reach on the third blade strike.", "monster", "sketch_finisher_reach", 18,
           ("pencil_blade",)),
    Sketch("shrine_roof", 0, "THE KITE RONIN", "PAPER KITE",
           "Change direction faster in the air.",
           "+30% air control; jump height stays the same.", "kite", "sketch_air_control", 1.30),
    Sketch("beyond_red", 1, "THE MARGIN HOUSE", "QUICK DRAW",
           "Reload your sidearm faster.",
           "Sidearm reloads take 22% less time.", "house", "sketch_pistol_reload", .78,
           ("ink_pistol",)),
    Sketch("coffee_secret", 1, "COFFEE UMBRELLA", "TIGHT FOLD",
           "Your scattergun keeps a tighter spread.",
           "25% narrower pellet spread.", "umbrella", "sketch_shotgun_spread", .75,
           ("marker_shotgun",)),
    Sketch("margin_battle_note", 1, "THE VICTORY POSE", "MAKE SOME ROOM",
           "Scattergun hits push enemies farther.",
           "+35% scattergun knockback.", "victory", "sketch_shotgun_knockback", 1.35,
           ("marker_shotgun",)),
    Sketch("water_tower", 1, "THE UNUSED TICKET", "THROUGH TICKET",
           "Sidearm shots pass through one enemy.",
           "One extra target per sidearm bullet.", "ticket", "sketch_pistol_pierce", 1,
           ("ink_pistol",)),
    Sketch("bad_draft", 2, "THE APOLOGETIC BEAST", "ELASTIC MEMORY",
           "Ricochet shots bounce twice more.",
           "Two extra rebounds for Orbit Pulse / Rubber Band.", "beast", "sketch_rubber_bounces", 2,
           ("rubber_band",)),
    Sketch("eraser_survivor_sketch", 2, "THE ERASER SURVIVOR", "CLEAN SLATE",
           "Reload your heavy cannon faster.",
           "Null / Eraser Cannon reloads take 22% less time.", "patchwork", "sketch_eraser_reload", .78,
           ("eraser_cannon",)),
    Sketch("orbit_observatory", 2, "THE SECOND MOON", "LOW ORBIT",
           "Ricochet shots stay in flight longer.",
           "+40% Orbit Pulse / Rubber Band projectile lifetime.", "moon", "sketch_rubber_lifetime", 1.40,
           ("rubber_band",)),
    Sketch("agent_badge", 3, "THE FORGED BADGE", "FAST INK",
           "Sidearm bullets reach their target faster.",
           "+30% sidearm projectile speed.", "badge", "sketch_pistol_velocity", 1.30,
           ("ink_pistol",)),
    Sketch("last_homework", 4, "THE LAST HOMEWORK", "REVISION RHYTHM",
           "Your dash becomes ready sooner.",
           "Dash recovery is 0.14 seconds shorter.", "homework", "sketch_dash_recovery", .14),
    Sketch("cloud_heart", 0, "THE CLOUD HEART", "SKYWARD RUNE",
           "Air +35%; dash -0.08s; edge grace +0.04s.",
           "Permanent movement rune. Stacks with Paper Kite, Second Thought and Revision Rhythm.",
           "cloud", "sketch_air_control", 1.35, (),
           (("sketch_dash_recovery", .08), ("sketch_coyote_bonus", .04))),
    Sketch("fold_bastion", 1, "THE FOLDED BASTION", "BASTION RUNE",
           "Knockback +30%; spread -10%; cannon reload -10%.",
           "Permanent weapon rune. Works with Scattergun and Null / Eraser Cannon across pages.",
           "shield", "sketch_shotgun_knockback", 1.30,
           ("marker_shotgun", "eraser_cannon"),
           (("sketch_shotgun_spread", .90), ("sketch_eraser_reload", .90))),
    Sketch("carbon_echo", 3, "THE CARBON ORIGINAL", "ECHO RUNE",
           "Sidearm: speed +25%; pierce +1; reload -10%.",
           "Permanent sidearm rune. Its piercing stacks with Through Ticket; its speed stacks with Fast Ink.",
           "echo", "sketch_pistol_velocity", 1.25, ("ink_pistol",),
           (("sketch_pistol_pierce", 1), ("sketch_pistol_reload", .90))),
    Sketch("brass_spur", 1, "THE BRASS SPUR", "SPUR RUNE",
           "Your dash becomes ready a little sooner.",
           "Dash recovery is 0.06 seconds shorter.", "spur", "sketch_dash_recovery", .06),
    Sketch("orbit_shell", 2, "THE ORBIT SHELL", "SHELL RUNE",
           "Ricochet shots stay in flight a little longer.",
           "+20% Orbit Pulse / Rubber Band projectile lifetime.", "shell", "sketch_rubber_lifetime", 1.20,
           ("rubber_band",)),
    Sketch("carbon_fang", 3, "THE CARBON FANG", "FANG RUNE",
           "Reload your sidearm a little faster.",
           "Sidearm reloads take 10% less time.", "fang", "sketch_pistol_reload", .90,
           ("ink_pistol",)),
    Sketch("draft_wing", 4, "THE DRAFT WING", "WING RUNE",
           "Your blade finisher reaches a little farther.",
           "+12 reach on the third blade strike.", "wing", "sketch_finisher_reach", 12,
           ("pencil_blade",)),
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
    attributes = {attribute for sketch in SKETCHES
                  for attribute, _ in ((sketch.attribute, sketch.value), *sketch.extra_effects)}
    result = {attribute: 0 if attribute in _ADDITIVE else 1
              for attribute in attributes}
    for sketch in SKETCHES:
        if sketch.secret_id not in owned:
            continue
        for attribute, value in ((sketch.attribute, sketch.value), *sketch.extra_effects):
            if attribute in _ADDITIVE:
                result[attribute] += value
            else:
                result[attribute] *= value
    return result


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
    return (f"TECHNIQUE LEARNED: {sketch.technique} — {sketch.benefit if sketch.extra_effects else sketch.detail}"
            if sketch else "LOST SKETCH — clipped into the back pages.")


def draw_sketch_icon(surface, icon, center, size=42, color=(70, 66, 60), accent=(154, 64, 61)):
    """Authored drawings shared by pickups and the back cover."""
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
    elif icon == "cloud":
        line([(-25,5),(-24,-5),(-16,-12),(-7,-10),(-4,-21),(6,-24),
              (17,-15),(18,-5),(27,-2),(29,8),(20,14),(-16,14),(-25,5)], closed=True)
        line([(-11,22),(0,32),(11,22)], accent)
        line([(0,16),(0,31)], accent)
    elif icon == "shield":
        line([(-22,-19),(0,-27),(23,-19),(18,8),(0,26),(-18,8)], closed=True)
        line([(0,-25),(0,25)], accent, 1)
        line([(-14,-7),(-2,8),(15,-11)], accent, 3)
    elif icon == "echo":
        for shift, ink in ((-9,accent),(0,color),(9,accent)):
            line([(-15+shift,-22),(12+shift,-22),(18+shift,-13),
                  (18+shift,22),(-15+shift,22),(-15+shift,-22)], ink, 1)
        line([(-7,-4),(2,5),(14,-9)], color, 3)
    elif icon == "spur":
        line([(-20,-21),(-7,-21),(-8,6),(4,6),(10,12),(-22,12)], closed=True)
        line([(-7,-15),(9,-12),(17,-4)], accent)
        circle(16,8,9,accent)
        for i in range(8):
            a = i*math.tau/8
            line([(16+math.cos(a)*4,8+math.sin(a)*4),
                  (16+math.cos(a)*13,8+math.sin(a)*13)],accent,1)
    elif icon == "shell":
        line([(-24,11),(-23,-3),(-15,-17),(0,-23),(15,-17),(23,-3),(24,11)],closed=True)
        for x in (-15,-7,7,15):line([(0,-20),(x,10)],accent,1)
        line([(-23,11),(-9,15),(0,10),(9,15),(23,11)])
        circle(-22,23,3,accent,1);line([(-15,22),(24,18)],accent,1)
    elif icon == "fang":
        line([(-18,-23),(8,-20),(20,-9),(9,1),(3,22),(-3,27),(-7,8),(-18,-3)],closed=True)
        line([(-18,-23),(-4,-6),(9,1)],accent,1)
        line([(-4,-6),(-3,27)],accent,1)
        line([(-24,16),(-18,10),(-13,13)],accent)
    elif icon == "wing":
        line([(0,-13),(-18,-25),(-26,-16),(-21,6),(-9,15),(0,-2),
              (9,15),(21,6),(26,-16),(18,-25),(0,-13)],closed=True)
        line([(0,-15),(0,24)],accent)
        for side in (-1,1):
            line([(0,-2),(side*22,-13)],accent,1)
            line([(0,3),(side*16,9)],accent,1)
            line([(0,-15),(side*7,-26)],accent,1)
    else:
        line([(-19,-25),(10,-25),(21,-14),(21,24),(-19,24)],closed=True)
        line([(10,-25),(10,-14),(21,-14)],accent,1)
        for y in (-10,-3,4):line([(-12,y),(6,y)],width=1)
        line([(-10,14),(-3,19),(13,6)],accent,3)


def wrap_text(text, font, width):
    from localization import translate
    text = translate(text)
    # The text has already been translated. Measure it once, without
    # reinterpreting a line fragment as another localization key.
    raw = getattr(font, "raw", font)
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and raw.size(candidate)[0] > width:
            lines.append(line)
            line = ""
        while raw.size(word)[0] > width and len(word) > 1:
            split = 1
            while split < len(word) and raw.size(word[:split+1])[0] <= width:
                split += 1
            lines.append(word[:split])
            word = word[split:]
        line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def _card_label(font, value, color, width):
    image = font.render(value, True, color)
    if image.get_width() > width:
        image = pygame.transform.smoothscale(image, (width,
            max(1, round(image.get_height() * width / image.get_width()))))
    return image


def draw_sketch_card(surface, rect, sketch, renderer, discovered=True, available_weapons=()):
    """Compact back-page card. Use rectangles at least 315 by 100 pixels."""
    ink = (65, 62, 56) if discovered else (151, 145, 128)
    accent = (138, 65, 59) if discovered else (169, 160, 139)
    pygame.draw.rect(surface, (242, 235, 210) if discovered else (232, 226, 210), rect)
    renderer.rough_rect(surface, ink, rect, 1, 2500+sketch.page*91+len(sketch.secret_id))
    draw_sketch_icon(surface, sketch.icon, (rect.x+30,rect.y+33), 36, ink, accent)
    font = renderer.font_small
    label = sketch.technique if discovered else "UNDISCOVERED SKETCH"
    surface.blit(_card_label(font,label,ink,rect.width-68),(rect.x+56,rect.y+9))
    if discovered:
        status = "ACTIVE" if sketch_active(sketch,available_weapons) else "NEEDS ITS WEAPON"
        surface.blit(_card_label(font,status,accent,rect.width-68),(rect.x+56,rect.y+31))
        detail = sketch.benefit if sketch.extra_effects else sketch.detail
        body_font = font
        lines = wrap_text(detail, body_font, rect.width-24)
        max_rows = max(1, (rect.height-62)//19)
        if len(lines) > max_rows:
            from localization import LocalizedFont
            for size in range(20, 13, -1):
                body_font = LocalizedFont(pygame.font.Font(None, size))
                lines = wrap_text(detail, body_font, rect.width-24)
                if len(lines) <= max_rows:
                    break
        for index,line in enumerate(lines):
            surface.blit(getattr(body_font,"raw",body_font).render(line,True,ink),(rect.x+12,rect.y+58+index*19))
    else:
        surface.blit(_card_label(font,PAGE_NAMES[sketch.page],accent,rect.width-68),(rect.x+56,rect.y+31))
