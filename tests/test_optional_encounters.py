"""Reachable opt-in duels preserve their clear and their unclaimed reward."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from camera import Camera
from chapters import build_chapter
from game import Game
from level import Level
from major_campaign import SecretPocket
from margin_guardians import GuardianProjectile
from optional_encounters import OPTIONAL_DUELS, OptionalGuardianPocket
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from route_expeditions import RouteExpedition
from save_system import SaveSystem
from sketches import SKETCHES, apply_sketch_rewards, derive_modifiers
from weapons import WeaponSystem, _live_enemies


class OptionalGuardianContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, page):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        save = SaveSystem(Path(folder.name)/"save.json")
        level = Level(save, page)
        pocket = next(e for e in level.entities.items if isinstance(e, OptionalGuardianPocket))
        player = Player(pocket.base+48, 590-Player.HEIGHT)
        player.on_ground = True
        player.draw_amount = 1
        level.weapons = WeaponSystem(player)
        level.weapons.configure_page(page)
        ctx = level.context(player, Camera(1120), ParticleSystem(), Mock())
        return level, pocket, ctx, save

    def reveal_route(self, pocket, ctx):
        pocket.update(.01, ctx, True)
        self.assertTrue(pocket.entrance_open)
        for _ in range(50):
            pocket.update(1/60, ctx)
        self.assertEqual(pocket.entrance_progress, 1)
        ctx.player.x, ctx.player.y = pocket.bounds[0]+35, pocket.ground-Player.HEIGHT

    def challenge(self, pocket, ctx):
        self.reveal_route(pocket, ctx)
        pocket.update(.01, ctx, True)
        self.assertTrue(pocket.encounter_active)
        for _ in range(53):
            pocket.update(1/60, ctx)
        self.assertEqual(pocket.reveal, 1)
        return pocket.enemies[0]

    def defeat(self, pocket, ctx):
        enemy = self.challenge(pocket, ctx)
        for _ in range(5):
            enemy._open(ctx)
            for _ in range(2):
                enemy.invulnerable = 0
                self.assertTrue(ctx.weapons.damage_enemy(enemy, 1, 1, 0, 0, "pencil", ctx))
        self.assertTrue(enemy.dead)
        pocket.update(.01, ctx)

    def test_four_side_routes_preserve_the_old_secret_and_heart_routes(self):
        expected_old_secrets = {0: ("cloud",), 1: ("fold",), 2: (), 3: ("carbon",), 4: ()}
        for page in range(5):
            runtime = build_chapter(page)
            self.assertEqual(tuple(e.kind for e in runtime.entities.items if isinstance(e, SecretPocket)),
                             expected_old_secrets[page])
            self.assertEqual(sum(isinstance(e, RouteExpedition) for e in runtime.entities.items), 1)
            pockets = [e for e in runtime.entities.items if isinstance(e, OptionalGuardianPocket)]
            self.assertEqual(len(pockets), int(page > 0))
            for pocket in pockets:
                self.assertFalse(pocket.mandatory)
                self.assertFalse(pocket.entrance_open)
                self.assertTrue(all(not p.collision_rects() for p in pocket.steps))
                self.assertNotIn(pocket.sketch.secret_id, runtime.required_ids)
                self.assertEqual(pocket.bounds[1]-pocket.bounds[0], 520)
                for arena in runtime.entities.items:
                    if getattr(arena, "is_combat_arena", False):
                        self.assertFalse(pocket.base < arena.end_x and pocket.bounds[1] > arena.start_x)
        self.assertEqual(len(SKETCHES), 19)

    def test_every_new_route_reaches_its_deck_with_normal_jumps(self):
        for page in range(1, 5):
            with self.subTest(page=page):
                _, pocket, ctx, _ = self.context(page)
                self.reveal_route(pocket, ctx)
                player = ctx.player
                player.x, player.y = pocket.base+12, 590-Player.HEIGHT
                for landing in pocket.steps:
                    player.queue_jump()
                    reached = False
                    for _ in range(200):
                        target = (landing.x1+landing.x2)/2
                        axis = 1 if player.center_x < target-5 else -1 if player.center_x > target+5 else 0
                        player.update(1/120, axis, ctx.world, ctx.particles)
                        if player.on_ground and abs(player.rect.bottom-landing.y) < 2:
                            reached = True
                            break
                    self.assertTrue(reached, (landing.name, player.x, player.y))
                self.assertFalse(pocket.encounter_active)

    def test_main_road_input_and_unrevealed_ink_cannot_start_or_damage_a_guardian(self):
        for page in range(1, 5):
            _, pocket, ctx, save = self.context(page)
            self.assertFalse(pocket.begin(ctx))
            self.reveal_route(pocket, ctx)
            ctx.player.y = 590-Player.HEIGHT
            pocket.update(.01, ctx, True)
            self.assertFalse(pocket.encounter_active)
            ctx.player.y = pocket.ground-Player.HEIGHT
            pocket.update(.01, ctx, True)
            enemy = pocket.enemies[0]
            self.assertEqual(enemy.notebook_reveal, 0)
            self.assertIs(ctx.director.canvas_owner, pocket)
            self.assertNotIn(enemy, _live_enemies(ctx.level.entities))
            self.assertFalse(ctx.weapons.damage_enemy(enemy, 99, 1, 0, 0, "ink", ctx))
            self.assertEqual(enemy.hp, 10)
            pocket.sketch.update(.01, ctx, True)
            self.assertEqual(save.data["secrets"], [])

    def test_guardian_waits_for_clear_paper_before_becoming_solid(self):
        _, pocket, ctx, _ = self.context(2)
        self.reveal_route(pocket, ctx)
        pocket.begin(ctx)
        enemy = pocket.enemies[0]
        ctx.player.x = enemy.x-Player.WIDTH/2
        pocket.update(1.0, ctx)
        self.assertLess(enemy.notebook_reveal, 1)
        self.assertIs(ctx.director.canvas_owner, pocket)
        ctx.player.x = pocket.bounds[0]+35
        pocket.update(.05, ctx)
        self.assertEqual(enemy.notebook_reveal, 1)
        self.assertIsNone(ctx.director.canvas_owner)
        self.assertIn(enemy, _live_enemies(ctx.level.entities))

    def test_victory_persists_before_collection_and_rune_collects_once(self):
        for page in range(1, 5):
            with self.subTest(page=page):
                level, pocket, ctx, save = self.context(page)
                self.defeat(pocket, ctx)
                self.assertTrue(pocket.completed)
                self.assertFalse(pocket.encounter_active)
                self.assertFalse(pocket.boss_cue_started)
                self.assertEqual(save.data["secrets"], [])
                restored_save = SaveSystem(save.path)
                self.assertEqual(restored_save.data["optional_bosses"], [pocket.kind])
                # Reload before pressing E on the reward: no fight, intact
                # staircase and an available physical rune on the deck.
                restored = Level(restored_save, page)
                reward_pocket = next(e for e in restored.entities.items if isinstance(e, OptionalGuardianPocket))
                self.assertTrue(reward_pocket.completed)
                self.assertFalse(reward_pocket.sketch.discovered)
                self.assertTrue(all(p.collider_active for p in reward_pocket.steps))
                ctx = restored.context(ctx.player, ctx.camera, ctx.particles, ctx.sounds)
                ctx.player.x, ctx.player.y = reward_pocket.sketch.x-12, reward_pocket.ground-Player.HEIGHT
                self.assertFalse(reward_pocket.begin(ctx))
                reward_pocket.sketch.update(.01, ctx, True)
                reward_pocket.sketch.update(.01, ctx, True)
                self.assertEqual(SaveSystem(save.path).data["secrets"], [reward_pocket.sketch.secret_id])
                self.assertEqual(derive_modifiers([reward_pocket.sketch.secret_id]*5),
                                 derive_modifiers([reward_pocket.sketch.secret_id]))

    def test_leave_death_competing_fight_and_reload_clear_music_canvas_and_ink(self):
        for exit_kind in ("leave", "death", "other_fight", "reload"):
            with self.subTest(exit=exit_kind):
                level, pocket, ctx, save = self.context(3)
                self.reveal_route(pocket, ctx)
                pocket.begin(ctx)
                enemy = pocket.enemies[0]
                enemy.projectiles.append(GuardianProjectile(enemy.x, enemy.y, 10, 0, "ink"))
                pocket.hand.tool.visible = True
                old_director = ctx.director
                game = Game.__new__(Game)
                game.level, game.sounds = level, ctx.sounds
                game._update_combat_music()
                ctx.sounds.set_combat.assert_called_with(True, True, pocket.kind)
                if exit_kind == "leave":
                    ctx.player.y = 590-Player.HEIGHT
                    pocket.update(.01, ctx)
                elif exit_kind == "death":
                    ctx.player.health = 0
                    level.begin_respawn(ctx.player, pocket.kind, ctx.particles, ctx.sounds)
                elif exit_kind == "other_fight":
                    level.entities.add(SimpleNamespace(encounter_active=True, completed=False))
                    pocket.update(.01, ctx)
                    level.entities.items.pop()
                else:
                    level.load_chapter(3, "start", ctx.player, ctx.camera)
                game._update_combat_music()
                ctx.sounds.set_combat.assert_called_with(False)
                self.assertEqual(enemy.projectiles, [])
                self.assertEqual(pocket.enemies, [])
                self.assertFalse(pocket.encounter_active)
                self.assertFalse(pocket.boss_cue_started)
                self.assertFalse(pocket.hand.tool.visible)
                self.assertIsNone(old_director.canvas_owner)
                self.assertEqual(save.data["optional_bosses"], [])
                with patch("boss_presentation.draw_boss_entrance") as card:
                    pocket.draw_overlay(pygame.Surface((1120,700)), ctx.camera, self.renderer)
                card.assert_not_called()

    def test_opening_bell_and_two_hit_marks_use_the_actual_guardian(self):
        for page in range(1, 5):
            _, pocket, ctx, _ = self.context(page)
            enemy = self.challenge(pocket, ctx)
            ctx.sounds.play.reset_mock()
            enemy._open(ctx)
            ctx.sounds.play.assert_called_once_with("boss_opening")
            self.assertEqual(enemy.opening_status()[:2], (2, 2))
            enemy.invulnerable = 0
            ctx.weapons.damage_enemy(enemy, 1, 1, 0, 0, "pencil", ctx)
            self.assertEqual(enemy.opening_status()[:2], (1, 2))
            pocket.abort(ctx)
            ctx.sounds.play.reset_mock()
            pocket.update(.1, ctx)
            ctx.sounds.play.assert_not_called()

    def test_new_runes_change_real_dash_reload_projectile_and_blade_values(self):
        baseline = Player()
        rewarded = Player()
        ids = [spec.rune for spec in OPTIONAL_DUELS]
        apply_sketch_rewards(rewarded, ids*3)
        baseline.start_dash(1)
        rewarded.start_dash(1)
        self.assertAlmostEqual(baseline.dash_cooldown-rewarded.dash_cooldown, .06)
        systems = [WeaponSystem(player) for player in (baseline, rewarded)]
        for system in systems:
            system.configure_page(3)
            system.lend_drawn_tool("ink_pistol")
            system.current.ammo = 0
            system.current.start_reload()
        self.assertAlmostEqual(systems[1].current.reload_duration/systems[0].current.reload_duration, .90)
        shots, reaches = [], []
        for system in systems:
            system.configure_page(2)
            system.lend_drawn_tool("rubber_band")
            system.current.fire(system, SimpleNamespace())
            shots.append(system.projectiles[-1].life)
            system.configure_page(4)
            system.lend_drawn_tool("pencil_blade")
            system.combo_index = 2
            system.combo_window = .4
            system.current.fire(system, SimpleNamespace())
            reaches.append(system.melee.reach)
        self.assertAlmostEqual(shots[1]/shots[0], 1.20)
        self.assertAlmostEqual(reaches[1]-reaches[0], 12)
        self.assertEqual(rewarded.max_health, baseline.max_health)

    def test_optional_clear_schema_repairs_and_resets_only_on_new_campaign(self):
        _, _, _, save = self.context(1)
        save.path.write_text(json.dumps({"optional_bosses": ["orbit_crab", "orbit_crab", None, {}],
                                        "secrets": ["old_first_figure"]}), encoding="utf8")
        restored = SaveSystem(save.path)
        self.assertEqual(restored.data["optional_bosses"], ["orbit_crab"])
        self.assertEqual(restored.data["secrets"], ["old_first_figure"])
        restored.checkpoint(3, "start")
        self.assertEqual(SaveSystem(save.path).data["optional_bosses"], ["orbit_crab"])
        restored.new_game()
        self.assertEqual(SaveSystem(save.path).data["optional_bosses"], [])


if __name__ == "__main__":
    unittest.main()
