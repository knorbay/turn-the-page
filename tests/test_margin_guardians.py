"""Real chapter guardian contracts: published danger, counterplay and rewards."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import re
import unittest
import pygame

from camera import Camera
from localization import CATALOGS, SUPPORTED_LANGUAGES, set_language, translate
from localization_guardians import GUARDIAN_TEXT
from margin_guardians import (GUARDIAN_CLASSES, BrassTumbleweedGuardian,
                              OrbitCrabGuardian, CarbonHoundGuardian,
                              DraftMothGuardian, GuardianProjectile)
from paper_renderer import PaperRenderer
from optional_encounters import OPTIONAL_DUELS
from particles import ParticleSystem
from player import Player
from weapons import WeaponSystem
from world import PaperWorld
from sketches import collection_message, sketch_for


class ChapterGuardianContracts(unittest.TestCase):
    bounds = (160, 880)

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
            enemy.update(1/120, ctx, self.bounds)

    def begin(self, cls, pattern, ctx):
        enemy = cls(660, 295, seed=17)
        enemy.pattern_index = pattern
        enemy._begin_pattern(ctx, self.bounds)
        return enemy

    def test_all_twelve_warnings_lock_aim_and_never_damage(self):
        for cls in GUARDIAN_CLASSES.values():
            for pattern in range(3):
                with self.subTest(kind=cls.kind, pattern=pattern):
                    ctx = self.context()
                    enemy = self.begin(cls, pattern, ctx)
                    warning = enemy.patterns[pattern]
                    self.assertEqual(enemy.state, warning[0])
                    self.assertGreaterEqual(enemy.state_time, 1.0)
                    lock = (enemy.target_x, enemy.target_y, enemy.facing, enemy.shot_vectors)
                    # Cross the body and both arena edges after its warning.
                    ctx.player.x = 860
                    self.advance(enemy, ctx, .4)
                    ctx.player.x = 166
                    self.advance(enemy, ctx, warning[2]-.51)
                    self.assertEqual((enemy.target_x, enemy.target_y,
                                      enemy.facing, enemy.shot_vectors), lock)
                    self.assertEqual(enemy.state, warning[0])
                    self.assertEqual(ctx.player.health, ctx.player.max_health)
                    self.assertFalse(enemy.vulnerable)

    def test_every_attack_finishes_with_a_projectile_free_two_hit_opening(self):
        for cls in GUARDIAN_CLASSES.values():
            for pattern in range(3):
                with self.subTest(kind=cls.kind, pattern=pattern):
                    ctx = self.context(820)
                    enemy = self.begin(cls, pattern, ctx)
                    duration = enemy.patterns[pattern][2]+enemy.patterns[pattern][3]
                    self.advance(enemy, ctx, duration+.04)
                    self.assertEqual(enemy.state, "recover")
                    self.assertEqual(enemy.projectiles, [])
                    self.assertTrue(enemy.vulnerable)
                    remaining, total, fraction = enemy.opening_status()
                    self.assertEqual((remaining, total), (2, 2))
                    self.assertGreater(fraction, .9)
                    self.assertEqual(enemy.y, 295)
                    self.assertGreaterEqual(enemy.x, self.bounds[0]+enemy.radius)
                    self.assertLessEqual(enemy.x, self.bounds[1]-enemy.radius)

    def test_ten_marks_take_five_normal_weapon_openings(self):
        for cls in GUARDIAN_CLASSES.values():
            with self.subTest(kind=cls.kind):
                ctx = self.context()
                enemy = cls(660, 295)
                self.assertEqual(enemy.max_hp, 10)
                self.assertFalse(enemy.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
                for expected in (8, 6, 4, 2, 0):
                    enemy._open(ctx)
                    for _ in range(2):
                        enemy.invulnerable = 0
                        self.assertTrue(enemy.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
                    self.assertEqual(enemy.hp, expected)
                    if expected:
                        self.assertFalse(enemy.vulnerable)
                        self.assertEqual(enemy.opening_status()[0], 0)
                        enemy.invulnerable = 0
                        self.assertFalse(enemy.hit_from_weapon(1, 0, 380, {"ink"}, ctx))
                self.assertTrue(enemy.dead)
                self.assertEqual(enemy.projectiles, [])

    def test_heavy_tool_advantage_cannot_skip_multiple_opening_marks(self):
        for cls in GUARDIAN_CLASSES.values():
            ctx = self.context()
            enemy = cls(660, 295)
            enemy._open(ctx)
            self.assertTrue(enemy.hit_from_weapon(99, 0, 380,
                {"weapon:eraser_cannon", "eraser", "heavy"}, ctx))
            self.assertAlmostEqual(enemy.hp, 8.6)
            enemy.invulnerable = 0
            self.assertTrue(enemy.hit_from_weapon(99, 0, 380,
                {"weapon:eraser_cannon", "eraser", "heavy"}, ctx))
            self.assertAlmostEqual(enemy.hp, 7.2)
            enemy.invulnerable = 0
            self.assertFalse(enemy.hit_from_weapon(99, 0, 380,
                {"weapon:eraser_cannon", "eraser", "heavy"}, ctx))
            self.assertFalse(enemy.dead)

    def test_second_draft_links_two_fixed_warnings_before_the_two_hit_opening(self):
        for cls in GUARDIAN_CLASSES.values():
            for pattern in range(3):
                with self.subTest(kind=cls.kind, pattern=pattern):
                    ctx = self.context(820)
                    enemy = cls(660, 295)
                    enemy.hp = 5
                    enemy.phase = 2
                    enemy.pattern_index = pattern
                    enemy._begin_pattern(ctx, self.bounds)
                    self.assertEqual(enemy.combo_remaining, 1)
                    first = enemy.active_pattern
                    ctx.player.invulnerable = 999
                    self.advance(enemy, ctx,
                        enemy.state_time+enemy.patterns[first][3]+.04)
                    second = cls.followup_patterns[first]
                    self.assertEqual(enemy.active_pattern, second)
                    self.assertEqual(enemy.state, enemy.patterns[second][0])
                    self.assertFalse(enemy.vulnerable)
                    self.assertEqual(enemy.projectiles, [])
                    self.assertGreaterEqual(enemy.state_duration, .9)
                    locked = (enemy.target_x, enemy.target_y, enemy.facing, enemy.shot_vectors)
                    ctx.player.x = 200
                    self.advance(enemy, ctx, .3)
                    self.assertEqual((enemy.target_x, enemy.target_y, enemy.facing,
                                      enemy.shot_vectors), locked)
                    self.assertFalse(enemy.hit_from_weapon(10, 0, 380, {"ink"}, ctx))
                    self.advance(enemy, ctx,
                        enemy.state_time+enemy.patterns[second][3]+.04)
                    self.assertEqual(enemy.state, "recover")
                    self.assertEqual(enemy.projectiles, [])
                    self.assertEqual(enemy.opening_status()[:2], (2, 2))
                    self.assertLess(enemy.state_duration, 1.65)

    def test_phase_two_followup_is_a_real_attack_that_can_be_dodged(self):
        for cls, first in ((BrassTumbleweedGuardian, 0),
                           (CarbonHoundGuardian, 0), (OrbitCrabGuardian, 0)):
            for dodge in (False, True):
                with self.subTest(kind=cls.kind, dodge=dodge):
                    ctx = self.context()
                    ctx.player.invulnerable = 999
                    enemy = cls(660, 295)
                    enemy.phase = 2
                    enemy.pattern_index = first
                    enemy._begin_pattern(ctx, self.bounds)
                    self.advance(enemy, ctx,
                        enemy.state_time+enemy.patterns[first][3]+.04)
                    self.assertNotEqual(enemy.active_pattern, first)
                    ctx.player.invulnerable = 0
                    if dodge:
                        ctx.player.x += 170
                    self.advance(enemy, ctx,
                        enemy.state_time+enemy.patterns[enemy.active_pattern][3]+.04)
                    self.assertEqual(ctx.player.health, 3 if dodge else 2)
                    self.assertEqual(enemy.state, "recover")

    def test_real_five_opening_clear_reaches_second_draft_and_takes_a_full_duel(self):
        for cls in GUARDIAN_CLASSES.values():
            with self.subTest(kind=cls.kind):
                ctx = self.context()
                ctx.player.invulnerable = 999
                enemy = cls(660, 295)
                elapsed = 0.0
                opening_age = 0.0
                warnings = set()
                while not enemy.dead and elapsed < 55:
                    enemy.update(1/120, ctx, self.bounds)
                    elapsed += 1/120
                    if enemy.state == "recover":
                        opening_age += 1/120
                        if (enemy.window_hits == 0 and opening_age >= .20
                                or enemy.window_hits == 1 and opening_age >= .60):
                            self.assertTrue(enemy.hit_from_weapon(1, 0, 380,
                                {"weapon:pencil_blade", "melee"}, ctx))
                    else:
                        opening_age = 0.0
                        if enemy.phase == 2:
                            warnings.add(enemy.state)
                self.assertTrue(enemy.dead)
                self.assertEqual(enemy.phase, 2)
                self.assertTrue(enemy.phase_announced)
                self.assertGreaterEqual(len(warnings), 4)
                self.assertGreater(elapsed, 18)
                self.assertLess(elapsed, 45)

    def test_actual_split_bolt_hits_one_mark_and_saw_pulses_hit_two(self):
        for cls in GUARDIAN_CLASSES.values():
            for weapon, damage, marks in (("fold_crossbow", .95, 1),
                                           ("orbit_saw", 1.44, 2)):
                with self.subTest(kind=cls.kind, weapon=weapon):
                    ctx = self.context(480)
                    enemy = cls(660, 295)
                    enemy.hp = 5
                    enemy.phase = 2
                    enemy._open(ctx)
                    ctx.weapons.configure_page(3 if weapon == "fold_crossbow" else 2)
                    ctx.weapons.unlock(weapon)
                    ctx.weapons.select(weapon)
                    ctx.weapons.aim_direction = pygame.Vector2(1, 0)
                    self.assertTrue(ctx.weapons.handle_input(fire_pressed=True, ctx=ctx))
                    for _ in range(120):
                        enemy.update(1/120, ctx, self.bounds)
                        ctx.weapons.update(1/120, ctx, [enemy])
                    self.assertAlmostEqual(enemy.hp, 5-damage, places=4)
                    self.assertEqual(enemy.window_hits, marks)
                    self.assertEqual(enemy.state, "recover")
                    if marks == 2:
                        self.assertFalse(enemy.vulnerable)

    def test_actual_chapter_starting_tools_can_cash_both_short_opening_marks(self):
        cases = ((BrassTumbleweedGuardian, 1, "ink_pistol"),
                 (OrbitCrabGuardian, 2, "rubber_band"),
                 (CarbonHoundGuardian, 3, "ink_pistol"),
                 (DraftMothGuardian, 4, "margin_maul"))
        for cls, page, weapon in cases:
            with self.subTest(kind=cls.kind, weapon=weapon):
                ctx = self.context(550)
                ctx.weapons.configure_page(page)
                ctx.weapons.unlock(weapon)
                ctx.weapons.select(weapon)
                ctx.weapons.aim_direction = pygame.Vector2(1, 0)
                enemy = cls(660, 295)
                enemy.hp = 5
                enemy.phase = 2
                enemy._open(ctx)
                for _ in range(180):
                    if enemy.state != "recover":
                        break
                    ctx.weapons.handle_input(fire_pressed=True, ctx=ctx)
                    enemy.update(1/120, ctx, self.bounds)
                    ctx.weapons.update(1/120, ctx, [enemy])
                self.assertEqual(enemy.window_hits, 2)
                self.assertGreater(5-enemy.hp, 1.4)
                self.assertGreater(enemy.hp, 0)

    def test_body_is_safe_during_idle_warning_and_recovery(self):
        for cls in GUARDIAN_CLASSES.values():
            with self.subTest(kind=cls.kind):
                ctx = self.context(650)
                enemy = cls(660, 295)
                for state in ("idle", enemy.patterns[0][0], "recover"):
                    enemy._set_state(state, 1)
                    enemy._deal_contact_damage(ctx)
                    self.assertEqual(ctx.player.health, ctx.player.max_health)

    def test_low_wheels_hit_feet_and_leave_a_jump_safe(self):
        for cls, pattern in ((BrassTumbleweedGuardian, 2), (OrbitCrabGuardian, 0)):
            for jumped in (False, True):
                with self.subTest(kind=cls.kind, jumped=jumped):
                    ctx = self.context()
                    enemy = self.begin(cls, pattern, ctx)
                    if jumped:
                        ctx.player.y -= 105
                    self.advance(enemy, ctx, enemy.patterns[pattern][2]+.9)
                    self.assertEqual(ctx.player.health, 3 if jumped else 2)

    def test_lasso_and_stamp_hit_the_mark_once_and_can_be_left(self):
        for cls in (BrassTumbleweedGuardian, CarbonHoundGuardian):
            for dodge in (False, True):
                with self.subTest(kind=cls.kind, dodge=dodge):
                    ctx = self.context()
                    enemy = self.begin(cls, 1, ctx)
                    target = enemy.target_x
                    if dodge:
                        ctx.player.x += 130
                    self.advance(enemy, ctx, 1.13)
                    self.assertEqual(enemy.target_x, target)
                    self.assertEqual(ctx.player.health, 3 if dodge else 2)
                    ctx.player.invulnerable = 0
                    self.advance(enemy, ctx, .12)
                    self.assertEqual(ctx.player.health, 3 if dodge else 2)

    def test_ground_charges_hit_the_lane_and_can_be_jumped(self):
        for cls in (BrassTumbleweedGuardian, CarbonHoundGuardian):
            for jumped in (False, True):
                with self.subTest(kind=cls.kind, jumped=jumped):
                    ctx = self.context()
                    enemy = self.begin(cls, 0, ctx)
                    if jumped:
                        ctx.player.y -= 110
                    target = enemy.target_x
                    self.advance(enemy, ctx, 1.96)
                    self.assertEqual(enemy.state, "recover")
                    self.assertAlmostEqual(enemy.x, target, places=4)
                    self.assertEqual(ctx.player.health, 3 if jumped else 2)

    def test_lunar_drop_lands_at_its_mark_and_does_not_follow_dodge(self):
        for dodge in (False, True):
            with self.subTest(dodge=dodge):
                ctx = self.context()
                enemy = self.begin(OrbitCrabGuardian, 2, ctx)
                target = enemy.target_x
                self.advance(enemy, ctx, 1.05)
                self.assertLess(enemy.y, 210)
                if dodge:
                    ctx.player.x += 165
                self.advance(enemy, ctx, .74)
                self.assertEqual(enemy.state, "recover")
                self.assertAlmostEqual(enemy.x, target)
                self.assertEqual(enemy.y, 295)
                self.assertEqual(ctx.player.health, 3 if dodge else 2)

    def test_close_claw_and_wing_attacks_have_real_range_and_can_be_left(self):
        for cls, pattern in ((OrbitCrabGuardian, 1), (DraftMothGuardian, 2)):
            for dodge in (False, True):
                with self.subTest(kind=cls.kind, dodge=dodge):
                    ctx = self.context(590)
                    enemy = self.begin(cls, pattern, ctx)
                    if dodge:
                        ctx.player.x -= 170
                    self.advance(enemy, ctx, enemy.patterns[pattern][2]+.06)
                    self.assertEqual(ctx.player.health, 3 if dodge else 2)

    def test_twin_page_cut_has_a_published_safe_middle(self):
        for step_into_page in (False, True):
            with self.subTest(step_into_page=step_into_page):
                ctx = self.context()
                enemy = self.begin(DraftMothGuardian, 0, ctx)
                target = enemy.target_x
                if step_into_page:
                    ctx.player.x += 70
                self.advance(enemy, ctx, 1.17)
                self.assertEqual(enemy.target_x, target)
                self.assertEqual(ctx.player.health, 2 if step_into_page else 3)

    def test_carbon_and_dust_fans_commit_to_the_warning_and_hit(self):
        for cls, pattern in ((CarbonHoundGuardian, 2), (DraftMothGuardian, 1)):
            for dodge in (False, True):
                with self.subTest(kind=cls.kind, dodge=dodge):
                    ctx = self.context()
                    enemy = self.begin(cls, pattern, ctx)
                    vectors = enemy.shot_vectors
                    if dodge:
                        ctx.player.y -= 140
                    self.advance(enemy, ctx, enemy.patterns[pattern][2]+1.45)
                    self.assertEqual(enemy.shot_vectors, vectors)
                    self.assertEqual(ctx.player.health, 3 if dodge else 2)

    def test_all_four_projectiles_support_real_dash_returns(self):
        for kind in ("brass_spur", "orbit_ring", "carbon_slip", "moth_dust"):
            with self.subTest(kind=kind):
                ctx = self.context()
                ctx.player.dash_timer = .15
                shot = GuardianProjectile(ctx.player.center_x, 273, -220, 0, kind,
                    radius=11, gravity=0, grace=0, terrain_collision=False)
                shot.update(.001, ctx)
                self.assertEqual(shot.life, 0)
                self.assertTrue(ctx.player.return_used)
                self.assertEqual(len(ctx.weapons.projectiles), 1)
                self.assertEqual(ctx.player.health, ctx.player.max_health)

    def test_all_silhouettes_and_states_render_in_four_languages(self):
        ctx, renderer = self.context(), PaperRenderer()
        surface = pygame.Surface((1120, 700))
        backdrop = (241, 233, 211)
        try:
            for language in ("en", "tr", "de", "it"):
                set_language(language)
                for cls in GUARDIAN_CLASSES.values():
                    for pattern in range(3):
                        enemy = self.begin(cls, pattern, ctx)
                        warning, active, _, _, _ = enemy.patterns[pattern]
                        for state in (warning, active, "recover"):
                            with self.subTest(language=language, kind=cls.kind, state=state):
                                enemy._set_state(state, 1)
                                surface.fill(backdrop)
                                enemy.draw(surface, ctx.camera, renderer)
                                pixels = pygame.PixelArray(surface)
                                background = surface.map_rgb(backdrop)
                                changed = sum(pixels[x, y] != background
                                              for x in range(610, 710, 4)
                                              for y in range(220, 286, 4))
                                del pixels
                                self.assertGreater(changed, 30)
        finally:
            set_language("tr")

    def test_every_new_duel_prompt_and_rune_is_covered_in_all_catalogs(self):
        sources = set(GUARDIAN_TEXT)
        for spec in OPTIONAL_DUELS:
            sources.update((spec.title, spec.rule, spec.caption,
                            f"E  challenge {spec.title.lower()} / optional"))
            rune = sketch_for(spec.rune)
            sources.update((rune.title, rune.technique, rune.benefit, rune.detail))
        try:
            for language in ("tr", "de", "it"):
                set_language(language)
                self.assertEqual(set(CATALOGS[language]), set(CATALOGS["tr"]))
                for source in sources:
                    with self.subTest(language=language, source=source):
                        self.assertIn(source, CATALOGS[language])
                        self.assertNotEqual(translate(source), source)
                        self.assertEqual(translate(translate(source)), translate(source))
        finally:
            set_language("tr")

    def test_reward_pickup_translates_the_technique_and_preserves_its_numbers(self):
        try:
            for language in ("tr", "de", "it"):
                set_language(language)
                for spec in OPTIONAL_DUELS:
                    with self.subTest(language=language, rune=spec.rune):
                        source = collection_message(spec.rune)
                        copy = translate(source)
                        rune = sketch_for(spec.rune)
                        self.assertIn(translate(rune.technique), copy)
                        self.assertIn(translate(rune.detail), copy)
                        self.assertNotIn("TECHNIQUE LEARNED", copy)
                        self.assertEqual(re.findall(r"\d+(?:\.\d+)?", source),
                                         re.findall(r"\d+(?:\.\d+)?", copy))
                        self.assertEqual(translate(copy), copy)
        finally:
            set_language("tr")

    def test_all_attack_and_opening_cues_fit_440_pixels_in_four_languages(self):
        renderer = PaperRenderer()
        try:
            for language in SUPPORTED_LANGUAGES:
                set_language(language)
                for cls in GUARDIAN_CLASSES.values():
                    cues = (cls.opening_cue, *(pattern[4] for pattern in cls.patterns))
                    for cue in cues:
                        with self.subTest(language=language, cue=cue):
                            self.assertLessEqual(renderer.font_small.size(cue)[0], 440)
                            self.assertNotRegex(translate(cue), r"Space|W/|W /")
        finally:
            set_language("tr")


if __name__ == "__main__":
    unittest.main()
