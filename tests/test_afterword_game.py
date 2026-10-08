"""Final victory becomes an interactive page, and completed saves can replay."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import tempfile
import unittest
import pygame
from game import Game
from input_state import InputFrame
from localization import set_language, SUPPORTED_LANGUAGES, translate
from localization_release_041 import RELEASE_041
from save_system import SaveSystem


class AfterwordGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.display=pygame.display.set_mode((1120,700))

    @classmethod
    def tearDownClass(cls):
        set_language('en')
        pygame.quit()

    def setUp(self):
        folder=tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path=Path(folder.name)/'game.json'
        self.game=Game(self.display,self.path)

    def ending(self):
        game=self.game
        game.reset()
        game.level.load_chapter(4,'after_final_margin_revision',game.player,game.camera)
        game._attach_runtime()
        game._start_ending()
        for _ in range(200):game.update(1/60,InputFrame())
        return game

    def finish(self, game):
        word=game.afterword
        for memory in word.memories:
            word.player.x,word.player.y=memory.x-12,word.GROUND_Y-48
            word.player.vx=word.player.vy=0
            game.update(1/60,InputFrame(interact=True))
            for _ in range(220):game.update(1/60,InputFrame())
            self.assertTrue(memory.completed)
        word.player.x,word.player.y=word.SEAL_X-12,word.GROUND_Y-48
        word.player.vx=word.player.vy=0
        game.update(1/60,InputFrame(interact=True))
        for _ in range(195):game.update(1/60,InputFrame())
        self.assertTrue(word.complete)

    def test_final_keeps_control_and_requires_deliberate_completion(self):
        game=self.ending()
        self.assertEqual(game.state,'ending')
        self.assertTrue(SaveSystem(self.path).data['completed'])
        start=game.afterword.player.x
        for _ in range(60):game.update(1/60,InputFrame(right=True))
        self.assertGreater(game.afterword.player.x,start+100)
        self.assertFalse(game.afterword.complete)
        game._key_down(pygame.K_RETURN)
        self.assertEqual(game.state,'ending')
        self.assertTrue(game.pending_input.interact)
        self.finish(game)
        game.draw()

    def test_completed_notebook_opens_replay_and_retains_learned_sketches(self):
        game=self.ending()
        game.save.discover('cloud_heart')
        game.save.data['optional_bosses']=['carbon_hound']
        game.save.write()
        game._return_to_title()
        self.assertIn('REPLAY PAGES',game._title_options())
        self.assertNotIn('CONTINUE',game._title_options())
        game._activate_title('REPLAY PAGES')
        game.replay_page_index=2
        game._key_down(pygame.K_RETURN)
        self.assertEqual(game.state,'playing')
        self.assertEqual(game.level.chapter_index,2)
        saved=SaveSystem(self.path).data
        self.assertTrue(saved['completed'])
        self.assertIn('cloud_heart',saved['secrets'])
        self.assertEqual(saved['optional_bosses'],['carbon_hound'])
        self.assertNotIn('boss_cinematic',game.player.control_locks)

    def test_completed_old_save_can_open_afterword_without_replaying_finale(self):
        game=self.game
        game.save.mark_complete(120)
        game._activate_title('REPLAY PAGES')
        game.replay_page_index=5
        game._controller_button_down(0)
        self.assertEqual(game.state,'ending')
        self.assertEqual(game.ending_time,3.3)
        game._controller_button_down(3)
        self.assertTrue(game.pending_input.interact)
        game._controller_button_down(0)
        self.assertTrue(game.pending_input.jump_pressed)
        game.draw()

    def test_afterword_end_buttons_round_trip_collection_and_replay(self):
        game=self.ending()
        self.finish(game)
        game.afterword.menu_index=1
        game._key_down(pygame.K_RETURN)
        self.assertEqual(game.state,'back_pages')
        game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state,'ending')
        self.assertTrue(game.afterword.complete)
        game.afterword.menu_index=0
        game._controller_button_down(0)
        self.assertEqual(game.state,'replay_pages')
        game._controller_hat((1,0))
        self.assertEqual(game.replay_page_index,1)
        game._controller_button_down(1)
        self.assertEqual(game.state,'title')

    def test_all_new_player_text_is_translated_and_new_screens_draw(self):
        game=self.ending()
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            for source in RELEASE_041:
                self.assertTrue(translate(source))
                if language!='en':self.assertNotEqual(translate(source),source)
            game.state='ending'
            game.draw()
            game._open_replay_pages()
            game.draw()
