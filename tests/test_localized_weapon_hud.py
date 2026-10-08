"""Real translated combat labels must stay inside their paper plate."""
import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
from localization import get_language, set_language, SUPPORTED_LANGUAGES
from paper_renderer import PaperRenderer
from player import Player
from weapons import WeaponSystem


class LocalizedWeaponHudContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.language = get_language()
        self.addCleanup(set_language, self.language)
        self.surface = pygame.Surface((1120, 700))

    def check_hud(self, system, expected):
        with patch.object(self.renderer, "rough_rect", wraps=self.renderer.rough_rect) as plate, \
                patch.object(self.renderer, "doodle_text", wraps=self.renderer.doodle_text) as labels:
            system.draw_hud(self.surface, self.renderer)
        panel = plate.call_args.args[2]
        calls = labels.call_args_list
        self.assertIn(expected, [call.args[1] for call in calls])
        for call in calls:
            _, text, (x, y), _, font, *_ = call.args
            with self.subTest(text=text):
                self.assertGreaterEqual(x, panel.left)
                self.assertLessEqual(x+font.size(text)[0], panel.right-12)
        return panel, calls

    def test_returning_fold_cue_fits_in_each_real_language(self):
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                set_language(language)
                system = WeaponSystem(Player())
                system.configure_page(0)
                system.lend_drawn_tool("folded_shuriken")
                system.projectiles = [SimpleNamespace(active=True, visual="fold_star")]
                self.check_hud(system, "returning · line up the fold")

    def test_reload_word_fits_and_plate_does_not_shift_on_reload(self):
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                set_language(language)
                system = WeaponSystem(Player())
                system.configure_page(3)
                system.lend_drawn_tool("ink_pistol")
                weapon = system.current
                full_plate, _ = self.check_hud(system, f"{weapon.ammo} / {weapon.mag_size}")
                weapon.reload_timer = weapon.reload_time / 2
                reload_plate, calls = self.check_hud(system, "reload")
                self.assertEqual(full_plate, reload_plate)
                title = next(call for call in calls if call.args[1] == system.profile().label)
                reload = next(call for call in calls if call.args[1] == "reload")
                self.assertLess(title.args[2][0]+title.args[4].size(title.args[1])[0],
                                reload.args[2][0]-10)

    def test_finishing_reload_fills_the_entire_translated_track(self):
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                set_language(language)
                system = WeaponSystem(Player())
                system.configure_page(3)
                system.lend_drawn_tool("ink_pistol")
                # Keep the final reload frame visible, close enough to round
                # to a completely full track at the actual HUD pixel size.
                system.current.reload_timer = .000001
                with patch("pygame.draw.line", wraps=pygame.draw.line) as strokes:
                    system.draw_hud(self.surface, self.renderer)
                bars = [call.args for call in strokes.call_args_list
                        if call.args[2][1] == 637 and call.args[3][1] == 637
                        and call.args[2][0] > 150]
                track = next(args for args in bars if args[4] == 2)
                fill = next(args for args in bars if args[4] == 3)
                self.assertEqual(fill[2], track[2])
                self.assertEqual(fill[3], track[3])
                if language == "de":
                    self.assertGreater(track[3][0]-track[2][0], 64,
                                       "German reload text needs the wider reserve")


if __name__ == "__main__":
    unittest.main()
