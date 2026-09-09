"""Focused regressions for action progression and authored arena geometry.

These tests stay below the game-loop level on purpose.  They exercise the
same save, player collision, and chapter factories used by a real playthrough
without replaying the campaign simulation in ``test_paper_story``.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from action_content import ACTION_ENCOUNTER_IDS, WeaponPickup
from advanced_enemies import ENEMY_TYPES
from camera import Camera
from chapters import build_chapter
from combat import CombatArena, LEGACY_ENEMY_TYPES
from particles import ParticleSystem
from player import Player
from save_system import SaveSystem
from settings import WIDTH
from weapons import WeaponSystem
from world import PaperWorld


class _SilentSounds:
    def play(self, _name):
        pass


class ActionRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_weapon_pickup_unlocks_selects_and_persists_immediately(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "pickup-save.json")
            save = SaveSystem(save_path)
            player = Player(200, 542)
            weapons = WeaponSystem(player)
            world = PaperWorld(page=1, build_legacy=False)
            level = SimpleNamespace(
                flags=set(), interaction_hint="", toast="", toast_time=0.0,
                save_system=save,
            )
            context = SimpleNamespace(
                player=player,
                weapons=weapons,
                world=world,
                level=level,
                particles=ParticleSystem(),
                sounds=_SilentSounds(),
                camera=Camera(WIDTH),
            )
            pickup = WeaponPickup(player.center_x, 590, "ink_pistol", label="INK PISTOL")

            # The Artist must visibly finish the weapon before it can exist in
            # the loadout; completion still saves immediately.
            pickup.update(.25, context)
            self.assertFalse(pickup.collected)
            self.assertGreater(pickup.draw_progress, 0)
            for _ in range(80):
                pickup.update(1 / 60, context)
                if pickup.collected:
                    break

            self.assertTrue(pickup.collected)
            self.assertTrue(pickup.completed)
            self.assertIn("pickup_ink_pistol", level.flags)
            self.assertIn("ink_pistol", weapons.unlocked)
            self.assertEqual(weapons.current_id, "ink_pistol")
            self.assertTrue(os.path.exists(save_path))

            reloaded = SaveSystem(save_path)
            self.assertIn("ink_pistol", reloaded.data["weapons"])
            self.assertEqual(reloaded.data["current_weapon"], "ink_pistol")
            self.assertEqual(
                reloaded.data["weapon_ammo"]["ink_pistol"],
                weapons.weapons["ink_pistol"].ammo,
            )

    def test_dash_cannot_tunnel_through_closed_thin_arena_gate_at_30_fps(self):
        world = PaperWorld(page=0, build_legacy=False)
        world.width = 900
        world.add(0, 900, 590, 18, "dash_test_floor", 1401)
        arena = CombatArena(
            world, 300, 700, "dash_gate_regression",
            [{"wave": 0, "kind": "crawler", "offset": 210}],
        )
        self.assertTrue(arena.exit_gate.enabled)
        gate_rect = list(arena.exit_gate.collision_rects())[0]
        player = Player(gate_rect.left - Player.WIDTH - 2, 542)
        player.on_ground = True
        particles = ParticleSystem()

        self.assertTrue(player.start_dash(1, particles))
        # At 690 px/s the first 30 FPS frame moves 23 px, enough to skip this
        # 22 px ink stroke without swept/substep collision.
        for _ in range(6):
            player.update(1 / 30, 1, world, particles)
            self.assertLessEqual(player.rect.right, gate_rect.left)
        self.assertLess(player.center_x, arena.end_x)

    def test_all_action_factories_build_ordered_in_bounds_encounters(self):
        declared = tuple(ACTION_ENCOUNTER_IDS)
        self.assertEqual(len(declared), len(set(declared)), "encounter ids must be unique")
        built: dict[str, tuple[int, CombatArena]] = {}

        for chapter_index in range(5):
            with self.subTest(chapter=chapter_index):
                runtime = build_chapter(chapter_index)
                self.assertLessEqual(runtime.end_x, runtime.world.width)

                checkpoints = runtime.checkpoints
                checkpoint_ids = [checkpoint.checkpoint_id for checkpoint in checkpoints]
                self.assertEqual(len(checkpoint_ids), len(set(checkpoint_ids)))
                trigger_positions = [
                    float(checkpoint.trigger_x or checkpoint.x)
                    for checkpoint in checkpoints
                ]
                self.assertEqual(trigger_positions, sorted(trigger_positions))
                for checkpoint, trigger_x in zip(checkpoints, trigger_positions):
                    self.assertGreaterEqual(checkpoint.x, 0)
                    self.assertLessEqual(checkpoint.x, runtime.world.width)
                    self.assertGreaterEqual(trigger_x, 0)
                    self.assertLessEqual(trigger_x, runtime.world.width)
                    self.assertIn(checkpoint.layer, (0, 1))

                for entity in runtime.entities.items:
                    if not isinstance(entity, CombatArena) or entity.arena_id not in declared:
                        continue
                    self.assertNotIn(entity.arena_id, built)
                    built[entity.arena_id] = (chapter_index, entity)
                    self.assertLess(entity.start_x, entity.end_x)
                    self.assertGreaterEqual(entity.entrance_gate.x1, 0)
                    self.assertLessEqual(entity.exit_gate.x2, runtime.world.width)
                    self.assertEqual(entity.entrance_gate.layer, entity.layer)
                    self.assertEqual(entity.exit_gate.layer, entity.layer)

                    checkpoint_id = f"after_{entity.arena_id}"
                    checkpoint = next(
                        (item for item in checkpoints if item.checkpoint_id == checkpoint_id),
                        None,
                    )
                    self.assertIsNotNone(checkpoint, checkpoint_id)
                    self.assertIn(entity.arena_id, checkpoint.requires)
                    self.assertEqual(checkpoint.layer, entity.layer)
                    self.assertGreaterEqual(float(checkpoint.trigger_x or checkpoint.x), entity.end_x)
                    self.assertLessEqual(checkpoint.x, runtime.world.width)

                    self._assert_valid_enemy_specs(entity)

        self.assertEqual(set(built), set(declared))
        self.assertEqual(len(built), len(declared))

    def _assert_valid_enemy_specs(self, arena):
        """Mirror CombatArena's placement contract without spawning enemies."""
        valid_kinds = set(LEGACY_ENEMY_TYPES) | set(ENEMY_TYPES)
        for wave in arena.wave_ids:
            counter = 0
            specs = [spec for spec in arena.enemy_specs if int(spec.get("wave", 0)) == wave]
            self.assertTrue(specs, f"{arena.arena_id} has an empty declared wave {wave}")
            for spec in specs:
                kind = str(spec.get("kind", "crawler")).strip().lower()
                kind = kind.replace("-", "_").replace(" ", "_")
                self.assertIn(kind, valid_kinds, f"unknown enemy kind {kind!r}")
                count = int(spec.get("count", 1))
                self.assertGreaterEqual(count, 1)
                for index in range(count):
                    if "x" in spec:
                        base_x = float(spec["x"])
                    elif "offset" in spec:
                        base_x = arena.start_x + float(spec["offset"])
                    else:
                        base_x = arena.start_x + 250 + counter * 130
                    spawn_x = base_x + index * float(spec.get("spacing", 95))
                    self.assertGreaterEqual(spawn_x, arena.start_x)
                    self.assertLessEqual(spawn_x, arena.end_x)
                    ground_y = float(spec.get("ground_y", spec.get("y", 590)))
                    self.assertGreater(ground_y, 0)
                    self.assertLess(ground_y, 850)
                    counter += 1


if __name__ == "__main__":
    unittest.main()
