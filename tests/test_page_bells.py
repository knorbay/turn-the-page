"""The school bell must follow every page curl, including later pages."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import pygame
from game import Game
from settings import WIDTH, HEIGHT


class PageBellContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_each_page_curl_rings_once_and_releases_player(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/"test.json")
            game.sounds.play = Mock()
            for page in range(4):
                game.level.load_chapter(page, "start", game.player, game.camera)
                game.player.release_all_locks()
                game.sounds.play.reset_mock()
                game._start_transition()
                for frame in range(180):
                    game._update_transition(1/60)
                    if not game.transition_active:
                        break
                played = [call.args[0] for call in game.sounds.play.call_args_list]
                self.assertEqual(played.count("bell"), 1, (page, played))
                self.assertEqual(game.level.chapter_index, page+1)
                self.assertNotIn("page_transition", game.player.control_locks)
