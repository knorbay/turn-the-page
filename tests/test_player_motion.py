"""Animation must stay bounded and must never affect the controller."""
from __future__ import annotations

import copy
import math
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from camera import Camera
from particles import ParticleSystem
from player import Player
from world import PaperWorld


class PlayerMotionContracts(unittest.TestCase):
    def setUp(self):
        self.world = PaperWorld(page=1, build_legacy=False)
        self.world.add(0, 20000, 590, 18, "motion_test_floor", 18)
        self.player = Player(150, 542)
        self.player.on_ground = self.player.was_grounded = True
        self.particles = ParticleSystem()

    def tick(self, frames=1, axis=1, dt=1/120):
        for _ in range(frames):
            self.player.update(dt, axis, self.world, self.particles)

    def test_stance_foot_remains_planted_while_body_advances(self):
        self.player.motion_speed = 1
        self.player.vx = 285
        self.player.stride_phase = .12 * math.tau
        before = self.player._body_pose()["legs"][0][1]
        self.tick(1, dt=1/240)
        after = self.player._body_pose()["legs"][0][1]
        self.assertAlmostEqual(before[0], after[0], places=5)
        self.assertEqual(before[1], after[1])

    def test_dash_impressions_expire_and_repeated_dashes_remain_bounded(self):
        for _ in range(12):
            self.player.dash_cooldown = 0
            self.assertTrue(self.player.start_dash())
            self.tick(15)
            self.assertGreater(len(self.player.dash_impressions), 0)
            self.assertLessEqual(len(self.player.dash_impressions), 5)
            self.tick(45)
            self.assertEqual(self.player.dash_impressions, [])

    def test_redraw_death_lock_and_teleport_remove_previous_page_traces(self):
        for transition in ("redraw", "death", "lock", "teleport"):
            with self.subTest(transition=transition):
                self.setUp()
                self.player.start_dash()
                self.tick(6)
                self.assertTrue(self.player.dash_impressions)
                if transition == "redraw":
                    self.player.draw_amount = .2
                elif transition == "death":
                    self.player.health = 0
                elif transition == "lock":
                    self.player.acquire_lock("page_turn")
                else:
                    self.player.x += 1500
                self.tick()
                self.assertEqual(self.player.dash_impressions, [])

    def test_draw_is_read_only_across_costumes_and_camera_positions(self):
        self.player.start_dash()
        self.tick(8)
        self.player.combat_swing = (-.65, 64, .8)
        target = pygame.Surface((640, 480))
        camera = Camera(640)
        for page, style in enumerate(("ronin", "cowboy", "astronaut", "ink_agent", "bad_drawing")):
            self.player.arsenal_page = page
            self.player.page_style = style
            before = copy.deepcopy(self.player.__dict__)
            for x in (0, 120, 900):
                camera.x = x
                self.player.draw(target, camera)
            self.assertEqual(self.player.__dict__, before)

    def test_animation_state_cannot_change_jump_or_dash_physics(self):
        other = copy.deepcopy(self.player)
        self.player.stride_phase = 2.4
        self.player.motion_speed = .8
        for frame in range(100):
            if frame == 5:
                self.player.queue_jump()
                other.queue_jump()
            if frame == 40:
                self.player.start_dash()
                other.start_dash()
            self.player.update(1/120, 1, self.world, self.particles)
            other.update(1/120, 1, self.world, self.particles)
            for attribute in ("x", "y", "vx", "vy", "on_ground", "health", "dash_timer"):
                self.assertEqual(getattr(self.player, attribute), getattr(other, attribute))

    def test_redraw_pencil_reaches_the_visible_articulated_leg(self):
        for variant in ("clean", "long_leg", "long_arm", "rushed", "crooked_head"):
            self.player.redraw_variant = variant
            for progress in (.65, .735, .85, .94, 1):
                self.player.draw_amount = progress
                pose = self.player._body_pose()
                index = 0 if progress < .76 else 1
                knee, foot = pose["legs"][index]
                begin, middle, end = (.60, .71, .82) if index == 0 else (.76, .88, 1)
                a, b = (pose["hip"], knee) if progress < middle else (knee, foot)
                start, finish = (begin, middle) if progress < middle else (middle, end)
                t = (progress-start)/(finish-start)
                expected = (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
                for actual, wanted in zip(self.player.redraw_tip(), expected):
                    self.assertAlmostEqual(actual, wanted)

    def test_redraw_pencil_starts_on_the_visible_head_arc(self):
        self.player.redraw_variant = "crooked_head"
        self.player.draw_amount = 0
        pose = self.player._body_pose()
        self.assertEqual(self.player.redraw_tip(),
                         (pose["head"][0], pose["head"][1]+pose["radius"]))


if __name__ == "__main__":
    unittest.main()
