"""Music keeps encounter identity and follows deliberate exits to the title."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import pygame

from game import Game


class MusicGameLifecycleTests(unittest.TestCase):
    def game(self, *rooms):
        game = Game.__new__(Game)
        game.sounds = Mock()
        game.level = SimpleNamespace(entities=SimpleNamespace(items=list(rooms)),
                                     respawn_timer=0)
        return game

    def room(self, enemies=(), **values):
        fields = dict(encounter_active=True, completed=False, enemies=list(enemies),
                      boss_cue_started=False, boss_kind=None)
        fields.update(values)
        return SimpleNamespace(**fields)

    def test_boss_score_keeps_its_identity_through_the_victory_delay(self):
        boss = SimpleNamespace(is_boss=True, kind="moon_compass")
        room = self.room((boss,), boss_cue_started=True, boss_kind=boss.kind)
        game = self.game(room)
        game._update_combat_music()
        game.sounds.set_combat.assert_called_with(True, True, "moon_compass")
        room.enemies.clear()
        game._update_combat_music()
        game.sounds.set_combat.assert_called_with(True, True, "moon_compass")
        room.completed = True
        game._update_combat_music()
        game.sounds.set_combat.assert_called_with(False)

    def test_boss_room_guard_wave_waits_for_the_actual_boss(self):
        room = self.room((SimpleNamespace(is_boss=False),), boss=True)
        game = self.game(room)
        game._update_combat_music()
        game.sounds.set_combat.assert_called_with(True, False, None)
        boss = SimpleNamespace(is_boss=True, kind="railroad_stapler")
        room.enemies[:] = [boss]
        room.boss_cue_started = True
        room.boss_kind = boss.kind
        game._update_combat_music()
        game.sounds.set_combat.assert_called_with(True, True, "railroad_stapler")

    def test_secret_guardian_selects_its_score_without_arena_metadata(self):
        guardian = SimpleNamespace(is_boss=True, kind="cloud_kite")
        game = self.game(SimpleNamespace(encounter_active=True, completed=False,
                                        enemies=[guardian]))
        game._update_combat_music()
        game.sounds.set_combat.assert_called_once_with(True, True, "cloud_kite")

    def test_death_stops_the_boss_score_while_waiting_for_respawn(self):
        game = self.game(self.room(boss_cue_started=True, boss_kind="final_editor"))
        game.level.respawn_timer = 1
        game._update_combat_music()
        game.sounds.set_combat.assert_called_once_with(False)

    def test_leaving_pause_returns_to_the_title_page_theme(self):
        game = self.game()
        game.state = "pause"
        game._activate_pause("TITLE")
        self.assertEqual(game.state, "title")
        game.sounds.set_combat.assert_called_once_with(False)
        game.sounds.start_ambience.assert_called_once_with(0)
        game.sounds.quiet_ambience.assert_called_once_with(False)

    def test_training_completion_and_cancellation_release_combat_music(self):
        for completed in (False, True):
            with self.subTest(completed=completed):
                game = self.game()
                game.state = "playing"
                game.training_only = True
                game.campaign_save = SimpleNamespace(data={"settings": {"music_volume": .2}})
                game.save = SimpleNamespace(data={"settings": {"music_volume": .4}})
                game.finish_training(completed=completed)
                self.assertEqual(game.state, "title")
                self.assertIs(game.save, game.campaign_save)
                self.assertFalse(game.training_only)
                self.assertEqual(game.save.data["settings"]["music_volume"], .4)
                game.sounds.set_combat.assert_called_once_with(False)
                game.sounds.start_ambience.assert_called_once_with(0)
                game.sounds.quiet_ambience.assert_called_once_with(False)

    def test_keyboard_and_controller_endings_restore_audible_title_music(self):
        for controller, control in ((False, pygame.K_RETURN),
                                    (False, pygame.K_ESCAPE), (True, 0)):
            with self.subTest(controller=controller, control=control):
                game = self.game()
                game.state = "ending"
                if controller:
                    game._controller_button_down(control)
                else:
                    game._key_down(control)
                self.assertEqual(game.state, "title")
                game.sounds.set_combat.assert_called_once_with(False)
                game.sounds.quiet_ambience.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
