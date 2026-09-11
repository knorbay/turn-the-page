"""Focused contracts for the three veteran regular-enemy families."""

from __future__ import annotations

import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from advanced_enemies import EmberHound, GutterLantern, RakeCactus
from behavior import BehaviorLedger
from camera import Camera
from campaign import NEW_ROOMS
from identity_content import CURATED_SPECS
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from settings import HEIGHT, WIDTH
from world import PaperWorld


class _SilentSounds:
    def __init__(self):
        self.played = []

    def play(self, name):
        self.played.append(name)


class EnemyVarietyContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT))
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_context(self, player_x=220, width=1000):
        player = Player(player_x, 542)
        player.on_ground = True
        player.invulnerable = 999
        world = PaperWorld(page=2, build_legacy=False)
        world.width = width
        world.add(0, width, 590, 18, "variety_test_floor", 881)
        level = SimpleNamespace(world=world, toast="", toast_time=0.0,
                                chapter_index=2)
        return SimpleNamespace(
            player=player,
            world=world,
            level=level,
            particles=ParticleSystem(),
            sounds=_SilentSounds(),
            camera=Camera(WIDTH),
            game=SimpleNamespace(hit_stop=0.0),
        )

    def test_gutter_lantern_freezes_a_visible_drop_column(self):
        context = self.make_context(player_x=230)
        enemy = GutterLantern(620, seed=10)
        enemy.state_time = 0

        enemy.update(.01, context, (100, 900))
        self.assertEqual(enemy.state, "drop_warn")
        locked_x = enemy.target_x

        context.player.x = 760
        for _ in range(86):
            enemy.update(.01, context, (100, 900))

        drops = [shot for shot in enemy.projectiles
                 if shot.kind == "gutter_drop"]
        self.assertEqual(len(drops), 3)
        self.assertEqual({round(shot.x - locked_x) for shot in drops},
                         {-24, 0, 24})
        self.assertGreater(abs(context.player.center_x - locked_x), 400)

    def test_rake_cactus_fires_three_sequenced_ankle_needles(self):
        context = self.make_context(player_x=230)
        enemy = RakeCactus(650, seed=11)
        enemy.state_time = 0

        enemy.update(.01, context, (100, 900))
        self.assertEqual(enemy.state, "prickle")
        for _ in range(116):
            enemy.update(.01, context, (100, 900))

        needles = [shot for shot in enemy.projectiles if shot.kind == "needle"]
        self.assertEqual(len(needles), 3)
        self.assertTrue(all(shot.y == enemy.ground_y - 14 for shot in needles))
        self.assertEqual(len({round(shot.x) for shot in needles}), 3,
                         "the warning must resolve as a rhythm, not one pellet fan")

    def test_ember_hound_dash_leaves_stationary_floor_sparks(self):
        context = self.make_context(player_x=180, width=1200)
        enemy = EmberHound(520, seed=12)
        enemy.facing = 1
        enemy._set_state("comet_dash", 1.0)

        for _ in range(20):
            enemy.update(.02, context, (100, 1100))

        embers = [shot for shot in enemy.projectiles
                  if shot.kind == "comet_ember"]
        self.assertGreaterEqual(len(embers), 4)
        self.assertTrue(all(shot.vx == shot.vy == 0 for shot in embers))
        self.assertTrue(all(shot.y == enemy.ground_y - 9 for shot in embers))

    def test_variants_have_distinct_silhouettes_and_telegraph_colors(self):
        actors = [GutterLantern(300, seed=20),
                  RakeCactus(600, seed=21),
                  EmberHound(900, seed=22)]
        states = ("drop_warn", "prickle", "tail_warn")
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for actor, state in zip(actors, states):
            actor._set_state(state, .5)
            actor.draw(surface, Camera(WIDTH), self.renderer)
            accent = tuple(actor.accent)
            rect = surface.get_bounding_rect()
            found = any(surface.get_at((x, y))[:3] == accent
                        for x in range(rect.left, rect.right)
                        for y in range(rect.top, rect.bottom))
            self.assertTrue(found, actor.kind)
        self.assertEqual(len({actor.accent for actor in actors}), 3)
        self.assertEqual(len({(actor.width, actor.height) for actor in actors}), 3)

    def test_veterans_are_sparse_and_recur_on_later_pages(self):
        curated = [spec["kind"] for specs in CURATED_SPECS.values()
                   for spec in specs]
        later = [kind for rooms in NEW_ROOMS.values() for room in rooms
                 for wave in room[3:] for kind in wave]
        for kind in ("gutter_lantern", "rake_cactus", "ember_hound"):
            self.assertEqual(curated.count(kind), 1)
            self.assertIn(kind, later)

    def test_death_reactions_repeat_each_visual_rule(self):
        ledger = BehaviorLedger()
        self.assertIn("violet", ledger.death_reaction("gutter_lantern").lower())
        self.assertIn("gold", ledger.death_reaction("rake_cactus").lower())
        self.assertIn("blue", ledger.death_reaction("ember_hound").lower())


if __name__ == "__main__":
    unittest.main()
