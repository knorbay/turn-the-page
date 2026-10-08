"""A barrel, both wrists and a bounded silhouette must share the real pose."""
import math
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
from types import SimpleNamespace
import unittest

import pygame

from page_arsenal import draw_weapon, profile_for
from player import Player
from weapons import WeaponSystem


class HeldWeaponProportions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def actor(self, page, weapon):
        player = Player(200, 542)
        player.on_ground = True
        system = WeaponSystem(player)
        system.configure_page(page)
        system.lend_drawn_tool(weapon)
        return player, system

    def tool_bounds(self, player):
        pose = player.weapon_attachment()
        surface = pygame.Surface((1120, 700), pygame.SRCALPHA)
        draw_weapon(surface, player.current_weapon, player.arsenal_page,
                    pose.draw_origin, pose.angle, pose.scale)
        return surface.get_bounding_rect()

    def test_handguns_remain_smaller_than_the_figure_and_rifle_has_room_for_two_hands(self):
        for page in (None, 1, 3):
            player, _ = self.actor(page, "ink_pistol")
            bounds = self.tool_bounds(player)
            self.assertLess(bounds.width, player.HEIGHT * .65)
            self.assertLess(bounds.height, player.HEIGHT * .50)
            self.assertLess(player.weapon_attachment().grip.distance_to(player._body_pose()["shoulder"]), 23)
        player, _ = self.actor(3, "carbon_lance")
        pose = player.weapon_attachment()
        self.assertTrue(pose.two_handed)
        self.assertGreater(pose.support.x, pose.grip.x + 7)
        self.assertLess(pose.support.x, pose.muzzle.x - 10)
        self.assertLess(self.tool_bounds(player).width, player.HEIGHT * 1.15)

    def test_projectiles_and_flash_start_at_the_drawn_barrel_in_every_aim_direction(self):
        for page, weapon in ((1, "ink_pistol"), (3, "ink_pistol"), (1, "marker_shotgun"),
                              (2, "eraser_cannon"), (2, "rubber_band"), (3, "carbon_lance")):
            for angle in (0, math.pi, -1.1, -2.04):
                with self.subTest(page=page, weapon=weapon, angle=angle):
                    player, system = self.actor(page, weapon)
                    player.facing = 1 if math.cos(angle) >= 0 else -1
                    player.aim_angle = angle
                    expected = player.weapon_attachment().muzzle
                    self.assertTrue(system.handle_input(fire_pressed=True,
                        aim={"direction": (math.cos(angle), math.sin(angle))}, ctx=SimpleNamespace()))
                    shot = system.projectiles[0]
                    self.assertAlmostEqual(shot.x, expected.x)
                    self.assertAlmostEqual(shot.y, expected.y)
                    flash = next(mark for mark in system.impacts if mark.kind.endswith("_muzzle"))
                    self.assertAlmostEqual(flash.x, shot.x)
                    self.assertAlmostEqual(flash.y, shot.y)
                    self.assertEqual(system.current.ammo, system.current.mag_size - 1
                                     if system.current.mag_size > 0 else -1)

    def test_knives_keep_their_size_when_sketch_or_combo_extends_combat_reach(self):
        for page in (1, 3):
            player, system = self.actor(page, "pencil_blade")
            player.combat_swing = (.1, 60, .8)
            ordinary = self.tool_bounds(player)
            player.combat_swing = (.1, 140, .8)
            extended = self.tool_bounds(player)
            self.assertEqual(ordinary.size, extended.size)
            self.assertLess(extended.width, player.HEIGHT * .60)
            system.handle_input(fire_pressed=True, ctx=SimpleNamespace())
            self.assertGreater(system.melee.reach, extended.width * 1.5,
                               "physical combat reach still belongs to the committed cut")

    def test_left_aim_keeps_grip_below_barrel_and_support_between_fist_and_muzzle(self):
        for page, weapon in ((1, "marker_shotgun"), (3, "carbon_lance"), (2, "eraser_cannon")):
            player, _ = self.actor(page, weapon)
            player.facing = -1
            player.aim_angle = math.pi
            pose = player.weapon_attachment()
            self.assertGreater(pose.grip.y, pose.muzzle.y)
            self.assertLess(pose.support.x, pose.grip.x)
            self.assertGreater(pose.support.x, pose.muzzle.x)
            self.assertLess(pose.support.distance_to(player._body_pose()["shoulder"]), 34)

    def test_reload_is_lowered_and_contact_points_follow_recoil_and_squash(self):
        for page, weapon in ((1, "ink_pistol"), (1, "marker_shotgun"), (3, "carbon_lance")):
            player, _ = self.actor(page, weapon)
            aimed = player.weapon_attachment()
            player.weapon_reload_progress = .5
            reload_pose = player.weapon_attachment()
            self.assertGreater(reload_pose.grip.y, aimed.grip.y)
            self.assertGreater(reload_pose.muzzle.y, reload_pose.grip.y,
                               "a lowered reload tilts the barrel toward the ground")
            self.assertLess(reload_pose.support.distance_to(reload_pose.grip), 20)
            player.weapon_reload_progress = None
            player.weapon_recoil = .7
            player.land_squash = .18
            recoiled = player.weapon_attachment()
            self.assertNotEqual(recoiled.grip, aimed.grip)
            self.assertLess(recoiled.grip.distance_to(player._body_pose()["shoulder"]), 23)


if __name__ == "__main__":
    unittest.main()
