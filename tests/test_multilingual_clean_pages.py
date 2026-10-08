"""All selectable languages cover actual campaign content and joined UI text."""
from __future__ import annotations
import re
import unittest

from achievements import ACHIEVEMENTS
from advanced_enemies import FinalEditorBoss
from chapters import build_chapter
from identity_content import BOSS_ENCOUNTERS, BOSS_RULES
from localization import (CATALOGS, LANGUAGE_NAMES, SUPPORTED_LANGUAGES,
                          LocalizedFont, get_language, normalize_language,
                          set_language, translate)
from localization_clean_pages import CLEAN_PAGES
from sketches import SKETCHES, collection_message, wrap_text
from staging import ENCOUNTERS
from tutorial import TrainingLesson


class MultilingualCleanPagesTests(unittest.TestCase):
    def setUp(self):
        self.language = get_language()

    def tearDown(self):
        set_language(self.language)

    def test_language_selection_accepts_all_four_and_rejects_invalid_saves(self):
        self.assertEqual(SUPPORTED_LANGUAGES, ('tr', 'en', 'de', 'it'))
        self.assertEqual(set(LANGUAGE_NAMES), set(SUPPORTED_LANGUAGES))
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            self.assertEqual(get_language(), language)
        for invalid in (None, '', 'fr', 'DE', [], {}, 1):
            self.assertEqual(normalize_language(invalid), 'tr')
            set_language(invalid)
            self.assertEqual(get_language(), 'tr')

    def test_authored_campaign_catalogs_have_equal_coverage(self):
        keys = set(CATALOGS['tr'])
        self.assertGreater(len(keys), 1000)
        for language in ('de', 'it'):
            self.assertEqual(set(CATALOGS[language]), keys)
            for source, copy in CATALOGS[language].items():
                with self.subTest(language=language, text=source):
                    self.assertTrue(copy.strip())
                    self.assertNotIn('\\n', copy)

    def test_actual_five_page_prose_uses_the_selected_language(self):
        sources = set()
        for page in range(5):
            runtime = build_chapter(page)
            sources.update(note.text for note in runtime.world.notes)
            sources.update(doodle[2] for doodle in runtime.world.doodles)
            sources.update(zone.label for zone in runtime.world.zones)
            for entity in runtime.entities.items:
                for field in ('display_name', 'boss_rule', 'prompt', 'invitation',
                              'answer', 'title', 'caption', 'label'):
                    value = getattr(entity, field, '')
                    if isinstance(value, str):
                        sources.add(value)
        for pair in ENCOUNTERS.values():
            sources.update(pair)
        sources.update(pair[1] for pair in BOSS_ENCOUNTERS.values())
        sources.update(BOSS_RULES.values())
        sources.update(FinalEditorBoss.SCENARIO_LABELS.values())
        sources.update(TrainingLesson.TITLES)
        sources.update(TrainingLesson.TIPS)
        for achievement in ACHIEVEMENTS:
            sources.update((achievement.title, achievement.description))
        for language in ('tr', 'de', 'it'):
            set_language(language)
            for source in sources:
                if re.search(r'[A-Za-z]{3}', source):
                    with self.subTest(language=language, text=source):
                        self.assertTrue(source in CATALOGS[language] or translate(source) != source)
                        self.assertEqual(translate(translate(source)), translate(source))
        set_language('en')
        for source in sources:
            self.assertEqual(translate(source), source)

    def test_joined_ui_translates_prefix_payload_and_nested_effects(self):
        expected = {
            'de': {
                'COPY: FOLDED SHURIKEN': 'KOPIE: GEFALTETER SHURIKEN',
                'FIELD NOTES / 0.39': 'FELDNOTIZEN / 0.39',
                'wave 2/3': 'Welle 2/3',
                'clue: valley': 'Hinweis: Tal',
                'E  fold tab 2 (mountain)': 'E / Lasche 2 falten (Berg)',
                'E  transfer impression 4 (right to left)': 'E / Druckmarke 4 übertragen (rechts nach links)',
                'ORBIT 3 / 3 — NEW CONSTELLATION': 'UMLAUF 3 / 3 — NEUES STERNBILD',
                'IN HAND\nRELOAD': 'IN DER HAND\nNACHLADEN',
                'E  learn second thought': 'E / zweiter gedanke lernen',
            },
            'it': {
                'COPY: FOLDED SHURIKEN': 'COPIA: SHURIKEN PIEGATO',
                'FIELD NOTES / 0.39': 'APPUNTI / 0.39',
                'wave 2/3': 'ondata 2/3',
                'clue: valley': 'indizio: valle',
                'E  fold tab 2 (mountain)': 'E / piega la linguetta 2 (monte)',
                'E  transfer impression 4 (right to left)': 'E / trasferisci l\'impronta 4 (da destra a sinistra)',
                'ORBIT 3 / 3 — NEW CONSTELLATION': 'ORBITA 3 / 3 — NUOVA COSTELLAZIONE',
                'IN HAND\nRELOAD': 'IN MANO\nRICARICA',
                'E  learn second thought': 'E / impara secondo pensiero',
            },
        }
        for language, samples in expected.items():
            set_language(language)
            for source, copy in samples.items():
                with self.subTest(language=language, source=source):
                    self.assertEqual(translate(source), copy)
            for sketch in SKETCHES:
                source = collection_message(sketch.secret_id)
                copy = translate(source)
                with self.subTest(language=language, sketch=sketch.secret_id):
                    self.assertNotIn('TECHNIQUE LEARNED', copy)
                    self.assertIn(translate(sketch.technique), copy)
                    self.assertNotIn('seconds', copy)
                    self.assertNotIn('reload', copy)
                    self.assertNotIn('sidearm', copy)
                    self.assertEqual(re.findall(r'\d+(?:\.\d+)?', source),
                                     re.findall(r'\d+(?:[.,]\d+)?', copy.replace(',', '.')))
                    self.assertEqual(translate(copy), copy)
        set_language('tr')
        self.assertEqual(translate('E  learn second thought'), 'E / ikinci düşünce öğren')
        self.assertNotIn('\u0307', translate('E  learn second thought'))

    def test_new_route_prompts_and_controller_instructions_are_complete(self):
        for language in ('tr', 'de', 'it'):
            set_language(language)
            for source in CLEAN_PAGES:
                self.assertIn(source, CATALOGS[language])
                self.assertNotEqual(translate(source), source)
            for source in ('PAD-A / PAD-B   close', 'CONTROLLER CONNECTED',
                           'D-PAD change  •  PAD-A confirm  •  PAD-B returns'):
                self.assertNotEqual(translate(source), source)
                self.assertEqual(re.findall(r'PAD-[A-Z]|D-PAD', translate(source)),
                                 re.findall(r'PAD-[A-Z]|D-PAD', source))

    def test_training_tips_fit_actual_three_line_space_in_all_languages(self):
        import pygame
        from paper_renderer import PaperRenderer
        pygame.font.init()
        renderer = PaperRenderer()
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            for source in TrainingLesson.TIPS:
                with self.subTest(language=language, tip=source):
                    lines = wrap_text(source, renderer.font_small, 391)
                    self.assertLessEqual(len(lines), 3)
                    self.assertTrue(all(renderer.font_small.size(line)[0] <= 391 for line in lines))

    def test_font_sizes_use_same_translation_as_rendering(self):
        class Font:
            def size(self, text):
                return len(text), 20
            def render(self, text, *args, **kwargs):
                return text
        font = LocalizedFont(Font())
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            source = 'E  take SIX-SHOOTER'
            self.assertEqual(font.render(source), translate(source))
            self.assertEqual(font.size(source)[0], len(font.render(source)))


if __name__ == '__main__':
    unittest.main()
