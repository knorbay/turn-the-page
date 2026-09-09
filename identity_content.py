"""Build the shipping three-world route from the mechanics catalogue.

Older rooms, enemies, and puzzles are initially built as a regression-tested
parts bin, then removed from the production runtime.  This composition layer
authors 42,550 units of continuous travel, fourteen required arenas, distinct
world/costume/enemy identities, temporary page arsenals, and the signature
three-attempt Baby-Face gag before a real fifth boss, while preserving the
proven movement and collision core.
"""
from __future__ import annotations

import math
import pygame

from combat import CombatArena
from scripted_events import ArtistTool, EventSequence, EventStep
from settings import INK, INK_LIGHT, RED_RULE
from world import PaperNote


REQUIRED_SLICE_ENCOUNTERS = {
    0: ("first_crossout", "practice_crossouts", "bamboo_static", "moon_gate_duel"),
    1: ("pistol_margin_drill", "coffee_crossfire", "marker_margin_trial", "midnight_train"),
    2: ("safe_pocket_counterattack", "orbital_debris", "zero_garden", "eraser_calibration",
        "baby_face_interlude"),
    3: ("agent_checkpoint", "carbon_crossfire", "redacted_rooftops", "office_ambush", "scissor_office"),
    4: ("last_lesson", "erased_answers", "margin_revolt", "the_last_crossout", "final_margin_revision"),
}

# Every page clears the requested 10k floor and then grows at a different rate.
PAGE_ROUTE_ENDS = {0: 10950.0, 1: 13050.0, 2: 16750.0, 3: 10800.0, 4: 10800.0}

BOSS_ENCOUNTERS = {
    "moon_gate_duel": ("moon_compass", "THE MOON COMPASS"),
    "marker_margin_trial": ("wanted_sketch", "WANTED: FAILED ALIVE"),
    "midnight_train": ("railroad_stapler", "THE LAST STAPLER WEST"),
    "zero_garden": ("orbital_mistake", "ORBITAL ARTIST ERROR"),
    "scissor_office": ("scissor_director", "THE HEAD OF REDACTION"),
    "final_margin_revision": ("final_editor", "THE FINAL EDITOR"),
}

BOSS_RULES = {
    "moon_gate_duel": "JUMP THE ARC — STRIKE THE PINNED HINGE",
    "marker_margin_trial": "THE WET INK IS REAL — SHOOT BEFORE THE DRAW",
    "midnight_train": "JUMP THE RAIL — HIT THE REAR OR THE OPEN ENGINE",
    "zero_garden": "LET THE MOONS GO — HIT THE EXPOSED PLANET",
    "final_margin_revision": "READ THE PROOF — ATTACK WHEN THE CLIP OPENS",
}

CURATED_SPECS = {
    "first_crossout": [
        {"wave": 0, "kind": "ink_samurai", "offset": 265},
        {"wave": 1, "kind": "goblin_scribble", "offset": 205},
        {"wave": 1, "kind": "lantern_yokai", "offset": 365},
    ],
    "practice_crossouts": [
        {"wave": 0, "kind": "ink_samurai", "offset": 390},
        {"wave": 0, "kind": "origami_drone", "offset": 690},
        {"wave": 1, "kind": "goblin_scribble", "offset": 260},
        {"wave": 1, "kind": "ruler_guard", "offset": 515},
        {"wave": 1, "kind": "lantern_yokai", "offset": 760},
    ],
    "bamboo_static": [
        {"wave": 0, "kind": "ink_samurai", "offset": 330},
        {"wave": 0, "kind": "lantern_yokai", "offset": 760},
        {"wave": 1, "kind": "origami_drone", "offset": 270},
        {"wave": 1, "kind": "goblin_scribble", "offset": 565},
        {"wave": 1, "kind": "ruler_guard", "offset": 850},
    ],
    "moon_gate_duel": [
        {"wave": 0, "kind": "ink_samurai", "offset": 300},
        {"wave": 0, "kind": "origami_drone", "offset": 775},
        {"wave": 1, "kind": "moon_compass", "offset": 590},
    ],
    "pistol_margin_drill": [
        {"wave": 0, "kind": "ink_outlaw", "offset": 220},
        {"wave": 0, "kind": "tumbleweed_thing", "offset": 440},
        {"wave": 1, "kind": "cactus_gunner", "offset": 190},
        {"wave": 1, "kind": "paper_wasp", "offset": 450},
    ],
    "coffee_crossfire": [
        {"wave": 0, "kind": "ink_outlaw", "offset": 230},
        {"wave": 0, "kind": "paper_wasp", "offset": 690},
        {"wave": 1, "kind": "tumbleweed_thing", "offset": 260},
        {"wave": 1, "kind": "cactus_gunner", "offset": 520},
        {"wave": 1, "kind": "goblin_scribble", "offset": 810},
    ],
    "marker_margin_trial": [
        {"wave": 0, "kind": "ink_outlaw", "offset": 280},
        {"wave": 0, "kind": "crumpled_one", "offset": 780},
        {"wave": 1, "kind": "wanted_sketch", "offset": 580},
    ],
    "midnight_train": [
        {"wave": 0, "kind": "ink_outlaw", "offset": 280},
        {"wave": 0, "kind": "tumbleweed_thing", "offset": 650},
        {"wave": 0, "kind": "cactus_gunner", "offset": 1010},
        {"wave": 1, "kind": "railroad_stapler", "offset": 690},
    ],
    "safe_pocket_counterattack": [
        {"wave": 0, "kind": "star_scout", "offset": 230},
        {"wave": 0, "kind": "moon_bot", "offset": 610},
        {"wave": 1, "kind": "comet_hound", "offset": 250},
        {"wave": 1, "kind": "ink_clone", "offset": 625},
    ],
    "orbital_debris": [
        {"wave": 0, "kind": "origami_drone", "offset": 260},
        {"wave": 0, "kind": "star_scout", "offset": 750},
        {"wave": 1, "kind": "comet_hound", "offset": 240},
        {"wave": 1, "kind": "moon_bot", "offset": 555},
        {"wave": 1, "kind": "doodle_turret", "offset": 870},
    ],
    "zero_garden": [
        {"wave": 0, "kind": "star_scout", "offset": 250},
        {"wave": 0, "kind": "comet_hound", "offset": 575},
        {"wave": 0, "kind": "goblin_scribble", "offset": 900},
        {"wave": 1, "kind": "orbital_mistake", "offset": 625},
    ],
    "eraser_calibration": [
        {"wave": 0, "kind": "eraser_brute", "offset": 330},
        # Keep the ranged guard inside the cannon's readable opening range.
        # At the old 1050 offset a cautious player could spend forever trading
        # with a ballistic turret before even meeting the signature boss.
        {"wave": 0, "kind": "doodle_turret", "offset": 720},
        {"wave": 1, "kind": "moon_bot", "offset": 330},
        {"wave": 1, "kind": "star_scout", "offset": 720},
    ],
}


class BabyFaceSignatureBeat:
    """Three authored attempts: plain loss, moustached loss, sword reversal."""

    active = True
    mandatory = False

    def __init__(self, arena, layer=0):
        self.arena = arena
        self.layer = layer
        self.state = "waiting"
        self.timer = 0.0
        self.sword_progress = 0.0
        self.pull_progress = 0.0
        self.gift_x = arena.start_x + 175
        self.pull_target = (self.gift_x, 520)
        self.completed = False

    def _boss(self):
        return next((enemy for enemy in self.arena.enemies
                     if getattr(enemy, "kind", "") == "baby_face_giant"
                     and not getattr(enemy, "dead", False)), None)

    def update(self, dt, ctx, interact=False):
        del interact
        if not self.arena.encounter_active:
            return
        boss = self._boss()
        if boss is None:
            return
        weapons = getattr(ctx, "weapons", None)
        deaths = (ctx.game.behavior.deaths_to("baby_face_giant")
                  if getattr(ctx, "game", None) is not None else 0)
        attempt = max(1, min(3, deaths + 1))
        boss.signature_attempt = attempt
        if weapons is not None and "excalibur" in weapons.unlocked:
            boss.moustache_progress = 1
            boss.empowered = True
            boss.artist_paused = False
            self.state = "ready"
            self.completed = True
            return
        if self.state == "waiting":
            if deaths == 0:
                self.timer += dt
                if self.timer >= 2.6:
                    boss.trigger_unfair_slap()
            elif deaths == 1:
                self.state = "moustache"
                self.timer = 0
                boss.artist_paused = True
                ctx.player.acquire_lock("baby_face_revision")
                ctx.sounds.play("pencil")
            elif deaths >= 2:
                self.state = "sword_draw"
                self.timer = 0
                boss.moustache_progress = 1
                boss.artist_paused = True
                ctx.player.acquire_lock("baby_face_revision")
                ctx.camera.script_target = (ctx.player.center_x + boss.x) * .5
                ctx.sounds.play("hero_reveal")
        if self.state == "moustache":
            self.timer += dt
            progress = min(1.0, self.timer / 1.05)
            boss.moustache_progress = progress
            moustache_x = boss.x - 24 + 48 * progress
            moustache_y = boss.ground_y - 214 - math.sin(progress * math.pi) * 7
            ctx.director.tool = ArtistTool("pencil", moustache_x, moustache_y,
                                            True, -.52, 1.2)
            ctx.director.write(boss.x - 170, boss.ground_y - 345,
                               "It's more fair now.", progress)
            if progress >= 1:
                self.state = "second_attempt"
                self.timer = 0
                boss.artist_paused = False
                ctx.player.release_lock("baby_face_revision")
                ctx.level.toast = "attempt two — still completely unfair"
                ctx.level.toast_time = 3.2
        elif self.state == "second_attempt":
            self.timer += dt
            if self.timer >= 2.25:
                boss.trigger_unfair_slap()
        elif self.state == "sword_draw":
            self.timer += dt
            self.sword_progress = min(1.0, self.timer / 1.35)
            tip_y = 552 - self.sword_progress * 128
            ctx.director.tool = ArtistTool("pencil", self.gift_x, tip_y,
                                            True, -.75, 1.25)
            ctx.director.write(self.gift_x - 168, 372,
                               "No. You get the unfair part now.",
                               min(1, self.sword_progress * 1.35), True)
            if int(self.timer * 36) % 3 == 0:
                ctx.particles.pencil_speck(self.gift_x, tip_y)
            if self.sword_progress >= 1:
                self.state = "sword_pull"
                self.timer = 0
                ctx.sounds.play("hero_sword")
        elif self.state == "sword_pull":
            self.timer += dt
            self.pull_progress = min(1.0, self.timer / .92)
            self.pull_target = (ctx.player.center_x + ctx.player.facing * 19,
                                ctx.player.rect.centery - 5)
            ctx.player.set_weapon_pose("excalibur", -.15, self.pull_progress)
            if self.pull_progress >= 1:
                weapons.unlock("excalibur")
                weapons.select("excalibur")
                boss.empowered = True
                boss.artist_paused = False
                ctx.player.release_lock("baby_face_revision")
                ctx.camera.script_target = None
                ctx.level.toast = "THIRD ATTEMPT — ONE CLEAN SWING"
                ctx.level.toast_time = 4.0
                ctx.camera.kick(12, .35)
                ctx.sounds.play("hero_sword")
                self.state = "ready"
                self.completed = True
                if getattr(ctx, "game", None) is not None:
                    ctx.game.behavior.record("artist_help", kind="excalibur",
                                             page=ctx.level.chapter_index)
                    tracker = getattr(ctx.game, "achievements", None)
                    if tracker is not None:
                        tracker.unlock("king_arthur")
                    ctx.game.persist_behavior(write=False)
                save = getattr(ctx.level, "save_system", None)
                if save is not None:
                    snapshot = weapons.snapshot()
                    save.update_combat(snapshot["unlocked"], snapshot["current_id"],
                                       snapshot["ammo"])

    def draw(self, surface, camera, renderer):
        if self.state not in ("sword_draw", "sword_pull") or self.sword_progress <= 0:
            return
        ground_world = 590
        length = 132 * self.sword_progress
        if self.state == "sword_pull":
            eased = self.pull_progress * self.pull_progress * (3 - 2 * self.pull_progress)
            hilt_x = self.gift_x + (self.pull_target[0] - self.gift_x) * eased
            hilt_y = ground_world - 36 + (self.pull_target[1] - (ground_world - 36)) * eased
            facing = 1 if self.pull_target[0] >= self.gift_x else -1
            angle = -math.pi / 2 + facing * eased * 1.08
        else:
            eased = 0
            hilt_x, hilt_y = self.gift_x, ground_world - 36
            angle = -math.pi / 2
        x = camera.screen_x(hilt_x)
        y = round(hilt_y + camera.offset_y)
        tip = (round(x + math.cos(angle) * length),
               round(y + math.sin(angle) * length))
        if self.sword_progress > .48:
            glow = pygame.Surface((260, 260), pygame.SRCALPHA)
            strength = round(42 * min(1, (self.sword_progress - .48) / .35))
            pygame.draw.circle(glow, (229, 197, 83, strength), (130, 150), 92)
            for ray in range(12):
                angle = ray * math.pi / 6
                pygame.draw.line(glow, (217, 177, 62, strength + 18),
                                 (130 + math.cos(angle) * 44,
                                  150 + math.sin(angle) * 44),
                                 (130 + math.cos(angle) * 118,
                                  150 + math.sin(angle) * 118), 2)
            surface.blit(glow, (x - 130, y - 145))
        pygame.draw.line(surface, (48, 49, 54), (x, y), tip, 9)
        pygame.draw.line(surface, (224, 194, 83), (x - 2, y - 2), tip, 2)
        guard = pygame.Vector2(-math.sin(angle), math.cos(angle)) * 25
        pygame.draw.line(surface, RED_RULE,
                         (x - guard.x, y - guard.y), (x + guard.x, y + guard.y), 6)
        if self.sword_progress > .72:
            label = "PULL" if self.state == "sword_pull" else "KING?"
            renderer.doodle_text(surface, label, (tip[0] - 38, tip[1] - 38),
                                 INK_LIGHT, renderer.font_small, -3)


def _add_page_costume_event(runtime):
    if runtime.index not in (0, 1, 2):
        return
    style = ("ronin", "cowboy", "astronaut")[runtime.index]
    label = ("wrong century", "needs a hat", "close enough to space")[runtime.index]
    trigger_x = 1120 if runtime.index == 0 else runtime.spawn[0]

    def update(ctx, progress):
        ctx.player.page_style = style if progress > .22 else "plain"
        ctx.director.tool = ArtistTool("pencil", ctx.player.center_x + 8,
                                       ctx.player.y + 9, True, -.62, 1.0)
        ctx.director.write(ctx.player.x + 58, ctx.player.y - 72,
                           label, progress)

    runtime.director.add(EventSequence(f"page_{runtime.index}_costume",
                                       lambda ctx: ctx.player.x >= trigger_x, [
        EventStep(.18, lock_player=True),
        EventStep(.72, update=update, start=lambda ctx: ctx.sounds.play("pencil"),
                  lock_player=True),
        EventStep(.16, lock_player=True),
    ]))


def _assign_platform_appearances(runtime):
    styles = {
        0: ("handwriting", "torn_edge", "ruler_line"),
        1: ("annotation", "torn_edge", "margin_rule"),
        2: ("construction", "ghost_line", "equation_box"),
        3: ("carbon", "ghost_line", "fold_edge"),
        4: ("blank_line", "annotation", "ruler_line"),
    }
    choices = styles.get(runtime.index, styles[0])
    for index, platform in enumerate(runtime.world.platforms):
        name = platform.name.lower()
        if "gate" in name or "entrance" in name or "exit" in name:
            platform.appearance = "arena_border"
        elif "bridge" in name:
            platform.appearance = choices[2]
        elif "step" in name:
            platform.appearance = choices[1]
        else:
            platform.appearance = choices[index % len(choices)]


def _prune_mechanics_catalogue(runtime, authored_end_x):
    """Remove the unreachable prototype annex from the shipping route.

    The old expansion modules are still built so their isolated regression
    tests remain useful, but their rooms, gates and checkpoints no longer sit
    invisibly beyond the page edge or inflate camera bounds.
    """
    required = set(runtime.required_ids)
    kept = []
    removed_arenas = set()
    removed_platform_ids = set()
    for entity in runtime.entities.items:
        if isinstance(entity, CombatArena):
            if entity.arena_id in required:
                kept.append(entity)
            else:
                removed_arenas.add(entity.arena_id)
            continue
        attached_arena = getattr(entity, "arena", None)
        if attached_arena is not None and isinstance(attached_arena, CombatArena):
            if attached_arena.arena_id in required:
                kept.append(entity)
            continue
        # Glyph/circuit/carbon/crease rooms belong to the prototype catalogue,
        # not the three-page campaign.  Story pressure switches do not expose
        # puzzle_id and are preserved.
        if getattr(entity, "puzzle_id", None) is not None:
            gate = getattr(entity, "gate", None)
            if gate is not None:
                removed_platform_ids.add(id(gate))
            for flap in getattr(entity, "flaps", ()):
                removed_platform_ids.add(id(flap))
            continue
        entity_x = getattr(entity, "x", getattr(entity, "start_x", 0))
        if isinstance(entity_x, (int, float)) and entity_x > runtime.end_x + 120:
            continue
        kept.append(entity)
    runtime.entities.items[:] = kept

    catalogue_names = ("expanded_ground_", "room_", "action_annex_")
    def keep_platform(platform):
        name = platform.name
        if id(platform) in removed_platform_ids:
            return False
        if name.startswith(catalogue_names):
            return False
        return not any(name.startswith(f"{arena_id}_") for arena_id in removed_arenas)

    runtime.world.platforms[:] = [platform for platform in runtime.world.platforms
                                  if keep_platform(platform)]
    runtime.world.zones[:] = [
        zone for zone in runtime.world.zones
        if zone.rect.x <= runtime.end_x
        and zone.label not in ("fresh ring", "spilled correction", "old damp paper")
    ]
    runtime.world.notes[:] = [note for note in runtime.world.notes
                              if note.x < authored_end_x - 120]
    catalogue_checkpoints = {"first_puzzle", "margin_circuit", "corrected_glyphs"}
    arena_spans = [(arena.start_x, arena.end_x) for arena in kept
                   if isinstance(arena, CombatArena)]
    runtime.checkpoints[:] = [
        cp for cp in runtime.checkpoints
        if (cp.checkpoint_id not in catalogue_checkpoints
            and float(cp.trigger_x or cp.x) <= runtime.end_x
            and (not cp.checkpoint_id.startswith("after_")
                 or cp.checkpoint_id.removeprefix("after_") in required)
            and (cp.checkpoint_id.startswith("after_")
                 or not any(start < float(cp.trigger_x or cp.x) < end
                            for start, end in arena_spans)))
    ]


def _retarget_shipping_page(runtime):
    """Remove prototype-room residue and author the first half of each world."""
    world = runtime.world
    world.doodles[:] = []
    if runtime.index == 0:
        world.notes[:] = [
            PaperNote(310, 250, "A / D MOVE     SPACE JUMP", "small", INK_LIGHT, -2, False),
            PaperNote(660, 215, "THREE HEARTS / fresh ink at every new fight", "small", INK_LIGHT, 1, False),
            PaperNote(1050, 285, "F / J CUT     SHIFT / K DASH", "small", RED_RULE, 1, True),
            PaperNote(2200, 260, "INK VILLAGE / keep the blade dry", "small", INK, -1, False),
            PaperNote(3650, 245, "DASH INTO A SHOT / return it at the last moment", "small", RED_RULE, 2, False),
        ]
    elif runtime.index == 1:
        world.notes[:] = [
            PaperNote(330, 245, "NEW PAGE. NEW HAT.", "large", INK, -2, False),
            PaperNote(1900, 300, "SIX-SHOOTER ->", "small", RED_RULE, 1, True),
            PaperNote(2920, 300, "SALOON SPILL / still slippery", "small", INK_LIGHT, -1, False),
            PaperNote(4480, 230, "DUST DEVIL  ^", "large", RED_RULE, 2, False),
            PaperNote(6280, 270, "the rails continue in the margin", "small", INK, -1, False),
        ]
        for zone in world.zones:
            if zone.kind == "margin_gravity":
                zone.kind = "dust_updraft"
                zone.label = "dust updraft"
                zone.color = (169, 119, 67, 34)
    elif runtime.index == 2:
        # Switches, escort weight and collapsing bridge were experiments from
        # the discarded puzzle page. They had no readable role in the space
        # campaign and could silently invalidate respawn geometry.
        discarded = {"PressureSwitch", "FallingDoodle", "DoodleCreature"}
        runtime.entities.items[:] = [
            entity for entity in runtime.entities.items
            if type(entity).__name__ not in discarded
        ]
        runtime.live_events[:] = [
            event for event in runtime.live_events
            if type(event).__name__ != "EraserChase"
        ]
        runtime.initial_flags = {
            "erase_wrong", "support_erased", "weight_landed",
            "bad_draft_fixed", "bridge_correction", "blot_on_switch",
            "circuit_complete",
        }
        for event in runtime.director.events:
            if event.name in runtime.initial_flags:
                event.done = True
        for checkpoint in runtime.checkpoints:
            if not checkpoint.checkpoint_id.startswith("after_"):
                checkpoint.requires = ()
        for name in ("wrong_support", "correction_bridge", "circuit_gate",
                     "fixed_step_0", "fixed_step_1", "fixed_step_2"):
            platform = world.platform_named(name)
            if platform is not None:
                platform.draw_progress = 1
                platform.erased[:] = []
                platform.appearance = "construction"
        for zone in world.zones:
            if zone.kind == "ink_hazard":
                zone.label = "leaking star ink"
        world.notes[:] = [
            PaperNote(300, 245, "AIRLOCK? / draw one later", "large", INK, -2, False),
            PaperNote(1450, 260, "gravity still works. suspicious.", "small", INK_LIGHT, 1, False),
            PaperNote(3300, 250, "ORBITAL WALKWAY / DO NOT ERASE", "small", RED_RULE, -1, True),
            PaperNote(5220, 270, "LEAKING STAR INK", "small", RED_RULE, 2, False),
            PaperNote(7040, 250, "ORBIT PULSE ->", "small", INK, -1, False),
        ]


def _add_curated_page_end(runtime):
    """Build the long themed acts from authored traversal + arena landings."""
    world = runtime.world
    if runtime.index == 0:
        pieces = [
            world.add(5480, 11050, 590, 16, "route_bamboo_road", 4101),
            world.add(6400, 6650, 500, 11, "route_temple_step_a", 4102),
            world.add(6700, 6990, 482, 11, "route_temple_step_b", 4103),
            world.add(7040, 9000, 590, 16, "route_drone_ricefield", 4104),
            world.add(8950, 9250, 495, 11, "route_torii_bridge", 4105),
            world.add(9290, 11050, 590, 16, "route_moon_gate", 4106),
        ]
        for platform, style in zip(pieces, ("handwriting", "torn_edge", "torn_edge",
                                             "ruler_line", "margin_rule", "handwriting")):
            platform.appearance = style
        world.notes.extend([
            PaperNote(5940, 300, "BAMBOO? / definitely bamboo", "small", INK_LIGHT, -2, False),
            PaperNote(7240, 265, "why does the shogun have a drone", "small", RED_RULE, 1, False),
            PaperNote(9300, 230, "MOON GATE", "large", INK, -1, False),
        ])
    elif runtime.index == 1:
        pieces = [
            world.add(4800, 6200, 590, 16, "route_dry_riverbed", 4200),
            world.add(7580, 13150, 590, 16, "route_dust_road", 4201),
            world.add(9920, 10200, 500, 11, "route_canyon_step_a", 4202),
            world.add(10240, 10520, 480, 11, "route_canyon_step_b", 4203),
            world.add(10560, 10910, 500, 11, "route_canyon_step_c", 4204),
            world.add(10900, 13150, 590, 16, "route_railroad", 4205),
        ]
        for platform, style in zip(pieces, ("annotation", "torn_edge", "torn_edge",
                                             "torn_edge", "ruler_line")):
            platform.appearance = style
        world.notes.extend([
            PaperNote(7760, 280, "WANTED: whoever drew the goblin", "large", RED_RULE, -2, True),
            PaperNote(10020, 245, "not to scale: GRAND canyon", "small", INK_LIGHT, 1, False),
            PaperNote(11120, 255, "LAST TRAIN / no timetable", "small", INK, -1, False),
        ])
    elif runtime.index == 2:
        pieces = [
            world.add(7820, 18700, 590, 16, "route_orbit_deck", 4301),
            world.add(9250, 9530, 500, 11, "route_satellite_a", 4302),
            world.add(9580, 9880, 465, 11, "route_satellite_b", 4303),
            world.add(9930, 12250, 590, 16, "route_moon_surface", 4304),
            world.add(12180, 12510, 500, 11, "route_comet_a", 4305),
            world.add(12560, 12910, 475, 11, "route_comet_b", 4306),
            world.add(12950, 16600, 590, 16, "route_baby_constellation", 4307),
            world.add(16600, 16900, 590, 16, "route_final_proof", 4308),
        ]
        for platform, style in zip(pieces, ("ghost_line", "construction", "construction",
                                             "equation_box", "ghost_line", "ghost_line",
                                             "construction", "ruler_line")):
            platform.appearance = style
        world.notes.extend([
            PaperNote(8950, 250, "ORBIT DECAYS HERE", "small", (82, 105, 123), -2, True),
            PaperNote(10400, 225, "zero gravity*  (*mostly)", "large", INK_LIGHT, 1, False),
            PaperNote(13650, 230, "UNIDENTIFIED LARGE BABY", "large", RED_RULE, -1, True),
            PaperNote(16590, 230, "CLASSIFIED / turn over", "large", INK, -2, False),
        ])


def _add_page_three_climax(runtime):
    """Separate the Baby gag from the fifth boss and give both stable retries."""
    if runtime.index != 2:
        return
    from action_content import ArenaPaperBeat
    Checkpoint = type(runtime.checkpoints[0])

    baby = CombatArena(runtime.world, 15590, 16530, "baby_face_interlude", [
        {"wave": 0, "kind": "baby_face_giant", "offset": 655},
    ], 0, False)
    baby.mandatory = True
    baby.display_name = "A VERY LARGE ACCIDENT"
    baby.boss_rule = "THREE ATTEMPTS — THE ARTIST CHEATS LAST"
    runtime.entities.add(baby)
    runtime.entities.add(ArenaPaperBeat(runtime.world, baby, "draw_cover", 0, 590))
    runtime.entities.add(BabyFaceSignatureBeat(baby, 0))

    known = {checkpoint.checkpoint_id for checkpoint in runtime.checkpoints}
    checkpoints = (
        ("after_baby_face_interlude", 16572, ("baby_face_interlude",)),
    )
    for checkpoint_id, x, requires in checkpoints:
        if checkpoint_id not in known:
            runtime.checkpoints.append(Checkpoint(checkpoint_id, x, 542, 0, x, 1, requires))
    runtime.checkpoints.sort(key=lambda checkpoint: float(checkpoint.trigger_x or checkpoint.x))
    runtime.world.notes.append(PaperNote(
        baby.start_x + 90, 220, "WHY DID I DRAW IT THAT BIG?",
        "large", RED_RULE, -2, True,
    ))


def apply_identity_pass(runtime, authored_end_x):
    """Replace the parts-bin runtime with the long three-world campaign."""
    runtime.test_content_end_x = max(runtime.end_x, PAGE_ROUTE_ENDS.get(runtime.index, 0) + 1200)
    runtime.end_x = PAGE_ROUTE_ENDS.get(runtime.index, float(authored_end_x))
    runtime.campaign_last_index = 4
    runtime.page_style = ("samurai_collage", "wild_west", "space_age",
                          "underpage", "blank_final")[runtime.index]
    runtime.required_ids = tuple(REQUIRED_SLICE_ENCOUNTERS.get(runtime.index, ()))

    required = set(runtime.required_ids)
    for entity in runtime.entities.items:
        if isinstance(entity, CombatArena):
            entity.mandatory = entity.arena_id in required
            if entity.arena_id in CURATED_SPECS:
                entity.enemy_specs = list(CURATED_SPECS[entity.arena_id])
                entity.wave_ids = sorted({int(spec.get("wave", 0))
                                          for spec in entity.enemy_specs})
        elif getattr(entity, "mandatory", False):
            # Puzzles and annex gates remain playable but never hold the page
            # hostage.  Only explicitly selected combat beats define the beta.
            entity.mandatory = False

    if runtime.index == 2:
        # The old switch/circuit remains in the mechanics catalogue, but the
        # beta route uses the line as notebook geometry rather than a gate.
        circuit = runtime.world.platform_named("circuit_gate")
        if circuit is not None:
            circuit.draw_progress = 1
            circuit.appearance = "construction"
        checkpoint = next((cp for cp in runtime.checkpoints
                           if cp.checkpoint_id == "circuit"), None)
        if checkpoint is not None:
            checkpoint.requires = ()

    _prune_mechanics_catalogue(runtime, authored_end_x)
    _retarget_shipping_page(runtime)
    _add_curated_page_end(runtime)
    _add_page_three_climax(runtime)

    for arena in (entity for entity in runtime.entities.items
                  if isinstance(entity, CombatArena)
                  and entity.arena_id in BOSS_ENCOUNTERS):
        _, display_name = BOSS_ENCOUNTERS[arena.arena_id]
        arena.boss = True
        arena.display_name = display_name
        arena.boss_rule = BOSS_RULES[arena.arena_id]

    _assign_platform_appearances(runtime)
    # The generic appearance pass intentionally skips semantic knowledge; put
    # the authored closing motifs back on top after it has styled the rest.
    route_styles = {
        "route_bamboo_road": "handwriting", "route_temple_step_a": "torn_edge",
        "route_temple_step_b": "torn_edge", "route_drone_ricefield": "ruler_line",
        "route_torii_bridge": "margin_rule", "route_moon_gate": "handwriting",
        "route_dust_road": "annotation", "route_canyon_step_a": "torn_edge",
        "route_dry_riverbed": "torn_edge",
        "route_canyon_step_b": "torn_edge", "route_canyon_step_c": "torn_edge",
        "route_railroad": "ruler_line", "route_orbit_deck": "ghost_line",
        "route_satellite_a": "construction", "route_satellite_b": "construction",
        "route_moon_surface": "equation_box", "route_comet_a": "ghost_line",
        "route_comet_b": "ghost_line", "route_baby_constellation": "construction",
        "route_final_proof": "ruler_line",
    }
    for platform in runtime.world.platforms:
        if platform.name in route_styles:
            platform.appearance = route_styles[platform.name]
    if runtime.index == 2:
        circuit = runtime.world.platform_named("circuit_gate")
        if circuit is not None:
            circuit.appearance = "construction"
    from staging import compose
    compose(runtime)
    _add_page_costume_event(runtime)
    runtime.world.notes.append(PaperNote(
        runtime.end_x - 310, 265,
        ("turn it over — the dust is getting closer" if runtime.index == 0 else
         "turn it over — the stars are badly drawn" if runtime.index == 1 else
         "there is no next coordinate"),
        "small", INK_LIGHT, -1, False,
    ))
    runtime.world.width = runtime.end_x + 220
    return runtime


__all__ = ["REQUIRED_SLICE_ENCOUNTERS", "PAGE_ROUTE_ENDS", "BOSS_ENCOUNTERS", "BOSS_RULES",
           "BabyFaceSignatureBeat", "apply_identity_pass"]
