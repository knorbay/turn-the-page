"""Cloud guardian warnings, real damage, return shots and weapon openings."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import unittest
import pygame

from camera import Camera
from localization import set_language
from particles import ParticleSystem
from player import Player
from paper_renderer import PaperRenderer
from secret_guardian import CloudKiteGuardian, CloudGust
from weapons import WeaponSystem
from world import PaperWorld


class CloudGuardianContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, x=380):
        player = Player(x, 295-Player.HEIGHT)
        player.on_ground = True
        world = PaperWorld(page=0, build_legacy=False)
        world.width = 1200
        return SimpleNamespace(player=player, world=world,
            weapons=WeaponSystem(player), particles=ParticleSystem(), camera=Camera(1120),
            game=None, level=SimpleNamespace(toast="", toast_time=0, chapter_index=0),
            sounds=SimpleNamespace(play=lambda _: None))

    def advance(self, enemy, ctx, seconds):
        for _ in range(round(seconds*120)):
            enemy.update(1/120, ctx, (200, 730))

    def test_three_original_attacks_warn_and_lock_their_target(self):
        for pattern, state, duration in ((0, "gust_warn", 1.05),
                                          (1, "tail_warn", .95),
                                          (2, "dive_warn", 1.05)):
            with self.subTest(pattern=pattern):
                ctx = self.context()
                guardian = CloudKiteGuardian(630, 295, seed=2)
                guardian.pattern_index = pattern
                guardian._begin_pattern(ctx, (200, 730))
                self.assertEqual(guardian.state, state)
                self.assertGreaterEqual(guardian.state_time, .95)
                target, facing = guardian.target_x, guardian.facing
                ctx.player.x = 675
                self.advance(guardian, ctx, duration-.1)
                self.assertEqual((guardian.target_x, guardian.facing), (target, facing))
                self.assertEqual(ctx.player.health, ctx.player.max_health)
                self.assertFalse(guardian.vulnerable)

    def test_ground_gust_hurts_but_leaves_an_airborne_player_safe(self):
        for jumping in (False, True):
            with self.subTest(jumping=jumping):
                ctx = self.context(380)
                if jumping:
                    ctx.player.y -= 100
                guardian = CloudKiteGuardian(630, 295)
                guardian._begin_pattern(ctx, (200, 730))
                self.advance(guardian, ctx, 1.85)
                self.assertEqual(ctx.player.health, 3 if jumping else 2)
                self.assertEqual(guardian.state, "gust")
                self.advance(guardian, ctx, 1.1)
                self.assertEqual(guardian.state, "recover")
                self.assertEqual(guardian.projectiles, [])
                self.assertTrue(guardian.vulnerable)

    def test_gust_supports_the_actual_dash_return_contract(self):
        ctx = self.context()
        ctx.player.dash_timer = .15
        shot = CloudGust(ctx.player.center_x, 273, -280, 0, "cloud_gust",
                         radius=12, gravity=0, grace=0, terrain_collision=False)
        shot.update(.001, ctx)
        self.assertEqual(shot.life, 0)
        self.assertTrue(ctx.player.return_used)
        self.assertEqual(len(ctx.weapons.projectiles), 1)
        self.assertEqual(ctx.player.health, 3)

    def test_tail_hits_the_frozen_warning_once_and_can_be_dodged(self):
        for dodge in (False, True):
            with self.subTest(dodge=dodge):
                ctx = self.context()
                guardian = CloudKiteGuardian(630, 295)
                guardian.pattern_index = 1
                guardian._begin_pattern(ctx, (200, 730))
                target = guardian.target_x
                self.advance(guardian, ctx, .9)
                if dodge:
                    ctx.player.x += 110
                self.advance(guardian, ctx, .12)
                self.assertEqual(guardian.target_x, target)
                self.assertEqual(ctx.player.health, 3 if dodge else 2)
                ctx.player.invulnerable = 0
                self.advance(guardian, ctx, .15)
                self.assertEqual(ctx.player.health, 3 if dodge else 2)
                self.advance(guardian, ctx, .12)
                self.assertTrue(guardian.vulnerable)

    def test_dive_lands_at_the_mark_and_does_not_follow_a_dodging_player(self):
        ctx = self.context()
        guardian = CloudKiteGuardian(630, 295)
        guardian.pattern_index = 2
        guardian._begin_pattern(ctx, (200, 730))
        target = guardian.target_x
        self.advance(guardian, ctx, 1.06)
        ctx.player.x = 685
        self.advance(guardian, ctx, .65)
        self.assertEqual(guardian.state, "recover")
        self.assertAlmostEqual(guardian.x, target)
        self.assertEqual(guardian.y, 295)
        self.assertEqual(ctx.player.health, 3)

    def test_dive_has_real_contact_damage_in_its_locked_landing_lane(self):
        ctx = self.context()
        guardian = CloudKiteGuardian(630, 295)
        guardian.pattern_index = 2
        guardian._begin_pattern(ctx, (200, 730))
        self.advance(guardian, ctx, 1.66)
        self.assertEqual(ctx.player.health, 2)

    def test_normal_weapons_need_an_opening_and_can_finish_the_short_fight(self):
        ctx = self.context()
        guardian = CloudKiteGuardian(630, 295)
        self.assertEqual(guardian.max_hp, 8)
        self.assertFalse(guardian.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
        self.assertEqual(guardian.hp, 8)
        for expected_hp in (6, 4, 2, 0):
            guardian._open(ctx)
            for _ in range(2):
                guardian.invulnerable = 0
                self.assertTrue(guardian.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
            self.assertEqual(guardian.hp, expected_hp)
            if expected_hp:
                self.assertFalse(guardian.vulnerable)
                guardian.invulnerable = 0
                self.assertFalse(guardian.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
        self.assertTrue(guardian.dead)
        self.assertEqual(guardian.hp, 0)
        self.assertEqual(guardian.projectiles, [])

    def test_cloud_second_draft_warns_a_distinct_followup_before_any_opening(self):
        for first in range(3):
            with self.subTest(first=first):
                ctx = self.context()
                ctx.player.invulnerable = 999
                guardian = CloudKiteGuardian(630, 295)
                guardian.hp = 4
                guardian.phase = 2
                guardian.pattern_index = first
                guardian._begin_pattern(ctx, (200, 730))
                self.assertEqual(ctx.level.toast, "SECOND DRAFT")
                self.advance(guardian, ctx,
                    guardian.state_time+guardian.patterns[first][3]+.04)
                second = guardian.followup_patterns[first]
                self.assertEqual(guardian.active_pattern, second)
                self.assertEqual(guardian.state, guardian.patterns[second][0])
                self.assertEqual(guardian.projectiles, [])
                self.assertFalse(guardian.vulnerable)
                self.assertGreaterEqual(guardian.state_duration, .90)
                locked = (guardian.target_x, guardian.facing)
                ctx.player.x = 670
                self.advance(guardian, ctx, .3)
                self.assertEqual((guardian.target_x, guardian.facing), locked)
                self.assertFalse(guardian.hit_from_weapon(99, 0, 380, {"ink"}, ctx))
                self.advance(guardian, ctx,
                    guardian.state_time+guardian.patterns[second][3]+.04)
                self.assertEqual(guardian.state, "recover")
                self.assertEqual(guardian.opening_status()[:2], (2, 2))
                self.assertEqual(guardian.projectiles, [])

    def test_second_draft_tail_after_gust_really_hits_and_can_be_left(self):
        for dodge in (False, True):
            ctx = self.context()
            ctx.player.invulnerable = 999
            guardian = CloudKiteGuardian(630, 295)
            guardian.phase = 2
            guardian._begin_pattern(ctx, (200, 730))
            self.advance(guardian, ctx, guardian.state_time+1.85+.04)
            self.assertEqual(guardian.state, "tail_warn")
            self.assertEqual(guardian.projectiles, [])
            ctx.player.invulnerable = 0
            if dodge:
                ctx.player.x += 120
            self.advance(guardian, ctx, guardian.state_time+.27)
            self.assertEqual(ctx.player.health, 3 if dodge else 2)
            self.assertEqual(guardian.state, "recover")

    def test_cloud_heavy_hits_cannot_delete_a_whole_phase(self):
        ctx = self.context()
        guardian = CloudKiteGuardian(630, 295)
        guardian._open(ctx)
        self.assertTrue(guardian.hit_from_weapon(99, 0, 380,
            {"weapon:eraser_cannon", "eraser", "heavy"}, ctx))
        self.assertAlmostEqual(guardian.hp, 6.6)
        guardian.invulnerable = 0
        self.assertTrue(guardian.hit_from_weapon(99, 0, 380,
            {"weapon:eraser_cannon", "eraser", "heavy"}, ctx))
        self.assertAlmostEqual(guardian.hp, 5.2)
        self.assertFalse(guardian.dead)
        self.assertFalse(guardian.vulnerable)
        self.assertEqual(guardian.phase, 1)

    def test_real_returning_fold_can_use_both_short_second_phase_marks(self):
        ctx = self.context(550)
        guardian = CloudKiteGuardian(630, 295)
        guardian.hp = 4
        guardian.phase = 2
        guardian._open(ctx)
        ctx.weapons.configure_page(0)
        ctx.weapons.unlock("folded_shuriken")
        ctx.weapons.select("folded_shuriken")
        ctx.weapons.aim_direction = pygame.Vector2(1, 0)
        self.assertTrue(ctx.weapons.handle_input(fire_pressed=True, ctx=ctx))
        for _ in range(156):
            guardian.update(1/120, ctx, (200, 730))
            ctx.weapons.update(1/120, ctx, [guardian])
        self.assertAlmostEqual(guardian.hp, 2.6)
        self.assertEqual(guardian.window_hits, 2)
        self.assertEqual(guardian.state, "recover")

    def test_real_starting_fold_finishes_both_phases_in_a_complete_short_duel(self):
        ctx = self.context()
        ctx.player.invulnerable = 999
        ctx.weapons.configure_page(0)
        ctx.weapons.unlock("folded_shuriken")
        ctx.weapons.select("folded_shuriken")
        ctx.weapons.aim_direction = pygame.Vector2(1, 0)
        guardian = CloudKiteGuardian(630, 295)
        elapsed = 0.0
        while not guardian.dead and elapsed < 45:
            if guardian.state == "recover":
                ctx.player.x = guardian.x-80
                ctx.weapons.handle_input(fire_pressed=True, ctx=ctx)
            guardian.update(1/120, ctx, (200, 730))
            ctx.weapons.update(1/120, ctx, [guardian])
            elapsed += 1/120
        self.assertTrue(guardian.dead)
        self.assertEqual(guardian.hp, 0)
        self.assertEqual(guardian.phase, 2)
        self.assertTrue(guardian.phase_announced)
        self.assertGreater(elapsed, 23)
        self.assertLess(elapsed, 45)

    def test_all_four_languages_draw_both_phases_and_every_state(self):
        ctx = self.context()
        renderer = PaperRenderer()
        surface = pygame.Surface((1120, 700))
        for language in ("en", "tr", "de", "it"):
            set_language(language)
            for phase in (1, 2):
                for state in ("gust_warn", "tail_warn", "tail_snap",
                              "dive_warn", "kite_dive", "recover"):
                    guardian = CloudKiteGuardian(630, 295)
                    guardian.phase = phase
                    guardian._begin_pattern(ctx, (200, 730))
                    guardian._set_state(state, 1)
                    surface.fill((241, 233, 211))
                    guardian.draw(surface, ctx.camera, renderer)
                    # It is ink geometry, not a copied compass or missing asset.
                    self.assertNotEqual(surface.get_at((630, 256))[:3], (241, 233, 211))
        set_language("tr")


if __name__ == "__main__":
    unittest.main()
