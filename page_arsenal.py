"""Page-specific tool identities, handling, and resolution-independent drawings.

Save files continue to store the original six weapon IDs. A page changes the
physical drawing and its handling; collecting that drawing still owns unlocks.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import pygame


@dataclass(frozen=True)
class ToolProfile:
    label: str
    silhouette: str
    role: str
    mag_size: int = -1
    reload_time: float = 0.0
    fire_delay: float = .34
    speed: float = 0.0
    gravity: float = 0.0
    damage: float = 1.0
    reach_scale: float = 1.0
    tempo: float = 1.0
    spread: float = 0.0
    pellets: int = 1
    lifetime: float = 1.55
    knockback: float = 105.0
    recoil: float = 0.0
    bounces: int = 0
    pierce: int = 0
    erase_radius: int = 0
    accent: tuple = (136, 65, 57)


ORIGINAL = {
    "chalk_bomb": ToolProfile("CHALK CAPSULE", "chalk_bomb",
                              "lob two capsules · small paper burst", 2, 1.95, .78,
                              440, 760, .85, lifetime=1.7, knockback=115,
                              accent=(124, 112, 89)),
    "carbon_lance": ToolProfile("CARBON RIFLE", "carbon_rifle",
                               "one round · pierces a line · long reload", 1, 1.8, 1.0,
                               1120, 0, 1.8, pierce=3, recoil=145),
    "folded_shuriken": ToolProfile("RETURNING FOLD", "fold_star",
                                  "one fold at a time · catch the return line", fire_delay=.85),
    "margin_maul": ToolProfile("OVERSIZED PENCIL", "pencil_maul",
                               "wind up · crush · erase shots in reach", fire_delay=1.05),
    "pencil_blade": ToolProfile("PENCIL BLADE", "pencil", "three strokes · heavy finish"),
    "ink_pistol": ToolProfile("INK PISTOL", "ink_pistol", "steady ink fire", 9, 1.22, .30,
                             650, 35, 1.0),
    "marker_shotgun": ToolProfile("MARKER SHOTGUN", "marker", "close-range ink burst", 4, 1.72, 1.04,
                                 505, 95, .62, spread=28, pellets=7, lifetime=.55, knockback=145, recoil=112),
    "eraser_cannon": ToolProfile("ERASER CANNON", "eraser", "erase incoming fire", 2, 2.35, 1.38,
                                385, 130, 2.35, lifetime=2.15, knockback=335, recoil=175,
                                pierce=1, erase_radius=21),
    "rubber_band": ToolProfile("RUBBER BAND", "rubber", "two ricochets · hold to fire", fire_delay=.78,
                              speed=540, gravity=65, damage=.8, lifetime=3.4, knockback=125, bounces=2),
    "excalibur": ToolProfile("THE VERY DRAMATIC SWORD", "excalibur", "KING ARTHUR · subtlety unavailable",
                            fire_delay=.84),
}

PAGE_TOOLS = {
    0: {
        "pencil_blade": ToolProfile("INK KATANA", "katana", "draw dash · return step · rising launch",
                                   fire_delay=.32, reach_scale=1.18, tempo=1.0, accent=(155, 56, 54)),
    },
    1: {
        "chalk_bomb": ToolProfile("CHALK CAPSULE", "chalk_bomb",
                                  "arc over cover · two gentle bursts", 2, 1.95, .78,
                                  440, 760, .85, accent=(142, 91, 57)),
        "pencil_blade": ToolProfile("BOWIE KNIFE", "bowie", "stay close · mark twice · cash out",
                                   fire_delay=.27, reach_scale=.88, tempo=.88, damage=1.0, accent=(142, 91, 57)),
        "ink_pistol": ToolProfile("SIX-SHOOTER", "revolver", "six heavy shots · deliberate rhythm",
                                 6, 1.56, .42, 820, 0, 1.20, lifetime=1.15, knockback=145, recoil=18),
        "marker_shotgun": ToolProfile("DOUBLE BARREL", "double_barrel", "two quick blasts · wide spread",
                                     2, 1.66, .60, 590, 50, .50, spread=36, pellets=9, lifetime=.47,
                                     knockback=190, recoil=150, accent=(142, 91, 57)),
    },
    2: {
        "chalk_bomb": ToolProfile("METEOR CHALK", "chalk_bomb",
                                  "arc around shields · small impact cloud", 2, 1.95, .78,
                                  440, 760, .85, accent=(63, 111, 139)),
        "pencil_blade": ToolProfile("ION EDGE", "ion_blade", "third cut fires a piercing wave",
                                   fire_delay=.31, reach_scale=1.22, tempo=.96, accent=(63, 111, 139)),
        "rubber_band": ToolProfile("ORBIT PULSE", "pulse", "three ricochets · bank off ink",
                                   fire_delay=.64, speed=720, gravity=0, damage=.9, lifetime=2.7,
                                   knockback=145, bounces=3, accent=(63, 111, 139)),
        "eraser_cannon": ToolProfile("NULL CANNON", "null_cannon", "cut through volleys · straight flight",
                                     2, 2.12, 1.28, 535, 0, 2.35, lifetime=1.8, knockback=280,
                                     recoil=120, pierce=2, erase_radius=31, accent=(63, 111, 139)),
    },
    3: {
        "pencil_blade": ToolProfile("FIELD KNIFE", "field_knife", "rapid chain · execute wounded targets",
                                   fire_delay=.18, reach_scale=.82, tempo=.80, damage=.95,
                                   accent=(76, 104, 92)),
        "ink_pistol": ToolProfile("SUPPRESSED PISTOL", "suppressed", "quick, precise fire · light recoil",
                                 8, 1.32, .29, 960, 0, .85, lifetime=.95, knockback=75,
                                 accent=(76, 104, 92)),
        "marker_shotgun": ToolProfile("BREACH SHOTGUN", "breach", "tight grouping · controlled shove",
                                     3, 1.85, .90, 720, 25, .65, spread=13, pellets=5, lifetime=.49,
                                     knockback=175, recoil=85, accent=(76, 104, 92)),
    },
    4: {
        "pencil_blade": ToolProfile("REDRAW PENCIL", "redraw_pencil",
                                   "every stroke returns as a delayed trace",
                                   fire_delay=.34, reach_scale=1.04, tempo=.94,
                                   damage=.90, accent=(165, 60, 63)),
    },
}


def profile_for(page_index, weapon_id):
    return PAGE_TOOLS.get(page_index, {}).get(weapon_id, ORIGINAL.get(weapon_id, ORIGINAL["pencil_blade"]))


def label_for(page_index, weapon_id):
    return profile_for(page_index, weapon_id).label


def draw_weapon(surface, weapon_id, page_index, grip, angle=0.0, scale=1.0, ink=None):
    """Draw a held tool about its grip. The local barrel/blade points right.

    The same authored geometry is used by the player, pickup, and inventory.
    This keeps a collected silhouette recognizable once it is in the hand.
    """
    profile = profile_for(page_index, weapon_id)
    shape = profile.silhouette
    dark = ink or (49, 48, 49)
    light = (123, 116, 104)
    paper = (242, 232, 206)
    accent = profile.accent
    c, s = math.cos(angle), math.sin(angle)
    # Aiming to the left mirrors a firearm; it must not put its grip above
    # the barrel. Blades retain their full rotation through a cut.
    flip_y = -1 if c < 0 and weapon_id not in ("pencil_blade","excalibur") else 1
    def pt(x, y):
        y *= flip_y
        return round(grip[0] + (x*c-y*s)*scale), round(grip[1] + (x*s+y*c)*scale)
    def line(points, color=dark, width=2):
        from paper_renderer import jitter_line
        for i in range(len(points)-1):
            jitter_line(surface,color,pt(*points[i]),pt(*points[i+1]),
                        max(1,round(width*scale)),419+i,2,.9*scale)
    def poly(points, fill=paper, outline=dark, width=1):
        points = [pt(*p) for p in points]
        if fill is not None:
            pygame.draw.polygon(surface, fill, points)
        if outline is not None:
            pygame.draw.lines(surface, outline, True, points, max(1, round(width*scale)))
    def circle(x, y, radius, color=dark, width=1):
        pygame.draw.circle(surface, color, pt(x,y), max(1,round(radius*scale)),
                           min(max(1,round(radius*scale)), max(1,round(width*scale))) if width else 0)

    if shape == "carbon_rifle":
        # A long, braced drafting rifle, not another pistol-sized rectangle.
        poly([(-33,-11),(-15,-11),(-7,-3),(-7,5),(-25,12),(-34,7)], (149,137,117))
        poly([(-20,-8),(30,-8),(35,-5),(67,-5),(70,-2),(67,1),(31,1),(18,7),(-20,7)],
             (78,82,78))
        poly([(27,-13),(37,-13),(42,-8),(27,-8)], paper)
        line([(-17,-4),(26,-4),(67,-2)], (221,211,189), 2)
        line([(41,-6),(41,3),(47,3),(47,-6)], accent, 2)
        poly([(2,6),(17,6),(10,22),(1,20)], (112,105,91))
        for x in (19,23,27): line([(x,2),(x+2,7)], paper, 1)
        return
    if shape == "fold_star":
        points=[(0,-22),(5,-6),(23,0),(6,5),(0,22),(-5,6),(-22,0),(-6,-5)]
        poly(points, paper, dark, 2)
        for x,y in ((0,-22),(23,0),(0,22),(-22,0)):
            line([(0,0),(x,y)], accent, 1)
        circle(0,0,3,dark)
        return
    if shape == "chalk_bomb":
        # Broken chalk is contained in a squat hand-labelled paper capsule.
        poly([(-13,-10),(-9,-15),(9,-15),(14,-9),(14,8),(9,14),(-9,14),(-14,8)], paper, dark, 2)
        poly([(-5,-15),(6,-15),(6,-22),(-5,-22)], (204,180,139))
        line([(-10,-4),(10,-4)], accent, 3)
        line([(-8,1),(7,1)], accent, 2)
        for x,y in ((-7,7),(1,6),(8,8)): circle(x,y,2,light,1)
        return
    if shape == "pencil_maul":
        poly([(-16,-5),(72,-5),(93,0),(72,6),(-16,6)], (208,189,129))
        line([(-12,-2),(71,-2)],dark,2)
        line([(-12,3),(71,3)],accent,1)
        poly([(72,-5),(93,0),(72,6)],(178,151,112))
        poly([(84,-2),(93,0),(84,3)],dark)
        poly([(-22,-6),(-12,-6),(-12,7),(-22,7)],(180,117,111))
        for x in range(-5,65,7):line([(x,-5),(x+4,5)],light,1)
        return

    if shape in ("katana", "bowie", "field_knife", "ion_blade", "pencil",
                 "redraw_pencil", "excalibur"):
        length = {"katana":47,"bowie":27,"field_knife":24,"ion_blade":43,
                  "pencil":40,"redraw_pencil":44,"excalibur":67}[shape]
        if shape in ("pencil", "redraw_pencil"):
            poly([(-12,-3),(length-8,-3),(length,0),(length-8,3),(-12,3)], (204,174,93))
            line([(-8,0),(length-8,0)], light, 1)
            poly([(length-8,-3),(length,0),(length-8,3)], dark)
            poly([(-12,-3),(-8,-3),(-8,3),(-12,3)], (185,130,116))
            if shape == "redraw_pencil":
                # The final-page tool is visibly corrected over the original:
                # a red second lead and registration ticks preview its echo hit.
                line([(-7,2),(length-8,2)], accent, 2)
                poly([(length-8,0),(length,2),(length-8,4)], accent, accent)
                for x in (5,17,29):
                    line([(x,-5),(x,-2)], accent, 1)
        else:
            poly([(-12,-3),(3,-3),(3,3),(-12,3)], dark, dark)
            for x in (-9,-5,-1):
                line([(x,-3),(x+3,3)], accent, 1)
            if shape == "katana":
                poly([(5,-2),(30,-3),(43,-8),(length,-11),(length-2,-5),
                      (31,2),(5,3)], (230,226,208))
                line([(9,0),(29,-1),(44,-7)], (119,112,101),1)
                line([(3,-9),(5,9)], accent,3)
                line([(0,-7),(3,-7)], paper,1)
            elif shape == "bowie":
                poly([(4,-5),(length-10,-5),(length-8,-1),(length,-4),
                      (length-3,5),(4,5)], (207,209,196))
                line([(7,3),(length-5,3)], light,1)
                line([(3,-9),(3,8)], dark,3)
                line([(3,8),(7,8)], accent,2)
            elif shape == "field_knife":
                poly([(4,-4),(length-10,-5),(length-4,-3),(length,0),
                      (length-7,4),(4,4)], (155,163,154))
                for x in range(5,14,3):
                    line([(x,-3),(x+1,-1)],dark,1)
                line([(3,-6),(3,5)], accent,2)
            elif shape == "ion_blade":
                poly([(3,-8),(length-17,-8),(length-5,-3),(length,0),
                      (length-5,3),(length-17,8),(3,8),(9,0)],
                     (184,215,219), accent,2)
                line([(11,0),(length-5,0)], (248,248,233),3)
                line([(7,-9),(17,-12),(24,-9)], accent,1)
                circle(1,0,6,accent,2)
            else:
                poly([(4,-5),(length-10,-5),(length,0),(length-10,5),(4,5)], (220,217,184))
                line([(4,-12),(9,-7),(9,7),(4,12)], (187,152,51),3)
                line([(9,0),(length-5,0)],light,1)
        return

    if shape in ("revolver", "suppressed", "ink_pistol"):
        poly([(-6,-4),(7,-4),(4,15),(-6,11)],
             (135,104,75) if shape == "revolver" else (75,73,72))
        if shape == "revolver":
            poly([(-8,-14),(10,-14),(10,-10),(29,-10),(31,-8),(29,-5),
                  (10,-5),(9,-3),(-7,-3)], (184,174,150))
            circle(3,-8,8,(226,215,190),0)
            circle(3,-8,8,dark,2)
            for x,y in ((0,-11),(5,-11),(0,-6),(5,-6)): circle(x,y,1,dark,0)
            line([(-7,-12),(-12,-18)],dark,2)
            line([(23,-11),(24,-15)],dark,2)
            line([(5,0),(12,0),(10,6),(5,6)],dark,1)
        elif shape == "suppressed":
            poly([(-8,-14),(15,-14),(18,-6),(-8,-6)], (58,69,65))
            poly([(15,-13),(44,-13),(45,-6),(16,-6)], (111,126,116))
            line([(19,-9),(42,-9)],paper,1)
            for x in (22,31,39): line([(x,-13),(x,-6)],dark,1)
            for x in (-5,0,5): line([(x,-13),(x-2,-7)],light,1)
            line([(12,-16),(17,-16)],accent,1)
        else:
            poly([(-8,-14),(13,-14),(20,-11),(29,-11),(30,-5),
                  (13,-5),(8,-3),(-8,-4)], (87,87,97))
            circle(8,-8,5,(206,199,176),0)
            circle(8,-8,5,dark,1)
            line([(24,-12),(25,-16)],dark,1)
            line([(-4,-11),(3,-11)],accent,2)
        return

    if shape in ("double_barrel", "breach", "marker"):
        poly([(-25,0),(-13,-9),(1,-6),(-5,2),(-22,8)],
             (151,104,64) if shape=="double_barrel" else dark)
        if shape == "double_barrel":
            for y in (-13,-6):
                poly([(-8,y),(41,y),(44,y+3),(41,y+5),(-8,y+5)], (172,170,157))
                line([(-4,y+2),(41,y+2)],dark,1)
            poly([(3,-2),(18,-2),(16,5),(3,5)], (155,112,71))
            line([(-8,-10),(-14,-16)],dark,2)
        elif shape == "breach":
            poly([(-10,-13),(29,-13),(34,-8),(29,-5),(-9,-5)],(89,104,96))
            poly([(4,-5),(24,-5),(22,5),(5,5)],(119,126,111))
            poly([(29,-14),(37,-14),(37,-5),(29,-5)],(125,137,126))
            for x in range(8,22,4): line([(x,-4),(x,4)],dark,2)
            line([(2,-15),(11,-15)],accent,2)
        else:
            poly([(-10,-16),(31,-16),(43,-10),(43,-6),(31,-2),(-10,-2)],
                 (83,68,91))
            poly([(0,-16),(25,-16),(25,-2),(0,-2)],paper)
            for y in (-12,-8,-4): line([(3,y),(20,y)],accent,2)
            poly([(31,-15),(43,-10),(43,-6),(31,-3)],(107,65,101))
        line([(-2,-3),(-2,5),(3,5),(5,-3)],dark,1)
        return

    if shape in ("pulse", "null_cannon", "eraser"):
        poly([(-6,-3),(6,-3),(4,11),(-4,11)],dark)
        if shape == "pulse":
            poly([(-8,-17),(16,-17),(26,-10),(16,-1),(-8,-1)], (189,209,207),accent,2)
            circle(13,-9,8,accent,2)
            circle(13,-9,4,paper,0)
            line([(21,-17),(37,-17),(39,-12)],accent,2)
            line([(21,-1),(37,-1),(39,-6)],accent,2)
            line([(-5,-11),(2,-11)],dark,1)
        elif shape == "null_cannon":
            poly([(-15,-17),(21,-17),(28,-12),(28,-2),(21,3),(-15,3)],
                 (176,207,209),accent,2)
            poly([(-9,-13),(5,-13),(5,-1),(-9,-1)],(220,179,168))
            poly([(26,-18),(39,-18),(42,-12),(32,-10),(42,-4),
                  (39,4),(26,4)], paper, accent,2)
            for x in (11,16,21): line([(x,-17),(x,3)],accent,1)
            line([(-9,-8),(2,-8)],paper,2)
        else:
            poly([(-17,-17),(26,-17),(37,-12),(37,-2),(26,3),(-17,3)],
                 (211,165,151))
            poly([(-4,-17),(17,-17),(17,3),(-4,3)],(225,216,189))
            poly([(28,-15),(39,-12),(39,-2),(28,1)],(238,210,203))
            for y in (-12,-7,-2): line([(0,y),(14,y)],light,1)
            line([(-14,-12),(-14,-2)],accent,2)
        return

    # The original notebook rubber band is a small fork, visibly unlike the
    # orbital emitter even though both use the saved rubber_band identifier.
    line([(0,10),(0,0),(-8,-12)],dark,3)
    line([(0,0),(11,-12)],dark,3)
    line([(-8,-12),(2,-5),(11,-12)],(164,99,77),2)


def draw_weapon_icon(surface, weapon_id, page_index, center, size=42):
    profile = profile_for(page_index, weapon_id)
    shape = profile.silhouette
    # Center each authored outline rather than using one firearm-sized box.
    # Long tools retain their full silhouette in both the pickup and HUD.
    extent, offset_x, angle = {
        "carbon_rifle": (116, 18, -.10),
        "pencil_maul": (125, 35, -.28),
        "excalibur": (95, 27, -.37),
        "katana": (76, 17, -.37),
        "ion_blade": (72, 15, -.28),
        "redraw_pencil": (68, 16, -.33),
        "pencil": (65, 15, -.33),
        "bowie": (52, 7, -.27),
        "field_knife": (49, 6, -.35),
        "double_barrel": (84, 10, -.10),
        "breach": (76, 7, -.10),
        "marker": (83, 9, -.10),
        "null_cannon": (72, 13, .09),
        "eraser": (70, 11, .09),
        "pulse": (70, 10, .09),
        "suppressed": (63, 17, -.08),
        "revolver": (60, 9, -.08),
        "ink_pistol": (61, 10, -.08),
        "chalk_bomb": (44, 0, -.15),
        "fold_star": (49, 0, -.20),
        "rubber": (48, 1, -.23),
    }.get(shape, (62, 8, 0))
    scale = size / extent
    origin = (center[0] - offset_x * math.cos(angle) * scale,
              center[1] - offset_x * math.sin(angle) * scale)
    draw_weapon(surface, weapon_id, page_index, origin, angle=angle, scale=scale)
