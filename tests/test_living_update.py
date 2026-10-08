import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from game import Game
from input_state import InputFrame
from localization import translate, set_language
from save_system import SaveSystem

class LivingUpdateContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init(); pygame.display.set_mode((1120,700))
    @classmethod
    def tearDownClass(cls):
        pygame.quit()
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.game=Game(pygame.display.get_surface(),Path(self.folder.name)/'save.json')
        self.addCleanup(set_language,'en')

    def test_all_three_jump_keys_press_hold_and_release(self):
        game=self.game; game.state='playing'
        for key in (pygame.K_SPACE,pygame.K_w,pygame.K_UP):
            with self.subTest(key=key):
                game.pending_input=InputFrame()
                game._key_down(key)
                self.assertTrue(game.pending_input.jump_pressed)
                with patch('pygame.key.get_pressed',return_value={k:k==key for k in (
                    pygame.K_SPACE,pygame.K_w,pygame.K_UP,pygame.K_a,pygame.K_d,pygame.K_LEFT,
                    pygame.K_RIGHT,pygame.K_s,pygame.K_DOWN,pygame.K_f,pygame.K_j)}):
                    self.assertTrue(game._sample_input().jump_held)
                pygame.event.clear()
                pygame.event.post(pygame.event.Event(pygame.KEYUP,key=key))
                game.handle_events()
                self.assertTrue(game.pending_input.jump_released)

    def test_language_changes_immediately_persists_and_survives_new_game(self):
        game=self.game
        game.settings_index=5
        game._change_setting(1)
        self.assertEqual(game.save.data['settings']['language'],'en')
        self.assertEqual(translate('NEW GAME'),'NEW GAME')
        game._change_setting(-1)
        self.assertEqual(translate('NEW GAME'),'YENİ OYUN')
        self.assertEqual(translate('Jumps: 2 / 3'),'Zıplama: 2 / 3')
        game.save.new_game()
        self.assertEqual(SaveSystem(game.save.path).data['settings']['language'],'tr')

    def test_collection_subscreens_return_to_correct_parent(self):
        game=self.game
        game._activate_title('BACK PAGES')
        self.assertEqual(game.previous_state,'title')
        game._key_down(pygame.K_a)
        self.assertEqual(game.state,'achievements')
        game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state,'back_pages')
        game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state,'title')
        game.state='pause';game._activate_pause('BACK PAGES')
        game._key_down(pygame.K_c)
        self.assertEqual(game.state,'controls')
        game._key_down(pygame.K_ESCAPE);game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state,'pause')

    def test_lesson_cannot_open_by_waiting_or_count_paused_time(self):
        game=self.game;game.reset()
        for _ in range(240):game.update(1/60,InputFrame())
        lesson=game.level.runtime.training
        before=lesson.elapsed
        game.state='pause'
        for _ in range(120):game.update(1/60,InputFrame())
        self.assertEqual(lesson.elapsed,before)
        game.state='playing'
        for _ in range(4200):game.update(1/60,InputFrame())
        self.assertGreaterEqual(lesson.elapsed,60)
        self.assertFalse(lesson.completed)
        self.assertTrue(lesson.gate.enabled)
        self.assertFalse(next(e for e in game.level.entities.items if getattr(e,'is_combat_arena',False)).encounter_active)

    def test_first_lesson_completes_through_real_controller_actions_after_a_minute(self):
        game=self.game;game.reset()
        lesson=game.level.runtime.training
        first=next(e for e in game.level.entities.items if getattr(e,'is_combat_arena',False))
        practice=next(e for e in game.level.entities.items if type(e).__name__=='PracticeDrawing')
        from tools.training_pilot import lesson_input
        for tick in range(12000):
            game.update(1/60,lesson_input(game))
            if lesson.hand is not None:
                game.draw()
            if lesson.completed:break
            self.assertFalse(first.encounter_active)
        self.assertTrue(lesson.completed,(lesson.stage,lesson.elapsed,lesson.jumps,lesson.dashes,practice.completed,game.player.x))
        self.assertGreaterEqual(lesson.elapsed,60)
        self.assertGreaterEqual(lesson.jumps,3)
        self.assertGreaterEqual(lesson.dashes,3)
        self.assertTrue(all(target.completed for target in lesson.targets))
        self.assertGreaterEqual(lesson.dodges,3)
        self.assertTrue(lesson.bridge_requested)
        self.assertFalse(lesson.gate.enabled)
        self.assertEqual(game.behavior.count('deaths'),0)
        game.draw()
        game.save.write()
        restored=Game(pygame.display.get_surface(),game.save.path)
        restored.continue_game()
        self.assertTrue(restored.level.runtime.training.completed)
