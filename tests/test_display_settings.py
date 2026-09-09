"""Regression contracts for resilient audio settings and scalable display output."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game
from save_system import SaveSystem
from settings import HEIGHT, WIDTH


class DisplayAndSettingsContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    def test_integer_max_master_volume_is_repaired_and_drawable(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "save.json"
            save_path.write_text(json.dumps({
                "settings": {
                    "master_volume": 1,
                    "sfx_volume": 0.85,
                    "music_volume": 0.35,
                    "fullscreen": False,
                },
            }), encoding="utf8")
            game = Game(self.display, save_path)
            game.state = "settings"

            self.assertIsInstance(game.save.data["settings"]["master_volume"], float)
            self.assertEqual(game.save.data["settings"]["master_volume"], 1.0)
            game._change_setting(1)
            game.draw()
            game._present()

    def test_bad_volume_and_window_values_are_safely_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = Path(directory) / "save.json"
            save_path.write_text(json.dumps({
                "settings": {
                    "master_volume": "loud",
                    "sfx_volume": 8,
                    "music_volume": -4,
                    "fullscreen": "false",
                    "window_width": "wide",
                    "window_height": 99999,
                },
            }), encoding="utf8")
            settings = SaveSystem(save_path).data["settings"]

            self.assertEqual(settings["master_volume"], 0.8)
            self.assertEqual(settings["sfx_volume"], 1.0)
            self.assertEqual(settings["music_volume"], 0.0)
            self.assertFalse(settings["fullscreen"])
            self.assertEqual(settings["window_width"], WIDTH)
            self.assertEqual(settings["window_height"], 4320)

    def test_resized_window_letterboxes_and_maps_mouse_to_game_canvas(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            game._set_display_mode((1400, 900), fullscreen=False)
            game.draw()
            game._present()

            self.assertEqual(game.display.get_size(), (1400, 900))
            self.assertEqual(game.viewport.size, (1400, 875))
            canvas = game._window_to_canvas(game.viewport.center)
            self.assertAlmostEqual(canvas[0], WIDTH / 2, delta=1)
            self.assertAlmostEqual(canvas[1], HEIGHT / 2, delta=1)
            self.assertEqual(game.display.get_at((0, 0))[:3], (24, 23, 22))

            game._remember_window_size(write=True)
            restored = SaveSystem(Path(directory) / "save.json").data["settings"]
            self.assertEqual((restored["window_width"], restored["window_height"]),
                             (1400, 900))

    def test_scaled_settings_slider_supports_click_and_drag(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            game._set_display_mode((1400, 900), fullscreen=False)
            game.state = "settings"

            def window_point(canvas_x, canvas_y):
                return (
                    game.viewport.x + canvas_x * game.viewport.width / WIDTH,
                    game.viewport.y + canvas_y * game.viewport.height / HEIGHT,
                )

            game._mouse_click(window_point(640, 225))
            self.assertEqual(game.dragging_volume_index, 0)
            self.assertEqual(game.save.data["settings"]["master_volume"], 0.0)
            game._set_volume_from_canvas(745, write=False)
            self.assertEqual(game.save.data["settings"]["master_volume"], 0.5)
            game._set_volume_from_canvas(850, write=True)
            game.dragging_volume_index = None
            self.assertEqual(game.save.data["settings"]["master_volume"], 1.0)
            game.draw()

    def test_pause_menu_ignores_stray_clicks_and_activates_real_buttons(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            game.state = "pause"

            game._mouse_click((20, 20))
            self.assertEqual(game.state, "pause")
            game._mouse_click(game._pause_rect(game._pause_options().index("SETTINGS")).center)
            self.assertEqual(game.state, "settings")
            self.assertEqual(game.previous_state, "pause")

    def test_gameplay_mouse_has_a_visible_weapon_aware_cursor(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            game.state = "playing"
            game.last_input_device = "mouse"
            game.screen.fill((255, 255, 255))
            before = pygame.image.tostring(game.screen, "RGB")
            with patch("pygame.mouse.get_pos", return_value=(WIDTH // 2, HEIGHT // 2)):
                game._draw_aim_cursor()
            after = pygame.image.tostring(game.screen, "RGB")
            self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
