"""Page-specific tool identities, handling, and resolution-independent drawings.

Save files continue to store the original weapon IDs. A page changes the
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
    "unarmed": ToolProfile("EMPTY HANDS", "unarmed", "the next tool is still being drawn"),
    "fold_crossbow": ToolProfile("FOLD CROSSBOW", "fold_crossbow",
                                  "impact splits the bolt · one shot, then reload", 1, 1.15, .72,
                                  770, 90, .95, lifetime=1.3, knockback=120,
                                  accent=(142, 105, 63)),
    "orbit_saw": ToolProfile("ORBIT SAW", "orbit_saw",
                             "throw a ring · two cuts where it stops", 2, 1.65, .65,
                             560, 0, .72, lifetime=1.12, knockback=75,
                             accent=(68, 118, 142)),
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
        "fold_crossbow": ToolProfile("BAMBOO CROSSBOW", "fold_crossbow",
                                      "impact splits the bolt · one shot, then reload", 1, 1.15, .72,
                                      770, 90, .95, lifetime=1.3, knockback=120,
                                      accent=(134, 101, 63)),
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
        "orbit_saw": ToolProfile("REVISION WHEEL", "orbit_saw",
                                 "throw a ring · two cuts where it stops", 2, 1.65, .65,
                                 560, 0, .72, lifetime=1.12, knockback=75,
                                 accent=(131, 89, 121)),
        "pencil_blade": ToolProfile("REDRAW PENCIL", "redraw_pencil",
                                   "every stroke returns as a delayed trace",
                                   fire_delay=.34, reach_scale=1.04, tempo=.94,
                                   damage=.90, accent=(165, 60, 63)),
    },
}

# The Artist lends tools through completed physical drawings. These lists only
# permit selection; they never grant the first tool or a permanent sword.
PAGE_LOADOUTS = {
    0: ("folded_shuriken", "pencil_blade", "margin_maul", "fold_crossbow"),
    1: ("ink_pistol", "marker_shotgun", "chalk_bomb", "pencil_blade", "margin_maul", "fold_crossbow"),
    2: ("rubber_band", "eraser_cannon", "chalk_bomb", "excalibur", "pencil_blade", "margin_maul", "orbit_saw"),
    3: ("ink_pistol", "carbon_lance", "folded_shuriken", "marker_shotgun", "pencil_blade", "margin_maul", "fold_crossbow"),
    4: ("margin_maul", "eraser_cannon", "marker_shotgun", "folded_shuriken", "rubber_band", "pencil_blade", "orbit_saw"),
}
PAGE_ENTRY_TOOLS = {0: "folded_shuriken", 1: "ink_pistol", 2: "rubber_band",
                    3: "ink_pistol", 4: "margin_maul"}


def loadout_for(page_index):
    return PAGE_LOADOUTS.get(page_index, tuple(key for key in ORIGINAL if key != "unarmed"))


def profile_for(page_index, weapon_id):
    return PAGE_TOOLS.get(page_index, {}).get(weapon_id, ORIGINAL.get(weapon_id, ORIGINAL["pencil_blade"]))


def label_for(page_index, weapon_id):
    return profile_for(page_index, weapon_id).label


@dataclass(frozen=True)
class HeldTool:
    """Art landmarks and size for a 48-pixel figure, separate from damage.

    Coordinates refer to the unchanged pickup/HUD drawing. ``grip`` is the
    actual fist contact; muzzle and support follow the same transform through
    aiming, recoil and reload rather than guessing a distance from the hero.
    """
    scale: float
    grip: tuple = (0, 0)
    muzzle: tuple = (0, 0)
    support: tuple | None = None
    reload_socket: tuple = (0, 13)
    carry_angle: float = .4
    two_handed: bool = False


HELD_TOOLS = {
    "fold_crossbow": HeldTool(.61, (0, 6), (37, -5), (15, 3), (-4, -5), two_handed=True),
    "orbit_saw": HeldTool(.59, (0, 8), (29, -9), (14, 1), (12, -9), two_handed=True),
    "carbon_rifle": HeldTool(.48, (0, 8), (70, -2), (26, 5), (8, 19), two_handed=True),
    "revolver": HeldTool(.57, (0, 6), (31, -8), reload_socket=(3, -8)),
    "suppressed": HeldTool(.48, (0, 6), (45, -9), reload_socket=(0, 15)),
    "ink_pistol": HeldTool(.58, (0, 6), (30, -8), reload_socket=(0, 15)),
    "double_barrel": HeldTool(.60, (0, 3), (44, -7), (16, 4), (8, -6), two_handed=True),
    "breach": HeldTool(.62, (0, 3), (37, -9), (20, 4), (7, 7), two_handed=True),
    "marker": HeldTool(.60, (0, 3), (43, -8), (20, 1), (2, 9), two_handed=True),
    "null_cannon": HeldTool(.58, (0, 6), (42, -7), (21, 5), (-3, 5), two_handed=True),
    "eraser": HeldTool(.58, (0, 6), (39, -7), (23, 3), (-3, 5), two_handed=True),
    "pulse": HeldTool(.54, (0, 6), (39, -9), (14, 0), carry_angle=0),
    "rubber": HeldTool(.76, (0, 5), (3, -7), carry_angle=-.25),
    "fold_star": HeldTool(.43, (-12, 3), (23, 0), carry_angle=0),
    "chalk_bomb": HeldTool(.48, (0, 7), (0, -22), carry_angle=-.12),
    "katana": HeldTool(.66, (0, 0), (47, -8), (-8, 1), carry_angle=.25, two_handed=True),
    "bowie": HeldTool(.64, (0, 0), (27, 0), carry_angle=-.28),
    "field_knife": HeldTool(.68, (0, 0), (24, 0), carry_angle=.8),
    "ion_blade": HeldTool(.66, (0, 0), (43, 0), (-8, 1), carry_angle=-.08, two_handed=True),
    "pencil": HeldTool(.66, (0, 0), (40, 0), carry_angle=.58),
    "redraw_pencil": HeldTool(.65, (0, 0), (44, 1), carry_angle=.72),
    "excalibur": HeldTool(.60, (0, 0), (67, 0), (-9, 1), carry_angle=-.88, two_handed=True),
    "pencil_maul": HeldTool(.44, (0, 0), (93, 0), (-13, 1), carry_angle=-1.05, two_handed=True),
}


@dataclass(frozen=True)
class HeldWeaponPose:
    grip: pygame.Vector2
    support: pygame.Vector2
    muzzle: pygame.Vector2
    draw_origin: pygame.Vector2
    angle: float
    scale: float
    two_handed: bool


def weapon_art_point(point, origin, angle, scale, weapon_id):
    """Use exactly the drawing's left-aim mirror for every art landmark."""
    c, s = math.cos(angle), math.sin(angle)
    x, y = point
    if c < 0 and weapon_id not in ("pencil_blade", "excalibur", "margin_maul"):
        y = -y
    return pygame.Vector2(origin) + pygame.Vector2(x * c - y * s, x * s + y * c) * scale


def held_weapon_pose(player, body_pose=None, aim_angle=None):
    """World-space hand attachment used by both the drawing and fired shot.

    The weapon never grows to match a melee hitbox. A long cut's motion marks
    still describe its existing attack reach; a knife remains a knife.
    """
    weapon = player.current_weapon
    shape = profile_for(getattr(player, "arsenal_page", None), weapon).silhouette
    model = HELD_TOOLS.get(shape, HeldTool(.65))
    body = body_pose or player._body_pose()
    shoulder = pygame.Vector2(body["shoulder"])
    facing = player.facing
    recoil = player.weapon_recoil
    reloading = player.weapon_reload_progress is not None
    angle = player.aim_angle if aim_angle is None else aim_angle
    melee = weapon in ("pencil_blade", "margin_maul", "excalibur")
    if melee:
        if player.combat_swing is not None:
            angle = player.combat_swing[0]
            vector = pygame.Vector2(math.cos(angle), math.sin(angle))
            grip = pygame.Vector2(player.center_x, player.rect.centery - 5) + vector * 12
        else:
            angle = model.carry_angle if facing > 0 else math.pi - model.carry_angle
            grip = shoulder + pygame.Vector2(facing * 12, 14)
    elif shape in ("fold_star", "chalk_bomb"):
        angle = model.carry_angle if facing > 0 else math.pi - model.carry_angle
        grip = shoulder + pygame.Vector2(facing * (15 if shape == "fold_star" else 12),
                                         12 if shape != "chalk_bomb" else 7)
    else:
        angle -= facing * recoil * .16
        vector = pygame.Vector2(math.cos(angle), math.sin(angle))
        # Raise the forearm beside the face when aiming steeply upward. The
        # weapon should clear the hero's head instead of crossing its face.
        grip = shoulder + pygame.Vector2(facing * 8 * abs(math.sin(angle)), 13)
        grip += vector * ((7 if model.two_handed else 12) - recoil * 4)
    if reloading:
        angle = .65 if facing > 0 else math.pi - .65
        grip += pygame.Vector2(-facing * 3, 5)
    origin = grip - weapon_art_point(model.grip, (0, 0), angle, model.scale, weapon)
    muzzle = weapon_art_point(model.muzzle, origin, angle, model.scale, weapon)
    if reloading:
        progress = player.weapon_reload_progress
        support = weapon_art_point(model.reload_socket, origin, angle, model.scale, weapon)
        support += pygame.Vector2(0, 3 + math.sin(progress * math.pi) * 4)
    elif model.support is not None and model.two_handed:
        support = weapon_art_point(model.support, origin, angle, model.scale, weapon)
    else:
        support = shoulder + pygame.Vector2(-facing * 7, 22)
    return HeldWeaponPose(grip, support, muzzle, origin, angle, model.scale, model.two_handed)


def draw_weapon(surface, weapon_id, page_index, grip, angle=0.0, scale=1.0, ink=None):
    """Draw a held tool about its grip. The local barrel/blade points right.

    The same authored geometry is used by the player, pickup, and inventory.
    This keeps a collected silhouette recognizable once it is in the hand.
    """
    profile = profile_for(page_index, weapon_id)
    shape = profile.silhouette
    if shape == "unarmed":
        return
    dark = ink or (49, 48, 49)
    light = (110, 109, 103)
    paper = (247, 238, 214)
    steel = (141, 149, 144)
    accent = profile.accent
    c, s = math.cos(angle), math.sin(angle)
    # Aiming to the left mirrors a firearm; it must not put its grip above
    # the barrel. Blades retain their full rotation through a cut.
    flip_y = -1 if c < 0 and weapon_id not in ("pencil_blade","excalibur","margin_maul") else 1
    def pt(x, y):
        y *= flip_y
        return round(grip[0] + (x*c-y*s)*scale), round(grip[1] + (x*s+y*c)*scale)
    def line(points, color=dark, width=2):
        from paper_renderer import jitter_line
        for i in range(len(points)-1):
            jitter_line(surface,color,pt(*points[i]),pt(*points[i+1]),
                        max(1,round(width*scale)),419+i,2,.9*scale)
    def poly(points, fill=paper, outline=dark, width=2):
        points = [pt(*p) for p in points]
        if fill is not None:
            pygame.draw.polygon(surface, fill, points)
        if outline is not None:
            pygame.draw.lines(surface, outline, True, points, max(1, round(width*scale)))
    def circle(x, y, radius, color=dark, width=1):
        pygame.draw.circle(surface, color, pt(x,y), max(1,round(radius*scale)),
                           min(max(1,round(radius*scale)), max(1,round(width*scale))) if width else 0)

    if shape == "fold_crossbow":
        # Bent bamboo limbs and a taut thread make the bow legible even at
        # held scale; the folded, split tip matches the fired paper bolt.
        poly([(-22,-1),(-6,-8),(26,-8),(37,-5),(26,-2),(-4,0),(-18,7)],
             (173, 146, 91))
        poly([(-3,-1),(5,-1),(3,13),(-4,11)], (106, 91, 67))
        line([(19,-5),(9,-27),(4,-29),(10,-10)], accent, 3)
        line([(19,-5),(9,17),(4,19),(10,0)], accent, 3)
        line([(5,-29),(-7,-5),(5,19)], dark, 1)
        line([(-6,-5),(32,-5)], paper, 2)
        poly([(27,-9),(38,-5),(27,-1),(29,-5)], paper, dark, 1)
        for x in (-17,-10,1,12): line([(x,-4),(x+2,-1)], light, 1)
        return
    if shape == "orbit_saw":
        poly([(-9,-13),(10,-17),(26,-14),(30,-9),(26,-4),(10,0),(-9,-3)],
             (177, 195, 190), accent, 2)
        poly([(-5,-2),(4,-2),(3,14),(-5,11)], dark)
        circle(12,-9,12,accent,2)
        circle(12,-9,6,paper,0)
        for index in range(8):
            angle0 = index*math.tau/8
            x, y = 12+math.cos(angle0)*12, -9+math.sin(angle0)*12
            line([(x,y),(x+math.cos(angle0+.35)*4,y+math.sin(angle0+.35)*4)],dark,1)
        line([(-7,-11),(0,-11)],paper,1)
        line([(27,-15),(33,-12),(33,-6),(27,-3)],accent,2)
        return
    if shape == "carbon_rifle":
        # A long, braced drafting rifle, not another pistol-sized rectangle.
        poly([(-33,-11),(-15,-11),(-7,-3),(-7,5),(-25,12),(-34,7)], (149,137,117))
        poly([(-20,-8),(30,-8),(35,-5),(67,-5),(70,-2),(67,1),(31,1),(18,7),(-20,7)],
             (78,82,78))
        poly([(27,-13),(37,-13),(42,-8),(27,-8)], paper)
        line([(-17,-4),(26,-4),(67,-2)], (221,211,189), 2)
        poly([(32,-4),(67,-4),(67,-2),(32,-2)], steel, None)
        line([(-29,-8),(-25,-5),(-16,-5)], paper, 1)
        for x in (-27,-22,-17): line([(x,2),(x+2,8)], (96,82,66), 1)
        circle(26,-4,2,paper,0)
        line([(41,-6),(41,3),(47,3),(47,-6)], accent, 2)
        poly([(2,6),(17,6),(10,22),(1,20)], (112,105,91))
        for x in (19,23,27): line([(x,2),(x+2,7)], paper, 1)
        return
    if shape == "fold_star":
        points=[(0,-22),(5,-6),(23,0),(6,5),(0,22),(-5,6),(-22,0),(-6,-5)]
        poly(points, paper, dark, 2)
        for x,y in ((0,-22),(23,0),(0,22),(-22,0)):
            line([(0,0),(x,y)], accent, 1)
        for points in ([(0,-20),(4,-5),(0,0)],
                       [(21,0),(5,4),(0,0)],
                       [(0,20),(-4,5),(0,0)],
                       [(-20,0),(-5,-4),(0,0)]):
            poly(points, (196,190,173), None)
        line([(0,-19),(0,-5)],paper,1)
        line([(7,1),(18,1)],paper,1)
        circle(0,0,3,dark)
        return
    if shape == "chalk_bomb":
        # Broken chalk is contained in a squat hand-labelled paper capsule.
        poly([(-13,-10),(-9,-15),(9,-15),(14,-9),(14,8),(9,14),(-9,14),(-14,8)], paper, dark, 2)
        poly([(-5,-15),(6,-15),(6,-22),(-5,-22)], (204,180,139))
        line([(-4,-19),(5,-19)], dark,1)
        line([(10,-9),(10,7),(6,11)], (193,178,148), 2)
        line([(-10,-4),(10,-4)], accent, 3)
        line([(-8,1),(7,1)], accent, 2)
        for x,y in ((-7,7),(1,6),(8,8)): circle(x,y,2,light,1)
        return
    if shape == "pencil_maul":
        poly([(-16,-5),(72,-5),(93,0),(72,6),(-16,6)], (208,189,129))
        line([(-12,-2),(71,-2)],dark,2)
        line([(-12,3),(71,3)],accent,1)
        poly([(-10,0),(71,0),(77,4),(-10,4)],(158,137,79),None)
        line([(-10,-4),(70,-4)],(247,229,164),1)
        poly([(72,-5),(93,0),(72,6)],(178,151,112))
        poly([(84,-2),(93,0),(84,3)],dark)
        poly([(-22,-6),(-12,-6),(-12,7),(-22,7)],(180,117,111))
        poly([(-12,-6),(-6,-6),(-6,7),(-12,7)],steel)
        for x in (-10,-7): line([(x,-4),(x,5)],paper,1)
        for x in range(6,62,17):line([(x,-2),(x+7,-2)],dark,1)
        return

    if shape in ("katana", "bowie", "field_knife", "ion_blade", "pencil",
                 "redraw_pencil", "excalibur"):
        length = {"katana":47,"bowie":27,"field_knife":24,"ion_blade":43,
                  "pencil":40,"redraw_pencil":44,"excalibur":67}[shape]
        if shape in ("pencil", "redraw_pencil"):
            poly([(-12,-3),(length-8,-3),(length,0),(length-8,3),(-12,3)], (204,174,93))
            line([(-8,0),(length-8,0)], light, 1)
            line([(-7,-2),(length-11,-2)],(249,228,158),1)
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
                poly([(7,1),(30,0),(44,-6),(45,-5),(31,2),(7,3)], steel, None)
                line([(8,-2),(29,-3),(41,-7)],paper,1)
                line([(3,-9),(5,9)], accent,3)
                circle(4,0,5,(177,121,72),1)
                line([(0,-7),(3,-7)], paper,1)
            elif shape == "bowie":
                poly([(4,-5),(length-10,-5),(length-8,-1),(length,-4),
                      (length-3,5),(4,5)], (207,209,196))
                line([(7,3),(length-5,3)], light,1)
                poly([(5,2),(length-4,2),(length-3,5),(5,5)],steel,None)
                line([(3,-9),(3,8)], dark,3)
                line([(3,8),(7,8)], accent,2)
            elif shape == "field_knife":
                poly([(4,-4),(length-10,-5),(length-4,-3),(length,0),
                      (length-7,4),(4,4)], (155,163,154))
                for x in range(5,14,3):
                    line([(x,-3),(x+1,-1)],dark,1)
                line([(3,-6),(3,5)], accent,2)
                line([(6,2),(length-5,2)],paper,1)
            elif shape == "ion_blade":
                poly([(3,-8),(length-17,-8),(length-5,-3),(length,0),
                      (length-5,3),(length-17,8),(3,8),(9,0)],
                     (184,215,219), accent,2)
                line([(11,0),(length-5,0)], (248,248,233),3)
                poly([(10,3),(length-10,4),(length-16,6),(6,6)],(91,145,164),None)
                line([(12,-6),(length-19,-6)],paper,1)
                line([(7,-9),(17,-12),(24,-9)], accent,1)
                circle(1,0,6,accent,2)
            else:
                poly([(4,-5),(length-10,-5),(length,0),(length-10,5),(4,5)], (220,217,184))
                line([(4,-12),(9,-7),(9,7),(4,12)], (187,152,51),3)
                line([(9,0),(length-5,0)],light,1)
                poly([(11,1),(length-9,2),(length-12,4),(11,4)],steel,None)
                line([(12,-3),(length-12,-3)],paper,1)
        return

    if shape in ("revolver", "suppressed", "ink_pistol"):
        poly([(-6,-4),(7,-4),(4,15),(-6,11)],
             (135,104,75) if shape == "revolver" else (75,73,72))
        if shape == "revolver":
            poly([(-8,-14),(10,-14),(10,-10),(29,-10),(31,-8),(29,-5),
                  (10,-5),(9,-3),(-7,-3)], (184,174,150))
            circle(3,-8,8,(226,215,190),0)
            circle(3,-8,8,dark,2)
            line([(11,-9),(28,-9)],paper,1)
            line([(13,-6),(29,-6)],steel,1)
            for x in (-3,0,3): line([(x,3),(x-2,10)],(92,66,51),1)
            for x,y in ((0,-11),(5,-11),(0,-6),(5,-6)): circle(x,y,1,dark,0)
            line([(-7,-12),(-12,-18)],dark,2)
            line([(23,-11),(24,-15)],dark,2)
            line([(5,0),(12,0),(10,6),(5,6)],dark,1)
            circle(-2,7,1,paper,0)
        elif shape == "suppressed":
            poly([(-8,-14),(15,-14),(18,-6),(-8,-6)], (58,69,65))
            poly([(15,-13),(44,-13),(45,-6),(16,-6)], (111,126,116))
            line([(19,-9),(42,-9)],paper,1)
            line([(-6,-12),(13,-12)],steel,1)
            for yy in (2,6,10): line([(-3,yy),(2,yy)],steel,1)
            for x in (22,31,39): line([(x,-13),(x,-6)],dark,1)
            for x in (-5,0,5): line([(x,-13),(x-2,-7)],light,1)
            line([(12,-16),(17,-16)],accent,1)
        else:
            poly([(-8,-14),(13,-14),(20,-11),(29,-11),(30,-5),
                  (13,-5),(8,-3),(-8,-4)], (87,87,97))
            circle(8,-8,5,(206,199,176),0)
            circle(8,-8,5,dark,1)
            line([(-6,-13),(12,-13),(19,-10),(28,-10)],(159,163,169),1)
            for yy in (1,5,9): line([(-4,yy),(1,yy)],light,1)
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
                line([(-5,y+1),(39,y+1)],paper,1)
            poly([(3,-2),(18,-2),(16,5),(3,5)], (155,112,71))
            for x in (6,10,14): line([(x,-1),(x-1,3)],(102,75,51),1)
            line([(-22,3),(-14,-3)],(203,151,93),1)
            line([(-8,-10),(-14,-16)],dark,2)
        elif shape == "breach":
            poly([(-10,-13),(29,-13),(34,-8),(29,-5),(-9,-5)],(89,104,96))
            poly([(4,-1),(24,-1),(22,5),(5,5)],(119,126,111))
            poly([(29,-14),(37,-14),(37,-5),(29,-5)],(125,137,126))
            for x in (9,19): line([(x,0),(x,4)],dark,2)
            line([(-7,-11),(28,-11)],paper,1)
            circle(32,-9,2,dark,0)
            line([(2,-15),(11,-15)],accent,2)
        else:
            poly([(-10,-16),(31,-16),(43,-10),(43,-6),(31,-2),(-10,-2)],
                 (83,68,91))
            poly([(0,-16),(25,-16),(25,-2),(0,-2)],paper)
            for y in (-12,-8,-4): line([(3,y),(20,y)],accent,2)
            poly([(31,-15),(43,-10),(43,-6),(31,-3)],(107,65,101))
            line([(32,-13),(40,-9)],(174,130,161),1)
            line([(-7,-14),(-2,-14)],paper,1)
        line([(-2,-3),(-2,5),(3,5),(5,-3)],dark,1)
        return

    if shape in ("pulse", "null_cannon", "eraser"):
        poly([(-6,-3),(6,-3),(4,11),(-4,11)],dark)
        if shape == "pulse":
            poly([(-8,-17),(16,-17),(26,-10),(16,-1),(-8,-1)], (189,209,207),accent,2)
            circle(13,-9,8,accent,2)
            circle(13,-9,4,paper,0)
            circle(13,-9,2,dark,0)
            line([(-5,-15),(14,-15)],paper,1)
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
            line([(-13,-15),(21,-15)],paper,1)
            line([(29,-15),(36,-15)],steel,1)
        else:
            poly([(-17,-17),(26,-17),(37,-12),(37,-2),(26,3),(-17,3)],
                 (211,165,151))
            poly([(-4,-17),(17,-17),(17,3),(-4,3)],(225,216,189))
            poly([(28,-15),(39,-12),(39,-2),(28,1)],(238,210,203))
            for y in (-12,-7,-2): line([(0,y),(14,y)],light,1)
            line([(-15,-14),(-6,-14)],(249,218,203),1)
            poly([(29,-11),(37,-10),(37,-5),(29,-4)],(186,123,122),None)
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
    if shape == "unarmed":
        return
    # Center each authored outline rather than using one firearm-sized box.
    # Long tools retain their full silhouette in both the pickup and HUD.
    extent, offset_x, angle = {
        "carbon_rifle": (116, 18, -.10),
        "fold_crossbow": (76, 7, -.08),
        "orbit_saw": (61, 11, .05),
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
