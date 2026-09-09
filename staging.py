"""Authored route landmarks and combat cues, drawn from runtime geometry."""
from __future__ import annotations

import math
import pygame

from entities import LostSketch
from world import PaperNote

INK = (49, 48, 47)
RED = (151, 61, 58)
BLUE = (69, 99, 117)

# A teaching beat, a combination and a payoff give each room a purpose.
ENCOUNTERS = {
    "first_crossout": ("01 / THE FIRST CUT", "Let the blade pass. Cut during recovery."),
    "practice_crossouts": ("02 / PAPER AMBUSH", "The drone drops after firing. Go behind the ruler."),
    "bamboo_static": ("03 / LANTERN PROCESSION", "Clear the low threat before chasing the lantern."),
    "pistol_margin_drill": ("01 / HIGH NOON", "Keep space. Jump the rolling tumbleweed."),
    "coffee_crossfire": ("02 / THREE NEEDLES", "Read the cactus fan; move between volleys."),
    "safe_pocket_counterattack": ("01 / AIRLOCK PATROL", "The bot braces before ramming. Let it commit."),
    "orbital_debris": ("02 / DEBRIS FIELD", "Jump the hound; close on the turret during reload."),
    "eraser_calibration": ("04 / CORRECTION BAY", "Watch the erased floor. Save a landing line."),
}

# These branches lie between fights. The ground remains a forgiving return
# path, while the collectible requires three deliberate, reachable jumps.
ROUTES = (
    (0, 6270, "THE FOLDED SHRINE", "shrine_roof", "a ronin who wanted to be a kite", "torn_edge"),
    (1, 9920, "THE WATER TOWER", "water_tower", "a train ticket to a town never drawn", "ruler_line"),
    (2, 12200, "THE ORRERY", "orbit_observatory", "a moon with an erased second face", "construction"),
)


def compose(runtime):
    for arena in runtime.entities.items:
        brief = ENCOUNTERS.get(getattr(arena, "arena_id", ""))
        if brief:
            arena.display_name, arena.tactical_hint = brief
            runtime.world.notes.append(PaperNote(
                arena.start_x - 330, 365, brief[1], "small", INK, -1, False, True))
    runtime.route_landmarks = []
    for page, start, title, secret, caption, style in ROUTES:
        if page != runtime.index:
            continue
        runtime.world.notes[:] = [n for n in runtime.world.notes
                                  if not start <= n.x <= start + 980]
        # Replace the old decorative steps in this corridor with a designed
        # ascent and descent. Do not remove the primary ground stroke.
        runtime.world.platforms[:] = [p for p in runtime.world.platforms
            if not (start - 20 <= p.x1 < start + 1060 and p.y < 550
                    and p.name.startswith("route_"))]
        heights = (505, 425, 345, 425, 505)
        for i, height in enumerate(heights):
            p = runtime.world.add(start + i * 205, start + i * 205 + 160,
                                  height, 10, f"vignette_{secret}_{i}", 6100 + page * 10 + i)
            p.appearance = style
        cx = start + 490
        runtime.entities.add(LostSketch(cx, 327, secret, caption))
        runtime.world.notes.append(PaperNote(start, 238, title, "large", INK, -1, False, True))
        runtime.world.notes.append(PaperNote(start + 15, 280,
            "UP: a lost sketch     /     ground: onward", "small", BLUE, 0, False, True))
        runtime.route_landmarks.append((page, cx))


def draw_landmarks(surface, camera, runtime, time):
    """Big silhouettes identify a place; the platforms draw on top."""
    for page, center in getattr(runtime, "route_landmarks", ()):
        x = camera.screen_x(center)
        if x < -650 or x > surface.get_width() + 650:
            continue
        y = round(camera.offset_y)
        if page == 0:
            # Folded temple roof, hanging prayer strips and exposed supports.
            for side in (-1, 1):
                pygame.draw.line(surface, (135, 121, 95), (x + side * 155, 430+y),
                                 (x + side * 155, 590+y), 5)
            roof = [(x-245, 417+y), (x, 303+y), (x+245, 417+y),
                    (x+174, 405+y), (x, 342+y), (x-174, 405+y)]
            pygame.draw.polygon(surface, (218, 204, 170), roof)
            pygame.draw.lines(surface, RED, True, roof, 3)
            for i in range(-3, 4):
                sway = round(math.sin(time*1.6+i)*4)
                px = x+i*49
                pygame.draw.lines(surface, (139, 123, 95), False,
                    [(px, 433+y), (px+sway, 458+y), (px-5+sway, 474+y)], 2)
        elif page == 1:
            # Riveted water tank and cross-braced trestle; no fake collision.
            pygame.draw.rect(surface, (209, 183, 138), (x-90, 354+y, 180, 67))
            pygame.draw.rect(surface, (116, 88, 60), (x-90, 354+y, 180, 67), 3)
            pygame.draw.ellipse(surface, (177, 143, 100), (x-90, 343+y, 180, 25), 2)
            for px in range(x-75, x+90, 30):
                pygame.draw.line(surface, (151, 119, 81), (px, 369+y), (px, 411+y), 1)
            for side in (-1, 1):
                pygame.draw.line(surface, (123, 95, 66), (x+side*65, 422+y), (x+side*110, 590+y), 5)
            pygame.draw.line(surface, (151, 119, 81), (x-65, 435+y), (x+105, 578+y), 3)
            pygame.draw.line(surface, (151, 119, 81), (x+65, 435+y), (x-105, 578+y), 3)
            # A slow, mechanical wind vane is distinct from the temple strips.
            tip = (x+round(math.cos(time*.65)*62), 303+y+round(math.sin(time*.65)*8))
            pygame.draw.line(surface, INK, (x, 343+y), (x, 300+y), 2)
            pygame.draw.line(surface, RED, (x, 303+y), tip, 3)
        else:
            # An armillary sphere with three independently rotating satellites.
            pygame.draw.line(surface, BLUE, (x, 450+y), (x, 584+y), 5)
            pygame.draw.ellipse(surface, (126, 149, 157), (x-186, 358+y, 372, 135), 2)
            pygame.draw.ellipse(surface, (126, 149, 157), (x-118, 305+y, 236, 218), 2)
            pygame.draw.circle(surface, BLUE, (x, 417+y), 60, 2)
            for i in range(3):
                a = time*.25+i*math.tau/3
                pos = (x+round(math.cos(a)*186), 425+y+round(math.sin(a)*67))
                pygame.draw.circle(surface, (226, 231, 219), pos, 9)
                pygame.draw.circle(surface, BLUE, pos, 9, 2)


def draw_enemy_read(surface, camera, renderer, enemy):
    """Open brackets signal recovery without recoloring the whole actor."""
    if enemy.dead:
        return
    state = getattr(enemy, "state", "")
    windows = {"recover", "overheat", "cool", "smoke", "pluck", "stuck",
               "reload", "unravel", "proof_window", "wall_stun"}
    if state not in windows or not getattr(enemy, "vulnerable", True):
        return
    x = camera.screen_x(enemy.x)
    y = round(enemy.y - enemy.height * .5 + camera.offset_y)
    r = enemy.radius + 7
    for side in (-1, 1):
        px = x + side*r
        pygame.draw.lines(surface, BLUE, False,
            [(px-side*5, y-9), (px, y-9), (px, y+9), (px-side*5, y+9)], 2)
