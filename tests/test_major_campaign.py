"""Real collision, ownership, reward and retry contracts for Living Runes."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

from types import SimpleNamespace
import unittest
import pygame
from chapters import build_chapter
from entities import LostSketch
from major_campaign import SecretPocket
from notebook_agency import NotebookAgency
from particles import ParticleSystem
from player import Player
from camera import Camera
from scripted_events import ArtistDirector
from sketches import SKETCHES, apply_sketch_rewards, derive_modifiers
from weapons import WeaponSystem
from advanced_enemies import MoonCompassBoss


class LivingRunesContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, page):
        runtime = build_chapter(page)
        pocket = next(e for e in runtime.entities.items if isinstance(e, SecretPocket))
        player = Player(pocket.bounds[0]+35, pocket.ground-48)
        player.on_ground = True
        player.draw_amount = 1
        collected = []
        level = SimpleNamespace(entities=runtime.entities, flags=set(), chapter_index=page,
            interaction_hint='', toast='', toast_time=0,
            discover_secret=lambda secret, caption: collected.append(secret))
        weapons = WeaponSystem(player)
        weapons.configure_page(page)
        ctx = SimpleNamespace(player=player, world=runtime.world, director=ArtistDirector(),
            level=level, weapons=weapons, particles=ParticleSystem(), game=None,
            camera=Camera(1120), sounds=SimpleNamespace(play=lambda cue: None))
        return runtime, pocket, ctx, collected

    def uncover_cloud(self, pocket, ctx):
        ctx.player.x, ctx.player.y = pocket.base+60-12, 542
        pocket.update(.01, ctx, True)
        self.assertTrue(pocket.entrance_open)
        for _ in range(50): pocket.update(1/60, ctx)
        self.assertEqual(pocket.entrance_progress, 1)
        ctx.player.x, ctx.player.y = pocket.bounds[0]+35, pocket.ground-48

    def test_all_pages_grow_with_revised_room_widths_and_stable_gate_relationships(self):
        original_ends = (10950, 13050, 16750, 14200, 14200)
        from encounter_revision import ROOM_LAYOUTS
        old_widths = {name: width for name, (width, waves) in ROOM_LAYOUTS.items()}
        for page in range(5):
            runtime = build_chapter(page)
            self.assertGreaterEqual(runtime.end_x-original_ends[page], 2300)
            arenas = [e for e in runtime.entities.items if getattr(e, 'is_combat_arena', False)]
            for arena in arenas:
                self.assertEqual(arena.end_x-arena.start_x, old_widths[arena.arena_id])
                self.assertEqual(arena.entrance_gate.x1, arena.start_x-80)
                self.assertEqual(arena.exit_gate.x2, arena.end_x)
                retry = next(cp for cp in runtime.checkpoints if cp.checkpoint_id == 'before_'+arena.arena_id)
                self.assertLess(retry.x, arena.start_x)
                self.assertLessEqual(arena.start_x-retry.x, 160)
            for a, b in zip(arenas, arenas[1:]):
                self.assertGreaterEqual(b.start_x-a.end_x, 1300)
        first = build_chapter(0)
        self.assertEqual(first.pacing_map(1415), 1415)
        self.assertEqual(first.pacing_map(1580), 5580)

    def test_secret_climbs_are_reachable_with_ordinary_jump_physics(self):
        for page in (0, 1, 3):
            runtime, pocket, ctx, _ = self.context(page)
            player = ctx.player
            if page == 0: self.uncover_cloud(pocket, ctx)
            player.x, player.y = pocket.base+12, 542
            steps = sorted((p for p in runtime.world.platforms
                            if p.name.startswith('secret_'+pocket.kind+'_step_')),
                           key=lambda p: p.x1)
            for landing in steps:
                player.queue_jump()
                reached = False
                for _ in range(180):
                    target = (landing.x1+landing.x2)/2
                    axis = 1 if player.center_x < target-5 else -1 if player.center_x > target+5 else 0
                    player.update(1/120, axis, runtime.world, ctx.particles)
                    if player.on_ground and abs(player.rect.bottom-landing.y) < 2:
                        reached = True
                        break
                self.assertTrue(reached, (page, landing.name, player.x, player.y))
            self.assertEqual(player.rect.bottom, pocket.ground)

    def test_main_road_never_starts_secret_combat_or_requires_a_secret(self):
        runtime, pocket, ctx, _ = self.context(0)
        ctx.player.y = 542
        for _ in range(120):
            pocket.update(1/60, ctx, True)
        self.assertFalse(pocket.encounter_active)
        self.assertFalse(pocket.completed)
        self.assertFalse(pocket.mandatory)
        self.assertIsNone(ctx.director.canvas_owner)
        self.assertNotIn(pocket.sketch.secret_id, runtime.required_ids)

    def test_cloud_path_is_hidden_until_the_loose_corner_is_examined(self):
        runtime, pocket, ctx, _ = self.context(0)
        self.assertFalse(pocket.entrance_open)
        self.assertTrue(all(not p.enabled and p.draw_progress == 0 for p in pocket.steps))
        self.assertTrue(all(not p.collision_rects() for p in pocket.steps))
        self.assertFalse(any('SECRET UP' in note.text for note in runtime.world.notes))
        ctx.player.x, ctx.player.y = pocket.base+60-12, 542
        pocket.update(.01, ctx)
        self.assertFalse(pocket.entrance_open)
        self.assertIn('paper corner', ctx.level.interaction_hint)
        self.uncover_cloud(pocket, ctx)
        self.assertTrue(all(p.enabled and p.draw_progress == 1 for p in pocket.steps))
        self.assertTrue(all(p.collision_rects() for p in pocket.steps))
        self.assertFalse(pocket.encounter_active)

    def test_cloud_duel_reveals_before_collision_and_cancels_cleanly_when_dropped(self):
        _, pocket, ctx, collected = self.context(0)
        self.uncover_cloud(pocket, ctx)
        pocket.update(.01, ctx, True)
        self.assertTrue(pocket.encounter_active)
        enemy = pocket.enemies[0]
        self.assertEqual(enemy.max_hp, 8)
        self.assertEqual(enemy.notebook_reveal, 0)
        ctx.weapons.damage_enemy(enemy, 99, 1, 0, 0, 'ink', ctx)
        self.assertEqual(enemy.hp, 8)
        pocket.sketch.update(.01, ctx, True)
        self.assertFalse(pocket.sketch.discovered)
        self.assertEqual(collected, [])
        self.assertIs(ctx.director.canvas_owner, pocket)
        ctx.player.y = 542
        pocket.update(.01, ctx)
        self.assertEqual(pocket.enemies, [])
        self.assertFalse(pocket.encounter_active)
        self.assertIsNone(ctx.director.canvas_owner)

    def test_cloud_guardian_requires_real_openings_then_awards_saved_movement_rune(self):
        _, pocket, ctx, collected = self.context(0)
        self.uncover_cloud(pocket, ctx)
        pocket.update(.01, ctx, True)
        enemy = pocket.enemies[0]
        for _ in range(54):
            pocket.update(1/60, ctx)
        self.assertEqual(enemy.notebook_reveal, 1)
        self.assertIsNone(ctx.director.canvas_owner)
        # The regular boss damage path enforces two strikes per opening.
        # Readability/attack sequencing itself is covered by boss contracts.
        for opening in range(4):
            enemy._set_state('recover', 1.8)
            enemy.window_hits = 0
            for _ in range(int(min(2, enemy.hp))):
                enemy.invulnerable = 0
                self.assertTrue(ctx.weapons.damage_enemy(enemy, 1, 1, 0, 0, 'pencil', ctx))
        self.assertTrue(enemy.dead)
        pocket.update(.01, ctx)
        self.assertTrue(pocket.completed)
        self.assertFalse(pocket.encounter_active)
        self.assertEqual(pocket.enemies, [])
        ctx.player.x, ctx.player.y = pocket.sketch.x-12, pocket.ground-48
        pocket.sketch.update(.01, ctx, True)
        pocket.sketch.update(.01, ctx, True)
        self.assertEqual(collected, ['cloud_heart'])
        apply_sketch_rewards(ctx.player, collected)
        self.assertEqual(ctx.player.sketch_air_control, 1.35)
        self.assertEqual(ctx.player.sketch_dash_recovery, .08)

    def test_two_mark_puzzles_draw_real_jump_step_then_save_rune_once(self):
        for page in (1, 3):
            _, pocket, ctx, collected = self.context(page)
            first, second = pocket.mark_positions
            ctx.player.x, ctx.player.y = first[0]-12, first[1]-48
            pocket.update(.01, ctx, True)
            self.assertEqual(pocket.phase, 1)
            self.assertFalse(pocket.completed)
            for _ in range(40):
                pocket.update(1/60, ctx)
            self.assertTrue(pocket.revision.collision_rects())
            # The second answer is on the Artist's new upper line.
            ctx.player.x, ctx.player.y = second[0]-12, first[1]-48
            pocket.update(.01, ctx, True)
            self.assertFalse(pocket.completed)
            ctx.player.queue_jump()
            for frame in range(180):
                ctx.player.update(1/120, 0, ctx.world, ctx.particles)
                pocket.update(1/120, ctx, frame%20 == 0)
                if pocket.completed:
                    break
            self.assertTrue(pocket.completed)
            self.assertIsNone(ctx.director.canvas_owner)
            ctx.player.x, ctx.player.y = pocket.sketch.x-12, pocket.ground-48
            pocket.sketch.update(.01, ctx, True)
            pocket.sketch.update(.01, ctx, True)
            self.assertEqual(collected, [pocket.sketch.secret_id])
            restored = build_chapter(page, collected)
            restored_pocket = next(e for e in restored.entities.items if isinstance(e, SecretPocket))
            self.assertTrue(restored_pocket.completed)
            self.assertTrue(restored_pocket.sketch.discovered)

    def test_new_runes_stack_deterministically_using_real_existing_modifiers(self):
        self.assertEqual(len(SKETCHES), 19)
        collected = ('shrine_roof','cloud_heart','old_first_figure','last_homework',
                     'water_tower','carbon_echo','agent_badge')
        modifiers = derive_modifiers(collected)
        self.assertAlmostEqual(modifiers['sketch_air_control'], 1.755)
        self.assertAlmostEqual(modifiers['sketch_dash_recovery'], .22)
        self.assertAlmostEqual(modifiers['sketch_coyote_bonus'], .12)
        self.assertEqual(modifiers['sketch_pistol_pierce'], 2)
        self.assertEqual(modifiers['sketch_pistol_velocity'], 1.625)
        player = Player()
        for _ in range(8):
            apply_sketch_rewards(player, collected*3)
        self.assertAlmostEqual(player.sketch_air_control, 1.755)
        self.assertEqual(player.max_health, 3)
        self.assertEqual(derive_modifiers(('unknown',))['sketch_pistol_pierce'], 0)

    def test_artist_redraws_one_real_heart_per_boss_without_completing_it(self):
        runtime, _, ctx, _ = self.context(0)
        agency = next(e for e in runtime.entities.items if isinstance(e, NotebookAgency))
        agency.restored = True
        arena = agency.first
        arena.encounter_active = True
        arena.encounter_time = 3
        from adaptive_artist import AdaptiveArtist
        ctx.game = SimpleNamespace(artist_director=AdaptiveArtist(),
            save=SimpleNamespace(data={}), behavior=SimpleNamespace(record=lambda *a, **k: None),
            persist_behavior=lambda **k: None)
        arena.enemies = [MoonCompassBoss(arena.start_x+300)]
        ctx.player.health = 1
        agency.update(.01, ctx)
        self.assertEqual(agency.operation, 'patch_player')
        self.assertEqual(ctx.player.health, 1)
        for _ in range(80):
            agency.update(1/60, ctx)
        self.assertEqual(ctx.player.health, 2)
        self.assertFalse(arena.completed)
        self.assertIsNone(ctx.director.canvas_owner)
        ctx.player.health = 1
        agency.update(.01, ctx)
        self.assertIsNone(agency.operation)
        self.assertEqual(ctx.player.health, 1)


if __name__ == '__main__':
    unittest.main()
