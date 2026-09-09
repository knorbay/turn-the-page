"""Behavior checks for the authored polish pass."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import tempfile
import unittest
from unittest.mock import patch
import pygame
from advanced_enemies import MoonBot, InkOutlaw, CometHound
from camera import Camera
from chapters import build_chapter
from entities import LostSketch
from game import Game
from particles import Particle, ParticleSystem
from player import Player
from settings import WIDTH, HEIGHT
from staging import ROUTES

class PolishContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))
    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_all_branch_platforms_are_reachable_with_real_jump_physics(self):
        for page, start, _, secret, _, _ in ROUTES:
            runtime = build_chapter(page)
            world = runtime.world
            steps = sorted((p for p in world.platforms if p.name.startswith('vignette_')), key=lambda p:p.x1)
            player = Player(start-90, 542)
            player.on_ground = True
            particles = ParticleSystem()
            for step in steps:
                # Walk to the takeoff edge before attempting the next gap.
                launch = step.x1-65
                for _ in range(180):
                    if player.center_x >= launch:
                        break
                    player.update(1/120, 1, world, particles)
                player.queue_jump()
                landed = False
                for frame in range(180):
                    target = step.x1+75
                    axis = 1 if player.center_x < target-7 else -1 if player.center_x > target+7 else 0
                    player.update(1/120, axis, world, particles)
                    if frame > 8 and player.on_ground:
                        landed = abs(player.rect.bottom-step.y) < 3 and step.x1 < player.center_x < step.x2
                        break
                self.assertTrue(landed, (page, step.name, player.x, player.rect.bottom))
            replay = build_chapter(page, [secret])
            self.assertTrue(next(e for e in replay.entities.items if isinstance(e, LostSketch) and e.secret_id == secret).discovered)

    def test_bot_has_non_damaging_warning_before_ram(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, directory+'/save.json')
            game.player.x, game.player.y = 450, 542
            enemy = MoonBot(510)
            enemy.state_time = 0
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            enemy.update(.01, ctx, (200, 1000))
            self.assertEqual(enemy.state, 'ram_warn')
            health = game.player.health
            for _ in range(40):
                enemy.update(.01, ctx, (200, 1000))
            self.assertEqual(enemy.state, 'ram_warn')
            self.assertEqual(game.player.health, health)
            for _ in range(14):
                enemy.update(.01, ctx, (200, 1000))
            self.assertEqual(enemy.state, 'ram')

    def test_ranged_warning_locks_target_and_hound_cannot_reverse_mid_dash(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, directory+'/save.json')
            game.player.x, game.player.y = 300, 542
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            outlaw = InkOutlaw(600)
            outlaw.state_time = 0
            outlaw.update(.01, ctx, (200, 1000))
            locked = outlaw.aim_target
            game.player.x = 850
            for _ in range(85):
                outlaw.update(.01, ctx, (200, 1000))
            self.assertLess(outlaw.projectiles[0].vx, 0)
            hound = CometHound(600)
            hound.facing = -1
            hound._set_state('comet_dash', 1)
            hound.update(.01, ctx, (200, 1000))
            self.assertEqual(hound.facing, -1)
            self.assertLess(hound.vx, 0)

    def test_long_shake_never_exceeds_requested_strength(self):
        camera = Camera(WIDTH)
        camera.kick(5, 1.5)
        with patch('camera.random.uniform', side_effect=lambda a,b:b):
            camera.update(.01, 300, 2000)
        self.assertLessEqual(abs(camera.offset_x), 5)
        camera.update(2, 300, 2000)
        camera.update(.01, 300, 2000)
        self.assertEqual(camera.offset_x, 0)

    def test_dust_fades_into_paper_without_blackening(self):
        particles = ParticleSystem()
        particles.items = [Particle(50,50,0,0,.03,1,3,(180,170,150))]
        canvas = pygame.Surface((100,100)); canvas.fill((240,230,210))
        particles.draw(canvas, Camera(100))
        pixel = canvas.get_at((50,50))
        self.assertGreater(pixel.r, 225)
        self.assertGreater(pixel.g, 215)
