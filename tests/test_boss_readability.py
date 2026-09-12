"""Visible boss promises must agree with the attacks and damage windows."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
import pygame
from game import Game
from settings import WIDTH, HEIGHT
from advanced_enemies import (MoonCompassBoss, WantedSketchBoss, RailroadStaplerBoss,
                              OrbitalMistakeBoss, ScissorDirector, FinalEditorBoss)


class BossReadabilityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.game = Game(self.screen, Path(self.temp.name)/"save.json")
        self.game.player.x, self.game.player.y = 340, 542
        self.ctx = self.game.level.context(self.game.player, self.game.camera,
                                           self.game.particles, self.game.sounds)

    def tearDown(self):
        self.temp.cleanup()

    def test_crossing_final_boss_during_warning_does_not_reverse_its_attack(self):
        for scenario, attack in (("avoidant", "counter_cut"), ("aggressive", "red_stamp")):
            boss = FinalEditorBoss(600)
            boss.scenario = scenario
            self.game.player.x = 340
            boss._start_pattern(self.ctx)
            self.assertEqual(boss.pattern, attack)
            facing, target = boss.facing, boss.proof_target
            self.game.player.x = 900
            for _ in range(44):
                boss.update(1/60, self.ctx, (100, 1200))
            self.assertEqual(boss.state, attack)
            self.assertEqual(boss.facing, facing)
            self.assertEqual(boss.proof_target, target)
            self.assertGreater(boss.vx * facing, 0)

    def test_moons_launch_along_the_displayed_frozen_trajectories(self):
        boss = OrbitalMistakeBoss(600)
        boss.y = 450
        boss.phase = 3
        boss._reset_orbiters()
        boss._prepare_release_targets(self.ctx, (100, 1200))
        boss._set_state("moon_release_warn", 1)
        indices = list(boss.orbiters)
        positions = {i: boss._moon_position(i) for i in indices}
        targets = dict(boss.release_targets)
        for _ in range(45):
            self.game.player.x += 4
            boss.update(1/60, self.ctx, (100, 1200))
            self.assertEqual({i: boss._moon_position(i) for i in indices}, positions)
            self.assertEqual(boss.release_targets, targets)
        boss._set_state("moon_release", 1.2)
        for i in indices:
            boss.shot_timer = 0
            boss.update(.001, self.ctx, (100, 1200))
            shot = boss.projectiles[-1]
            expected = (pygame.Vector2(targets[i]) - positions[i]).normalize()
            self.assertAlmostEqual(pygame.Vector2(shot.vx, shot.vy).normalize().dot(expected), 1)

    def test_opening_marks_count_real_hits_and_close_with_the_boss(self):
        cases = ((MoonCompassBoss, "stuck", 2), (WantedSketchBoss, "bounty_draw", 1),
                 (RailroadStaplerBoss, "reload", 2), (OrbitalMistakeBoss, "unravel", 3),
                 (ScissorDirector, "open_hinge", 3), (FinalEditorBoss, "proof_window", 2))
        for kind, state, budget in cases:
            with self.subTest(boss=kind.__name__):
                boss = kind(650)
                if hasattr(boss, "orbiters"):
                    boss.orbiters.clear()
                boss._set_state(state, 2)
                for hit in range(budget):
                    self.assertEqual(boss.opening_status()[:2], (budget-hit, budget))
                    boss.invulnerable = 0
                    self.assertTrue(boss.hit_from_weapon(1, 0, 400, {"ink"}, self.ctx))
                status = boss.opening_status()
                self.assertTrue(status is None or status[0] == 0)
                boss.invulnerable = 0
                health = boss.hp
                self.assertFalse(boss.hit_from_weapon(1, 0, 400, {"ink"}, self.ctx))
                self.assertEqual(boss.hp, health)

    def test_opening_cue_expires_and_armoured_core_never_shows_free_hits(self):
        boss = MoonCompassBoss(600)
        self.assertIsNone(boss.opening_status())
        boss._set_state("stuck", 2)
        boss.state_time = .5
        self.assertEqual(boss.opening_status(), (2, 2, .25))
        boss.state_time = 0
        self.assertIsNone(boss.opening_status())
        boss = OrbitalMistakeBoss(600)
        boss._set_state("unravel", 2)
        self.assertEqual(boss.opening_status()[0], 0)
