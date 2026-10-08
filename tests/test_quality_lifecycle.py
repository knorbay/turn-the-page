"""Runtime contracts for stroke activation, erasure, retries, and audio headroom."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import math
import tempfile
import unittest
from array import array
from pathlib import Path
from types import SimpleNamespace

import pygame
from audio import NotebookSounds
from audio_mix import condition_pcm, voice_gains, EFFECT_GAIN_BUDGET, REPEATED_PEAK
from camera import Camera
from game import Game
from input_state import InputFrame
from notebook_agency import NotebookAgency
from player import Player
from scripted_events import ArtistDirector, EventSequence, EventStep
from world import PaperWorld


class QualityLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_partial_strokes_do_not_collide_and_occupied_completion_waits(self):
        world = PaperWorld(build_legacy=False)
        world.width = 1500
        ledge = world.add(200, 400, 560, 10, "live_line")
        ledge.begin_drawing()
        player = Player(250, 542)
        for progress in (0, .25, .99):
            ledge.draw_progress = progress
            world.refresh_drawings([player])
            self.assertEqual(list(world.collision_rects()), [])
        ledge.complete_drawing()
        world.refresh_drawings([player])
        self.assertEqual(ledge.lifecycle_state, "settling")
        self.assertFalse(ledge.collider_active)
        player.x = 500
        world.refresh_drawings([player])
        self.assertEqual(ledge.lifecycle_state, "active")
        self.assertTrue(ledge.collision_rects())
        player.x = 250
        world.refresh_drawings([player])
        self.assertTrue(ledge.collider_active, "normal contact cannot turn established ink off")

    def test_partial_drawing_with_future_erased_ranges_never_draws_backwards(self):
        world = PaperWorld(build_legacy=False)
        line = world.add(0, 1000, 500, name="revision")
        line.erase(400, 450)
        line.erase(650, 700)
        line.draw_progress = .2
        self.assertEqual(list(line.visible_intervals()), [(0, 200)])
        line.draw_progress = 1
        self.assertEqual(list(line.visible_intervals()), [(0, 400), (450, 650), (700, 1000)])
        self.assertFalse(any(r.collidepoint(425, 502) for r in line.collision_rects()))

    def test_retracing_an_occupied_hole_preserves_other_support_and_waits(self):
        world = PaperWorld(build_legacy=False)
        floor = world.add(0, 1000, 560, 50, "heavy_floor")
        standing = Player(200, 512)
        falling = Player(480, 575)
        world.refresh_drawings([standing])
        owner = object()
        floor.erase_owned(owner, 450, 570)
        floor.restore_owned(owner)
        world.refresh_drawings([standing, falling])
        self.assertTrue(floor.collider_active)
        self.assertFalse(any(r.colliderect(falling.rect) for r in floor.collision_rects()))
        self.assertTrue(any(r.collidepoint(standing.center_x, 561)
                            for r in floor.collision_rects()))
        falling.update(1/60, 1, world, SimpleNamespace())
        self.assertGreater(falling.x, 480)
        self.assertLess(falling.x, 510, "retracing must not eject an actor to the floor's edge")
        falling.y = 650
        world.refresh_drawings([standing, falling])
        self.assertTrue(any(r.collidepoint(500, 561) for r in floor.collision_rects()))
        self.assertEqual(list(floor.visible_intervals()), [(0, 1000)])

    def test_overlapping_owned_cut_remains_erased_when_other_cut_retraces(self):
        world = PaperWorld(build_legacy=False)
        floor = world.add(0, 1000, 560, 16, "shared_floor")
        first, second = object(), object()
        floor.erase(600, 650)
        floor.erase_owned(first, 400, 550)
        floor.erase_owned(second, 500, 700)
        world.refresh_drawings([])
        floor.restore_owned(first)
        world.refresh_drawings([])
        self.assertTrue(any(r.collidepoint(450, 561) for r in floor.collision_rects()))
        self.assertFalse(any(r.collidepoint(525, 561) for r in floor.collision_rects()))
        floor.restore_owned(second)
        world.refresh_drawings([])
        self.assertTrue(any(r.collidepoint(525, 561) for r in floor.collision_rects()))
        self.assertFalse(any(r.collidepoint(625, 561) for r in floor.collision_rects()))

    def test_airborne_exit_does_not_bypass_required_rooms_or_death(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"exit.json")
            game.reset()
            game.player.x = game.level.runtime.end_x + 10
            game.player.y = 430
            game.player.draw_amount = 1
            game.update(1/60, InputFrame())
            self.assertFalse(game.level.chapter_complete)
            self.assertFalse(game.transition_active)
            game.level.load_chapter(0, "after_moon_gate_duel", game.player, game.camera)
            game.player.x = game.level.runtime.end_x + 10
            game.player.health = 0
            game.update(1/60, InputFrame())
            self.assertGreater(game.level.respawn_timer, 0)
            self.assertFalse(game.level.chapter_complete)
            self.assertFalse(game.transition_active)

    def test_artist_director_queues_a_second_hand_and_releases_step_lock(self):
        director = ArtistDirector()
        player = Player()
        ctx = SimpleNamespace(player=player, director=director, camera=Camera(1120),
                              level=SimpleNamespace(entities=SimpleNamespace(items=[]), flags=set()))
        seen = []
        director.add(EventSequence("a", lambda ctx: True, [
            EventStep(.1, lock_player=True, update=lambda ctx,p: seen.append("a")),
            EventStep(.1, lock_player=False)]))
        director.add(EventSequence("b", lambda ctx: True, [
            EventStep(.1, update=lambda ctx,p: seen.append("b"))]))
        director.update(.05, ctx)
        self.assertEqual(seen, ["a"])
        self.assertTrue(player.locked)
        director.update(.05, ctx)
        director.update(.05, ctx)
        self.assertFalse(player.locked)
        self.assertNotIn("b", seen)
        director.update(.05, ctx)
        director.update(.1, ctx)
        self.assertIn("b", seen)

    def test_optional_stroke_keeps_the_canvas_until_complete(self):
        director = ArtistDirector()
        owner, other = object(), object()
        player = Player()
        ctx = SimpleNamespace(player=player, director=director, camera=Camera(1120),
                              level=SimpleNamespace(entities=SimpleNamespace(items=[]), flags=set()))
        seen = []
        event = director.add(EventSequence("main_line", lambda ctx: True, [
            EventStep(.1, update=lambda ctx,p: seen.append(p))]))
        self.assertTrue(director.claim_canvas(owner))
        self.assertFalse(director.claim_canvas(other))
        for _ in range(60):
            director.update(1/60, ctx)
        self.assertFalse(event.active)
        self.assertFalse(seen)
        self.assertTrue(director.blocks_combat)
        director.release_canvas(other)
        self.assertIs(director.canvas_owner, owner)
        director.release_canvas(owner)
        director.update(.1, ctx)
        self.assertTrue(event.done)
        self.assertTrue(seen)

    def test_checkpoint_completes_both_geometry_and_its_artist_timeline(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"save.json")
            game.level.load_chapter(1, "coffee", game.player, game.camera)
            for name in ("ruled_one", "ruled_two", "ruled_three"):
                self.assertTrue(next(e for e in game.level.director.events if e.name == name).done)
                self.assertIn(name, game.level.flags)
            for name in ("ruled_line_1", "ruled_line_2", "ruled_line_3"):
                self.assertEqual(game.level.world.platform_named(name).draw_progress, 1)
            game.level.load_chapter(0, "before_first_crossout", game.player, game.camera)
            game.weapons.erase_page_tools()
            game._attach_runtime()
            game.state = "playing"
            self.assertEqual(game.weapons.current_id, "unarmed")
            gift = next(e for e in game.level.entities.items
                        if getattr(e,"weapon_id",None) == "folded_shuriken")
            self.assertLess(abs(gift.x-game.player.center_x), 100)
            self.assertEqual(gift.draw_progress, 0)
            self.assertFalse(gift.collected)
            for _ in range(150):
                game.update(1/60, InputFrame())
            self.assertEqual(gift.draw_progress, 1)
            self.assertEqual(game.weapons.current_id, "unarmed")
            game.player.x = gift.x-12
            game.update(1/60, InputFrame())
            self.assertEqual(game.weapons.current_id, "folded_shuriken")

    def test_restart_during_death_discards_transient_ink_and_respawn_timer(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"save.json")
            game.reset()
            old_world = game.level.world
            old_world.add(340, 460, 475, name="transient_artist_test").begin_drawing()
            game.level.begin_respawn(game.player, "fall")
            self.assertGreater(game.level.respawn_timer, 0)
            game._activate_pause("RESTART PAGE")
            self.assertEqual(game.level.respawn_timer, 0)
            self.assertIsNot(game.level.world, old_world)
            self.assertIsNone(game.level.world.platform_named("transient_artist_test"))
            self.assertFalse(game.player.locked)
            self.assertEqual(game.weapons.current_id, "unarmed")
            for _ in range(120):
                game.update(1/60, InputFrame())
            self.assertGreater(game.player.health, 0)
            self.assertNotIn("respawn", game.player.control_locks)

    def test_an_unfinished_observed_tool_is_not_saved_or_restored_early(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"save.json")
            game.reset()
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency._restore(ctx)
            self.assertTrue(agency._begin_tool(ctx, "margin_maul", "repeated_defeat"))
            self.assertNotIn("margin_maul", game.weapons.unlocked)
            self.assertNotIn("0", game.save.data["notebook_choices"])
            game.level.restart_chapter(game.player, game.camera)
            self.assertNotIn("margin_maul", game.weapons.unlocked)
            new_agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            new_agency._restore(ctx)
            self.assertEqual(new_agency.choice, "")
            self.assertFalse(new_agency.choose("road", ctx))
            new_agency._route(ctx)
            names = [p.name for p in game.level.world.platforms]
            new_agency._route(ctx)
            self.assertEqual(names, [p.name for p in game.level.world.platforms])

    def test_effect_conditioning_reduces_brittle_highs_and_bounds_peaks(self):
        rate = 22050
        raw = array("h", (round(14000*(math.sin(math.tau*300*i/rate)
                                      + math.sin(math.tau*8500*i/rate)))
                          for i in range(rate//5))).tobytes()
        mixed_tone = array("h", condition_pcm(raw, rate))
        def energy(frequency):
            real=sum(v*math.cos(math.tau*frequency*i/rate) for i,v in enumerate(mixed_tone))
            imaginary=sum(v*math.sin(math.tau*frequency*i/rate) for i,v in enumerate(mixed_tone))
            return math.hypot(real,imaginary)
        self.assertLess(energy(8500), energy(300)*.20)
        self.assertLessEqual(max(abs(v) for v in mixed_tone), round(32767*REPEATED_PEAK))
        self.assertEqual((mixed_tone[0], mixed_tone[-1]), (0, 0))
        mixed = voice_gains([.8]*6)
        self.assertLessEqual(sum(mixed), EFFECT_GAIN_BUDGET+.00001)

    def test_active_effects_obey_volume_changes_and_burst_budget(self):
        sounds = NotebookSounds()
        sounds.apply_settings({"master_volume":1,"sfx_volume":1})
        for cue in ("pencil", "erase", "heavy_hit", "blade", "enemy_break", "paper_break"):
            sounds.play(cue, cooldown_ms=0)
        self.assertLessEqual(sum(c.get_volume() for c in sounds.effect_channels),
                             EFFECT_GAIN_BUDGET)
        self.assertTrue(any(c.get_busy() for c in sounds.effect_channels))
        sounds.apply_settings({"master_volume":0})
        self.assertTrue(all(c.get_volume()==0 for c in sounds.effect_channels))
        pygame.mixer.stop()

    def test_first_sketch_explanation_defers_achievement_without_losing_it(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"save.json")
            game.state = "playing"
            game.player.draw_amount = 1
            game.achievements.unlock("heard_you")
            game.level.discover_secret("old_first_figure", "old figure")
            game._update_achievements(1)
            self.assertIsNone(game.achievement_banner)
            self.assertTrue(game.achievements.pending)
            game.draw()
            game.level.toast_time = 0
            game._update_achievements(.1)
            self.assertIsNotNone(game.achievement_banner)
            remaining = game.achievement_time
            game.level.toast_time = 2
            game._update_achievements(1)
            self.assertEqual(game.achievement_time, remaining)
            game.level.toast_time = 0
            game._update_achievements(1)
            self.assertLess(game.achievement_time, remaining)

    def test_new_tool_reveal_keeps_its_time_until_pickup_message_finishes(self):
        with tempfile.TemporaryDirectory() as folder:
            game = Game(self.screen, Path(folder)/"tool.json")
            game.reset()
            game.level.load_chapter(0, "after_moon_gate_duel", game.player, game.camera)
            game._attach_runtime()
            game.weapons.unlock("folded_shuriken")
            game.weapons.select("folded_shuriken")
            game.level.toast_time = 4
            game.level.toast = "The Artist folds a tool into your hand."
            game.update(1/60, InputFrame())
            remaining = game.weapon_reveal_time
            self.assertEqual(remaining, 2.4)
            for _ in range(120):
                game.update(1/60, InputFrame())
            self.assertEqual(game.weapon_reveal_time, remaining)
            game.level.toast_time = 0
            game.achievement_time = 0
            game.achievements.pending.clear()
            game.update(.1, InputFrame())
            self.assertTrue(game._can_show_weapon_reveal())
            self.assertLess(game.weapon_reveal_time, remaining)
            game.draw()


if __name__ == "__main__":
    unittest.main()
