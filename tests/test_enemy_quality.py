"""Warning promises, floor edits, and erasure stay true during player dodges."""
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from advanced_enemies import (AdvancedEnemy, DoodleTurret, EraserBrute, FinalEditorBoss,
                              InkOutlaw, MoonBot, OrbitalMistakeBoss,
                              PaperProjectile, RailroadStaplerBoss,
                              ScissorDirector, TumbleweedThing, WantedSketchBoss)
from camera import Camera
from particles import ParticleSystem
from player import Player
from world import PaperWorld


class EnemyQualityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, width=1200, player_x=220):
        player = Player(player_x, 542)
        player.on_ground = True
        player.invulnerable = 99
        world = PaperWorld(page=2, build_legacy=False)
        world.width = width
        world.add(0, width, 590, 18, "quality_floor", 9201)
        world.refresh_drawings([player])
        return SimpleNamespace(player=player, world=world,
                               level=SimpleNamespace(toast="", toast_time=0, chapter_index=2),
                               particles=ParticleSystem(),
                               sounds=SimpleNamespace(play=lambda *args: None),
                               camera=Camera(1120), game=SimpleNamespace(hit_stop=0))

    def test_ranged_warning_does_not_follow_a_player_crossing_the_muzzle(self):
        for enemy_type, state in ((InkOutlaw, "quickdraw"), (DoodleTurret, "aim")):
            with self.subTest(enemy=enemy_type.__name__):
                ctx = self.context()
                enemy = enemy_type(600)
                enemy.state_time = 0
                enemy.update(.001, ctx, (100, 1100))
                self.assertEqual(enemy.state, state)
                target = enemy.aim_target
                ctx.player.x = 920
                for _ in range(90):
                    enemy.update(.01, ctx, (100, 1100))
                    if enemy.projectiles:
                        break
                self.assertEqual(enemy.facing, -1)
                self.assertLess(enemy.projectiles[0].vx, 0)
                self.assertEqual(enemy.aim_target, target)

    def test_charge_keeps_the_side_shown_during_the_warning(self):
        for enemy_type, warning, attack in ((MoonBot, "ram_warn", "ram"),
                                            (TumbleweedThing, "rustle", "roll")):
            with self.subTest(enemy=enemy_type.__name__):
                ctx = self.context(player_x=800)
                enemy = enemy_type(600)
                enemy.facing = 1
                enemy._set_state(warning, .25)
                ctx.player.x = 200
                for _ in range(30):
                    enemy.update(.01, ctx, (100, 1100))
                self.assertEqual(enemy.state, attack)
                self.assertEqual(enemy.facing, 1)
                self.assertGreater(enemy.vx, 0)

    def test_eraser_lands_on_its_mark_after_player_dodges_behind_it(self):
        ctx = self.context(player_x=525)
        enemy = EraserBrute(600)
        enemy.state_time = 0
        enemy.update(.001, ctx, (100, 1100))
        self.assertEqual(enemy.state, "slam_telegraph")
        target = enemy.slam_x
        plan = enemy.floor_edit_preview
        ctx.player.x = 980
        for _ in range(150):
            enemy.update(1/60, ctx, (100, 1100))
            if enemy.state == "recover":
                break
        self.assertEqual(enemy.state, "recover")
        self.assertAlmostEqual(enemy.x, target)
        self.assertEqual(plan["platform"].erased_intervals, [(plan["start"], plan["end"])])

    def test_no_safe_floor_interval_declines_erase_instead_of_cutting_feet(self):
        ctx = self.context(width=170, player_x=73)
        enemy = AdvancedEnemy(85)
        self.assertFalse(enemy._erase_floor_temporarily(ctx, 85, width=128))
        self.assertEqual(ctx.world.platforms[0].erased_intervals, [])

    def test_published_floor_cut_never_relocates_when_player_moves_onto_it(self):
        ctx = self.context(player_x=100)
        enemy = AdvancedEnemy(600)
        plan = enemy._plan_floor_erase(ctx, 600, 128, avoid_feet=False)
        self.assertIsNotNone(plan)
        ctx.player.x = 590
        self.assertFalse(enemy._erase_floor_temporarily(ctx, 600, 128, plan=plan))
        self.assertEqual(ctx.world.platforms[0].erased_intervals, [])
        ctx.player.x = 900
        self.assertTrue(enemy._erase_floor_temporarily(ctx, 600, 128, plan=plan))
        self.assertEqual(ctx.world.platforms[0].erased_intervals, [(plan["start"], plan["end"])])
        self.assertEqual(ctx.world.platforms[0].erased, [], "temporary edits do not rewrite permanent erases")
        enemy._update_temporary_erases(2.1)
        ctx.world.refresh_drawings([ctx.player, enemy])
        self.assertEqual(ctx.world.platforms[0].erased_intervals, [])

    def test_floor_edit_ignores_unfinished_artist_strokes(self):
        ctx = self.context()
        ctx.world.platforms[0].begin_drawing()
        ctx.world.platforms[0].draw_progress = .95
        enemy = AdvancedEnemy(600)
        self.assertIsNone(enemy._plan_floor_erase(ctx, 600, avoid_feet=False))

    def test_expired_cut_preserves_later_overlapping_artist_and_other_owner_edits(self):
        ctx = self.context(player_x=100)
        enemy = AdvancedEnemy(600)
        floor = ctx.world.platforms[0]
        self.assertTrue(enemy._erase_floor_temporarily(ctx, 600, 128, duration=.5))
        other_owner = object()
        floor.erase_owned(other_owner, 600, 700)
        floor.erase(635, 750)
        self.assertEqual(floor.erased_intervals, [(536, 750)])

        enemy._update_temporary_erases(.6)
        ctx.world.refresh_drawings([ctx.player, enemy])

        self.assertEqual(enemy._temporary_erases, [])
        self.assertEqual(floor.erased_intervals, [(600, 750)])
        self.assertEqual(floor.erased, [(635, 750)])
        self.assertTrue(any(rect.collidepoint(560, 590) for rect in floor.collision_rects()))
        self.assertFalse(any(rect.collidepoint(650, 590) for rect in floor.collision_rects()))
        floor.restore_owned(other_owner)
        ctx.world.refresh_drawings([ctx.player, enemy])
        self.assertEqual(floor.erased_intervals, [(635, 750)])

    def test_forced_cleanup_removes_only_its_cut_and_is_idempotent(self):
        ctx = self.context(player_x=100)
        enemy = AdvancedEnemy(600)
        floor = ctx.world.platforms[0]
        floor.erase(100, 140)
        self.assertTrue(enemy._erase_floor_temporarily(ctx, 600, 128))
        other_owner = object()
        floor.erase_owned(other_owner, 500, 550)
        floor.erase(650, 720)
        self.assertEqual(floor.erased_intervals, [(100, 140), (500, 720)])

        enemy._restore_temporary_erases(force=True)
        enemy._restore_temporary_erases(force=True)
        ctx.world.refresh_drawings([ctx.player, enemy])

        self.assertEqual(enemy._temporary_erases, [])
        self.assertEqual(floor.erased_intervals, [(100, 140), (500, 550), (650, 720)])
        self.assertEqual(floor.erased, [(100, 140), (650, 720)])
        floor.restore_owned(other_owner)
        ctx.world.refresh_drawings([ctx.player, enemy])
        self.assertEqual(floor.erased_intervals, [(100, 140), (650, 720)])

    def test_two_enemies_restore_independent_cuts_at_different_times(self):
        ctx = self.context(player_x=100)
        floor = ctx.world.platforms[0]
        first, second = AdvancedEnemy(350), AdvancedEnemy(750)
        self.assertTrue(first._erase_floor_temporarily(ctx, 350, 128, duration=.3))
        self.assertTrue(second._erase_floor_temporarily(ctx, 750, 128, duration=1))
        self.assertEqual(floor.erased_intervals, [(286, 414), (686, 814)])

        first._update_temporary_erases(.4)
        second._update_temporary_erases(.4)
        ctx.world.refresh_drawings([ctx.player, first, second])

        self.assertEqual(floor.erased_intervals, [(686, 814)])
        second._update_temporary_erases(.7)
        ctx.world.refresh_drawings([ctx.player, first, second])
        self.assertEqual(floor.erased_intervals, [])
        self.assertEqual(floor.erased, [])

    def test_director_uses_the_prepared_page_cut_then_restores_it(self):
        ctx = self.context()
        enemy = ScissorDirector(600)
        enemy.phase = 2
        enemy.pattern_index = 2
        enemy._begin_pattern(ctx, (100, 1100))
        self.assertEqual(enemy.state, "drop_warn")
        plan = enemy.floor_edit_preview
        self.assertIsNotNone(plan)
        ctx.player.x = 900
        for _ in range(160):
            enemy.update(1/60, ctx, (100, 1100))
            if enemy.state == "open_hinge":
                break
        self.assertEqual(enemy.state, "open_hinge")
        self.assertEqual(plan["platform"].erased_intervals, [(plan["start"], plan["end"])])
        enemy._update_temporary_erases(3)
        ctx.world.refresh_drawings([ctx.player, enemy])
        self.assertEqual(plan["platform"].erased_intervals, [])

    def test_final_stamp_lands_on_the_signed_mark_after_crossing_dodge(self):
        ctx = self.context()
        enemy = FinalEditorBoss(600)
        enemy.scenario = "aggressive"
        enemy.arena_bounds = (100, 1100)
        enemy._start_pattern(ctx)
        signed_x = enemy.stamp_x
        ctx.player.x = 980
        for _ in range(120):
            enemy.update(1/60, ctx, (100, 1100))
            if enemy.state == "proof_window":
                break
        self.assertEqual(enemy.state, "proof_window")
        self.assertAlmostEqual(enemy.x, signed_x)
        self.assertIsNone(enemy.floor_edit_preview)
        self.assertGreater(enemy.attack_rect_for_state("red_stamp").width, enemy.width)

    def test_clean_margin_can_be_reached_by_running_in_a_wide_arena(self):
        ctx = self.context(width=2800, player_x=2440)
        ctx.player.invulnerable = 0
        enemy = FinalEditorBoss(600)
        enemy.scenario, enemy.phase = "aggressive", 3
        enemy.arena_bounds = (100, 2700)
        enemy._start_pattern(ctx)
        self.assertEqual(enemy.pattern, "redaction_wall")
        destination = enemy.safe_margin[1] - ctx.player.WIDTH
        health = ctx.player.health
        for _ in range(600):
            ctx.player.x = max(destination, ctx.player.x - 300/60)
            enemy.update(1/60, ctx, (100, 2700))
            if enemy.redaction_checked:
                break
        self.assertTrue(enemy.redaction_checked)
        self.assertEqual(ctx.player.health, health)

    def test_train_staple_columns_stay_in_the_drawn_border(self):
        for player_x in (105, 1080):
            ctx = self.context(player_x=player_x)
            enemy = RailroadStaplerBoss(600)
            enemy._brake(ctx, (100, 1100))
            self.assertEqual(len(set(enemy.lanes)), 3)
            self.assertTrue(all(128 <= lane <= 1072 for lane in enemy.lanes))

    def test_meteor_shards_use_the_vectors_published_by_the_landing_graph(self):
        ctx = self.context()
        enemy = OrbitalMistakeBoss(600)
        enemy.phase = 3
        vectors = enemy._shard_vectors()
        enemy._impact_shards(ctx)
        self.assertEqual(len(enemy.projectiles), 6)
        self.assertEqual([(shot.vx, shot.vy) for shot in enemy.projectiles], list(vectors))

    def test_interrupting_wet_ink_retires_the_entire_poster_volley(self):
        ctx = self.context()
        enemy = WantedSketchBoss(600)
        enemy._shuffle(ctx, (100, 1100))
        enemy._set_state("bounty_volley", .7)
        enemy.projectiles.append(PaperProjectile(ctx.player.center_x, 565, 0, 0,
                                                grace=0, terrain_collision=False))
        self.assertTrue(enemy.hit_from_weapon(1, 0, 0, {"ink"}, ctx))
        self.assertEqual(enemy.state, "poster_escape")
        self.assertEqual(enemy.projectiles, [])
        self.assertEqual(enemy.combat_targets, [])

    def test_artist_erasure_retires_attacks_and_temporary_floor_edits(self):
        ctx = self.context(player_x=100)
        enemy = AdvancedEnemy(600)
        enemy._erase_floor_temporarily(ctx, 600)
        enemy.projectiles.append(PaperProjectile(ctx.player.center_x, 565, 0, 0,
                                                grace=0, terrain_collision=False))
        enemy.artist_erasing = True
        hp = enemy.hp
        self.assertFalse(enemy.hit_from_weapon(99, 0, 0, {"heavy"}, ctx))
        enemy.update(.1, ctx, (0, 1200))
        ctx.world.refresh_drawings([ctx.player, enemy])
        self.assertEqual(enemy.hp, hp)
        self.assertEqual(enemy.projectiles, [])
        self.assertEqual(enemy._temporary_erases, [])
        self.assertEqual(ctx.world.platforms[0].erased_intervals, [])

    def test_expiry_and_forced_cleanup_wait_for_the_body_inside_a_restored_hole(self):
        for cleanup in ("expiry", "forced_cleanup"):
            with self.subTest(cleanup=cleanup):
                ctx = self.context(player_x=100)
                floor = ctx.world.platforms[0]
                floor.thickness = 50
                enemy = AdvancedEnemy(600)
                self.assertTrue(enemy._erase_floor_temporarily(ctx, 600, 128, duration=.5))
                floor.erase(1000, 1080)
                other_owner = object()
                floor.erase_owned(other_owner, 635, 710)
                supported = Player(150, 542)
                supported.on_ground = True
                # Falling into the cut is legitimate after its warning. The
                # retraced interval must wait rather than pushing this body.
                ctx.player.x, ctx.player.y = 575, 575
                ctx.player.vx = 150
                if cleanup == "expiry":
                    enemy._update_temporary_erases(.6)
                else:
                    enemy._restore_temporary_erases(force=True)
                ctx.world.refresh_drawings([ctx.player, supported, enemy])

                self.assertEqual(enemy._temporary_erases, [])
                self.assertTrue(floor.collider_active, "existing support remains active")
                self.assertTrue(any(r.collidepoint(162, 590) for r in floor.collision_rects()))
                self.assertFalse(any(r.colliderect(ctx.player.rect) for r in floor.collision_rects()))
                self.assertFalse(any(r.collidepoint(600, 590) for r in floor.collision_rects()))
                ctx.player._move_x(.01, ctx.world)
                self.assertAlmostEqual(ctx.player.x, 576.5, msg="restoring ink cannot teleport a body")

                ctx.player.x = 900
                ctx.world.refresh_drawings([ctx.player, supported, enemy])
                self.assertEqual(floor.erased_intervals, [(635, 710), (1000, 1080)])
                self.assertTrue(any(r.collidepoint(600, 590) for r in floor.collision_rects()))
                self.assertFalse(any(r.collidepoint(680, 590) for r in floor.collision_rects()))
                self.assertEqual(floor.erased, [(1000, 1080)])

    def test_completed_enemy_waiting_for_a_clear_footprint_cannot_attack_or_take_hits(self):
        ctx = self.context(player_x=590)
        ctx.player.invulnerable = 0
        enemy = AdvancedEnemy(600)
        enemy.contact_states = ("rush",)
        enemy._set_state("rush", .5)
        enemy.projectiles.append(PaperProjectile(ctx.player.center_x, 565, 0, 0,
                                                grace=0, terrain_collision=False))
        enemy.notebook_activation_blocked = True
        hp, health = enemy.hp, ctx.player.health

        self.assertFalse(enemy.hit_from_weapon(99, 0, 0, {"heavy"}, ctx))
        enemy.update(.1, ctx, (100, 1100))

        self.assertEqual(enemy.hp, hp)
        self.assertEqual(ctx.player.health, health)
        self.assertEqual(enemy.state_time, .5)


if __name__ == "__main__":
    unittest.main()
