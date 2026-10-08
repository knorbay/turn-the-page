"""Settings and compact cards remain usable after changing among four languages."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from game import Game, LANGUAGE_RECT
from localization import LocalizedFont, SUPPORTED_LANGUAGES, set_language, get_language, translate
from save_system import SaveSystem
from sketches import wrap_text
from soundtrack_credits import CREDIT_COPY, draw_music_credits
from scene_music import MUSIC_CREDITS


class CleanUIContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.language = get_language()
        self.addCleanup(set_language, self.language)
        self.game = Game(self.screen, Path(self.folder.name) / 'save.json')

    def test_four_languages_cycle_in_both_directions_and_persist(self):
        game = self.game
        game.settings_index = 5
        for expected in ('en', 'de', 'it', 'tr'):
            game._change_setting(1)
            self.assertEqual(game.save.data['settings']['language'], expected)
            self.assertEqual(get_language(), expected)
            self.assertEqual(SaveSystem(game.save.path).data['settings']['language'], expected)
        for expected in ('it', 'de', 'en', 'tr'):
            game._change_setting(-1)
            self.assertEqual(game.save.data['settings']['language'], expected)
        game._change_setting(-1)
        game.save.new_game()
        self.assertEqual(SaveSystem(game.save.path).data['settings']['language'], 'it')

    def test_core_prompts_do_not_fall_back_to_english_in_translated_locales(self):
        sources = ('NEW GAME', 'SETTINGS', 'Language', 'MUSIC CREDITS',
                   'Hidden margins. Optional routes.', 'Enter / click: choose',
                   'Learned techniques survive every redraw.', '+1 HEART',
                   'Route drawn. +1 heart.', 'E / trace the blue mark',
                   'JUMP THE GUST', 'LEAVE THE TAIL MARK', 'DIVE — STEP ASIDE',
                   'LOOSE STRING — HIT')
        for language in ('tr', 'de', 'it'):
            set_language(language)
            for source in sources:
                with self.subTest(language=language, source=source):
                    self.assertNotEqual(translate(source), source)

    def test_title_language_button_uses_the_visible_bounds(self):
        game = self.game
        with patch.object(game, '_window_to_canvas', return_value=(LANGUAGE_RECT.left + 3, LANGUAGE_RECT.centery)):
            game._mouse_click((0, 0))
        self.assertEqual(game.save.data['settings']['language'], 'en')
        self.assertEqual(game.state, 'title')

    def test_empty_notice_cannot_crash_hud(self):
        game = self.game
        game.level.toast, game.level.toast_time = '   ', 2
        game._draw_hud()

    def test_controller_interaction_keeps_translation_before_button_substitution(self):
        game = self.game
        game.last_input_device = 'controller'
        game.level.interaction_hint = 'E  examine lost sketch'
        game.level.toast_time = 0
        game.level.page_title_time = 0
        set_language('tr')
        rendered = []
        original = game.renderer.font_small.render
        def capture(value, *args, **kwargs):
            rendered.append(str(value))
            return original(value, *args, **kwargs)
        with patch.object(game.renderer.font_small, 'render', side_effect=capture):
            game._draw_hud()
        self.assertIn('PAD-Y  kayıp eskizi incele', rendered)
        self.assertNotIn('PAD-Y  examine lost sketch', rendered)

    def test_compound_words_wrap_without_losing_characters(self):
        set_language('de')
        font = LocalizedFont(pygame.font.Font(None, 24))
        source = 'Donaudampfschifffahrtsgesellschaftskapitän'
        lines = wrap_text(source, font, 100)
        self.assertGreater(len(lines), 1)
        self.assertEqual(''.join(lines), source)
        self.assertTrue(all(font.raw.size(line)[0] <= 100 for line in lines))

    def test_all_music_credits_are_reachable_from_keyboard_mouse_and_controller(self):
        from soundtrack_credits import CREDITS_NEXT_RECT, music_credit_page_count
        game = self.game
        self.assertEqual(music_credit_page_count(MUSIC_CREDITS), 3)
        game.state = "credits"
        game.music_credit_page = 0
        game._key_down(pygame.K_RIGHT)
        self.assertEqual(game.music_credit_page, 1)
        with patch.object(game, '_window_to_canvas', return_value=CREDITS_NEXT_RECT.center):
            game._mouse_click((0, 0))
        self.assertEqual(game.music_credit_page, 2)
        game._controller_button_down(5)
        self.assertEqual(game.music_credit_page, 0)
        game._controller_hat((-1, 0))
        self.assertEqual(game.music_credit_page, 2)
        game.previous_state = "title"
        game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state, "title")

    def test_music_attribution_navigation_has_native_copy_for_each_language(self):
        game = self.game
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                set_language(language)
                self.assertEqual(len(CREDIT_COPY[language]), 6)
                draw_music_credits(game.screen, game.renderer, MUSIC_CREDITS, language)
                for state in ('title', 'settings', 'controls', 'pause', 'back_pages', 'achievements', 'credits'):
                    game.state = state
                    game.draw()
