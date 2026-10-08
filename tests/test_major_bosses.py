"""The expanded repertoires execute their visible promises and then stop."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import unittest
import pygame

from advanced_enemies import (MoonCompassBoss, WantedSketchBoss, RailroadStaplerBoss,
                              OrbitalMistakeBoss, ScissorDirector, FinalEditorBoss,
                              PaperProjectile)
from camera import Camera
from particles import ParticleSystem
from player import Player
from weapons import WeaponSystem
from world import PaperWorld


class MajorBossContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, x=340):
        player = Player(x, 542)
        player.on_ground = True
        world = PaperWorld(page=2, build_legacy=False)
        world.width = 1200
        return SimpleNamespace(player=player, world=world, weapons=WeaponSystem(player),
                               particles=ParticleSystem(), camera=Camera(1120), game=None,
                               level=SimpleNamespace(toast="", toast_time=0, chapter_index=1),
                               sounds=SimpleNamespace(play=lambda _: None))

    def advance(self, boss, ctx, seconds):
        for _ in range(round(seconds*120)):
            boss.update(1/120, ctx, (100, 1100))

    def test_compass_high_line_is_locked_and_spares_a_grounded_player(self):
        ctx = self.context(700)
        boss = MoonCompassBoss(600)
        boss.measure_count = 2
        boss.state_time = 0
        boss.update(.001, ctx, (100, 1100))
        self.assertEqual(boss.state, "needle_thrust_warn")
        self.assertGreaterEqual(boss.state_time, .9)
        facing, anchor = boss.facing, boss.anchor_x
        ctx.player.x = 300
        self.advance(boss, ctx, .95)
        self.assertEqual(boss.state, "needle_thrust")
        self.assertEqual((boss.facing, boss.x), (facing, anchor))
        ctx.player.x = boss.x + 120
        health = ctx.player.health
        self.advance(boss, ctx, .06)
        self.assertEqual(ctx.player.health, health, "high thrust leaves the floor safe")
        ctx.player.y = 455
        self.advance(boss, ctx, .06)
        self.assertEqual(ctx.player.health, health-1, "jumping into the shown line is dangerous")
        self.advance(boss, ctx, .45)
        self.assertEqual(boss.state, "stuck")
        self.assertTrue(boss.vulnerable)
        self.assertGreaterEqual(boss.state_time, 1.5)

    def test_outlaw_alternates_frozen_ricochet_and_clears_the_opening(self):
        ctx = self.context()
        boss = WantedSketchBoss(600)
        boss.shuffle_index = 1
        boss._shuffle(ctx, (100, 1100))
        self.assertEqual(boss.bounty_pattern, "bounty_ricochet")
        targets = [actor.bounty_target for actor in [boss]+boss.combat_targets]
        ctx.player.x = 980
        self.advance(boss, ctx, 1.18)
        self.assertEqual(boss.state, "bounty_volley")
        self.assertEqual([actor.bounty_target for actor in [boss]+boss.combat_targets], targets)
        self.assertEqual(len(boss.projectiles), 3)
        self.assertTrue(all(shot.kind == "bounty_slug" and shot.bounces_left == 1
                            for shot in boss.projectiles))
        self.advance(boss, ctx, 1.85)
        self.assertEqual(boss.state, "unravel")
        self.assertTrue(boss.vulnerable)
        self.assertEqual(boss.projectiles, [])
        boss.hit_from_weapon(1, 0, 340, {"ink"}, ctx)
        self.assertEqual(boss.state, "poster_escape")

    def test_bounced_bullet_hurts_and_can_be_dash_returned_once(self):
        ctx = self.context(1060)
        shot = PaperProjectile(1090, 566, 380, 0, "bounty_slug", gravity=0,
                               grace=0, terrain_collision=False,
                               ricochet_bounds=(100, 1100), bounces_left=1)
        shot.update(.03, ctx)
        self.assertLess(shot.vx, 0)
        self.assertEqual(shot.bounces_left, 0)
        health = ctx.player.health
        shot.update(.045, ctx)
        self.assertEqual(ctx.player.health, health-1)

        ctx = self.context(1054)
        ctx.player.dash_timer = .15
        shot = PaperProjectile(ctx.player.center_x, 566, -380, 0, "bounty_slug",
                               gravity=0, grace=0, terrain_collision=False,
                               ricochet_bounds=(100, 1100), bounces_left=0)
        shot.update(.001, ctx)
        self.assertEqual(shot.life, 0)
        self.assertTrue(ctx.player.return_used)
        self.assertEqual(len(ctx.weapons.projectiles), 1)
        self.assertGreater(ctx.weapons.projectiles[0].vx, 0)
        self.assertEqual(ctx.player.health, ctx.player.max_health)

    def test_train_alternates_low_high_crossfire_and_opens_without_live_staples(self):
        ctx = self.context(150)
        ctx.player.invulnerable = 99
        boss = RailroadStaplerBoss(900)
        boss.brake_count = 1
        boss._brake(ctx, (100, 1100))
        self.assertEqual(boss.state, "staple_cross_warn")
        self.assertGreaterEqual(boss.state_time, 1)
        lanes = list(boss.cross_lanes)
        ctx.player.x = 700
        self.advance(boss, ctx, 1.14)
        self.assertEqual(boss.state, "staple_crossfire")
        self.assertEqual(boss.cross_lanes, lanes)
        self.assertEqual(len(boss.projectiles), 2)
        self.assertEqual({shot.y for shot in boss.projectiles}, {566})
        self.advance(boss, ctx, .6)
        self.assertEqual({shot.y for shot in boss.projectiles}, {566, 466})
        self.advance(boss, ctx, 1.35)
        self.assertEqual(boss.state, "reload")
        self.assertTrue(boss.vulnerable)
        self.assertEqual(boss.projectiles, [])

    def test_comet_gap_stays_safe_and_the_moons_get_their_own_warning(self):
        ctx = self.context()
        boss = OrbitalMistakeBoss(600)
        boss._prepare_comet_corridor(ctx, (100, 1100))
        gap = boss.safe_corridor
        self.assertTrue(all(not gap[0]-9 <= lane <= gap[1]+9 for lane in boss.comet_lanes))
        health = ctx.player.health
        self.advance(boss, ctx, 1.95)
        self.assertEqual(boss.safe_corridor, gap)
        self.assertEqual(ctx.player.health, health)
        self.advance(boss, ctx, .15)
        self.assertEqual(boss.state, "moon_release_warn")
        self.assertGreater(boss.state_time, .9)
        self.assertEqual(boss.projectiles, [])

    def test_comet_lane_deals_damage_and_exposed_core_neutralizes_old_moons(self):
        ctx = self.context()
        boss = OrbitalMistakeBoss(600)
        boss._prepare_comet_corridor(ctx, (100, 1100))
        ctx.player.x = boss.comet_lanes[0] - ctx.player.WIDTH/2
        health = ctx.player.health
        self.advance(boss, ctx, 1.88)
        self.assertEqual(ctx.player.health, health-1)

        ctx = self.context()
        boss = OrbitalMistakeBoss(600)
        boss.orbiters = []
        boss.projectiles = [PaperProjectile(ctx.player.center_x, 566, 0, 0, "moon",
                                           gravity=0, grace=0, terrain_collision=False)]
        boss._set_state("moon_release", 1)
        boss.update(.001, ctx, (100, 1100))
        self.assertTrue(boss.vulnerable)
        self.assertEqual(ctx.player.health, ctx.player.max_health)
        self.assertFalse(boss.projectiles[0].damage_enabled)
        self.advance(boss, ctx, .4)
        self.assertEqual(boss.projectiles, [])

    def test_closing_bracket_hits_its_frozen_region_once_and_allows_a_jump(self):
        for jumped in (False, True):
            with self.subTest(jumped=jumped):
                ctx = self.context()
                boss = ScissorDirector(600)
                boss.pattern_index = 1
                boss._begin_pattern(ctx, (100, 1100))
                self.assertEqual(boss.state, "binding_warn")
                target = boss.target_x
                ctx.player.x = 760
                self.advance(boss, ctx, .9)
                self.assertEqual(boss.target_x, target)
                ctx.player.x = target - 12
                ctx.player.y = 440 if jumped else 542
                health = ctx.player.health
                self.advance(boss, ctx, .55)
                self.assertEqual(ctx.player.health, health if jumped else health-1)
                ctx.player.invulnerable = 0
                self.advance(boss, ctx, .25)
                self.assertEqual(ctx.player.health, health if jumped else health-1)
                self.assertEqual(boss.state, "open_hinge")
                self.assertTrue(boss.vulnerable)

    def test_final_numbered_eraser_columns_lock_then_open_and_accept_real_hits(self):
        ctx = self.context()
        boss = FinalEditorBoss(600)
        boss.scenario = "precise"
        boss.phase = 2
        boss.pattern_cursor = 1
        boss.arena_bounds = (100, 1100)
        boss._start_pattern(ctx)
        self.assertEqual(boss.pattern, "erase_columns")
        lanes = list(boss.erase_lanes)
        self.assertGreaterEqual(boss.state_time, 1)
        ctx.player.x = 900
        self.advance(boss, ctx, 1.13)
        self.assertEqual(boss.erase_lanes, lanes)
        self.assertEqual(boss.state, "erase_columns")
        self.assertTrue(all(shot.x in lanes for shot in boss.projectiles))
        self.advance(boss, ctx, 1.4)
        self.assertEqual(boss.state, "proof_window")
        self.assertEqual(boss.projectiles, [])
        hp = boss.hp
        self.assertTrue(boss.hit_from_weapon(1, 0, 100, {"ink"}, ctx))
        self.assertEqual(boss.hp, hp-1)
        self.assertEqual(boss.opening_status()[:2], (1, 2))


if __name__ == "__main__":
    unittest.main()
