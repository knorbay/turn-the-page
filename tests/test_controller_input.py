"""Common gamepad input contracts for gameplay and notebook menus."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game
from settings import HEIGHT, WIDTH


class _FakeJoystick:
    def get_numaxes(self):
        return 1

    def get_axis(self, axis):
        return -.8 if axis == 0 else 0.0

    def get_numbuttons(self):
        return 6

    def get_button(self, button):
        return int(button in (0, 2))

    def get_numhats(self):
        return 1

    def get_hat(self, index):
        return 0, 0


class ControllerInputContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_game(self):
        directory = tempfile.TemporaryDirectory()
        display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
        game = Game(display, Path(directory.name) / "save.json")
        return directory, game

    def test_common_pad_buttons_cover_core_combat_actions(self):
        directory, game = self.make_game()
        try:
            game.state = "playing"
            for button in range(6):
                game._controller_button_down(button)
            self.assertTrue(game.pending_input.jump_pressed)
            self.assertTrue(game.pending_input.dash_pressed)
            self.assertTrue(game.pending_input.attack_pressed)
            self.assertTrue(game.pending_input.interact)
            self.assertEqual(game.pending_input.weapon_cycle, -1)
            self.assertTrue(game.pending_input.reload_pressed)

            game._controller_button_up(0)
            self.assertTrue(game.pending_input.jump_released)
            game._controller_button_down(7)
            self.assertEqual(game.state, "pause")
            game._controller_button_down(1)
            self.assertEqual(game.state, "playing")
        finally:
            directory.cleanup()

    def test_held_stick_and_buttons_join_the_sampled_input_frame(self):
        directory, game = self.make_game()
        try:
            game.state = "playing"
            game.joysticks = {7: _FakeJoystick()}
            frame = game._sample_input()
            self.assertTrue(frame.left)
            self.assertFalse(frame.right)
            self.assertTrue(frame.jump_held)
            self.assertTrue(frame.attack_held)
            self.assertIsNone(frame.aim_x)
            self.assertIsNone(frame.aim_y)
        finally:
            directory.cleanup()

    def test_dpad_and_confirm_navigate_title_settings_and_pause(self):
        directory, game = self.make_game()
        try:
            game.state = "title"
            game.menu_index = game._title_options().index("SETTINGS")
            game._controller_button_down(0)
            self.assertEqual(game.state, "settings")

            before = game.save.data["settings"]["master_volume"]
            game.settings_index = 0
            game._controller_hat((-1, 0))
            self.assertLess(game.save.data["settings"]["master_volume"], before)
            game._controller_button_down(1)
            self.assertEqual(game.state, "title")

            game.state = "pause"
            game.pause_index = game._pause_options().index("SETTINGS")
            game._controller_button_down(0)
            self.assertEqual(game.state, "settings")
            self.assertEqual(game.previous_state, "pause")
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
