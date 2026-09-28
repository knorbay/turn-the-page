"""The notebook puzzle must be readable, physical, and checkpoint safe."""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from camera import Camera
from behavior import BehaviorLedger
from chapters import build_chapter
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from route_puzzles import (DraftBridgePuzzle, PerforatedPosterPuzzle,
                           SatelliteRelayPuzzle)
from settings import HEIGHT, WIDTH
from world import PaperWorld


class _Sounds:
    def __init__(self):
        self.heard = []

    def play(self, cue):
        self.heard.append(cue)


class RoutePuzzleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.world = PaperWorld(0, False)
        self.world.width = 1000
        self.world.add(0, 1000, 590, 16, "safe_floor", 8001)
        self.puzzle = DraftBridgePuzzle(self.world, 100, puzzle_id="test_draft")
        self.player = Player(100, 542)
        self.player.on_ground = True
        self.level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        self.sounds = _Sounds()
        self.ctx = SimpleNamespace(player=self.player, world=self.world, level=self.level,
                                   camera=Camera(WIDTH), sounds=self.sounds,
                                   particles=ParticleSystem())

    def _stand_at(self, index):
        x, bottom = self.puzzle.marks[index]
        self.player.x = x - self.player.WIDTH / 2
        self.player.y = bottom - self.player.HEIGHT
        self.player.vx = self.player.vy = 0
        self.player.on_ground = True
        self.level.interaction_hint = ""

    def test_gate_and_ledge_change_only_after_the_visible_sequence(self):
        self.assertTrue(self.puzzle.mandatory)
        self.assertFalse(self.puzzle.completed)
        self.assertTrue(self.puzzle.gate.collision_rects())
        self.assertFalse(self.puzzle.ledge.collision_rects())

        self._stand_at(2)
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 0)
        self.assertIn("FIRST", self.level.interaction_hint)

        self._stand_at(0)
        self.puzzle.update(1 / 60, self.ctx)
        self.assertIn("E  trace", self.level.interaction_hint)
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 1)
        self.puzzle.update(.7, self.ctx)
        self.assertAlmostEqual(self.puzzle.ledge.draw_progress, 1)
        self.assertTrue(self.puzzle.ledge.collision_rects())

        # The upper symbol cannot be activated while still on the floor.
        self.player.x = self.puzzle.marks[1][0] - 12
        self.player.y = 542
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 1)
        self._stand_at(1)
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 2)
        self.puzzle.update(1 / 60, self.ctx)
        self.assertTrue(self.puzzle.ledge.collision_rects())

        self._stand_at(2)
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 3)
        self.assertTrue(self.puzzle.gate.enabled)
        self.puzzle.update(.26, self.ctx)
        self.assertTrue(self.puzzle.gate.collision_rects())
        self.puzzle.update(.27, self.ctx)
        self.assertTrue(self.puzzle.completed)
        self.assertFalse(self.puzzle.gate.collision_rects())
        self.assertIn("test_draft", self.level.flags)
        self.assertEqual(self.sounds.heard, ["pencil", "pencil", "erase", "paper_break"])

    def test_solid_gate_stops_dash_and_checkpoint_restore_opens_it(self):
        gate_rect = self.puzzle.gate.collision_rects()[0]
        self.player.x = gate_rect.left - self.player.WIDTH - 2
        self.player.y = 542
        self.player.on_ground = True
        self.assertTrue(self.player.start_dash(1, self.ctx.particles))
        for _ in range(6):
            self.player.update(1 / 30, 1, self.world, self.ctx.particles)
            self.assertLessEqual(self.player.rect.right, gate_rect.left)

        # Level's checkpoint snapshot restores this property directly.
        restored_world = PaperWorld(0, False)
        restored_world.add(0, 1000, 590, 16, "safe_floor", 8001)
        restored = DraftBridgePuzzle(restored_world, 100, puzzle_id="test_draft")
        restored.completed = True
        self.assertFalse(restored.gate.collision_rects())
        self.assertTrue(restored.ledge.collision_rects())
        self.assertEqual(restored.phase, 3)

        runner = Player(gate_rect.left - Player.WIDTH - 2, 542)
        runner.on_ground = True
        self.assertTrue(runner.start_dash(1, self.ctx.particles))
        for _ in range(6):
            runner.update(1 / 30, 1, restored_world, self.ctx.particles)
        self.assertGreater(runner.x, gate_rect.right)

    def test_new_upper_line_is_reachable_with_the_existing_jump(self):
        self._stand_at(0)
        self.puzzle.update(1 / 60, self.ctx, True)
        self.puzzle.update(.7, self.ctx)
        self.player.x = self.puzzle.marks[1][0] - 12
        self.player.y = 542
        self.player.on_ground = True
        self.player.queue_jump()
        landed = False
        for _ in range(70):
            self.player.update(1 / 60, 0, self.world, self.ctx.particles)
            if self.player.on_ground and self.player.rect.bottom == 495:
                landed = True
                break
        self.assertTrue(landed, "the drawn ledge must be reachable without a special move")
        self.puzzle.update(1 / 60, self.ctx, True)
        self.assertEqual(self.puzzle.phase, 2)

    def test_puzzle_draws_on_opaque_page_during_every_phase(self):
        renderer = PaperRenderer()
        for phase in (0, 1, 2, 3):
            with self.subTest(phase=phase):
                self.puzzle.phase = phase
                self.puzzle.ledge.draw_progress = 1 if phase else 0
                surface = pygame.Surface((WIDTH, HEIGHT))
                surface.fill((241, 235, 212))
                blank = pygame.image.tobytes(surface, "RGB")
                self.puzzle.draw(surface, self.ctx.camera, renderer)
                self.assertNotEqual(pygame.image.tobytes(surface, "RGB"), blank)
        self.puzzle.completed = True
        surface = pygame.Surface((WIDTH, HEIGHT))
        surface.fill((241, 235, 212))
        self.puzzle.draw(surface, self.ctx.camera, renderer)

    def test_wanted_poster_requires_a_dash_at_the_elevated_seam(self):
        runtime = build_chapter(1)
        world = runtime.world
        poster = next(e for e in runtime.entities.items
                      if isinstance(e, PerforatedPosterPuzzle))
        self.assertEqual((poster.ledge.x1, poster.ledge.x2, poster.ledge.y),
                         (10370, 10654, 500))
        self.assertTrue(poster.ledge.collision_rects())
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        sounds = _Sounds()
        particles = ParticleSystem()
        player = Player(poster.gate.x1 - Player.WIDTH - 5, 542)
        player.on_ground = True
        ctx = SimpleNamespace(player=player, level=level, sounds=sounds,
                              camera=Camera(WIDTH), particles=particles)
        self.assertTrue(player.start_dash(1, particles))
        for _ in range(6):
            player.update(1 / 60, 1, world, particles)
            poster.update(1 / 60, ctx)
        self.assertFalse(poster.completed)
        self.assertLessEqual(player.rect.right, poster.gate.x1)
        self.assertIn("JUMP ABOVE", level.interaction_hint)

        # Jump onto the authored y500 shelf with the real controller, then
        # walk along it through the adjacent water-tower geometry.
        player = Player(10400, 542)
        player.on_ground = True
        ctx.player = player
        player.queue_jump()
        landed = False
        for _ in range(80):
            player.update(1 / 60, 0, world, particles)
            poster.update(1 / 60, ctx)
            if player.on_ground and player.rect.bottom == 500:
                landed = True
                break
        self.assertTrue(landed, "the raised poster shelf must be reachable")
        for _ in range(120):
            if player.center_x >= 10618:
                break
            player.update(1 / 60, 1, world, particles)
            poster.update(1 / 60, ctx)
        self.assertGreaterEqual(player.center_x, 10618)
        self.assertEqual(player.rect.bottom, 500)
        self.assertTrue(player.start_dash(1, particles))
        for _ in range(12):
            player.update(1 / 60, 1, world, particles)
            poster.update(1 / 60, ctx)
            if poster.completed:
                break
        self.assertTrue(poster.completed)
        self.assertFalse(poster.gate.collision_rects())
        self.assertIn(poster.puzzle_id, level.flags)
        self.assertIn("paper_break", sounds.heard)

        restored_world = PaperWorld(1, False)
        restored = PerforatedPosterPuzzle(restored_world, 10670)
        restored.completed = True
        self.assertFalse(restored.gate.collision_rects())

    def test_satellite_star_is_carried_over_real_ledge_collisions(self):
        world = PaperWorld(2, False)
        world.width = 10300
        world.add(9000, 10300, 590, 16, "orbit_deck", 9601)
        world.add(9250, 9530, 500, 11, "satellite_a", 9602)
        world.add(9580, 9880, 465, 11, "satellite_b", 9603)
        relay = SatelliteRelayPuzzle(world, 9100)
        player = Player(relay.source[0] - Player.WIDTH / 2, 542)
        player.on_ground = True
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        particles = ParticleSystem()
        sounds = _Sounds()
        ctx = SimpleNamespace(player=player, level=level, sounds=sounds,
                              camera=Camera(WIDTH), particles=particles)
        relay.update(1 / 60, ctx, True)
        self.assertEqual(relay.phase, "carrying")
        self.assertTrue(relay.gate.collision_rects())

        # A ground-level E at the dish's x-coordinate cannot deliver it.
        player.x = relay.receiver[0] - Player.WIDTH / 2
        relay.update(1 / 60, ctx, True)
        self.assertFalse(relay.completed)
        player.x = relay.source[0] - Player.WIDTH / 2

        def walk_to(x):
            for _ in range(180):
                if player.center_x >= x:
                    return
                player.update(1 / 60, 1, world, particles)
                relay.update(1 / 60, ctx)
            self.fail("player could not walk to the satellite step")

        def jump_and_land(bottom, target_x):
            player.queue_jump()
            for _ in range(110):
                axis = 1 if player.center_x < target_x else 0
                player.update(1 / 60, axis, world, particles)
                relay.update(1 / 60, ctx)
                if player.on_ground and player.rect.bottom == bottom:
                    return
            self.fail(f"the y{bottom} satellite ledge was unreachable")

        walk_to(9255)
        jump_and_land(500, 9450)
        walk_to(9480)
        jump_and_land(465, 9725)
        walk_to(9725)
        self.assertTrue(player.on_ground)
        self.assertLess(player.rect.bottom, 590)
        self.assertGreater(relay.charge, 0)
        relay.update(1 / 60, ctx, True)
        self.assertTrue(relay.completed)
        self.assertFalse(relay.gate.collision_rects())
        self.assertIn(relay.puzzle_id, level.flags)

        # A checkpoint beyond the gate restores the physical open state.
        restored_world = PaperWorld(2, False)
        restored = SatelliteRelayPuzzle(restored_world, 9100)
        restored.completed = True
        self.assertEqual(restored.phase, "delivered")
        self.assertFalse(restored.gate.collision_rects())

    def test_satellite_charge_expiry_rearms_without_softlock(self):
        world = PaperWorld(2, False)
        world.add(9000, 10300, 590, 16, "orbit_deck", 9604)
        relay = SatelliteRelayPuzzle(world, 9100)
        player = Player(relay.source[0] - Player.WIDTH / 2, 542)
        player.on_ground = True
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        sounds = _Sounds()
        ctx = SimpleNamespace(player=player, level=level, sounds=sounds,
                              camera=Camera(WIDTH), particles=ParticleSystem())
        relay.update(1 / 60, ctx, True)
        relay.update(relay.charge_duration + .01, ctx)
        self.assertEqual(relay.phase, "idle")
        self.assertFalse(relay.completed)
        relay.update(1 / 60, ctx, True)
        self.assertEqual(relay.phase, "carrying")
        self.assertGreater(relay.charge, 14)

    def test_new_route_art_is_visible_on_opaque_pages(self):
        renderer = PaperRenderer()
        for page, cls, start in ((1, PerforatedPosterPuzzle, 10670),
                                 (2, SatelliteRelayPuzzle, 9100)):
            with self.subTest(page=page):
                world = PaperWorld(page, False)
                puzzle = cls(world, start)
                camera = Camera(WIDTH)
                camera.x = start - WIDTH / 2
                surface = pygame.Surface((WIDTH, HEIGHT))
                surface.fill((241, 235, 212))
                blank = pygame.image.tobytes(surface, "RGB")
                puzzle.draw(surface, camera, renderer)
                self.assertNotEqual(pygame.image.tobytes(surface, "RGB"), blank)

    def test_actual_solve_records_behavior_once_but_checkpoint_restore_does_not(self):
        world = PaperWorld(1, False)
        poster = PerforatedPosterPuzzle(world, 10670)
        player = Player(poster.gate.x1 - Player.WIDTH, 452)
        player.on_ground = True
        player.start_dash(1)
        ledger = BehaviorLedger()
        writes = []
        game = SimpleNamespace(behavior=ledger,
                               persist_behavior=lambda write=False: writes.append(write))
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0,
                                chapter_index=1)
        ctx = SimpleNamespace(player=player, level=level, sounds=_Sounds(),
                              camera=Camera(WIDTH), particles=ParticleSystem(), game=game)
        poster.update(1 / 60, ctx)
        self.assertTrue(poster.completed)
        self.assertEqual(ledger.count("puzzle_solved"), 1)
        self.assertEqual(ledger.data["recent"][-1]["puzzle_id"], poster.puzzle_id)
        self.assertEqual(writes, [True])

        restored = PerforatedPosterPuzzle(PaperWorld(1, False), 10670)
        restored.completed = True
        restored.update(1 / 60, ctx)
        self.assertEqual(ledger.count("puzzle_solved"), 1)
        self.assertEqual(writes, [True])


if __name__ == "__main__":
    unittest.main()
