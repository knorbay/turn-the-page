"""Recovery routes remain playable after removing copied chores and signs."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from types import SimpleNamespace
import unittest
import pygame

from camera import Camera
from chapters import build_chapter
from particles import ParticleSystem
from player import Player
from route_expeditions import RouteExpedition, RouteScenery
from scripted_events import ArtistDirector
from tutorial import TrainingLesson


class RouteCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, page=3):
        runtime = build_chapter(page)
        route = next(e for e in runtime.entities.items if isinstance(e, RouteExpedition))
        player = Player(route.left+10, 542)
        player.on_ground = True
        player.health = 2
        level = SimpleNamespace(flags=set(), interaction_hint="", toast="", toast_time=0)
        ctx = SimpleNamespace(player=player, world=runtime.world, director=ArtistDirector(),
            level=level, sounds=SimpleNamespace(play=lambda cue: None), game=None,
            particles=ParticleSystem(), weapons=None)
        return runtime, route, ctx

    def trace(self, route, ctx):
        for x, y in route.mark_positions:
            ctx.player.x, ctx.player.y = x-ctx.player.WIDTH/2, y-ctx.player.HEIGHT
            route.update(.01, ctx, True)

    def finish(self, route, ctx):
        for _ in range(100):
            route.update(.01, ctx)

    def test_each_page_has_one_short_recovery_detour_and_varied_optional_climbs(self):
        shapes = set()
        for page in range(5):
            runtime = build_chapter(page)
            routes = [e for e in runtime.entities.items if isinstance(e, RouteExpedition)]
            self.assertEqual(len(routes), 1, page)
            route = routes[0]
            self.assertFalse(route.mandatory)
            self.assertIn(len(route.mark_positions), (1, 2))
            shapes.add(tuple((p.x1-route.left, p.x2-p.x1, p.y) for p in route.landings))
            # All former copied detours retain real optional traversal lines.
            quiet = [e for e in runtime.entities.items if type(e) is RouteScenery]
            self.assertTrue(all(e.landings and not e.obstacles for e in quiet))
        self.assertEqual(len(shapes), 5)

    def test_recovery_climbs_and_drawn_bridges_are_reachable_with_normal_jumps(self):
        for page in range(5):
            runtime, route, ctx = self.context(page)
            for landing in route.landings:
                ctx.player.queue_jump()
                target = (landing.x1+landing.x2)/2
                for frame in range(260):
                    runtime.world.refresh_drawings((ctx.player,))
                    axis = 1 if ctx.player.center_x < target-5 else -1 if ctx.player.center_x > target+5 else 0
                    ctx.player.update(1/120, axis, runtime.world, ctx.particles)
                    route.update(1/120, ctx, True)
                    if (ctx.player.on_ground and abs(ctx.player.rect.bottom-landing.y) < 2
                            and abs(ctx.player.center_x-target) < 8):
                        break
                self.assertLess(abs(ctx.player.rect.bottom-landing.y), 2, (page, landing.name))
                self.assertLess(abs(ctx.player.center_x-target), 8, (page, landing.name))
            self.finish(route, ctx)
            self.assertTrue(route.completed, page)
            self.assertEqual(ctx.player.health, 3, page)
            ctx.player.queue_jump()
            target = route.bridge.x1+80
            for _ in range(180):
                runtime.world.refresh_drawings((ctx.player,))
                axis = 1 if ctx.player.center_x < target-5 else -1 if ctx.player.center_x > target+5 else 0
                ctx.player.update(1/120, axis, runtime.world, ctx.particles)
                if ctx.player.on_ground and ctx.player.center_x >= route.bridge.x1:
                    break
            self.assertEqual(ctx.player.rect.bottom, route.bridge.y, page)
            self.assertGreater(ctx.player.center_x, route.bridge.x1, page)

    def test_recovery_is_awarded_once_and_does_not_claim_to_heal_full_health(self):
        _, route, ctx = self.context()
        self.trace(route, ctx)
        self.finish(route, ctx)
        self.assertEqual(ctx.player.health, 3)
        self.assertEqual(ctx.level.toast, "Route drawn. +1 heart.")
        ctx.player.health = 1
        self.finish(route, ctx)
        self.assertEqual(ctx.player.health, 1)
        _, route, ctx = self.context()
        ctx.player.health = ctx.player.max_health
        self.trace(route, ctx)
        self.finish(route, ctx)
        self.assertEqual(ctx.level.toast, "Route drawn.")
        self.assertEqual(ctx.player.health_restore_flash, 0)

    def test_departing_or_locking_a_pending_route_releases_the_artist(self):
        for cause in ("depart", "lock", "death"):
            _, route, ctx = self.context()
            self.trace(route, ctx)
            self.assertIs(ctx.director.canvas_owner, route)
            if cause == "depart":
                ctx.player.x = route.left+route.width+200
            elif cause == "lock":
                ctx.player.acquire_lock("test")
            else:
                ctx.player.health = 0
            before = route.reward_time
            self.finish(route, ctx)
            self.assertFalse(route.completed, cause)
            self.assertEqual(route.reward_time, before, cause)
            self.assertIsNone(ctx.director.canvas_owner, cause)

    def test_recovery_waits_for_the_artist_and_has_no_repeated_jump_signs(self):
        _, route, ctx = self.context()
        calls = []
        renderer = SimpleNamespace(font_small=None,
            doodle_text=lambda surface, text, *args: calls.append(text))
        camera = Camera(1120)
        camera.x = route.left
        route.draw(pygame.display.get_surface(), camera, renderer)
        self.assertEqual(calls, ["+1 HEART", "E", "E"])
        owner = object()
        ctx.director.claim_canvas(owner)
        self.trace(route, ctx)
        self.finish(route, ctx)
        self.assertFalse(route.completed)
        self.assertEqual(ctx.player.health, 2)
        self.assertIs(ctx.director.canvas_owner, owner)
        ctx.director.release_canvas(owner)
        self.finish(route, ctx)
        self.assertTrue(route.completed)

    def test_quiet_walks_need_no_interaction_and_have_no_sign_text(self):
        for page in range(5):
            runtime, _, ctx = self.context(page)
            for route in (e for e in runtime.entities.items if type(e) is RouteScenery):
                ctx.player.x, ctx.player.y = route.left+5, 542
                ctx.player.on_ground = True
                for _ in range(round(route.width/285*120)+120):
                    runtime.world.refresh_drawings((ctx.player,))
                    ctx.player.update(1/120, 1, runtime.world, ctx.particles)
                    if ctx.player.x >= route.left+route.width:
                        break
                self.assertGreaterEqual(ctx.player.x, route.left+route.width, (page, route.index))
                self.assertEqual(ctx.player.health, 2)
                calls = []
                renderer = SimpleNamespace(font_small=None,
                    doodle_text=lambda surface, text, *args: calls.append(text))
                camera = Camera(1120)
                camera.x = route.left
                route.draw(pygame.display.get_surface(), camera, renderer)
                self.assertEqual(calls, [])

    def test_corrupt_tutorial_counters_cannot_crash_or_select_a_negative_stage(self):
        for saved in (None, "bad", {"course_revision": 2, "stage": -50, "seconds": "NaN",
                "jumps": {}, "distance": "inf", "targets": None},
                {"course_revision": 2, "stage": "bad", "dashes": float("inf"),
                 "stage_seconds": [], "targets": [False, True, -1, 100], "completed": "no"}):
            runtime = build_chapter(0)
            lesson = TrainingLesson(runtime, SimpleNamespace(data={"tutorial": saved}), "start")
            self.assertEqual(lesson.stage, 0)
            self.assertEqual(lesson.elapsed, 0)
            self.assertEqual(lesson.dashes, 0)
            self.assertFalse(lesson.completed)
            self.assertFalse(any(t.completed for t in lesson.targets))

    def test_rune_seal_explanation_is_shown_once(self):
        runtime, _, ctx = self.context(0)
        lesson = TrainingLesson(runtime, None, "start")
        ctx.player.x = lesson.seal_x-ctx.player.WIDTH/2
        ctx.player.y = lesson.seal_ground-ctx.player.HEIGHT
        lesson.update(.01, ctx, True)
        self.assertTrue(lesson.read_seal)
        self.assertEqual(ctx.level.toast, "Sketch runes grant permanent techniques. Find them on optional routes.")
        ctx.level.toast, ctx.level.toast_time, ctx.level.interaction_hint = "new toast", 1, ""
        lesson.update(.01, ctx, True)
        self.assertEqual(ctx.level.toast, "new toast")
        self.assertEqual(ctx.level.toast_time, 1)
        self.assertEqual(ctx.level.interaction_hint, "")


if __name__ == "__main__":
    unittest.main()
