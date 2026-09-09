"""Authored campaign extension rooms.

Kept separate from the original chapter builders so the first vertical slice remains
readable while the longer combat/puzzle route can be iterated independently.
"""
from __future__ import annotations

import pygame

from combat import CombatArena
from entities import LostSketch
from paper_puzzles import CarbonTransferPuzzle, CreaseWeavePuzzle
from puzzles import GlyphLockPuzzle, InkCircuitPuzzle
from world import MaterialZone, PaperNote


def _ground(world, a, b, seed, layer=0):
    return world.add(a, b, 590, 16, f"expanded_ground_{seed}", seed, layer)


def _note(world, x, y, text, angle=0, crossed=False):
    world.notes.append(PaperNote(x, y, text, "small", angle=angle, crossed=crossed))


def _platform_room(world, x, seed, layer=0):
    """A readable four-jump room, never a flat distance filler."""
    _ground(world, x, x + 500, seed, layer)
    world.add(x + 540, x + 790, 535, 11, f"room_{seed}_a", seed + 1, layer)
    world.add(x + 835, x + 1095, 475, 11, f"room_{seed}_b", seed + 2, layer)
    world.add(x + 1140, x + 1400, 525, 11, f"room_{seed}_c", seed + 3, layer)
    _ground(world, x + 1445, x + 1900, seed + 4, layer)
    return x + 1900


def _checkpoint(runtime, checkpoint_id, x, requires=(), layer=0):
    Checkpoint = type(runtime.checkpoints[0])
    runtime.checkpoints.append(Checkpoint(checkpoint_id, x, 510, layer, x, 1, tuple(requires)))


def _add_arena(runtime, start, width, arena_id, specs, boss=False, layer=0):
    world = runtime.world
    _ground(world, start - 100, start + width + 230, 800 + len(runtime.entities.items), layer)
    arena = CombatArena(world, start, start + width, arena_id, specs, layer, boss)
    runtime.entities.add(arena)
    _checkpoint(runtime, f"after_{arena_id}", start + width + 80, (arena_id,), layer)
    return start + width + 180


def _carbon_room(runtime, start, puzzle_id, seed, glyphs=("O", "X", "^", "[]"), layer=0):
    """A reveal/turn/mirror route that asks the player to cross the room three times."""
    world = runtime.world
    count = len(glyphs)
    spacing = 255
    stations = [(start + 130 + i * spacing, 590) for i in range(count)]
    turn_x = stations[-1][0] + 185
    gate_x = turn_x + 175
    _ground(world, start - 90, gate_x + 310, seed, layer)
    # Optional high pencil strokes keep each traversal from reading as a flat corridor.
    for i in range(count - 1):
        px = start + 245 + i * spacing
        world.add(px, px + 145, 520 - (i % 2) * 42, 10,
                  f"room_{seed}_carbon_{i}", seed + 1 + i, layer)
    puzzle = CarbonTransferPuzzle(
        world, start + 80, gate_x, puzzle_id, stations, glyphs, layer, 590,
        (turn_x, 590),
    )
    runtime.entities.add(puzzle)
    _checkpoint(runtime, f"after_{puzzle_id}", gate_x + 105, (puzzle_id,), layer)
    _note(world, start + 25, 315, "pressure leaves a story on the other side", angle=-1)
    return gate_x + 240


def _crease_room(runtime, start, puzzle_id, seed, target=(0, 0, 0, 1), layer=0):
    """Four linked, collidable page strips form a short fold-and-traverse room."""
    world = runtime.world
    _ground(world, start - 160, start + 12, seed, layer)
    # A faint backing stroke catches the player between individual paper
    # strips; the visible crease strokes above it still provide the changing
    # ramp collision and cannot be walked through horizontally.
    _ground(world, start + 10, start + 785, seed + 2, layer)
    _ground(world, start + 785, start + 1260, seed + 1, layer)
    stations = [(start + 95 + i * 190, 590) for i in range(4)]
    gate_x = start + 1010
    puzzle = CreaseWeavePuzzle(
        # Fold geometry hangs above the walking stroke, so the current AABB
        # controller can read it as an optional upper route without snagging
        # on the steep concertina edges.
        world, start, gate_x, puzzle_id, target, layer, 482, stations,
    )
    runtime.entities.add(puzzle)
    _checkpoint(runtime, f"after_{puzzle_id}", gate_x + 110, (puzzle_id,), layer)
    _note(world, start + 90, 205, "the whole sheet moves when one corner bends", angle=1)
    return start + 1210


def expand_chapter(runtime):
    builders = [_expand_prologue, _expand_margins, _expand_mistakes, _expand_under_ink, _expand_finale]
    builders[runtime.index](runtime)
    runtime.world.width = max(runtime.world.width, runtime.end_x + 180)
    return runtime


def _expand_prologue(runtime):
    world = runtime.world
    x = runtime.end_x - 80
    _ground(world, x, x + 900, 201)
    _note(world, x + 180, 330, "three old shapes keep the page shut")
    lock = GlyphLockPuzzle(world, x + 260, x + 720, "first_glyph_lock", (0, 2, 1))
    runtime.entities.add(lock)
    _checkpoint(runtime, "first_puzzle", x + 820, ("first_glyph_lock",))
    x = _platform_room(world, x + 860, 210)
    runtime.entities.add(LostSketch(x - 710, 450, "practice_monster",
                                    "the Artist once tried to draw something dangerous"))
    _note(world, x - 1220, 300, "O   triangle   X", crossed=True)
    _ground(world, x, x + 980, 216)
    _note(world, x + 310, 290, "it moved when I wasn't looking", angle=-2)
    runtime.end_x = x + 820


def _expand_margins(runtime):
    world = runtime.world
    x = runtime.end_x - 70
    _ground(world, x, x + 500, 230)
    _note(world, x + 80, 330, "F / J", angle=-3)
    _note(world, x + 190, 365, "cross it out before it crosses you out")
    x = _add_arena(runtime, x + 360, 900, "margin_scribbles", [
        {"wave": 0, "kind": "crawler", "x": x + 680, "count": 2},
        {"wave": 1, "kind": "hopper", "x": x + 720, "count": 1},
        {"wave": 2, "kind": "crawler", "x": x + 650, "count": 2},
    ])
    world.zones.append(MaterialZone(pygame.Rect(x + 100, 420, 620, 220), "coffee_slippery",
                                    "fresh ring", 1, (110, 63, 34, 38)))
    x = _platform_room(world, x, 240)
    _note(world, x - 1350, 285, "the stain remembers every cup")
    _ground(world, x, x + 1200, 246)
    circuit = InkCircuitPuzzle(world, x + 220, x + 850, "margin_ink_circuit")
    runtime.entities.add(circuit)
    _checkpoint(runtime, "margin_circuit", x + 950, ("margin_ink_circuit",))
    runtime.entities.add(LostSketch(x + 590, 550, "margin_battle_note",
                                    "a victory pose the Artist immediately disliked"))
    x = _carbon_room(runtime, x + 1180, "margin_carbon_copy", 250)
    runtime.end_x = x - 120


def _expand_mistakes(runtime):
    world = runtime.world
    x = runtime.end_x - 60
    _ground(world, x, x + 430, 260)
    x = _add_arena(runtime, x + 320, 980, "bad_draft_pack", [
        {"wave": 0, "kind": "crawler", "x": x + 650, "count": 2},
        {"wave": 1, "kind": "spitter", "x": x + 810, "count": 2},
        {"wave": 2, "kind": "hopper", "x": x + 610, "count": 2},
    ])
    _note(world, x + 50, 280, "WRONG", crossed=True)
    glyph = GlyphLockPuzzle(world, x + 210, x + 720, "mistake_glyph_lock", (2, 1, 2))
    runtime.entities.add(glyph)
    _ground(world, x - 20, x + 900, 268)
    _checkpoint(runtime, "corrected_glyphs", x + 800, ("mistake_glyph_lock",))
    x = _platform_room(world, x + 930, 270)
    world.zones.append(MaterialZone(pygame.Rect(x - 1700, 565, 130, 75), "ink_hazard",
                                    "spilled correction", 1, (24, 24, 31, 150)))
    x = _add_arena(runtime, x + 120, 1100, "eraser_survivors", [
        {"wave": 0, "kind": "spitter", "x": x + 520, "count": 1},
        {"wave": 0, "kind": "crawler", "x": x + 720, "count": 2},
        {"wave": 1, "kind": "hopper", "x": x + 560, "count": 2},
        {"wave": 2, "kind": "spitter", "x": x + 800, "count": 2},
    ])
    runtime.entities.add(LostSketch(x - 620, 550, "eraser_survivor_sketch",
                                    "a creature assembled from everything the eraser missed"))
    _ground(world, x, x + 850, 280)
    x = _crease_room(runtime, x + 860, "mistake_shared_crease", 284, (1, 0, 1, 0))
    runtime.end_x = x - 100


def _expand_under_ink(runtime):
    world = runtime.world
    x = runtime.end_x - 80
    _ground(world, x, x + 900, 290)
    _note(world, x + 90, 290, "the older layer can fight back")
    circuit = InkCircuitPuzzle(world, x + 180, x + 700, "palimpsest_circuit")
    runtime.entities.add(circuit)
    _checkpoint(runtime, "old_circuit", x + 790, ("palimpsest_circuit",))
    x = _platform_room(world, x + 820, 295)
    world.zones.append(MaterialZone(pygame.Rect(x - 1500, 405, 500, 235), "coffee_sticky",
                                    "old damp paper", 1, (91, 49, 27, 48)))
    x = _add_arena(runtime, x + 100, 1080, "underpage_shapes", [
        {"wave": 0, "kind": "hopper", "x": x + 500, "count": 2},
        {"wave": 1, "kind": "spitter", "x": x + 720, "count": 2},
        {"wave": 2, "kind": "crawler", "x": x + 530, "count": 3},
    ])
    runtime.entities.add(LostSketch(x - 500, 550, "ink_family",
                                    "three discarded shapes holding hands below the page"))
    glyph = GlyphLockPuzzle(world, x + 180, x + 700, "under_glyph_lock", (1, 2, 0))
    runtime.entities.add(glyph)
    _ground(world, x, x + 940, 302)
    _checkpoint(runtime, "under_symbols", x + 800, ("under_glyph_lock",))
    x = _carbon_room(runtime, x + 950, "under_carbon_memory", 306,
                     ("O", "X", "^", "[]", "?"))
    runtime.end_x = x - 110


def _expand_finale(runtime):
    world = runtime.world
    x = runtime.end_x - 80
    _ground(world, x, x + 480, 320)
    _note(world, x + 60, 300, "NO MORE", crossed=True)
    x = _add_arena(runtime, x + 350, 1150, "finale_chase_pack", [
        {"wave": 0, "kind": "crawler", "x": x + 710, "count": 3},
        {"wave": 1, "kind": "hopper", "x": x + 650, "count": 2},
        {"wave": 1, "kind": "spitter", "x": x + 900, "count": 1},
        {"wave": 2, "kind": "spitter", "x": x + 780, "count": 2},
    ])
    x = _platform_room(world, x + 80, 330)
    circuit = InkCircuitPuzzle(world, x + 180, x + 760, "finale_circuit")
    runtime.entities.add(circuit)
    _ground(world, x, x + 930, 336)
    _checkpoint(runtime, "finale_circuit", x + 840, ("finale_circuit",))
    x = _crease_room(runtime, x + 960, "finale_living_fold", 340, (1, 0, 1, 1))
    x = _add_arena(runtime, x + 120, 1320, "artist_last_scribble", [
        {"wave": 0, "kind": "boss", "x": x + 820, "count": 1},
    ], boss=True)
    _note(world, x - 1060, 250, "I DIDN'T MEAN TO DRAW THIS")
    runtime.entities.add(LostSketch(x - 520, 550, "boss_first_draft",
                                    "the first quiet version of the final scribble"))
    _ground(world, x, x + 1100, 342)
    _note(world, x + 330, 270, "...you can choose now")
    runtime.end_x = x + 920
