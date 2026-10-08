"""Intentional chapter cast sizes and bounded Artist responses."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from collections import Counter
from copy import deepcopy
from types import SimpleNamespace
import unittest

from adaptive_artist import AdaptiveArtist
from chapters import build_chapter
from encounter_variety import (CHAPTER_CASTS, MAX_AUTHORED_ENEMIES,
                               MAX_ADAPTED_ENEMIES, compose_encounter_variety)


class EncounterVarietyContracts(unittest.TestCase):
    def test_every_page_changes_cast_sizes_without_adding_boss_guards(self):
        for page in range(5):
            runtime = build_chapter(page)
            sizes = set()
            for arena in runtime.entities.items:
                if not getattr(arena, 'is_combat_arena', False):
                    continue
                if arena.boss or arena.arena_id == 'baby_face_interlude':
                    self.assertEqual(len(arena.enemy_specs), 1)
                    continue
                counts = Counter(s.get('wave', 0) for s in arena.enemy_specs)
                sizes.update(counts.values())
                self.assertLessEqual(max(counts.values()), MAX_AUTHORED_ENEMIES)
                self.assertEqual(len(counts), len(CHAPTER_CASTS[page][arena.arena_id]))
            self.assertIn(2, sizes)
            self.assertIn(5, sizes)
            self.assertGreaterEqual(len(sizes), 3)

    def test_cast_composition_is_repeatable_and_has_no_route_geometry_side_effects(self):
        for page in range(5):
            first, second = build_chapter(page), build_chapter(page)
            geometry = [(p.name, p.x1, p.x2, p.y) for p in first.world.platforms]
            before = [deepcopy(a.enemy_specs) for a in first.entities.items
                      if getattr(a, 'is_combat_arena', False)]
            compose_encounter_variety(first)
            after = [a.enemy_specs for a in first.entities.items
                     if getattr(a, 'is_combat_arena', False)]
            repeat = [a.enemy_specs for a in second.entities.items
                      if getattr(a, 'is_combat_arena', False)]
            self.assertEqual(before, after)
            self.assertEqual(after, repeat)
            self.assertEqual(geometry, [(p.name, p.x1, p.x2, p.y) for p in first.world.platforms])
            self.assertEqual(first.end_x, second.end_x)

    def test_artist_challenge_does_not_add_a_seventh_opponent(self):
        runtime = build_chapter(4)
        arena = next(a for a in runtime.entities.items
                     if getattr(a, 'arena_id', '') == 'unfinished_corridor')
        arena.enemy_specs = [{'wave': 0, 'kind': 'ink_clone', 'offset': 250+i*100}
                             for i in range(MAX_ADAPTED_ENEMIES)]
        artist = AdaptiveArtist({'recent': [
            {'result': 'clear', 'damage': 0, 'seconds': 22, 'boss': False}]*2})
        ctx = SimpleNamespace(level=SimpleNamespace(chapter_index=4), game=None)
        original = deepcopy(arena.enemy_specs)
        artist.prepare_encounter(arena, ctx)
        self.assertEqual(arena.artist_mode, 'challenge')
        self.assertEqual(arena.enemy_specs, original)
        self.assertEqual(arena.artist_notice, '')
        artist.prepare_encounter(arena, ctx)
        self.assertEqual(arena.enemy_specs, original)

    def test_artist_chooses_a_distinct_chapter_threat_for_the_extra_slot(self):
        for page in range(5):
            runtime = build_chapter(page)
            for arena in runtime.entities.items:
                if (not getattr(arena, 'is_combat_arena', False) or arena.boss
                        or arena.arena_id == 'baby_face_interlude'):
                    continue
                last = max(arena.wave_ids)
                existing = {s['kind'] for s in arena.enemy_specs if s.get('wave', 0) == last}
                artist = AdaptiveArtist({'recent': [
                    {'result': 'clear', 'damage': 0, 'seconds': 22, 'boss': False}]*2})
                ctx = SimpleNamespace(level=SimpleNamespace(chapter_index=page), game=None)
                artist.prepare_encounter(arena, ctx)
                added = [s for s in arena.enemy_specs if s.get('artist_challenge')]
                self.assertEqual(len(added), 1)
                self.assertNotIn(added[0]['kind'], existing)


if __name__ == '__main__':
    unittest.main()
