import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
from pathlib import Path
import unittest
import pygame
from chapters import build_chapter
from game import Game
from particles import ParticleSystem
from player import Player
from tools.training_pilot import lesson_input


class PlayableTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_menu_replay_preserves_campaign_file_when_completed_or_cancelled(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/"save.json"
            game = Game(pygame.display.get_surface(), path)
            game.save.data.update(chapter=3, checkpoint="after_carbon_crossfire", secrets=["carbon_echo"])
            game.save.write()
            before = path.read_bytes()
            self.assertIn("TRAINING", game._title_options())
            game.start_training()
            for tick in range(15000):
                game.update(1/60, lesson_input(game))
                if game.state == "title":
                    break
            self.assertEqual(game.state, "title")
            self.assertGreaterEqual(tick/60, 75)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(game.save.data["chapter"], 3)
            game.start_training()
            game._activate_pause("TITLE")
            self.assertEqual(path.read_bytes(), before)
            self.assertFalse(game.training_only)

    def test_new_route_obstacles_can_be_crossed_with_normal_jump_physics(self):
        for page in range(5):
            runtime = build_chapter(page)
            expeditions = [e for e in runtime.entities.items if getattr(e, "is_route_expedition", False)]
            self.assertTrue(expeditions)
            for route in expeditions:
                for post in route.obstacles:
                    player = Player(post.x1-85, 542)
                    player.on_ground = True
                    particles = ParticleSystem()
                    player.queue_jump()
                    for _ in range(120):
                        runtime.world.refresh_drawings((player,))
                        player.update(1/120, 1, runtime.world, particles)
                        if player.x > post.x2+15:
                            break
                    self.assertGreater(player.x, post.x2+15, (page, post.name))

    def test_pages_contain_the_new_routes_and_preserve_authored_encounters(self):
        original = (10950, 13050, 16750, 14200, 14200)
        for page, old_end in enumerate(original):
            runtime = build_chapter(page)
            self.assertGreater(runtime.end_x-old_end, 4300)
            self.assertGreaterEqual(len([e for e in runtime.entities.items
                if getattr(e, "is_route_expedition", False)]), 1)

    def test_expedition_waypoints_restore_a_heart_and_draw_a_real_bridge(self):
        from types import SimpleNamespace
        from scripted_events import ArtistDirector
        from camera import Camera
        from paper_renderer import PaperRenderer
        runtime = build_chapter(3)
        route = next(e for e in runtime.entities.items if getattr(e, "is_route_expedition", False))
        player = Player(route.left+10, 542)
        player.health = 2
        particles = ParticleSystem()
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        ctx = SimpleNamespace(player=player, world=runtime.world, director=ArtistDirector(),
            level=level, sounds=SimpleNamespace(play=lambda cue:None), game=None)
        for x, y in route.mark_positions:
            for _ in range(240):
                runtime.world.refresh_drawings((player,))
                if player.on_ground and player.rect.bottom > y+3:
                    player.queue_jump()
                axis = 1 if player.center_x < x-7 else -1 if player.center_x > x+7 else 0
                player.update(1/120, axis, runtime.world, particles)
                route.update(1/120, ctx, True)
                if player.on_ground and abs(player.rect.bottom-y)<3 and abs(player.center_x-x)<8:
                    break
            self.assertLess(abs(player.rect.bottom-y), 3)
        camera = Camera(1120)
        camera.x = route.left
        renderer = PaperRenderer()
        for _ in range(120):
            route.update(1/120, ctx)
            route.draw_overlay(pygame.display.get_surface(), camera, renderer)
            ctx.director.draw_tool(pygame.display.get_surface(), camera)
        self.assertTrue(route.completed)
        self.assertEqual(player.health, 3)
        self.assertEqual(route.bridge.draw_progress, 1)
        self.assertIsNone(ctx.director.canvas_owner)


if __name__ == "__main__":
    unittest.main()
