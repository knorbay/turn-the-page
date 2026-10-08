"""The Artist reacts to play, then waits until the page has room to speak."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from types import SimpleNamespace
import unittest

from behavior import BehaviorLedger
from input_state import InputFrame
from major_update import ArtistCompanion


class ArtistDialogueTests(unittest.TestCase):
    def setUp(self):
        self.saved = []
        self.game = SimpleNamespace(
            behavior=BehaviorLedger(),
            player=SimpleNamespace(locked=False, health=3, x=350),
            weapons=SimpleNamespace(current_id='pencil_blade', unlocked={'pencil_blade'}),
            level=SimpleNamespace(chapter_index=0, respawn_timer=0, respawn_cause='',
                                  toast_time=0, interaction_hint='', flags=set(),
                                  entities=SimpleNamespace(items=[])),
            achievement_time=0,
            persist_behavior=lambda **kwargs: self.saved.append(kwargs),
        )
        self.artist = ArtistCompanion()
        self.tick(.1)

    def tick(self, seconds=.1, **inputs):
        self.artist.update(seconds, self.game, InputFrame(**inputs))

    def test_new_weapon_waits_for_pickup_notice_and_exchanges_once(self):
        self.game.weapons.unlocked.add('chalk_bomb')
        self.game.weapons.current_id = 'chalk_bomb'
        self.game.level.toast_time = 4
        self.tick()
        self.assertEqual(self.artist.text, '')
        self.assertEqual(len(self.artist.pending), 1)
        self.game.level.toast_time = 0
        self.tick()
        self.assertIn('chalk over cover', self.artist.text)
        self.tick(interact=True)
        self.assertIn('different answers', self.artist.text)
        self.assertEqual(self.game.behavior.count('artist_reply'), 1)
        self.tick(interact=True)
        self.assertEqual(self.game.behavior.count('artist_reply'), 1)
        self.assertEqual(self.saved, [{'write': True}])

    def test_puzzle_solution_is_not_announced_during_fight(self):
        puzzle = SimpleNamespace(puzzle_id='folding_margin', encounter_active=False)
        arena = SimpleNamespace(encounter_active=True)
        self.game.level.entities.items.extend((puzzle, arena))
        self.game.level.flags.add('folding_margin')
        self.tick()
        self.assertEqual(self.artist.text, '')
        self.assertEqual(len(self.artist.pending), 1)
        arena.encounter_active = False
        self.tick()
        self.assertIn('answer', self.artist.text)
        self.assertTrue(self.artist.reply)

    def test_western_route_puzzle_gets_its_own_artist_exchange(self):
        self.game.level.chapter_index = 1
        self.tick()
        self.game.level.entities.items.append(
            SimpleNamespace(puzzle_id='wanted_perforation', encounter_active=False))
        self.game.level.flags.add('wanted_perforation')
        self.tick()
        self.assertIn('poster', self.artist.text)
        self.tick(interact=True)
        self.assertIn('chose when', self.artist.text)

    def test_retry_waits_for_respawn_and_artist_overlay(self):
        self.game.behavior.record('death', cause='fall')
        self.game.level.respawn_cause = 'fall'
        self.game.level.respawn_timer = 1
        self.tick()
        self.assertEqual(self.artist.text, '')
        self.game.level.respawn_timer = 0
        other_note = SimpleNamespace(letter_time=3, encounter_active=False)
        self.game.level.entities.items.append(other_note)
        self.tick()
        self.assertEqual(self.artist.text, '')
        other_note.letter_time = 0
        self.tick()
        self.assertIn('landing', self.artist.text)

    def test_switch_reaction_is_paced_and_does_not_stack(self):
        self.game.weapons.unlocked.update(('ink_pistol', 'eraser_cannon'))
        self.artist.last_unlocked = set(self.game.weapons.unlocked)
        self.game.weapons.current_id = 'ink_pistol'
        self.tick()
        self.assertIn('Different tool', self.artist.text)
        self.game.weapons.current_id = 'eraser_cannon'
        self.tick()
        self.assertEqual(self.artist.text.startswith('Different tool'), True)
        self.assertEqual(len(self.artist.pending), 1)
        self.tick(14.1)
        self.assertIn('wider mark', self.artist.text)

    def test_input_during_combat_cannot_reply_to_hidden_note(self):
        self.artist.say('manual', 'Are you there?', 'Here.')
        self.game.level.entities.items.append(SimpleNamespace(encounter_active=True))
        self.tick(interact=True)
        self.assertEqual(self.game.behavior.count('artist_reply'), 0)
        self.assertEqual(self.artist.timer, 0)

    def test_input_during_artist_stroke_cannot_reply_to_hidden_note(self):
        self.artist.say('manual','Are you there?','Here.')
        director=SimpleNamespace(canvas_owner=object(),
            tool=SimpleNamespace(visible=False),blocks_combat=False)
        self.game.level.director=director
        for _ in range(5):self.tick(interact=True)
        self.assertEqual(self.game.behavior.count('artist_reply'),0)
        self.assertEqual(self.artist.text,'Are you there?')
        self.assertEqual(self.saved,[])
        director.canvas_owner=None
        director.tool.visible=True
        self.tick(interact=True)
        director.tool.visible=False
        director.blocks_combat=True
        self.tick(interact=True)
        self.assertEqual(self.game.behavior.count('artist_reply'),0)
        director.blocks_combat=False
        self.tick(interact=True)
        self.assertEqual(self.artist.text,'Here.')
        self.assertEqual(self.game.behavior.count('artist_reply'),1)

    def test_new_note_waits_until_the_local_artist_releases_the_canvas(self):
        director=SimpleNamespace(canvas_owner=object())
        self.game.level.director=director
        self.game.weapons.unlocked.add('chalk_bomb')
        self.game.weapons.current_id='chalk_bomb'
        self.tick()
        self.assertEqual(self.artist.text,'')
        self.assertEqual(len(self.artist.pending),1)
        director.canvas_owner=None
        self.tick()
        self.assertIn('chalk over cover',self.artist.text)
        self.assertEqual(self.artist.pending,[])

    def test_completed_puzzle_does_not_silence_its_artist_exchange(self):
        self.game.level.entities.items.append(SimpleNamespace(
            puzzle_id='first_page_draft',encounter_active=True,completed=True))
        self.game.level.flags.add('first_page_draft')
        self.tick()
        self.assertIn('step where my first line failed',self.artist.text)
        self.tick(interact=True)
        self.assertIn('next answer',self.artist.text)
        self.assertEqual(self.game.behavior.count('artist_reply'),1)


if __name__ == '__main__':
    unittest.main()
