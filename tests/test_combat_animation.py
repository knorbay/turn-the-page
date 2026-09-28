"""Graphite combat animation keeps the paper readable and effects bounded."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from camera import Camera
from particles import ParticleSystem


class CombatAnimationTests(unittest.TestCase):
    def test_enemy_death_leaves_bounded_temporary_rejected_drawing(self):
        particles = ParticleSystem()
        particles.enemy_break(110, 80, 1, 30)
        self.assertEqual(len(particles.death_marks), 1)
        surface = pygame.Surface((240, 160))
        paper = (243, 237, 215)
        surface.fill(paper)
        particles.draw(surface, Camera(240))
        self.assertNotEqual(surface.get_at((110, 80))[:3], paper)
        self.assertEqual(surface.get_at((10, 10))[:3], paper)

        for index in range(40):
            particles.enemy_break(110 + index, 80, -1, 6)
        self.assertLessEqual(len(particles.death_marks), 16)
        particles.update(6)
        self.assertEqual(particles.death_marks, [])


if __name__ == "__main__":
    unittest.main()
