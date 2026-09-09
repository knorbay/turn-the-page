"""Contracts for the direction-correction / Turn the Page identity pass."""
from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from camera import Camera
from chapters import build_chapter
from combat import CombatArena
from game import Game
from identity_content import BOSS_ENCOUNTERS, REQUIRED_SLICE_ENCOUNTERS
from paper_renderer import PaperRenderer
from player import Player
from settings import HEIGHT, WIDTH


class IdentityRebuildContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_game(self):
        directory = tempfile.TemporaryDirectory()
        game = Game(self.screen, os.path.join(directory.name, "save.json"))
        game.state = "playing"
        return directory, game

    def test_shipping_route_is_three_long_uneven_worlds_and_fourteen_encounters(self):
        selected = 0
        for page in range(5):
            runtime = build_chapter(page)
            mandatory = {
                entity.arena_id for entity in runtime.entities.items
                if isinstance(entity, CombatArena) and entity.mandatory
            }
            self.assertEqual(mandatory, set(REQUIRED_SLICE_ENCOUNTERS.get(page, ())))
            self.assertEqual(runtime.campaign_last_index, 4)
            if page < 3:
                self.assertGreaterEqual(runtime.end_x, 10000)
            selected += len(mandatory)
        self.assertEqual(selected, 23)
        self.assertEqual([build_chapter(page).end_x for page in range(3)],
                         [10950.0, 13050.0, 16750.0])

    def test_shipping_route_contains_five_distinct_themed_bosses(self):
        found = {}
        normal_kinds = set()
        authored_spawns = 0
        for page in range(5):
            runtime = build_chapter(page)
            for arena in (entity for entity in runtime.entities.items
                          if isinstance(entity, CombatArena) and entity.mandatory):
                kinds = {str(spec["kind"]) for spec in arena.enemy_specs}
                authored_spawns += sum(int(spec.get("count", 1))
                                       for spec in arena.enemy_specs)
                normal_kinds.update(kinds - {value[0] for value in BOSS_ENCOUNTERS.values()})
                if arena.boss:
                    found[arena.arena_id] = kinds
        self.assertEqual(set(found), set(BOSS_ENCOUNTERS))
        for arena_id, (boss_kind, display_name) in BOSS_ENCOUNTERS.items():
            self.assertIn(boss_kind, found[arena_id])
            runtime_page = next(
                build_chapter(page) for page in range(5)
                if arena_id in REQUIRED_SLICE_ENCOUNTERS[page]
            )
            arena = next(entity for entity in runtime_page.entities.items
                         if isinstance(entity, CombatArena) and entity.arena_id == arena_id)
            self.assertEqual(arena.display_name, display_name)
        self.assertGreaterEqual(len(normal_kinds), 16)
        self.assertGreaterEqual(authored_spawns, 48)
        page_three = build_chapter(2)
        baby = next(entity for entity in page_three.entities.items
                    if isinstance(entity, CombatArena)
                    and entity.arena_id == "baby_face_interlude")
        final = next(entity for entity in build_chapter(4).entities.items
                     if isinstance(entity, CombatArena)
                     and entity.arena_id == "final_margin_revision")
        self.assertFalse(baby.boss)
        self.assertTrue(final.boss)

    def test_pages_and_platforms_have_real_distinct_visual_recipes(self):
        renderer = PaperRenderer()
        self.assertEqual(len(set(renderer.page_styles)), 5)
        bitmaps = {pygame.image.tostring(page, "RGB") for page in renderer.pages}
        self.assertEqual(len(bitmaps), 5)
        appearances = []
        for page in range(3):
            runtime = build_chapter(page)
            appearances.append({getattr(platform, "appearance", "")
                                for platform in runtime.world.platforms
                                if "gate" not in platform.name})
        self.assertNotEqual(appearances[0], appearances[1])
        self.assertNotEqual(appearances[1], appearances[2])
        self.assertEqual(renderer.page_styles[:3],
                         ["samurai_collage", "wild_west", "space_age"])
        self.assertIn("annotation", appearances[1])
        self.assertIn("ghost_line", appearances[2])

    def test_death_is_recorded_and_rebuilt_with_visible_monotonic_strokes(self):
        directory, game = self.make_game()
        try:
            game.level.load_chapter(0, "bridge", game.player, game.camera)
            game.level.begin_respawn(game.player, "fall", game.particles, game.sounds)
            samples = []
            pencil_seen = False
            for _ in range(220):
                game.level.update(1 / 120, game.player, game.camera, game.particles,
                                  game.sounds, False, game.session_seconds)
                if game.level.respawn_committed:
                    samples.append(game.player.draw_amount)
                    pencil_seen = pencil_seen or (
                        game.level.director.tool.visible
                        and game.level.director.tool.kind == "pencil"
                    )
                if game.level.respawn_timer <= 0:
                    break
            self.assertTrue(pencil_seen)
            self.assertTrue(samples)
            self.assertEqual(samples[0], 0)
            self.assertEqual(game.player.draw_amount, 1)
            self.assertTrue(all(a <= b + 1e-6 for a, b in zip(samples, samples[1:])))
            self.assertFalse(game.player.locked)
            self.assertEqual(game.behavior.deaths_to("fall"), 1)
            self.assertTrue(game.level.respawn_message)
            self.assertEqual(game.save.data["behavior"]["deaths_by_cause"]["fall"], 1)
        finally:
            directory.cleanup()

    def test_redraw_variants_change_marks_but_not_collision(self):
        player = Player(220, 500)
        camera = Camera(WIDTH)
        reference = player.rect.copy()
        rendered = []
        for variant in ("clean", "crooked_head", "long_arm", "long_leg", "rushed"):
            surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            player.redraw_variant = variant
            player.draw(surface, camera)
            rendered.append(pygame.image.tostring(surface, "RGBA"))
            self.assertEqual(player.rect, reference)
        self.assertGreaterEqual(len(set(rendered)), 4)

    def test_baby_face_revision_draws_moustache_and_signature_sword(self):
        directory, game = self.make_game()
        try:
            def signature_scene():
                game.level.load_chapter(2, "after_eraser_calibration",
                                        game.player, game.camera)
                game._attach_runtime()
                arena = next(entity for entity in game.level.entities.items
                             if isinstance(entity, CombatArena)
                             and entity.arena_id == "baby_face_interlude")
                beat = next(entity for entity in game.level.entities.items
                            if type(entity).__name__ == "BabyFaceSignatureBeat")
                arena.encounter_active = True
                arena.wave = 0
                context = game.level.context(game.player, game.camera,
                                             game.particles, game.sounds)
                arena._spawn_wave(context, 0)
                boss = next(enemy for enemy in arena.enemies
                            if getattr(enemy, "kind", "") == "baby_face_giant")
                return beat, boss, context

            # Attempt one stays plain and schedules the unavoidable slap.
            beat, boss, context = signature_scene()
            for _ in range(165):
                beat.update(1 / 60, context)
            self.assertEqual(boss.moustache_progress, 0)
            self.assertNotIn("excalibur", game.weapons.unlocked)
            self.assertEqual(boss.state, "page_slap_warn")

            # Attempt two adds only the moustache, then releases control.
            game.behavior.record("death", cause="baby_face_giant",
                                 arena="baby_face_interlude", weapon="eraser_cannon")
            beat, boss, context = signature_scene()
            for _ in range(75):
                beat.update(1 / 60, context)
            self.assertEqual(boss.moustache_progress, 1)
            self.assertFalse(game.player.locked)
            self.assertNotIn("excalibur", game.weapons.unlocked)

            # Attempt three locks movement for both the draw and pull motions.
            game.behavior.record("death", cause="baby_face_giant",
                                 arena="baby_face_interlude", weapon="eraser_cannon")
            beat, boss, context = signature_scene()
            beat.update(1 / 60, context)
            self.assertTrue(game.player.locked)
            for _ in range(160):
                beat.update(1 / 60, context)
                if "excalibur" in game.weapons.unlocked:
                    break
            self.assertEqual(boss.moustache_progress, 1)
            self.assertTrue(boss.empowered)
            self.assertIn("excalibur", game.weapons.unlocked)
            self.assertEqual(game.weapons.current_id, "excalibur")
            self.assertIn("THIRD ATTEMPT", game.level.toast)
        finally:
            directory.cleanup()

    def test_first_arena_annotation_is_not_a_stationary_safe_platform(self):
        directory, game = self.make_game()
        try:
            runtime = game.level.runtime
            arena = next(entity for entity in runtime.entities.items
                         if isinstance(entity, CombatArena)
                         and entity.arena_id == "first_crossout")
            cover = runtime.world.platform_named("first_crossout_artist_cover")
            cover.draw_progress = 1
            context = game.level.context(game.player, game.camera,
                                         game.particles, game.sounds)
            arena.encounter_active = True
            arena.wave = 0
            arena._spawn_wave(context, 0)
            game.player.x = (cover.x1 + cover.x2) * .5 - game.player.WIDTH / 2
            game.player.y = cover.y - game.player.HEIGHT
            game.player.health = game.player.max_health
            for _ in range(360):
                arena.update(1 / 60, context)
                if game.player.health < game.player.max_health:
                    break
            self.assertLess(game.player.health, game.player.max_health)
        finally:
            directory.cleanup()

    def test_page_turn_erases_temporary_tools_and_persists_the_empty_hand(self):
        directory, game = self.make_game()
        try:
            game.weapons.unlock("ink_pistol")
            game.weapons.select("ink_pistol")
            game._start_transition()
            game._update_transition(.70)
            self.assertTrue(game.transition_weapon_erased)
            self.assertEqual(game.weapons.unlocked, {"pencil_blade"})
            self.assertEqual(game.weapons.current_id, "pencil_blade")
            self.assertEqual(game.save.data["weapons"], ["pencil_blade"])
            self.assertEqual(game.behavior.snapshot()["counts"]["page_tools_erased"], 1)
        finally:
            directory.cleanup()

    def test_new_world_cannot_restore_a_previous_world_weapon(self):
        directory, game = self.make_game()
        try:
            game.weapons.unlock("marker_shotgun")
            snapshot = game.weapons.snapshot()
            game.save.update_combat(snapshot["unlocked"], "marker_shotgun", snapshot["ammo"])
            game.level.load_chapter(2, "start", game.player, game.camera)
            game._apply_page_identity()
            self.assertEqual(game.weapons.unlocked, {"pencil_blade"})
            self.assertNotIn("marker_shotgun", game.weapons.active_loadout)
        finally:
            directory.cleanup()


if __name__ == "__main__":
    unittest.main()
