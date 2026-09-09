"""Action-heavy campaign pass for the Paper Story vertical slice.

The original authored paper events and puzzles stay intact.  This module lays a
combat rhythm over that route: weapons are found in the notebook, short arenas
teach one idea at a time, and tool-shaped bosses turn editing gestures into
attacks.  Everything is procedural Pygame drawing; there are no external art
assets or generic sprite rectangles.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import pygame

from combat import CombatArena
from paper_renderer import jitter_line
from page_arsenal import label_for, draw_weapon_icon
from scripted_events import ArtistTool, artist_canvas_free
from settings import INK, INK_LIGHT, PAPER, RED_RULE
from world import MaterialZone, PaperNote


ACTION_ENCOUNTER_IDS = (
    "first_crossout", "practice_crossouts", "bamboo_static", "moon_gate_duel",
    "pistol_margin_drill", "coffee_crossfire", "marker_margin_trial", "midnight_train",
    "safe_pocket_counterattack", "orbital_debris", "zero_garden", "eraser_calibration",
)

WEAPON_PICKUPS = {
    "ink_pistol": (1, 2085, 0),
    "marker_shotgun": (1, 8220, 0),
    "eraser_cannon": (2, 10200, 0),
    "rubber_band": (2, 7250, 0),
    # Drawn by BabyFaceSignatureBeat rather than a generic pickup entity.
    "excalibur": (2, 15765, 0),
}


@dataclass
class WeaponPickup:
    """A physical notebook doodle that unlocks and immediately saves a weapon."""

    x: float
    y: float
    weapon_id: str
    layer: int = 0
    label: str = ""
    active: bool = True
    mandatory: bool = False
    collected: bool = False
    completed: bool = False
    time: float = 0.0
    drawing: bool = False
    draw_progress: float = 0.0
    draw_sound_played: bool = False
    page_index: int = 0

    @property
    def display_label(self):
        return label_for(self.page_index, self.weapon_id)

    @property
    def pickup_id(self):
        return f"pickup_{self.weapon_id}"

    @property
    def rect(self):
        return pygame.Rect(round(self.x - 28), round(self.y - 54), 56, 58)

    def update(self, dt, ctx, interact=False):
        self.time += dt
        self.page_index = getattr(ctx.level, "chapter_index", self.page_index)
        weapons = getattr(ctx, "weapons", None)
        if weapons is None:
            return
        if self.weapon_id in weapons.unlocked:
            self.collected = self.completed = True
            ctx.level.flags.add(self.pickup_id)
            return
        reveal_near = abs(ctx.player.center_x - self.x) < 390
        canvas_free = artist_canvas_free(ctx)
        if reveal_near and canvas_free and not self.drawing:
            self.drawing = True
        if self.drawing and self.draw_progress < 1 and canvas_free:
            if not self.draw_sound_played:
                self.draw_sound_played = True
                ctx.sounds.play("pencil")
            self.draw_progress = min(1, self.draw_progress + dt / .72)
            stroke_x = self.x - 31 + 62 * self.draw_progress
            director = getattr(ctx, "director", None)
            if director is not None:
                director.tool = ArtistTool("pencil", stroke_x, self.y - 32,
                                           True, -.58, 1.1)
            if int(self.time * 40) % 4 == 0:
                ctx.particles.pencil_speck(stroke_x, self.y - 32)
            if self.draw_progress >= 1:
                ctx.camera.kick(3.5, .16)
                if getattr(ctx, "game", None) is not None:
                    ctx.game.behavior.record("artist_help", kind="weapon_drawn",
                                             weapon=self.weapon_id)
        near = abs(ctx.player.center_x - self.x) < 66 and abs(ctx.player.rect.bottom - self.y) < 95
        touching = self.draw_progress >= 1 and self.rect.colliderect(ctx.player.rect.inflate(12, 8))
        if near and self.draw_progress >= 1:
            ctx.level.interaction_hint = f"E  take {self.display_label}"
        if self.draw_progress < 1 or not (touching or (near and interact)):
            return
        self._grant(ctx, weapons)

    def _grant(self, ctx, weapons):
        if self.collected:
            return
        weapons.unlock(self.weapon_id)
        weapons.select(self.weapon_id)
        self.collected = self.completed = True
        ctx.level.flags.add(self.pickup_id)
        ctx.level.toast = f"NEW DRAWING — {self.display_label}"
        ctx.level.toast_time = 4.0
        ctx.particles.paper_puff(self.x, self.y - 22, 20)
        ctx.sounds.play("pickup")
        ctx.camera.kick(4, .18)
        save = getattr(ctx.level, "save_system", None)
        if save is not None:
            snapshot = weapons.snapshot()
            save.update_combat(snapshot["unlocked"], snapshot["current_id"], snapshot["ammo"])

    def draw(self, surface, camera, renderer):
        if self.collected:
            return
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        if self.draw_progress <= 0:
            return
        bob = round(math.sin(self.time * 3.2) * 3 * self.draw_progress)
        y += bob
        width = round(68 * self.draw_progress)
        pygame.draw.ellipse(surface, (218, 211, 191), (x - 34, y - 8, width, 13), 1)
        clip = surface.get_clip()
        surface.set_clip(clip.clip(pygame.Rect(x - 43, y - 70,
                                              max(1, round(86 * self.draw_progress)), 65)))
        draw_weapon_icon(surface, self.weapon_id, self.page_index, (x, y - 35), size=70)
        surface.set_clip(clip)
        if self.draw_progress >= 1:
            label = self.display_label
            width = renderer.font_small.size(label)[0]
            renderer.doodle_text(surface, label, (x - width // 2, y - 92),
                                 INK_LIGHT, renderer.font_small, -1)


def register_artist_stage(arena, stage):
    if not hasattr(arena, "artist_stages"):
        arena.artist_stages = []
    arena.artist_stages.append(stage)


def claim_artist_stage(arena, stage):
    owner = getattr(arena, "artist_edit_owner", None)
    if owner is not None and owner is not stage:
        return False
    arena.artist_edit_owner = stage
    return True


def release_artist_stage(arena, stage):
    if getattr(arena, "artist_edit_owner", None) is stage:
        arena.artist_edit_owner = None


def cleared_wave(arena):
    return (arena.encounter_active and not arena.completed
            and not any(not enemy.dead for enemy in arena.enemies))


def player_uses_platform(player, platform):
    """Leave both a standing player and their committed landing intact."""
    rect = player.rect
    return (rect.right > platform.x1 - 22 and rect.left < platform.x2 + 22
            and rect.bottom <= max(platform.y, platform.end_y or platform.y) + 22
            and rect.bottom >= min(platform.y, platform.end_y or platform.y) - 180)


class ArenaPaperBeat:
    """Draw the room before combat; revise terrain in a genuinely empty wave."""

    active = True
    mandatory = False

    def __init__(self, world, arena, mode="draw_cover", layer=0, ground_y=590):
        self.world = world
        self.arena = arena
        self.mode = mode
        self.layer = layer
        self.ground_y = ground_y
        self.completed = False
        self.last_wave = -1
        self.time = 0.0
        self.erased = False
        self.folded = False
        self.edit_time = 0.0
        self.cover = None
        register_artist_stage(arena, self)
        span = arena.end_x - arena.start_x
        if mode in ("draw_cover", "erase_cover", "fold_shift") and span >= 390:
            cx = (arena.start_x + arena.end_x) * .5
            self.cover = world.add(cx - 95, cx + 95, ground_y - 85, 9,
                                   f"{arena.arena_id}_artist_cover", 9100 + int(cx), layer,
                                   ground_y - 85)
            self.cover.draw_progress = 0.0
            self.cover.appearance = {
                0: "torn_edge", 1: "ruler_line", 2: "construction",
                3: "carbon", 4: "handwriting",
            }.get(world.page, "annotation")
            self.cover.collidable = True
        if mode == "ink_spread":
            width = min(260, max(120, span * .34))
            cx = (arena.start_x + arena.end_x) * .5
            world.zones.append(MaterialZone(
                pygame.Rect(round(cx - width / 2), round(ground_y - 30), round(width), 78),
                "ink_sticky", "combat ink soaking through", 1.0, (25, 25, 34, 105), layer,
            ))

    @property
    def entry_ready(self):
        return self.cover is None or self.cover.draw_progress >= 1

    @property
    def wave_ready(self):
        if self.cover is None or self.arena.wave + 1 >= len(self.arena.wave_ids):
            return True
        if self.mode == "erase_cover":
            return self.erased
        if self.mode == "fold_shift":
            return self.folded
        return True

    def update(self, dt, ctx, interact=False):
        del interact
        self.time += dt
        if self.arena.completed:
            self.completed = True
            if self.cover is not None and self.cover.draw_progress < 1:
                self.cover.draw_progress = 1
            release_artist_stage(self.arena, self)
            return
        if not self.arena.encounter_active:
            if (self.cover is not None and self.cover.draw_progress < 1
                    and ctx.player.center_x >= self.arena.start_x - 420
                    and artist_canvas_free(ctx)):
                if self.cover.draw_progress == 0:
                    ctx.sounds.play("pencil")
                self.cover.draw_progress = min(1, self.cover.draw_progress + dt / .62)
                ctx.director.tool = ArtistTool("pencil", self.cover.visible_x2,
                                                self.cover.y, True, -.58, 1.0)
                ctx.particles.pencil_speck(self.cover.visible_x2, self.cover.y)
            return
        # Direct boss practice can enter without the approach animation. Finish
        # its physical cover immediately, without drawing over an active boss.
        if self.cover is not None and self.cover.draw_progress < 1:
            self.cover.draw_progress = 1
        if self.arena.wave != self.last_wave:
            self.last_wave = self.arena.wave
            if self.mode == "tear_spawn" and self.last_wave > 0:
                ctx.particles.paper_puff((self.arena.start_x + self.arena.end_x) / 2,
                                         self.ground_y - 38, 14)
                ctx.camera.kick(4, .18)
        if (self.wave_ready or not cleared_wave(self.arena)
                or not claim_artist_stage(self.arena, self)):
            return
        if player_uses_platform(ctx.player, self.cover):
            # The next wave must never depend on the player abandoning their
            # perch. Keep this useful landing rather than trapping the pause.
            self.erased = self.folded = True
            release_artist_stage(self.arena, self)
            return
        if self.edit_time == 0:
            ctx.level.toast = "THE ARTIST: A small revision. Next wave in a moment."
            ctx.level.toast_time = 1.8
            ctx.sounds.play("erase" if self.mode == "erase_cover" else "fold")
        self.edit_time += dt
        # A short hatched preview comes before collision changes. Neither the
        # current wave nor the next one can attack during this bounded edit.
        if self.edit_time < .28:
            return
        progress = min(1, (self.edit_time - .28) / .58)
        if self.mode == "erase_cover":
            mid = (self.cover.x1 + self.cover.x2) / 2
            cursor = mid - 42 + 94 * progress
            self.cover.erase(mid - 42, cursor)
            ctx.director.tool = ArtistTool("eraser", cursor, self.cover.y,
                                            True, -.2, 1.05)
            if int(self.edit_time * 35) % 4 == 0:
                ctx.particles.eraser_dust(cursor, self.cover.y, 3)
        elif self.mode == "fold_shift":
            self.cover.end_y = self.cover.y - 72 * progress
            ctx.director.tool = ArtistTool("pencil", self.cover.visible_x2,
                                            self.cover.end_y, True, -.85, 1.0)
        if progress >= 1:
            self.erased = self.folded = True
            ctx.camera.kick(3, .16)
            release_artist_stage(self.arena, self)

    def draw(self, surface, camera, renderer):
        if not self.arena.encounter_active:
            return
        cx = camera.screen_x((self.arena.start_x + self.arena.end_x) / 2)
        gy = round(self.ground_y + camera.offset_y)
        if self.mode == "tear_spawn":
            jitter_line(surface, INK_LIGHT, (cx - 18, gy - 92), (cx + 13, gy - 8),
                        3, 733 + self.last_wave, 3, 3)
            jitter_line(surface, PAPER, (cx - 11, gy - 78), (cx + 7, gy - 21),
                        6, 734 + self.last_wave, 2, 2)
        if self.cover is not None and 0 < self.edit_time < .28:
            y = round(self.cover.y + camera.offset_y)
            left, right = camera.screen_x(self.cover.x1), camera.screen_x(self.cover.x2)
            for x in range(left, right, 16):
                pygame.draw.line(surface, RED_RULE, (x, y - 8), (x + 7, y - 2), 2)
        if self.mode == "ink_spread":
            renderer.doodle_text(surface, "the ink is still wet", (cx - 78, gy - 118),
                                 INK_LIGHT, renderer.font_small, -2)


def _checkpoint(runtime, checkpoint_id, x, requires=(), layer=0, y=542):
    if any(cp.checkpoint_id == checkpoint_id for cp in runtime.checkpoints):
        return
    Checkpoint = type(runtime.checkpoints[0])
    runtime.checkpoints.append(Checkpoint(checkpoint_id, x, y, layer, x, 1, tuple(requires)))


def _arena(runtime, start, end, arena_id, specs, *, layer=0, ground_y=590,
           paper="draw_cover", checkpoint=True):
    arena = CombatArena(runtime.world, start, end, arena_id, specs, layer, False)
    runtime.entities.add(arena)
    runtime.entities.add(ArenaPaperBeat(runtime.world, arena, paper, layer, ground_y))
    if checkpoint:
        _checkpoint(runtime, f"after_{arena_id}", end + 42, (arena_id,), layer, ground_y - 48)
    return arena


def _revise(runtime, arena_id, specs, paper="erase_cover"):
    arena = next((e for e in runtime.entities.items
                  if getattr(e, "arena_id", None) == arena_id), None)
    if arena is None:
        return None
    arena.enemy_specs = list(specs)
    arena.wave_ids = sorted({int(spec.get("wave", 0)) for spec in specs})
    runtime.entities.add(ArenaPaperBeat(runtime.world, arena, paper, arena.layer, 590))
    return arena


def _pickup(runtime, weapon_id, x, y=590, layer=0, label=""):
    runtime.entities.add(WeaponPickup(x, y, weapon_id, layer, label, page_index=runtime.index))
    runtime.world.notes.append(PaperNote(x - 85, y - 168, f"{label_for(runtime.index, weapon_id)} ->",
                                         "small", INK_LIGHT, -2, False))


def _floor(runtime, x1, x2, seed, layer=0, y=590):
    return runtime.world.add(x1, x2, y, 16, f"action_annex_{seed}", seed, layer)


def _sort_checkpoints(runtime):
    # Trigger order is the save progression contract.  Python's stable sort
    # keeps start/alive in their authored order when both live at x=220.
    runtime.checkpoints.sort(key=lambda cp: (float(cp.trigger_x or cp.x),
                                             0 if cp.checkpoint_id == "start" else 1))


def expand_action_chapter(runtime):
    builders = (_action_prologue, _action_margins, _action_mistakes,
                _action_under_ink, _action_finale)
    builders[runtime.index](runtime)
    _sort_checkpoints(runtime)
    runtime.world.width = max(runtime.world.width, runtime.end_x + 220)
    return runtime


def _action_prologue(runtime):
    _arena(runtime, 1580, 2040, "first_crossout", [
        {"wave": 0, "kind": "crawler", "offset": 250},
        {"wave": 1, "kind": "crawler", "offset": 210, "count": 2, "spacing": 105},
    ], paper="draw_cover")
    # The second fight closes the page after its authored bridge and climbing
    # lesson.  It used to sit immediately after the first arena, leaving a
    # long, uneventful walk after combat.
    _arena(runtime, 4580, 5480, "practice_crossouts", [
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 2},
        {"wave": 1, "kind": "hopper", "offset": 250},
        {"wave": 1, "kind": "crawler", "offset": 390},
    ], paper="erase_cover")
    _arena(runtime, 7600, 8720, "bamboo_static", [
        {"wave": 0, "kind": "ink_samurai", "offset": 410},
        {"wave": 0, "kind": "origami_drone", "offset": 720},
        {"wave": 1, "kind": "goblin_scribble", "offset": 330},
        {"wave": 1, "kind": "ink_samurai", "offset": 780},
    ], paper="tear_spawn")
    _arena(runtime, 9500, 10620, "moon_gate_duel", [
        {"wave": 0, "kind": "ink_samurai", "offset": 340},
        {"wave": 0, "kind": "ink_samurai", "offset": 760},
        {"wave": 1, "kind": "origami_drone", "offset": 280},
        {"wave": 1, "kind": "goblin_scribble", "offset": 790},
    ], paper="draw_cover")
    _arena(runtime, 8010, 8690, "old_shapes_wake", [
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 3},
        {"wave": 1, "kind": "hopper", "offset": 260},
        {"wave": 1, "kind": "crawler", "offset": 460},
    ], paper="tear_spawn")
    runtime.world.notes.append(PaperNote(2880, 385, "SHIFT / K  dash through the red warning",
                                         "small", INK_LIGHT, -1, False))


def _action_margins(runtime):
    _pickup(runtime, "ink_pistol", 2085, label="INK PISTOL")
    _arena(runtime, 2130, 2740, "pistol_margin_drill", [
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 2},
        {"wave": 1, "kind": "spitter", "offset": 350},
        {"wave": 1, "kind": "crawler", "offset": 210},
    ], paper="ink_spread")
    _arena(runtime, 5150, 6120, "coffee_crossfire", [
        {"wave": 0, "kind": "spitter", "offset": 230, "count": 2, "spacing": 180},
        {"wave": 1, "kind": "paper_wasp", "offset": 245, "count": 2, "spacing": 170},
        {"wave": 1, "kind": "crawler", "offset": 410},
    ], paper="ink_spread")
    # The marker is drawn only after the red-margin traversal.  The page now
    # has a real quiet middle instead of three similarly spaced arenas.
    _pickup(runtime, "marker_shotgun", 8220, label="MARKER SHOTGUN")
    _arena(runtime, 8300, 9440, "marker_margin_trial", [
        {"wave": 0, "kind": "ruler_guard", "offset": 410},
        {"wave": 0, "kind": "crawler", "offset": 220, "count": 2},
        {"wave": 1, "kind": "ruler_guard", "offset": 350},
        {"wave": 1, "kind": "paper_wasp", "offset": 190, "count": 2, "spacing": 300},
    ], paper="draw_cover")
    _arena(runtime, 11200, 12520, "midnight_train", [
        {"wave": 0, "kind": "ink_outlaw", "offset": 330},
        {"wave": 0, "kind": "tumbleweed_thing", "offset": 760},
        {"wave": 1, "kind": "ink_outlaw", "offset": 900},
        {"wave": 1, "kind": "paper_wasp", "offset": 260},
        {"wave": 2, "kind": "goblin_scribble", "offset": 680},
    ], paper="fold_shift")
    _revise(runtime, "margin_scribbles", [
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 3},
        {"wave": 1, "kind": "spitter", "offset": 270, "count": 2, "spacing": 300},
        {"wave": 1, "kind": "paper_wasp", "offset": 450},
        {"wave": 2, "kind": "ruler_guard", "offset": 420},
        {"wave": 2, "kind": "doodle_turret", "offset": 650},
        {"wave": 2, "kind": "crawler", "offset": 190, "count": 2},
    ], "erase_cover")
    _arena(runtime, 8820, 9235, "coffee_highground", [
        {"wave": 0, "kind": "doodle_turret", "offset": 210},
        {"wave": 0, "kind": "paper_wasp", "offset": 305},
        {"wave": 1, "kind": "spitter", "offset": 200},
        {"wave": 1, "kind": "ruler_guard", "offset": 310},
    ], paper="fold_shift")
    _floor(runtime, 13170, 14720, 931)
    _arena(runtime, 13340, 14540, "margin_compass", [
        {"wave": 0, "kind": "compass", "offset": 610},
    ], paper="draw_cover")
    runtime.world.notes.append(PaperNote(13400, 275, "COMPASS TEST — wait for the needle",
                                         "small", INK_LIGHT, -2, False))
    runtime.end_x = max(runtime.end_x, 14670)


def _action_mistakes(runtime):
    _arena(runtime, 4270, 4980, "safe_pocket_counterattack", [
        {"wave": 0, "kind": "crumpled_one", "offset": 440},
        {"wave": 0, "kind": "crawler", "offset": 220, "count": 2},
        {"wave": 1, "kind": "spitter", "offset": 260, "count": 2, "spacing": 250},
    ], paper="draw_cover")
    _pickup(runtime, "rubber_band", 7250, label="ORBITAL RUBBER BAND")
    # BabyFace is the page-ending correction, not a mid-page speed bump.  The
    # construction route before it earns the extra length.
    _arena(runtime, 7500, 8620, "orbital_debris", [
        {"wave": 0, "kind": "star_scout", "offset": 300},
        {"wave": 0, "kind": "origami_drone", "offset": 760},
        {"wave": 1, "kind": "moon_bot", "offset": 540},
        {"wave": 1, "kind": "goblin_scribble", "offset": 260},
    ], paper="tear_spawn")
    _arena(runtime, 10500, 11720, "zero_garden", [
        {"wave": 0, "kind": "moon_bot", "offset": 340},
        {"wave": 0, "kind": "star_scout", "offset": 820},
        {"wave": 1, "kind": "goblin_scribble", "offset": 270},
        {"wave": 1, "kind": "star_scout", "offset": 900},
    ], paper="ink_spread")
    # Draw the Eraser before the Orbital Mistake so its phase windows teach
    # the page's heavy tool instead of saving it for the last thirty seconds.
    _pickup(runtime, "eraser_cannon", 10200, label="ERASER CANNON")
    _arena(runtime, 14020, 15480, "eraser_calibration", [
        {"wave": 0, "kind": "ruler_guard", "offset": 320, "count": 2, "spacing": 330},
        {"wave": 1, "kind": "eraser_brute", "offset": 570},
        {"wave": 1, "kind": "doodle_turret", "offset": 260},
    ], paper="erase_cover")
    _revise(runtime, "bad_draft_pack", [
        {"wave": 0, "kind": "crumpled_one", "offset": 520},
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 2},
        {"wave": 1, "kind": "spitter", "offset": 250, "count": 2, "spacing": 360},
        {"wave": 1, "kind": "paper_wasp", "offset": 500},
        {"wave": 2, "kind": "ruler_guard", "offset": 550},
        {"wave": 2, "kind": "doodle_turret", "offset": 750},
    ], "erase_cover")
    # The earlier platform-room pocket contains the authored correction-ink
    # death strip.  This fight belongs on the clean landing after it so combat
    # cannot turn that visible hazard into a respawn loop.
    _arena(runtime, 11460, 11810, "mistake_live_glyph", [
        {"wave": 0, "kind": "doodle_turret", "offset": 170, "count": 2, "spacing": 170},
        {"wave": 1, "kind": "spitter", "offset": 240},
        {"wave": 1, "kind": "paper_wasp", "offset": 330},
    ], paper="fold_shift")
    _revise(runtime, "eraser_survivors", [
        {"wave": 0, "kind": "eraser_brute", "offset": 560},
        {"wave": 0, "kind": "crawler", "offset": 230, "count": 2},
        {"wave": 1, "kind": "crumpled_one", "offset": 350, "count": 2, "spacing": 430},
        {"wave": 1, "kind": "spitter", "offset": 650},
        {"wave": 2, "kind": "ruler_guard", "offset": 430},
        {"wave": 2, "kind": "paper_wasp", "offset": 210, "count": 2, "spacing": 620},
    ], "erase_cover")
    _arena(runtime, 13310, 13960, "mistake_stapler", [
        {"wave": 0, "kind": "stapler", "offset": 340},
    ], paper="draw_cover")
    _floor(runtime, 15130, 17220, 951)
    _arena(runtime, 15400, 16980, "artist_mistake", [
        {"wave": 0, "kind": "artist_mistake", "offset": 800},
    ], paper="erase_cover")
    runtime.world.notes.append(PaperNote(15480, 250, "THE ARTIST'S MISTAKE",
                                         "large", RED_RULE, -2, True))
    runtime.end_x = max(runtime.end_x, 17180)


def _action_under_ink(runtime):
    _pickup(runtime, "rubber_band", 1815, 610, 1, "RUBBER BAND")
    _arena(runtime, 1860, 2220, "underlayer_ricochet", [
        {"wave": 0, "kind": "ink_clone", "offset": 260, "ground_y": 610},
        {"wave": 0, "kind": "crawler", "offset": 150, "ground_y": 610},
        {"wave": 1, "kind": "doodle_turret", "offset": 210, "ground_y": 610},
        {"wave": 1, "kind": "paper_wasp", "offset": 300, "ground_y": 610},
    ], layer=1, ground_y=610, paper="draw_cover")
    _arena(runtime, 3580, 3920, "underlayer_echo", [
        {"wave": 0, "kind": "ink_clone", "offset": 120, "count": 2, "spacing": 140,
         "ground_y": 610},
        {"wave": 1, "kind": "paper_wasp", "offset": 110, "count": 2, "spacing": 150,
         "ground_y": 610},
        {"wave": 1, "kind": "doodle_turret", "offset": 250, "ground_y": 610},
    ], layer=1, ground_y=610, paper="tear_spawn")
    # The return tear sits at x=3980, so this checkpoint is deliberately
    # placed before it but still requires the cleared arena.  It preserves the
    # actual layer route: under-page clear -> tear -> surface checkpoint.
    echo_cp = next(cp for cp in runtime.checkpoints
                   if cp.checkpoint_id == "after_underlayer_echo")
    echo_cp.x = echo_cp.trigger_x = 3950
    _arena(runtime, 5680, 6810, "folded_flock", [
        {"wave": 0, "kind": "paper_wasp", "offset": 240, "count": 3, "spacing": 310},
        {"wave": 1, "kind": "ink_clone", "offset": 300, "count": 2, "spacing": 470},
        {"wave": 1, "kind": "spitter", "offset": 620},
    ], paper="fold_shift")
    _arena(runtime, 7550, 8250, "palimpsest_siege", [
        {"wave": 0, "kind": "doodle_turret", "offset": 210, "count": 2, "spacing": 330},
        {"wave": 1, "kind": "spitter", "offset": 220, "count": 2, "spacing": 310},
        {"wave": 1, "kind": "paper_wasp", "offset": 500},
    ], paper="draw_cover")
    _revise(runtime, "underpage_shapes", [
        {"wave": 0, "kind": "ink_clone", "offset": 330, "count": 2, "spacing": 430},
        {"wave": 1, "kind": "paper_wasp", "offset": 250, "count": 2, "spacing": 500},
        {"wave": 1, "kind": "spitter", "offset": 560},
        {"wave": 2, "kind": "ruler_guard", "offset": 510},
        {"wave": 2, "kind": "ink_clone", "offset": 280},
        {"wave": 2, "kind": "doodle_turret", "offset": 760},
    ], "tear_spawn")
    _floor(runtime, 14120, 15860, 971)
    _arena(runtime, 14320, 15570, "failed_sketch", [
        {"wave": 0, "kind": "failed_sketch", "offset": 650},
    ], paper="tear_spawn")
    runtime.end_x = max(runtime.end_x, 15810)


def _action_finale(runtime):
    _arena(runtime, 1665, 2165, "living_line_start", [
        {"wave": 0, "kind": "crawler", "offset": 180, "count": 3, "spacing": 125},
        {"wave": 1, "kind": "paper_wasp", "offset": 300},
        {"wave": 1, "kind": "spitter", "offset": 180},
    ], paper="draw_cover")
    _arena(runtime, 2240, 2600, "living_line_mid", [
        {"wave": 0, "kind": "spitter", "offset": 140, "ground_y": 560},
        {"wave": 0, "kind": "doodle_turret", "offset": 270, "ground_y": 560},
        {"wave": 1, "kind": "paper_wasp", "offset": 200, "ground_y": 560},
    ], ground_y=560, paper="tear_spawn")
    _arena(runtime, 5030, 5450, "living_line_end", [
        {"wave": 0, "kind": "crumpled_one", "offset": 270},
        {"wave": 0, "kind": "ink_clone", "offset": 155},
        {"wave": 1, "kind": "eraser_brute", "offset": 280},
        {"wave": 1, "kind": "doodle_turret", "offset": 420},
    ], paper="erase_cover")
    _revise(runtime, "finale_chase_pack", [
        {"wave": 0, "kind": "crawler", "offset": 210, "count": 3},
        {"wave": 0, "kind": "paper_wasp", "offset": 620},
        {"wave": 1, "kind": "ruler_guard", "offset": 500},
        {"wave": 1, "kind": "spitter", "offset": 220, "count": 2, "spacing": 620},
        {"wave": 1, "kind": "doodle_turret", "offset": 780},
        {"wave": 2, "kind": "ruler_guard", "offset": 550},
        {"wave": 2, "kind": "crumpled_one", "offset": 270},
        {"wave": 2, "kind": "ink_clone", "offset": 820},
    ], "erase_cover")
    _arena(runtime, 10300, 10950, "finale_circuit_siege", [
        {"wave": 0, "kind": "doodle_turret", "offset": 180, "count": 2, "spacing": 350},
        {"wave": 0, "kind": "ruler_guard", "offset": 390},
        {"wave": 1, "kind": "paper_wasp", "offset": 230, "count": 2, "spacing": 330},
        {"wave": 1, "kind": "spitter", "offset": 480},
    ], paper="fold_shift")
    _revise(runtime, "artist_last_scribble", [
        {"wave": 0, "kind": "ink_clone", "offset": 270},
        {"wave": 0, "kind": "doodle_turret", "offset": 1000},
        {"wave": 1, "kind": "boss", "offset": 660},
    ], "erase_cover")
    runtime.world.notes.append(PaperNote(12620, 240, "SCRIBBLE GIANT — cross out the cross-out",
                                         "small", RED_RULE, -2, False))


__all__ = [
    "ACTION_ENCOUNTER_IDS", "WEAPON_PICKUPS", "WeaponPickup", "ArenaPaperBeat",
    "expand_action_chapter",
]
