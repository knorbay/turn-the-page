"""Valid JSON with damaged fields must still permit a campaign to resume."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from behavior import BehaviorLedger
from save_system import SaveSystem


class SaveResilienceContracts(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "save.json"

    def load(self, data):
        self.path.write_text(json.dumps(data), encoding="utf8")
        return SaveSystem(self.path)

    def test_non_object_json_uses_fresh_progress(self):
        for value in ([], ["chapter"], None, "save", 3):
            with self.subTest(value=value):
                save = self.load(value)
                self.assertEqual(save.data["chapter"], 0)
                self.assertEqual(save.data["checkpoint"], "start")
                self.assertFalse(save.can_continue)

    def test_damaged_fields_keep_valid_progress_without_crashing(self):
        save = self.load({
            "chapter": "3", "checkpoint": "after_scissor_office",
            "campaign_revision": "3", "completed": "false",
            "secrets": ["bad_draft", "bad_draft", None, {}],
            "achievements": None, "play_seconds": "not a time",
            "weapons": ["ink_pistol", "invented_tool"],
            "current_weapon": "invented_tool",
            "weapon_ammo": {"ink_pistol": "bad", "invented_tool": 5},
            "notebook_choices": [], "notebook_tools": False,
            "artist_adaptation": None, "behavior": [], "tutorial": False,
        })
        self.assertTrue(save.can_continue)
        self.assertEqual(save.data["chapter"], 3)
        self.assertEqual(save.data["checkpoint"], "after_scissor_office")
        self.assertEqual(save.data["secrets"], ["bad_draft"])
        self.assertFalse(save.data["completed"])
        self.assertEqual(save.data["play_seconds"], 0)
        self.assertEqual(save.data["weapons"], ["ink_pistol"])
        self.assertEqual(save.data["current_weapon"], "ink_pistol")
        self.assertEqual(save.data["weapon_ammo"], {"ink_pistol": 0})
        for key in ("notebook_choices", "notebook_tools", "artist_adaptation", "behavior", "tutorial"):
            self.assertEqual(save.data[key], {})
        save.checkpoint(3, "after_scissor_office", 123)
        self.assertEqual(SaveSystem(self.path).data["play_seconds"], 123)

    def test_invalid_chapter_checkpoint_and_nonfinite_numbers_are_repaired(self):
        for chapter in (None, {}, "page four", float("inf"), float("nan")):
            with self.subTest(chapter=chapter):
                save = self.load({"chapter": chapter, "checkpoint": [],
                                  "play_seconds": float("nan"),
                                  "weapon_ammo": {"ink_pistol": float("inf")}})
                self.assertEqual(save.data["chapter"], 0)
                self.assertEqual(save.data["checkpoint"], "start")
                self.assertEqual(save.data["play_seconds"], 0)
                self.assertEqual(save.data["weapon_ammo"], {"ink_pistol": 0})

    def test_old_completed_campaign_migrates_even_with_text_revision(self):
        save = self.load({"chapter": 2, "campaign_revision": "1",
                          "checkpoint": "after_final_margin_revision",
                          "completed": True, "secrets": ["bad_draft"]})
        self.assertEqual(save.data["chapter"], 3)
        self.assertEqual(save.data["checkpoint"], "start")
        self.assertFalse(save.data["completed"])
        self.assertEqual(save.data["secrets"], ["bad_draft"])

    def test_all_four_languages_survive_reload_and_new_campaign(self):
        for language in ("tr", "en", "de", "it"):
            with self.subTest(language=language):
                save = self.load({"settings": {"language": language}})
                self.assertEqual(save.data["settings"]["language"], language)
                save.new_game()
                self.assertEqual(SaveSystem(self.path).data["settings"]["language"], language)

    def test_repaired_behavior_still_records_combat_and_deaths(self):
        ledger = BehaviorLedger({
            "counts": {"attacks": "7", "deaths": None},
            "deaths_by_cause": {"fall": "bad"},
            "weapon_uses": {"ink_pistol": {}},
            "enemy_hits": {"crawler": float("inf")},
            "boss_clear_seconds": {"moon_compass": "19.5", "other": []},
            "combat_motion": {"seconds": "20", "retreat_seconds": [],
                              "distance": float("nan")},
        })
        ledger.record("attack", weapon="ink_pistol")
        ledger.record("death", cause="fall")
        ledger.record("enemy_hit", kind="crawler")
        ledger.observe_combat(.1, SimpleNamespace(locked=False, center_x=100, vx=10),
                              [SimpleNamespace(x=200, dead=False)])
        self.assertEqual(ledger.count("attacks"), 8)
        self.assertEqual(ledger.count("deaths"), 1)
        self.assertEqual(ledger.deaths_to("fall"), 1)
        self.assertEqual(ledger.data["enemy_hits"]["crawler"], 1)
        self.assertEqual(ledger.data["boss_clear_seconds"]["moon_compass"], 19.5)
        self.assertEqual(ledger.data["combat_motion"]["distance"], 1)
        self.assertEqual(ledger.broad_tendency(), "unreadable")


class GameSaveResilienceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import pygame
        pygame.init()
        cls.screen = pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        import pygame
        pygame.quit()

    def test_repaired_progress_reaches_the_title_and_live_game(self):
        from game import Game
        from input_state import InputFrame
        values = (None, [], "campaign", {
            "chapter": "not a page", "checkpoint": None, "secrets": 5,
            "play_seconds": [], "current_weapon": {}, "weapon_ammo": [],
            "notebook_choices": [], "tutorial": None,
            "behavior": {"counts": {"attacks": "unknown", "deaths": None}},
        })
        for data in values:
            with self.subTest(data=data), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "save.json"
                path.write_text(json.dumps(data), encoding="utf8")
                game = Game(self.screen, path)
                self.assertEqual(game.state, "title")
                game.draw()
                game.continue_game()
                game.update(1 / 60, InputFrame())
                game.draw()
                game.behavior.record("attack", weapon="unarmed")
                self.assertEqual(game.behavior.count("attacks"), 1)
                self.assertEqual(game.level.chapter_index, 0)


if __name__ == "__main__":
    unittest.main()
