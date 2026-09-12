"""Directional shot armour and visible, earned blade opportunities."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
from types import SimpleNamespace

import pygame

from advanced_enemies import RulerGuard, RailroadStaplerBoss
from camera import Camera
from particles import ParticleSystem
from player import Player
from weapons import PaperProjectile, WeaponSystem
from world import PaperWorld


class WeaponFeedbackContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, page=1):
        player = Player(100, 542)
        system = WeaponSystem(player)
        system.configure_page(page)
        world = PaperWorld(page=page+1, build_legacy=False)
        return system, SimpleNamespace(
            player=player, world=world, particles=ParticleSystem(),
            camera=Camera(1120), sounds=SimpleNamespace(play=lambda _: None),
            level=SimpleNamespace(toast="", toast_time=0), weapons=system,
        )

    def cut(self, system, ctx, combo, targets):
        system.current.cooldown = 0
        system.combo_index = combo-1
        system.combo_window = 1 if combo > 1 else 0
        system.handle_input(fire_pressed=True, aim={"direction": (1, 0)}, ctx=ctx)
        system.update(.05, ctx, targets)

    def target(self):
        return SimpleNamespace(rect=pygame.Rect(140, 542, 30, 48),
                               hp=20, max_hp=20, dead=False, active=True, vx=0)

    def test_banked_shot_uses_its_approach_side_for_directional_armour(self):
        for origin, speed, player_x, should_damage in (
                (463, 720, 700, True), (537, -720, 100, False)):
            system, ctx = self.context(2)
            ctx.player.x = player_x
            guard = RulerGuard(500)
            guard.facing = 1
            projectile = PaperProjectile("ink", origin, 565, speed, 0,
                                         1, 6, 1, 20)
            projectile.update(.05, ctx, [guard], [], system)
            self.assertEqual(guard.hp < guard.max_hp, should_damage)
            self.assertEqual(bool(system.impacts), should_damage,
                             "armour must not display a successful weapon cut")

        system, ctx = self.context(2)
        ctx.player.x = 700
        train = RailroadStaplerBoss(500)
        train.facing = 1
        train._set_state("rail_rush", 1)
        banked = PaperProjectile("rubber_band", 400, 565, 720, 0, 1, 6, 1, 20)
        banked.update(.05, ctx, [train], [], system)
        self.assertEqual(train.hp, train.max_hp-1,
                         "a banked shot can find the rear with its shooter ahead")

    def test_bowie_whiff_or_fresh_chain_cannot_spend_old_marks(self):
        system, ctx = self.context()
        enemy = self.target()
        self.cut(system, ctx, 1, [enemy])
        self.cut(system, ctx, 2, [])
        before = enemy.hp
        self.cut(system, ctx, 3, [enemy])
        whiffed_damage = before - enemy.hp
        self.cut(system, ctx, 1, [enemy])
        self.cut(system, ctx, 2, [enemy])
        self.assertEqual(system._bowie_marks[id(enemy)][0], 2)
        before = enemy.hp
        self.cut(system, ctx, 3, [enemy])
        self.assertGreater(before-enemy.hp, whiffed_damage+1)
        self.cut(system, ctx, 1, [enemy])
        self.cut(system, ctx, 2, [enemy])
        self.cut(system, ctx, 1, [])
        self.assertEqual(system._bowie_marks, {})

    def test_technique_marks_follow_only_live_relevant_opportunities(self):
        system, ctx = self.context()
        enemy = self.target()
        self.cut(system, ctx, 1, [enemy])
        self.cut(system, ctx, 2, [enemy])
        self.assertEqual(system.technique_cues()[0][1:3], ("cuts", 2))
        system.unlock("ink_pistol")
        system.select("ink_pistol")
        self.assertEqual(system.technique_cues(), [])
        system.select("pencil_blade")
        self.assertEqual(system.technique_cues(), [])

        system, ctx = self.context(3)
        enemy.hp = 8
        system.update(.01, ctx, [enemy])
        self.assertEqual(system.technique_cues()[0][1:3], ("execution", 1))
        system.combo_index = 2
        system.combo_window = .2
        self.assertEqual(system.technique_cues()[0][2], 2)
        enemy.is_boss = True
        self.assertEqual(system.technique_cues(), [])
        enemy.is_boss = False
        ctx.player.acquire_lock("redraw")
        self.assertEqual(system.technique_cues(), [])
        ctx.player.release_all_locks()
        enemy.dead = True
        self.assertEqual(system.technique_cues(), [])

    def test_blocked_melee_does_not_draw_a_successful_cut(self):
        system, ctx = self.context(0)
        guard = RulerGuard(160)
        guard.facing = -1
        self.cut(system, ctx, 1, [guard])
        self.assertEqual(guard.hp, guard.max_hp)
        self.assertEqual(system.impacts, [])


if __name__ == "__main__":
    unittest.main()
