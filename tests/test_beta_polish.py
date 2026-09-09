import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import pygame
from game import Game
from input_state import InputFrame
from runtime_paths import default_save_path
from save_system import SaveSystem


class BetaPolishTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen=pygame.display.set_mode((1120,700))
    @classmethod
    def tearDownClass(cls):pygame.quit()

    def test_frozen_save_is_outside_bundle_and_explicit_override_wins(self):
        with patch.dict(os.environ,{},clear=True),patch("sys.frozen",True,create=True):
            platform_paths={
                "darwin":Path.home()/"Library/Application Support/Turn the Page/paper_story_save.json",
                "win32":Path.home()/"AppData/Roaming/Turn the Page/paper_story_save.json",
                "linux":Path.home()/".local/share/Turn the Page/paper_story_save.json",
            }
            for platform,expected in platform_paths.items():
                with self.subTest(platform=platform),patch("sys.platform",platform):
                    self.assertEqual(default_save_path(),expected)
            with patch.dict(os.environ,{"PAPER_STORY_SAVE":"/tmp/ttp-test.json"}):
                self.assertEqual(default_save_path(),Path("/tmp/ttp-test.json"))

    def test_previous_beta_save_migrates_without_altering_the_original(self):
        with tempfile.TemporaryDirectory() as d:
            old=Path(d)/"old.json";new=Path(d)/"new"/"save.json"
            old.write_text('{"chapter": 2, "checkpoint": "start", "secrets": ["bad_draft"]}')
            with patch("save_system.default_save_path",return_value=new), \
                    patch("save_system.legacy_save_path",return_value=old):
                save=SaveSystem()
            self.assertEqual(save.data["chapter"],2)
            self.assertIn("bad_draft",save.data["secrets"])
            self.assertTrue(new.exists())
            self.assertTrue(old.exists())

    def test_focus_loss_pauses_and_clears_attack_buffer_without_auto_resume(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(self.screen,Path(d)/"save.json")
            g.state="playing"
            g._buffered_actions=InputFrame(attack_pressed=True,dash_pressed=True)
            pygame.event.clear()
            pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSLOST))
            g.handle_events()
            self.assertEqual(g.state,"pause")
            self.assertFalse(g._buffered_actions.attack_pressed)
            pygame.event.post(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
            g.handle_events()
            self.assertEqual(g.state,"pause")

    def test_controller_inventory_uses_controller_binding(self):
        with tempfile.TemporaryDirectory() as d:
            g=Game(self.screen,Path(d)/"save.json")
            g.weapons.configure_page(1)
            g.weapons.active_loadout=None
            g.weapons.unlock("ink_pistol")
            with patch.object(g.renderer,"doodle_text") as draw:
                g.weapons.draw_hud(g.screen,g.renderer,controller=True)
                labels=[c.args[1] for c in draw.call_args_list]
            self.assertIn("LB / D-PAD",labels)
            self.assertNotIn("Q / wheel",labels)
