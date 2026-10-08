"""Player movement owns framing unless a cutscene explicitly owns control."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import unittest

import pygame

from camera import Camera
from chapters import build_chapter
from combat import CombatArena
from player import Player
from scripted_events import ArtistDirector, EventSequence, EventStep


class CameraFollowContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def settle(self, camera, x, y=526, vx=0, locked=False, seconds=1.5):
        for _ in range(round(seconds * 60)):
            camera.update(1 / 60, x, 30000, vx, y, player_locked=locked)

    def context(self):
        player = Player(4000, 526)
        return SimpleNamespace(player=player, camera=Camera(1120),
            director=ArtistDirector(), level=SimpleNamespace(
                entities=SimpleNamespace(items=[]), flags=set()))

    def test_unlocked_controller_releases_a_stale_scene_target(self):
        camera = Camera(1120)
        camera.script_target = 12000
        self.settle(camera, 4200)
        self.assertIsNone(camera.script_target)
        self.assertAlmostEqual(camera.x, 4200 - 560, delta=1)

    def test_locked_scene_frames_the_drawing_then_returns_to_the_player(self):
        camera = Camera(1120)
        camera.set_script_target(8000, "sword_scene")
        self.settle(camera, 4200, locked=True)
        self.assertAlmostEqual(camera.x, 8000 - 560, delta=1)
        self.settle(camera, 4200, locked=False)
        self.assertIsNone(camera.script_target)
        self.assertAlmostEqual(camera.screen_x(4200), 560, delta=1)

    def test_follow_changes_direction_with_the_player(self):
        camera = Camera(1120)
        self.settle(camera, 4200, vx=320)
        right = camera.x
        self.assertAlmostEqual(camera.screen_x(4200), 490, delta=2)
        self.settle(camera, 3500, vx=-320)
        self.assertLess(camera.x, right - 600)
        self.assertAlmostEqual(camera.screen_x(3500), 630, delta=2)
        self.settle(camera, 3500)
        self.assertAlmostEqual(camera.screen_x(3500), 560, delta=2)

    def test_world_edges_still_bound_the_camera(self):
        camera = Camera(1120)
        camera.update(2, 50, 2000, -400)
        self.assertEqual(camera.target_x, 0)
        camera.update(2, 1950, 2000, 400)
        self.assertEqual(camera.target_x, 880)
        camera.update(2, 200, 500)
        self.assertEqual(camera.target_x, 0)

    def test_high_climb_follows_world_position_then_restores_floor_framing(self):
        camera = Camera(1120)
        self.settle(camera, 4200, y=526)
        self.assertEqual(camera.offset_y, 0)
        self.settle(camera, 4200, y=280)
        self.assertGreater(camera.offset_y, 100)
        self.assertAlmostEqual(280 + camera.offset_y, 400, delta=1)
        self.settle(camera, 4200, y=-220)
        self.assertGreater(camera.offset_y, 600)
        self.assertAlmostEqual(-220 + camera.offset_y, 400, delta=1)
        self.settle(camera, 4200, y=526)
        self.assertAlmostEqual(camera.offset_y, 0, delta=1)

    def test_scene_target_ends_with_its_step_not_with_the_whole_timeline(self):
        ctx = self.context()
        scene = EventSequence("draw_bridge", lambda ctx: True, [
            EventStep(.1, lock_player=True, camera_x=8000),
            EventStep(2, lock_player=False)])
        scene.update(.05, ctx)
        self.assertTrue(ctx.player.locked)
        self.assertEqual(ctx.camera.script_target, 8000)
        scene.update(.05, ctx)
        self.assertIsNone(ctx.camera.script_target)
        scene.update(.05, ctx)
        self.assertFalse(ctx.player.locked)
        self.assertFalse(scene.done)
        self.assertIsNone(ctx.camera.script_target)

    def test_unlocked_drawing_cannot_override_the_follow_camera(self):
        ctx = self.context()
        scene = EventSequence("draw_while_running", lambda ctx: True, [
            EventStep(2, camera_x=12000)])
        scene.update(.05, ctx)
        self.assertFalse(ctx.player.locked)
        self.assertIsNone(ctx.camera.script_target)

    def test_scene_suspension_releases_its_camera_without_erasing_another_owner(self):
        ctx = self.context()
        scene = EventSequence("bridge", lambda ctx: True, [
            EventStep(2, lock_player=True, camera_x=8000)])
        scene.update(.05, ctx)
        ctx.level.entities.items = [SimpleNamespace(is_combat_arena=True,
            encounter_active=True, completed=False)]
        scene.update(.05, ctx)
        self.assertFalse(ctx.player.locked)
        self.assertIsNone(ctx.camera.script_target)
        ctx.camera.set_script_target(10000, "baby_face_revision")
        scene.update(.05, ctx)
        self.assertEqual(ctx.camera.script_target, 10000)

    def test_live_boss_room_follows_both_directions_and_ignores_enemy_motion(self):
        runtime = build_chapter(0)
        arena = next(entity for entity in runtime.entities.items
            if isinstance(entity, CombatArena) and entity.arena_id == "moon_gate_duel")
        ctx = self.context()
        ctx.player.x = arena.start_x + 150
        arena.encounter_active = True
        arena.enemies = [SimpleNamespace(x=arena.end_x - 100, is_boss=True, dead=False)]
        ctx.camera.script_target = (arena.start_x + arena.end_x) / 2
        arena._frame_active_fight(ctx)
        self.settle(ctx.camera, ctx.player.center_x)
        left = ctx.camera.x
        ctx.player.x += 800
        arena._frame_active_fight(ctx)
        self.settle(ctx.camera, ctx.player.center_x)
        self.assertGreater(ctx.camera.x, left + 790)
        arena.enemies[0].x -= 700
        arena._frame_active_fight(ctx)
        self.settle(ctx.camera, ctx.player.center_x)
        self.assertAlmostEqual(ctx.camera.screen_x(ctx.player.center_x), 560, delta=1)
        ctx.player.x -= 650
        arena._frame_active_fight(ctx)
        self.settle(ctx.camera, ctx.player.center_x)
        self.assertAlmostEqual(ctx.camera.x, left + 150, delta=1)
        self.assertIsNone(ctx.camera.script_target)

    def test_boss_room_preserves_explicit_sword_reveal_lock(self):
        ctx = self.context()
        ctx.player.acquire_lock("baby_face_revision")
        ctx.camera.script_target = 8000
        CombatArena._frame_active_fight(SimpleNamespace(), ctx)
        self.settle(ctx.camera, ctx.player.center_x, locked=ctx.player.locked)
        self.assertEqual(ctx.camera.script_target, 8000)
        ctx.player.release_lock("baby_face_revision")
        CombatArena._frame_active_fight(SimpleNamespace(), ctx)
        self.assertIsNone(ctx.camera.script_target)


if __name__ == "__main__":
    unittest.main()
