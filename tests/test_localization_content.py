"""Coverage of authored player-visible text, not gameplay/save identifiers."""
from __future__ import annotations

import ast
from pathlib import Path
import re
import unittest

from achievements import ACHIEVEMENTS
from localization_content import TR_CONTENT


ROOT = Path(__file__).resolve().parents[1]


class AuthoredTurkishContentTests(unittest.TestCase):
    def test_every_achievement_heading_and_condition_has_a_turkish_copy(self):
        for achievement in ACHIEVEMENTS:
            for source in (achievement.title, achievement.description):
                with self.subTest(text=source):
                    self.assertIn(source, TR_CONTENT)
                    self.assertNotEqual(TR_CONTENT[source], source)

    def test_artist_advice_and_responses_have_complete_phrase_translations(self):
        module = ast.parse((ROOT / "major_update.py").read_text())
        companion = next(node for node in module.body
                         if isinstance(node, ast.ClassDef) and node.name == "ArtistCompanion")
        docstrings = {ast.get_docstring(node) for node in ast.walk(companion)
                      if isinstance(node, (ast.ClassDef, ast.FunctionDef))}
        # Source phrases contain words/spaces; all state keys remain identifiers.
        phrases = {node.value for node in ast.walk(companion)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)
                   and re.search(r"[A-Za-z]{3} ", node.value)
                   and node.value not in docstrings}
        self.assertGreater(len(phrases), 45)
        self.assertFalse(phrases - TR_CONTENT.keys(), phrases - TR_CONTENT.keys())

    def test_schoolwork_prose_is_translated_and_equations_keep_their_values(self):
        module = ast.parse((ROOT / "notebook_notes.py").read_text())
        assignment = next(node for node in module.body if isinstance(node, ast.Assign)
                          and any(isinstance(target, ast.Name) and target.id == "LESSONS"
                                  for target in node.targets))
        lessons = ast.literal_eval(assignment.value)
        prose = {text for page in lessons for lesson in page for text in lesson[:4]
                 if re.search(r"[A-Za-z]{3}", text) and not re.search(r"\b(cos|sin)\(", text)}
        self.assertFalse(prose - TR_CONTENT.keys(), prose - TR_CONTENT.keys())
        self.assertEqual(TR_CONTENT["circumference = 2πr"], "çevre = 2πr")
        self.assertEqual(TR_CONTENT["Earth: g ≈ 9.8 m/s²"], "Dünya: g ≈ 9.8 m/s²")

    def test_all_drawn_tools_have_localized_pickup_prompts(self):
        from page_arsenal import ORIGINAL, PAGE_TOOLS
        profiles = list(ORIGINAL.values()) + [profile for entries in PAGE_TOOLS.values()
                                             for profile in entries.values()]
        for profile in profiles:
            if profile.label == "EMPTY HANDS":
                continue
            with self.subTest(tool=profile.label):
                self.assertIn("E  take " + profile.label, TR_CONTENT)
                self.assertIn("NEW DRAWING — " + profile.label, TR_CONTENT)
        self.assertEqual(TR_CONTENT["E  take SIX-SHOOTER"], "E  ALTIPATLAR al")
        self.assertEqual(TR_CONTENT["NEW DRAWING — NULL CANNON"], "YENİ ÇİZİM — BOŞLUK TOPU")


if __name__ == "__main__":
    unittest.main()
