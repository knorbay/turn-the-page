"""Persistence and presentation contracts for notebook achievements."""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from achievements import ACHIEVEMENTS
from behavior import BehaviorLedger
from game import Game
from settings import HEIGHT, WIDTH


class AchievementContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.display = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_authored_achievements_unlock_once_and_survive_new_game(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            for _ in range(40):
                game.behavior.record("dash")
            game.behavior.record("enemy_defeated", kind="ink_samurai")
            game.behavior.record("page_complete", page=0, seconds=60)
            game.achievements.evaluate(game)
            self.assertIn("margin_runner", game.achievements.unlocked)
            self.assertIn("clean_copy", game.achievements.unlocked)

            for weapon in ("pencil_blade", "ink_pistol", "marker_shotgun",
                           "eraser_cannon", "rubber_band"):
                game.behavior.record("attack", weapon=weapon)
            for _ in range(89):
                game.behavior.record("attack", weapon="pencil_blade")
            for page in range(1, 5):
                game.behavior.record("page_complete", page=page, seconds=60)
            game.behavior.record("death", cause="baby_face_giant")
            game.behavior.record("death", cause="baby_face_giant")
            game.weapons.unlock("excalibur")
            game.behavior.record("enemy_defeated", kind="baby_face_giant")
            game.behavior.record("enemy_defeated", kind="final_editor")
            for boss in ("moon_compass", "wanted_sketch", "railroad_stapler",
                         "orbital_mistake", "scissor_director", "final_editor"):
                game.behavior.record("boss_clear", kind=boss, seconds=40)
            game.save.data["secrets"] = ["a", "b", "c"]
            game.save.data["completed"] = True
            game.behavior.record("final_scenario", kind="precise")

            for _ in range(3):
                game.behavior.record("perfect_return")
            game.behavior.record('practice_complete')
            for _ in range(5): game.behavior.record('artist_reply')
            for puzzle_id in ('first_page_draft', 'wanted_perforation', 'satellite_relay'):
                game.behavior.record('puzzle_solved', puzzle_id=puzzle_id)
            game.behavior.record('puzzle_solved', puzzle_id='first_page_draft')
            self.assertEqual(game.behavior.count('puzzle_solved'), 3)
            for _ in range(20): game.behavior.record('arena_clear')
            for _ in range(7): game.behavior.record('perfect_return')
            for kind in ('fold_duelist','margin_sniper','split_lantern', 'ruler_guard',
                         'paper_wasp','ink_clone','goblin_scribble','redaction_agent',
                         'moon_bot','star_scout','cactus_gunner','eraser_brute'):
                game.behavior.record('enemy_defeated', kind=kind)
            game.save.data['secrets'] = [str(i) for i in range(12)]
            game.achievements.evaluate(game)
            self.assertEqual(game.achievements.count, len(ACHIEVEMENTS))
            self.assertEqual(len(game.save.data["achievements"]), len(ACHIEVEMENTS))
            game.achievements.evaluate(game)
            self.assertEqual(len(game.achievements.pending), len(ACHIEVEMENTS))

            game.save.new_game()
            self.assertEqual(len(game.save.data["achievements"]), len(ACHIEVEMENTS))

    def test_achievement_page_and_banner_render(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.display, Path(directory) / "save.json")
            game.state = "achievements"
            game.previous_state = "title"
            game.achievements.unlock("first_crossout")
            game._update_achievements(1 / 60)
            game.draw()
            self.assertGreater(game.screen.get_bounding_rect().width, 0)
            self.assertIsNotNone(game.achievement_banner)
            game._key_down(pygame.K_ESCAPE)
            self.assertEqual(game.state, "title")

    def test_route_puzzle_progress_is_unique_across_save_reload(self):
        ledger = BehaviorLedger()
        ledger.record("puzzle_solved", puzzle_id="first_page_draft")
        restored = BehaviorLedger(ledger.snapshot())
        restored.record("puzzle_solved", puzzle_id="first_page_draft")
        restored.record("puzzle_solved", puzzle_id="wanted_perforation")
        self.assertEqual(restored.count("puzzle_solved"), 2)
        self.assertEqual(restored.data["puzzles_solved"],
                         ["first_page_draft", "wanted_perforation"])


if __name__ == "__main__":
    unittest.main()
