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
        "pencil_blade": ToolProfile("BOWIE KNIFE", "bowie", "stay close · mark twice · cash out",
                                   fire_delay=.27, reach_scale=.88, tempo=.88, damage=1.0, accent=(142, 91, 57)),
        "ink_pistol": ToolProfile("SIX-SHOOTER", "revolver", "six heavy shots · deliberate rhythm",
                                 6, 1.56, .42, 820, 0, 1.20, lifetime=1.15, knockback=145, recoil=18),
        "marker_shotgun": ToolProfile("DOUBLE BARREL", "double_barrel", "two quick blasts · wide spread",
                                     2, 1.66, .60, 590, 50, .56, spread=36, pellets=9, lifetime=.47,
                                     knockback=190, recoil=150, accent=(142, 91, 57)),
    },
    2: {
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
                                 9, 1.12, .24, 960, 0, .95, lifetime=.95, knockback=75,
                                 accent=(76, 104, 92)),
        "marker_shotgun": ToolProfile("BREACH SHOTGUN", "breach", "tight grouping · controlled shove",
                                     3, 1.85, .90, 720, 25, .85, spread=13, pellets=5, lifetime=.49,
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
        pygame.draw.lines(surface, color, False, [pt(*p) for p in points], max(1, round(width*scale)))
    def poly(points, fill=paper, outline=dark, width=1):
        points = [pt(*p) for p in points]
        if fill is not None:
            pygame.draw.polygon(surface, fill, points)
        if outline is not None:
            pygame.draw.lines(surface, outline, True, points, max(1, round(width*scale)))
    def circle(x, y, radius, color=dark, width=1):
        pygame.draw.circle(surface, color, pt(x,y), max(1,round(radius*scale)),
                           min(max(1,round(radius*scale)), max(1,round(width*scale))) if width else 0)

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
                poly([(5,-2),(31,-3),(length,-8),(length-3,-2),(29,2),(5,3)], paper)
                line([(8,0),(29,-1),(44,-5)], light,1)
                line([(3,-7),(5,7)], accent,2)
            elif shape == "bowie":
                poly([(4,-4),(length-9,-4),(length,-1),(length-4,5),(4,5)], (211,212,202))
                line([(7,3),(length-5,3)], light,1)
                line([(3,-6),(3,7)], dark,2)
            elif shape == "field_knife":
                poly([(4,-3),(length-6,-3),(length,0),(length-5,3),(4,3)], (155,163,154))
                for x in range(5,14,3):
                    line([(x,-3),(x+1,-1)],dark,1)
                line([(3,-6),(3,5)], accent,2)
            elif shape == "ion_blade":
                poly([(3,-4),(length-6,-3),(length,0),(length-6,3),(3,4)], (196,219,224), accent,1)
                line([(6,0),(length-4,0)], (244,245,230),2)
                circle(1,0,5,accent,1)
            else:
                poly([(4,-5),(length-10,-5),(length,0),(length-10,5),(4,5)], (220,217,184))
                line([(4,-12),(9,-7),(9,7),(4,12)], (187,152,51),3)
                line([(9,0),(length-5,0)],light,1)
        return

    if shape in ("revolver", "suppressed", "ink_pistol"):
        poly([(-5,-3),(6,-3),(4,12),(-4,10)], (134,111,89) if shape=="revolver" else dark)
        if shape == "revolver":
            poly([(-5,-12),(18,-12),(18,-7),(5,-7),(5,-2),(-5,-2)], (172,171,159))
            circle(2,-7,6,dark,1)
            for x in (-1,3): line([(x,-10),(x,-4)],light,1)
            line([(-5,-11),(-9,-14)],dark,2)
            line([(14,-13),(15,-15)],dark,2)
            line([(4,2),(10,2),(9,6),(4,6)],dark,1)
        elif shape == "suppressed":
            poly([(-8,-12),(15,-12),(17,-5),(-7,-5)], dark)
            poly([(15,-11),(35,-11),(35,-5),(16,-5)], (124,135,126))
            line([(18,-9),(32,-9)],light,1)
            for x in (-5,-2,1): line([(x,-11),(x-1,-6)],light,1)
        else:
            poly([(-7,-12),(22,-12),(23,-5),(-6,-5)], (90,90,97))
            circle(9,-8,3,(206,199,176),0)
            line([(19,-13),(19,-15)],dark,1)
        return

    if shape in ("double_barrel", "breach", "marker"):
        poly([(-22,0),(-11,-7),(0,-5),(-5,1),(-19,6)], (151,104,64) if shape=="double_barrel" else dark)
        if shape == "double_barrel":
            poly([(-6,-10),(35,-10),(35,-4),(-6,-4)], (172,170,157))
            line([(-3,-7),(35,-7)],dark,1)
            poly([(4,-4),(20,-4),(18,0),(4,0)], (155,112,71))
            line([(-6,-8),(-10,-12)],dark,2)
        elif shape == "breach":
            poly([(-9,-11),(27,-11),(30,-6),(-8,-5)],(89,104,96))
            poly([(7,-5),(20,-5),(20,0),(7,0)],dark)
            poly([(27,-12),(33,-12),(33,-5),(27,-5)],(125,137,126))
            for x in range(7,21,3): line([(x,-5),(x,0)],light,1)
        else:
            poly([(-8,-12),(32,-12),(36,-8),(32,-3),(-8,-3)],(79,67,87))
            poly([(5,-12),(20,-12),(20,-3),(5,-3)],paper)
            line([(8,-9),(17,-9)],accent,1)
            line([(8,-6),(16,-6)],dark,1)
        line([(-2,-3),(-2,5),(3,5),(5,-3)],dark,1)
        return

    if shape in ("pulse", "null_cannon", "eraser"):
        poly([(-6,-3),(6,-3),(4,11),(-4,11)],dark)
        if shape == "pulse":
            poly([(-8,-14),(16,-14),(24,-8),(16,-2),(-8,-2)], (189,209,207),accent)
            circle(12,-8,8,accent,2)
            circle(12,-8,4,paper,0)
            line([(20,-14),(30,-14),(32,-11)],accent,2)
            line([(20,-2),(30,-2),(32,-5)],accent,2)
            line([(-5,-11),(2,-11)],dark,1)
        elif shape == "null_cannon":
            poly([(-12,-16),(27,-16),(32,-11),(32,-3),(27,1),(-12,1)], (186,208,209),accent)
            poly([(-7,-13),(8,-13),(8,-2),(-7,-2)],(222,180,169))
            for x in (14,20,26): line([(x,-16),(x,1)],accent,2)
            line([(-8,-9),(3,-9)],paper,2)
        else:
            poly([(-12,-16),(29,-16),(33,-12),(33,-3),(29,1),(-12,1)],(211,165,151))
            poly([(-3,-16),(16,-16),(16,1),(-3,1)],(220,211,181))
            line([(1,-10),(12,-10)],light,1)
            line([(1,-6),(10,-6)],light,1)
        return

    # The original notebook rubber band is a small fork, visibly unlike the
    # orbital emitter even though both use the saved rubber_band identifier.
    line([(0,10),(0,0),(-8,-12)],dark,3)
    line([(0,0),(11,-12)],dark,3)
    line([(-8,-12),(2,-5),(11,-12)],(164,99,77),2)


def draw_weapon_icon(surface, weapon_id, page_index, center, size=42):
    profile = profile_for(page_index, weapon_id)
    shape = profile.silhouette
    extent = 80 if shape=="excalibur" else 62 if shape in ("katana","double_barrel","breach","marker") else 56
    scale = size / extent
    offset_x = 16 if shape in ("katana","pencil","redraw_pencil","ion_blade","excalibur") else 6
    offset_y = 0 if weapon_id in ("pencil_blade","excalibur","rubber_band") else -3
    draw_weapon(surface,weapon_id,page_index,(center[0]-offset_x*scale,center[1]-offset_y*scale),scale=scale)
