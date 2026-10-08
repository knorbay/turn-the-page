"""Ordinary rooms fill their lanes without turning duels into crowded waves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import pygame

from adaptive_artist import AdaptiveArtist
from camera import Camera
from chapters import build_chapter
from combat import CombatArena
from encounter_revision import ROOM_LAYOUTS
from encounter_variety import CHAPTER_CASTS, MAX_AUTHORED_ENEMIES, MAX_ADAPTED_ENEMIES
from game import Game
from input_state import InputFrame
from particles import ParticleSystem
from player import Player
from scripted_events import ArtistDirector
from settings import WIDTH, HEIGHT
from weapons import WeaponSystem


class EncounterDensityContracts(unittest.TestCase):
    @staticmethod
    def normal_rooms(runtime):
        return [e for e in runtime.entities.items if isinstance(e, CombatArena)
                and e.mandatory and not e.boss and e.arena_id != 'baby_face_interlude']

    @staticmethod
    def wave_sizes(arena):
        sizes = Counter()
        for spec in arena.enemy_specs:
            sizes[int(spec.get('wave', 0))] += int(spec.get('count', 1))
        return sizes

    @staticmethod
    def context(runtime, arena):
        player = Player(arena.start_x+120, 542)
        player.on_ground = True
        player.invulnerable = 100
        level = SimpleNamespace(entities=runtime.entities, flags=set(),
            chapter_index=runtime.index, interaction_hint='', toast='', toast_time=0)
        weapons = WeaponSystem(player)
        weapons.configure_page(runtime.index)
        return SimpleNamespace(player=player, world=runtime.world, level=level,
            weapons=weapons, particles=ParticleSystem(), director=ArtistDirector(),
            camera=Camera(1120), game=None, sounds=SimpleNamespace(play=lambda cue: None))

    def assert_clear_spawn(self, arena, ctx, count):
        self.assertEqual(len(arena.enemies), count)
        for index, enemy in enumerate(arena.enemies):
            self.assertFalse(enemy.is_boss)
            self.assertFalse(enemy.notebook_spawn_pending, enemy.kind)
            self.assertGreaterEqual(enemy.rect.left, arena.entrance_gate.x2+8)
            self.assertLessEqual(enemy.rect.right, arena.exit_gate.x1-8)
            self.assertFalse(enemy.rect.colliderect(ctx.player.rect))
            for other in arena.enemies[index+1:]:
                self.assertFalse(enemy.rect.colliderect(other.rect),
                                 (arena.arena_id, enemy.kind, other.kind))

    def test_all_normal_mandatory_waves_have_two_to_five_with_authored_chapter_rhythms(self):
        rooms = waves = 0
        found_sizes = set()
        for page in range(5):
            for arena in self.normal_rooms(build_chapter(page)):
                with self.subTest(page=page, room=arena.arena_id):
                    sizes = self.wave_sizes(arena)
                    self.assertEqual(len(sizes), ROOM_LAYOUTS[arena.arena_id][1])
                    self.assertTrue(set(sizes.values()) <= {2, 3, 4, 5})
                    self.assertEqual(list(sizes.values()),
                                     list(map(len, CHAPTER_CASTS[page][arena.arena_id])))
                    found_sizes.update(sizes.values())
                    casts = [tuple(spec['kind'] for spec in arena.enemy_specs
                                   if int(spec.get('wave', 0)) == wave)
                             for wave in arena.wave_ids]
                    if len(casts) > 1:
                        self.assertGreater(len({frozenset(cast) for cast in casts}), 1)
                    for cast in casts:
                        self.assertEqual(len(set(cast)), len(cast))
                    rooms += 1
                    waves += len(sizes)
        self.assertEqual((rooms, waves), (18, 34))
        self.assertEqual(found_sizes, {2, 3, 4, 5})

    def test_every_authored_wave_really_spawns_in_separate_gate_safe_footprints(self):
        for page in range(5):
            runtime = build_chapter(page)
            for arena in self.normal_rooms(runtime):
                ctx = self.context(runtime, arena)
                for wave, count in self.wave_sizes(arena).items():
                    with self.subTest(page=page, room=arena.arena_id, wave=wave):
                        arena.enemies.clear()
                        arena._spawn_wave(ctx, wave)
                        self.assert_clear_spawn(arena, ctx, count)
                        self.assertCountEqual([e.kind for e in arena.enemies],
                            [s['kind'] for s in arena.enemy_specs
                             if int(s.get('wave', 0)) == wave])

    def test_real_entry_camera_shows_all_opening_enemies_in_each_normal_room(self):
        pygame.init()
        screen = pygame.display.set_mode((WIDTH, HEIGHT))
        try:
            for page in range(5):
                ids = [a.arena_id for a in self.normal_rooms(build_chapter(page))]
                for room_id in ids:
                    with self.subTest(page=page, room=room_id), tempfile.TemporaryDirectory() as directory:
                        game = Game(screen, Path(directory)/'save.json')
                        game.state = 'playing'
                        game.level.load_chapter(page, 'before_'+room_id, game.player, game.camera)
                        game._attach_runtime()
                        arena = next(a for a in self.normal_rooms(game.level.runtime)
                                     if a.arena_id == room_id)
                        for _ in range(300):
                            game.update(1/60, InputFrame(right=not arena.encounter_active))
                            if arena.encounter_active:
                                break
                        self.assertTrue(arena.encounter_active)
                        positions = [e.x for e in arena.enemies]
                        self.assertLessEqual(max(positions)-min(positions), 850)
                        for _ in range(80):
                            game.update(1/60, InputFrame())
                            if all(e.notebook_reveal >= 1 for e in arena.enemies):
                                break
                        self.assertEqual(len(arena.enemies), self.wave_sizes(arena)[0])
                        for enemy in arena.enemies:
                            self.assertEqual(enemy.notebook_reveal, 1)
                            left = game.camera.screen_x(enemy.rect.left)
                            right = game.camera.screen_x(enemy.rect.right)
                            visible_width = max(0, min(WIDTH, right)-max(0, left))
                            self.assertGreaterEqual(visible_width/enemy.rect.width, .85,
                                                    (room_id, enemy.kind, left, right))
        finally:
            pygame.quit()

    def test_each_page_combines_air_and_ground_instead_of_only_repeating_gunners(self):
        for page in range(5):
            runtime = build_chapter(page)
            has_mixed_wave = False
            kinds = set()
            for arena in self.normal_rooms(runtime):
                ctx = self.context(runtime, arena)
                for wave in arena.wave_ids:
                    arena.enemies.clear()
                    arena._spawn_wave(ctx, wave)
                    kinds.update(e.kind for e in arena.enemies)
                    has_mixed_wave |= {e.uses_gravity for e in arena.enemies} == {True, False}
            self.assertTrue(has_mixed_wave, page)
            self.assertGreaterEqual(len(kinds), 5, page)

    def test_artist_challenge_adds_one_up_to_six_and_never_accumulates_on_retry(self):
        for page in range(5):
            runtime = build_chapter(page)
            for arena in self.normal_rooms(runtime):
                with self.subTest(page=page, room=arena.arena_id):
                    ctx = self.context(runtime, arena)
                    original = deepcopy(arena.enemy_specs)
                    artist = AdaptiveArtist({'recent': [
                        {'result': 'clear', 'damage': 0, 'seconds': 22, 'boss': False}
                    ]*2})
                    artist.prepare_encounter(arena, ctx)
                    self.assertEqual(arena.artist_mode, 'challenge')
                    self.assertLessEqual(max(self.wave_sizes(arena).values()), MAX_ADAPTED_ENEMIES)
                    last = max(arena.wave_ids)
                    base_count = sum(s.get("count", 1) for s in original if s.get("wave", 0) == last)
                    self.assertEqual(self.wave_sizes(arena)[last], base_count+1)
                    challenged = deepcopy(arena.enemy_specs)
                    artist.prepare_encounter(arena, ctx)
                    self.assertEqual(arena.enemy_specs, challenged)
                    arena._spawn_wave(ctx, max(arena.wave_ids))
                    self.assert_clear_spawn(arena, ctx, base_count+1)
                    artist.room(page, arena)['deaths'] = 2
                    artist.prepare_encounter(arena, ctx)
                    self.assertEqual(arena.artist_mode, 'support')
                    self.assertEqual(arena.enemy_specs, original)

    def test_five_body_waves_keep_real_attack_warnings_spaced_and_at_most_two_sources(self):
        cases = ((0, 'bamboo_static', 2), (1, 'coffee_crossfire', 2),
                 (2, 'eraser_calibration', 1), (3, 'redacted_rooftops', 2),
                 (4, 'the_last_crossout', 1))
        for page, room_id, wave in cases:
            with self.subTest(page=page, room=room_id):
                runtime = build_chapter(page)
                arena = next(a for a in self.normal_rooms(runtime) if a.arena_id == room_id)
                ctx = self.context(runtime, arena)
                arena._spawn_wave(ctx, wave)
                self.assertEqual(len(arena.enemies), 5)
                ctx.player.x = arena.start_x+(arena.end_x-arena.start_x)*.46
                starts = []
                for enemy in arena.enemies:
                    enemy.notebook_reveal = 1
                for _ in range(480):
                    previous_start = arena._last_attack_start
                    arena._coordinate_pressure(ctx, 1/60)
                    for enemy in arena.enemies:
                        enemy.update(1/60, ctx, (arena.start_x-45, arena.end_x-35))
                    self.assertLessEqual(len(arena._pressure_load()), 2)
                    if arena._last_attack_start != previous_start:
                        starts.append(arena._last_attack_start)
                self.assertGreater(len(starts), 2)
                for earlier, later in zip(starts, starts[1:]):
                    self.assertGreaterEqual(later-earlier, .24-1e-8)


if __name__ == '__main__':
    unittest.main()
