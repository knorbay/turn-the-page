"""Live attacks, traversal drawing and physical terrain edits never overlap."""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from action_content import ArenaPaperBeat, WeaponPickup
from campaign import ArtistCombatHand, FinalPageEdit
from combat import CombatArena
from game import Game
from scripted_events import ArtistTool
from settings import WIDTH, HEIGHT


class ArtistStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.game = Game(self.screen, Path(self.temp.name) / "save.json")

    def tearDown(self):
        self.temp.cleanup()

    def load(self, page, checkpoint="start"):
        game = self.game
        game.level.load_chapter(page, checkpoint, game.player, game.camera)
        game._apply_page_identity()
        return game.level.context(game.player, game.camera, game.particles, game.sounds)

    def arena(self, arena_id):
        return next(e for e in self.game.level.entities.items
                    if isinstance(e, CombatArena) and e.arena_id == arena_id)

    def test_west_exit_bridge_queues_until_the_entire_arena_is_clear(self):
        ctx = self.load(1, "coffee")
        arena = self.arena("coffee_crossfire")
        event = next(e for e in ctx.director.events if e.name == "margin_exit")
        arena.encounter_active = True
        ctx.player.x = 5970
        for _ in range(180):
            ctx.director.update(1 / 60, ctx)
        self.assertFalse(event.active)
        self.assertFalse(event.done)
        self.assertFalse(ctx.player.locked)
        self.assertFalse(ctx.director.tool.visible)
        arena.completed = True
        arena.encounter_active = False
        for _ in range(240):
            ctx.director.update(1 / 60, ctx)
        self.assertTrue(event.done)
        self.assertIn("margin_exit", ctx.level.flags)
        self.assertFalse(ctx.player.locked)

    def test_the_room_cover_finishes_before_the_gate_and_enemies_activate(self):
        ctx = self.load(3, "before_agent_checkpoint")
        arena = self.arena("agent_checkpoint")
        beat = next(e for e in ctx.level.entities.items
                    if isinstance(e, ArenaPaperBeat) and e.arena is arena)
        ctx.player.x = arena.start_x + 8
        arena.update(1 / 60, ctx)
        self.assertFalse(arena.encounter_active)
        self.assertFalse(arena.entrance_gate.enabled)
        self.assertFalse(arena.enemies)
        for _ in range(50):
            beat.update(1 / 60, ctx)
            arena.update(1 / 60, ctx)
        self.assertTrue(beat.entry_ready)
        self.assertTrue(beat.cover.collision_rects())
        self.assertTrue(arena.encounter_active)
        self.assertTrue(arena.enemies)
        ctx.director.tool = ArtistTool()
        beat.update(.5, ctx)
        self.assertFalse(ctx.director.tool.visible)

    def test_landing_and_cover_edit_hold_the_next_wave_and_never_add_health(self):
        ctx = self.load(3, "before_carbon_crossfire")
        arena = self.arena("carbon_crossfire")
        stages = arena.artist_stages
        hand = next(s for s in stages if isinstance(s, ArtistCombatHand))
        beat = next(s for s in stages if isinstance(s, ArenaPaperBeat))
        beat.cover.draw_progress = 1
        ctx.player.x = arena.start_x + 25
        ctx.player.health = 1
        arena.encounter_active = True
        arena.wave = 0
        arena._spawn_wave(ctx, 0)
        hand.update(8, ctx)
        self.assertEqual(hand.phase, "waiting")
        self.assertEqual(hand.platform.draw_progress, 0)
        self.assertEqual(ctx.player.health, 1)
        arena.enemies.clear()
        hand_seen = False
        for _ in range(300):
            ctx.director.tool = ArtistTool()
            arena.update(1 / 60, ctx)
            for stage in stages:
                stage.update(1 / 60, ctx)
            if ctx.director.tool.visible:
                hand_seen = True
                self.assertFalse(arena.enemies)
            if arena.wave == 1:
                break
        self.assertTrue(hand_seen)
        self.assertTrue(hand.completed)
        self.assertTrue(hand.platform.collision_rects())
        self.assertTrue(beat.wave_ready)
        self.assertEqual(arena.wave, 1)
        self.assertEqual(ctx.player.health, 1)

    def test_cover_is_kept_when_the_player_is_standing_on_it(self):
        ctx = self.load(3, "before_carbon_crossfire")
        arena = self.arena("carbon_crossfire")
        beat = next(s for s in arena.artist_stages if isinstance(s, ArenaPaperBeat))
        beat.cover.draw_progress = 1
        arena.encounter_active = True
        arena.wave = 0
        ctx.player.x = (beat.cover.x1 + beat.cover.x2) / 2
        ctx.player.y = beat.cover.y - ctx.player.rect.height
        for _ in range(90):
            beat.update(1 / 60, ctx)
        self.assertTrue(beat.wave_ready)
        self.assertEqual(beat.cover.erased, [])
        self.assertTrue(any(r.collidepoint(ctx.player.center_x, beat.cover.y + 1)
                            for r in beat.cover.collision_rects()))

    def test_pickup_uses_the_page_drawing_and_requires_a_close_collection(self):
        ctx = self.load(3)
        pickup = WeaponPickup(650, 590, "ink_pistol")
        ctx.player.x = 430
        for _ in range(60):
            pickup.update(1 / 60, ctx)
        self.assertEqual(pickup.draw_progress, 1)
        self.assertFalse(pickup.collected)
        self.assertNotIn("ink_pistol", ctx.weapons.unlocked)
        self.assertEqual(pickup.display_label, "SUPPRESSED PISTOL")
        ctx.player.x = 638
        pickup.update(1 / 60, ctx)
        self.assertTrue(pickup.collected)
        self.assertIn("ink_pistol", ctx.weapons.unlocked)
        self.assertIn("SUPPRESSED PISTOL", ctx.level.toast)

    def test_pickup_and_final_boss_edit_do_not_put_a_large_hand_over_attacks(self):
        ctx = self.load(4, "before_final_margin_revision")
        arena = self.arena("final_margin_revision")
        arena.encounter_active = True
        arena._spawn_wave(ctx, 0)
        arena.enemies[0].scenario = "precise"
        ctx.player.x = arena.start_x + 120
        pickup = WeaponPickup(ctx.player.center_x + 100, 590, "marker_shotgun")
        edit = next(e for e in ctx.level.entities.items if isinstance(e, FinalPageEdit))
        for _ in range(180):
            ctx.director.tool = ArtistTool()
            pickup.update(1 / 60, ctx)
            edit.update(1 / 60, ctx)
            self.assertFalse(ctx.director.tool.visible)
        self.assertEqual(pickup.draw_progress, 0)
        self.assertTrue(edit.completed)
        self.assertTrue(all(p.draw_progress == 1 and p.collision_rects()
                            for p in edit.platforms))


if __name__ == "__main__":
    unittest.main()
