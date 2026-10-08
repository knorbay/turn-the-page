"""Boss entrances must fade as one stamp and leave threats unobscured."""
import hashlib
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from boss_presentation import draw_boss_entrance, _wrap_rule, PORTRAIT_DURATION
from localization import set_language
from paper_renderer import PaperRenderer
from settings import WIDTH, HEIGHT


class BossPresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        set_language("en")
        pygame.quit()

    def frame(self, elapsed, kind="moon_compass", title="AY RONİNİ", rule="YANA ZIPLA. BIÇAĞI VUR."):
        surface = pygame.Surface((WIDTH, HEIGHT))
        surface.fill((242, 235, 211))
        draw_boss_entrance(surface, self.renderer, kind, title, rule, elapsed)
        return surface

    def digest(self, surface):
        return hashlib.sha256(pygame.image.tobytes(surface, "RGB")).digest()

    def test_text_and_seal_disappear_with_the_paper_at_both_edges(self):
        plain = pygame.Surface((WIDTH, HEIGHT))
        plain.fill((242, 235, 211))
        for elapsed in (-.1, 0, 2.8, 3.0):
            self.assertEqual(self.digest(self.frame(elapsed)), self.digest(plain))
        nearly_gone = self.frame(2.79)
        # The old card faded only its fill, leaving fully opaque title pixels.
        maximum_change = max(abs(nearly_gone.get_at((x,y))[channel]-plain.get_at((x,y))[channel])
            for x in range(225, 895, 2) for y in range(82, 224, 2) for channel in range(3))
        self.assertLess(maximum_change, 10)
        self.assertNotEqual(self.digest(self.frame(1.0)), self.digest(plain))

    def test_attack_lane_and_player_are_untouched_during_the_whole_entrance(self):
        plain = pygame.Surface((WIDTH, HEIGHT))
        plain.fill((242, 235, 211))
        attack_lane = pygame.Rect(0, 300, WIDTH, 340)
        expected = self.digest(plain.subsurface(attack_lane))
        for elapsed in (.1, .3, .65, 1.2, 2.6):
            self.assertEqual(self.digest(self.frame(elapsed).subsurface(attack_lane)), expected)

    def test_named_boss_seals_have_distinct_silhouettes(self):
        kinds = ("moon_compass", "wanted_sketch", "railroad_stapler", "orbital_mistake",
                 "scissor_director", "final_editor", "baby_face_giant", "cloud_kite",
                 "brass_tumbleweed", "orbit_crab", "carbon_hound", "draft_moth")
        seals = [self.frame(1.0, kind).subsurface(pygame.Rect(794, 96, 86, 112))
                 for kind in kinds]
        self.assertEqual(len({self.digest(seal) for seal in seals}), len(kinds))

    def test_localized_rules_wrap_inside_stamp_without_splitting_translation(self):
        set_language("tr")
        rule = "Read your old draft. Attack when its guard drops."
        lines = _wrap_rule(rule, self.renderer.font_small, 525)
        self.assertGreaterEqual(len(lines), 1)
        self.assertLessEqual(len(lines), 2)
        self.assertNotIn("Read", " ".join(lines))
        for line in lines:
            self.assertLessEqual(self.renderer.font_small.size(line)[0], 525)
        set_language("en")

    def test_title_writes_on_instead_of_appearing_as_a_floating_label(self):
        early = self.frame(.1)
        settled = self.frame(.65)
        title = pygame.Rect(255, 104, 518, 34)
        early_dark = sum(min(early.get_at((x,y))[:3]) < 120
            for x in range(title.left, title.right) for y in range(title.top, title.bottom))
        settled_dark = sum(min(settled.get_at((x,y))[:3]) < 120
            for x in range(title.left, title.right) for y in range(title.top, title.bottom))
        self.assertLess(early_dark, settled_dark*.2)

    def test_actual_boss_portraits_are_distinct_and_leave_the_fight_lane_clear(self):
        from advanced_enemies import create_enemy
        from secret_guardian import CloudKiteGuardian
        from margin_guardians import GUARDIAN_CLASSES
        kinds = ("moon_compass", "wanted_sketch", "railroad_stapler", "orbital_mistake",
                 "scissor_director", "final_editor", "baby_face_giant", "cloud_kite",
                 "brass_tumbleweed", "orbit_crab", "carbon_hound", "draft_moth")
        portraits = []
        plain = pygame.Surface((WIDTH, HEIGHT))
        plain.fill((242,235,211))
        lane = pygame.Rect(0,300,WIDTH,340)
        for kind in kinds:
            boss = (CloudKiteGuardian(800,590,13) if kind == "cloud_kite"
                    else GUARDIAN_CLASSES[kind](800,590,13) if kind in GUARDIAN_CLASSES
                    else create_enemy(kind,800,590,13))
            before = (boss.x,boss.y,boss.state,boss.state_time,boss.hp,
                      boss.facing,boss.time,boss.rng.getstate())
            frame = plain.copy()
            rect = draw_boss_entrance(frame,self.renderer,kind,kind,"READ THE RED MARK",
                                     .65,boss=boss)
            self.assertEqual(rect,pygame.Rect(230,86,660,174))
            portraits.append(self.digest(frame.subsurface((751,102,128,142))))
            self.assertEqual(self.digest(frame.subsurface(lane)),
                             self.digest(plain.subsurface(lane)))
            self.assertEqual(before,(boss.x,boss.y,boss.state,boss.state_time,boss.hp,
                                     boss.facing,boss.time,boss.rng.getstate()))
        self.assertEqual(len(set(portraits)),len(kinds))

    def test_portrait_and_all_its_text_fade_together_before_two_seconds(self):
        from advanced_enemies import create_enemy
        boss = create_enemy("final_editor",800,590,13)
        plain = pygame.Surface((WIDTH,HEIGHT))
        plain.fill((242,235,211))
        for elapsed in (0,PORTRAIT_DURATION,2.8):
            frame = plain.copy()
            self.assertIsNone(draw_boss_entrance(frame,self.renderer,boss.kind,
                "REJECTED HERO","READ THE DRAFT",elapsed,boss=boss))
            self.assertEqual(self.digest(frame),self.digest(plain))
        frame = plain.copy()
        draw_boss_entrance(frame,self.renderer,boss.kind,"REJECTED HERO",
                           "READ THE DRAFT",PORTRAIT_DURATION-.01,boss=boss)
        maximum_change = max(abs(frame.get_at((x,y))[channel]-plain.get_at((x,y))[channel])
            for x in range(230,891,2) for y in range(86,261,2) for channel in range(3))
        self.assertLess(maximum_change,10)


if __name__ == "__main__":
    unittest.main()
