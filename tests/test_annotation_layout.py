"""Translated handwriting must fit its sheet and leave space for the diagram."""
import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from localization import get_language, set_language, SUPPORTED_LANGUAGES
from notebook_notes import NotebookAnnotations


class AnnotationLayoutContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_localized_schoolwork_keeps_text_inside_its_allocated_area(self):
        previous = get_language()
        self.addCleanup(set_language, previous)
        original = NotebookAnnotations._hand
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            endpoints = []

            def track(notes, surface, text, x, y, font, color, seed, **kwargs):
                end = original(notes, surface, text, x, y, font, color, seed, **kwargs)
                if y in (1, 42, 75, 125):
                    endpoints.append((text, y, end))
                return end

            with self.subTest(language=language), patch.object(NotebookAnnotations, "_hand", track):
                notes = NotebookAnnotations()
                self.assertEqual(len(notes.sheets), 5)
                self.assertEqual(len(endpoints), 120)
                for text, row, end in endpoints:
                    with self.subTest(language=language, text=text):
                        boundary = 345 if row in (42, 75) else 510
                        self.assertLessEqual(end, boundary,
                            "localized handwriting must not clip or cover its diagram")


if __name__ == "__main__":
    unittest.main()
