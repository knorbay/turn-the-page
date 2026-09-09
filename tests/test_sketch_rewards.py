import hashlib
import math
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame

from camera import Camera
from chapters import build_chapter
from entities import LostSketch
from notebook_notes import LESSONS, NotebookAnnotations, PLAIN_GLYPHS
from paper_renderer import PaperRenderer
from player import Player
from particles import ParticleSystem
from save_system import SaveSystem
from sketches import (SKETCHES, SKETCH_BY_ID, apply_sketch_rewards,
                      draw_sketch_icon, sketch_active)
from weapons import WeaponSystem
from world import PaperWorld


class SketchRewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_every_shipped_optional_drawing_teaches_a_distinct_technique(self):
        shipped = {}
        for page in range(5):
            for item in build_chapter(page).entities.items:
                if isinstance(item, LostSketch):
                    shipped[item.secret_id] = page
        self.assertEqual(shipped, {s.secret_id: s.page for s in SKETCHES})
        self.assertEqual(len({s.technique for s in SKETCHES}), 12)
        self.assertEqual(len({s.attribute for s in SKETCHES}), 12)

    def test_old_collection_restores_rewards_without_stacking_or_changing_health(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"save.json"
            save = SaveSystem(path)
            for secret in ("old_first_figure", "shrine_roof", "last_homework"):
                save.discover(secret)
            restored = SaveSystem(path)
            player = Player()
            player.health = 1
            health_limit = player.max_health
            for _ in range(10):
                apply_sketch_rewards(player, restored.data["secrets"])
            self.assertEqual(player.sketch_coyote_bonus, .06)
            self.assertEqual(player.sketch_air_control, 1.20)
            self.assertEqual(player.sketch_dash_recovery, .10)
            self.assertEqual(player.health, 1)
            self.assertEqual(player.max_health, health_limit)
            apply_sketch_rewards(player, ["unknown_old_catalogue_id"])
            self.assertEqual(player.sketch_coyote_bonus, 0)
            self.assertEqual(player.sketch_air_control, 1)
            self.assertEqual(player.sketch_dash_recovery, 0)

    def test_pickup_explains_reward_before_interaction_and_collects_once(self):
        collected = []
        sounds = []
        level = SimpleNamespace(interaction_hint="", toast="", toast_time=0,
            discover_secret=lambda secret, caption: collected.append(secret))
        ctx = SimpleNamespace(player=Player(238, 252), level=level,
            sounds=SimpleNamespace(play=sounds.append),
            particles=SimpleNamespace(paper_puff=lambda *args: None))
        sketch = LostSketch(250, 300, "water_tower", "an unused ticket")
        sketch.update(.016, ctx, False)
        self.assertIn("through ticket", level.interaction_hint)
        self.assertFalse(sketch.discovered)
        renderer = PaperRenderer()
        surface = pygame.Surface((1120, 700))
        surface.fill((240, 235, 215))
        sketch.draw(surface, Camera(1120), renderer)
        # The reward preview is visible above the physical collectible.
        self.assertNotEqual(surface.get_at((250, 166))[:3], (240, 235, 215))
        sketch.update(.016, ctx, True)
        sketch.update(.016, ctx, True)
        self.assertEqual(collected, ["water_tower"])
        self.assertEqual(sounds, ["pencil"])
        self.assertIn("Sidearm shots pass through one enemy", level.toast)
        self.assertGreater(sketch.acquired_time, 0)

    def test_distinct_drawing_silhouettes_and_page_aware_activation(self):
        signatures = set()
        for sketch in SKETCHES:
            surface = pygame.Surface((100, 100))
            surface.fill((240, 235, 215))
            draw_sketch_icon(surface, sketch.icon, (50,50), 64)
            signatures.add(hashlib.sha256(pygame.image.tobytes(surface,"RGB")).hexdigest())
        self.assertEqual(len(signatures), 12)
        self.assertTrue(sketch_active(SKETCH_BY_ID["shrine_roof"], ()))
        self.assertFalse(sketch_active(SKETCH_BY_ID["water_tower"], ("pencil_blade",)))
        self.assertTrue(sketch_active(SKETCH_BY_ID["water_tower"], ("ink_pistol",)))

    def test_english_class_notes_keep_all_twenty_diagrams_legible(self):
        annotations = NotebookAnnotations()
        self.assertEqual(sum(map(len,LESSONS)),20)
        for lessons in LESSONS:
            for lesson in lessons:
                self.assertFalse(set("çğıöşüÇĞİÖŞÜ").intersection(" ".join(lesson)))
                # The diagram begins around x=350. English working stays in
                # its own column, including on installed handwriting fonts.
                for value,font,x in zip(lesson[:4],
                        (annotations.heading,annotations.body,annotations.small,annotations.small),
                        (12,17,19,27)):
                    self.assertLess(x+font.size(value.translate(PLAIN_GLYPHS))[0],350,value)

    def test_movement_drawings_change_edge_jump_air_steering_and_dash_recovery(self):
        world = PaperWorld(0, False)
        particles = ParticleSystem()
        ordinary, learned = Player(200,200), Player(200,200)
        apply_sketch_rewards(learned, ("old_first_figure", "shrine_roof", "last_homework"))
        # Both figures have just walked off a ledge. Only Second Thought
        # permits the late press after the ordinary grace interval expires.
        for player in (ordinary, learned):
            player.on_ground = True
            player.update(.001, 0, world, particles)
            player.update(.13, 0, world, particles)
            player.queue_jump()
            player.update(.016, 0, world, particles)
        self.assertGreater(ordinary.vy, 0)
        self.assertLess(learned.vy, -500)
        ordinary, learned = Player(200,200), Player(200,200)
        apply_sketch_rewards(learned, ("shrine_roof", "last_homework"))
        for player in (ordinary, learned):
            player.update(.05, 1, world, particles)
        self.assertGreater(learned.vx, ordinary.vx)
        self.assertEqual(learned.vy, ordinary.vy)
        for player in (ordinary, learned):
            player.start_dash()
            player.update(.6, 0, world, particles)
        self.assertFalse(ordinary.dash_ready)
        self.assertTrue(learned.dash_ready)

    def test_nine_weapon_drawings_modify_actual_page_tools_without_damage_inflation(self):
        def system_for(page, weapon, secrets=()):
            player = Player(100,250)
            apply_sketch_rewards(player,secrets)
            system = WeaponSystem(player)
            system.configure_page(page)
            system.current_id = weapon
            return system
        def fire(page, weapon, secrets=(), combo=0):
            system = system_for(page,weapon,secrets)
            system.combo_index = combo
            system.combo_window = 1 if combo else 0
            system.current.fire(system,None)
            return system
        blade = fire(0,"pencil_blade",combo=2).melee
        longer = fire(0,"pencil_blade",("practice_monster",),combo=2).melee
        self.assertGreater(longer.hit_rect(Player(100,250)).right,
                           blade.hit_rect(Player(100,250)).right)
        self.assertEqual(longer.damage,blade.damage)
        for page,weapon,secret in ((1,"ink_pistol","beyond_red"),
                                   (2,"eraser_cannon","eraser_survivor_sketch")):
            normal,quick = system_for(page,weapon),system_for(page,weapon,(secret,))
            for system in (normal,quick):
                system.current.ammo = 0
                self.assertTrue(system.reload())
            elapsed = quick.current.reload_timer+.001
            normal.current.update(elapsed)
            quick.current.update(elapsed)
            self.assertTrue(normal.current.reloading)
            self.assertFalse(quick.current.reloading)
            self.assertEqual(quick.current.ammo,quick.current.mag_size)
        normal = fire(1,"marker_shotgun").projectiles
        tight = fire(1,"marker_shotgun",("coffee_secret",)).projectiles
        shove = fire(1,"marker_shotgun",("margin_battle_note",)).projectiles
        self.assertEqual(len(normal),len(tight))
        self.assertLess(abs(math.atan2(tight[0].vy,tight[0].vx)),
                        abs(math.atan2(normal[0].vy,normal[0].vx)))
        self.assertGreater(shove[0].knockback,normal[0].knockback)
        self.assertEqual(shove[0].damage,normal[0].damage)
        normal = fire(2,"rubber_band").projectiles[0]
        rebound = fire(2,"rubber_band",("bad_draft",)).projectiles[0]
        orbit = fire(2,"rubber_band",("orbit_observatory",)).projectiles[0]
        self.assertEqual(rebound.bounces,normal.bounces+1)
        self.assertGreater(orbit.life,normal.life)
        self.assertEqual(orbit.damage,normal.damage)
        normal = fire(3,"ink_pistol").projectiles[0]
        faster = fire(3,"ink_pistol",("agent_badge",)).projectiles[0]
        self.assertGreater(faster.vx,normal.vx)
        self.assertEqual(faster.damage,normal.damage)
        # The unused ticket changes real projectile collision: the rear
        # target is hit only when the front target can be pierced.
        class Target:
            dead=False
            def __init__(self,x,y):
                self.rect=pygame.Rect(x,y-16,18,32)
                self.hits=0
            def hit_from_weapon(self,*args):
                self.hits+=1
                return True
        for secrets,rear_hits in (((),0),(("water_tower",),1)):
            system=fire(1,"ink_pistol",secrets)
            shot=system.projectiles[0]
            front,rear=Target(shot.x+45,shot.y),Target(shot.x+100,shot.y)
            for _ in range(25):
                shot.update(.01,None,[front,rear],[],system)
            self.assertEqual(front.hits,1)
            self.assertEqual(rear.hits,rear_hits)


if __name__ == "__main__":
    unittest.main()
