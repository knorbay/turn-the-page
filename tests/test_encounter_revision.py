"""The arena route moves as one map; authored duels and wave breaks stay fair."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
import pygame

from chapters import build_chapter
from combat import CombatArena
from encounter_revision import BOSS_KINDS, ROOM_LAYOUTS
from entities import LostSketch
from game import Game
from input_state import InputFrame
from settings import WIDTH, HEIGHT


class EncounterRevisionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def arenas(self, runtime):
        return [e for e in runtime.entities.items if isinstance(e, CombatArena)]

    def test_every_authored_room_is_wider_without_overlapping_the_next_room(self):
        found = set()
        for page in range(5):
            runtime = build_chapter(page)
            arenas = self.arenas(runtime)
            for arena in arenas:
                found.add(arena.arena_id)
                self.assertEqual(arena.end_x-arena.start_x, ROOM_LAYOUTS[arena.arena_id][0])
                self.assertGreater(arena.end_x-arena.start_x, arena.authored_width)
                self.assertEqual(arena.entrance_gate.x1, arena.start_x-80)
                self.assertEqual(arena.exit_gate.x2, arena.end_x)
                checkpoint = next(cp for cp in runtime.checkpoints
                                  if cp.checkpoint_id == 'before_'+arena.arena_id)
                self.assertLess(checkpoint.x, arena.entrance_gate.x1-15)
                self.assertLessEqual(arena.start_x-checkpoint.x, 160)
            for current, later in zip(arenas, arenas[1:]):
                self.assertGreater(later.start_x-current.end_x, 800)
            self.assertEqual(runtime.world.width, runtime.end_x+220)
        self.assertEqual(found, set(ROOM_LAYOUTS))

    def test_every_page_has_short_rooms_combinations_and_three_part_gauntlets(self):
        for page in range(5):
            runtime = build_chapter(page)
            wave_counts = {len(a.wave_ids) for a in self.arenas(runtime)
                           if not a.boss and a.arena_id != 'baby_face_interlude'}
            self.assertTrue({1, 3} <= wave_counts, (page, wave_counts))
        self.assertEqual({len(a.wave_ids) for page in range(5)
            for a in self.arenas(build_chapter(page)) if not a.boss}, {1, 2, 3})

    def test_named_bosses_are_single_duels_with_no_regular_guard_wave(self):
        found = {}
        for page in range(5):
            for arena in self.arenas(build_chapter(page)):
                if not arena.boss:
                    continue
                found[arena.arena_id] = arena
                self.assertEqual(arena.wave_ids, [0])
                self.assertEqual([spec['kind'] for spec in arena.enemy_specs],
                                 [BOSS_KINDS[arena.arena_id]])
                self.assertGreaterEqual(arena.end_x-arena.start_x, 2300)
        self.assertEqual(set(found), set(BOSS_KINDS))
        baby = next(a for a in self.arenas(build_chapter(2))
                    if a.arena_id == 'baby_face_interlude')
        self.assertFalse(baby.boss)  # Preserve its three-attempt Artist story.
        self.assertEqual([s['kind'] for s in baby.enemy_specs], ['baby_face_giant'])

    def test_insertion_floor_is_physical_and_short_covers_never_stretch_with_it(self):
        for page in range(5):
            runtime = build_chapter(page)
            for arena in self.arenas(runtime):
                midpoint = (arena.start_x+arena.end_x)*.5
                floors = [p for p in runtime.world.platforms if p.y == 590
                          and any(rect.collidepoint(midpoint, 594)
                                  for rect in p.collision_rects())]
                self.assertTrue(floors, arena.arena_id)
                for platform in runtime.world.platforms:
                    if platform.name == arena.arena_id+'_artist_cover':
                        self.assertEqual(platform.x2-platform.x1, 190)
                for spec in arena.enemy_specs:
                    self.assertGreaterEqual(spec['offset'], 250)
                    self.assertLess(spec['offset'], arena.end_x-arena.start_x-100)

    def test_room_insertions_do_not_add_quiet_expeditions_inside_a_fight(self):
        for page in range(5):
            runtime = build_chapter(page)
            for expedition in (e for e in runtime.entities.items
                               if getattr(e, 'is_route_expedition', False)):
                for arena in self.arenas(runtime):
                    self.assertFalse(arena.start_x < expedition.left < arena.end_x,
                                     (page, arena.arena_id, expedition.left))
            for sketch in (e for e in runtime.entities.items if isinstance(e, LostSketch)):
                self.assertLess(sketch.x, runtime.end_x+100)

    def test_actual_walk_enters_each_single_room_after_the_artist_finishes_cover(self):
        cases = ((0, 'first_crossout'), (1, 'pistol_margin_drill'),
                 (2, 'safe_pocket_counterattack'), (3, 'agent_checkpoint'),
                 (4, 'unfinished_corridor'))
        for page, arena_id in cases:
            with self.subTest(room=arena_id), tempfile.TemporaryDirectory() as directory:
                game = Game(self.screen, Path(directory)/'save.json')
                game.state = 'playing'
                game.level.load_chapter(page, 'before_'+arena_id, game.player, game.camera)
                game._attach_runtime()
                arena = next(a for a in self.arenas(game.level.runtime) if a.arena_id == arena_id)
                for _ in range(240):
                    game.update(1/60, InputFrame(right=not arena.encounter_active))
                    if arena.encounter_active:
                        break
                self.assertTrue(arena.encounter_active)
                self.assertEqual(arena.wave, 0)
                self.assertTrue(arena.entrance_gate.enabled)
                self.assertTrue(arena.enemies)
                self.assertEqual(game.behavior.count('deaths'), 0)
                for enemy in arena.enemies:
                    self.assertGreaterEqual(enemy.rect.left, arena.entrance_gate.x2+8)
                    self.assertLessEqual(enemy.rect.right, arena.exit_gate.x1-8)

    def test_retry_load_preserves_all_gate_and_post_room_requirements(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/'save.json')
            for page in range(5):
                names = [a.arena_id for a in self.arenas(build_chapter(page))]
                for arena_id in names:
                    with self.subTest(page=page, room=arena_id):
                        game.level.load_chapter(page, 'before_'+arena_id, game.player, game.camera)
                        before = next(a for a in self.arenas(game.level.runtime) if a.arena_id == arena_id)
                        self.assertFalse(before.completed)
                        self.assertTrue(before.exit_gate.enabled)
                        self.assertLess(game.player.rect.right, before.entrance_gate.x1)
                        game.level.load_chapter(page, 'after_'+arena_id, game.player, game.camera)
                        after = next(a for a in self.arenas(game.level.runtime) if a.arena_id == arena_id)
                        self.assertTrue(after.completed)
                        self.assertFalse(after.exit_gate.enabled)
                        self.assertIn(arena_id, game.level.flags)
                        self.assertGreater(game.player.x, after.end_x)
                        for later in self.arenas(game.level.runtime):
                            if later.start_x > after.end_x:
                                self.assertFalse(later.completed)


if __name__ == '__main__':
    unittest.main()
