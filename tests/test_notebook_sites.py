"""Keep the authored sketches visible, local, and safe on the paper canvas."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import unittest
import pygame

from identity_content import PAGE_ROUTE_ENDS
from notebook_sites import SITES, draw_notebook_sites
from paper_renderer import PaperRenderer
from settings import WIDTH, HEIGHT


class CameraStub:
    def __init__(self, x):
        self.x = x

    def screen_x(self, world_x):
        return round(world_x - self.x)


class NotebookSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((WIDTH, HEIGHT))
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_each_page_has_reachable_distinct_landmarks(self):
        for page, sites in SITES.items():
            self.assertGreaterEqual(len(sites), 5)
            self.assertEqual([x for x, _, _ in sites],
                             sorted(x for x, _, _ in sites))
            self.assertEqual(len({kind for _, kind, _ in sites}), len(sites))
            self.assertTrue(all(0 < x < PAGE_ROUTE_ENDS[page]
                                for x, _, _ in sites))

    def test_every_landmark_renders_without_covering_canvas(self):
        for page, sites in SITES.items():
            for world_x, kind, _ in sites:
                surface = pygame.Surface((WIDTH, HEIGHT))
                self.renderer.background(surface, page)
                before = pygame.image.tobytes(surface, "RGB")
                draw_notebook_sites(surface, CameraStub(world_x - WIDTH // 2),
                                    page, 1.7, self.renderer)
                self.assertNotEqual(pygame.image.tobytes(surface, "RGB"), before,
                                    (page, kind))
                self.assertGreater(surface.get_at((WIDTH - 12, 92)).r, 100,
                                   (page, kind))

    def test_animated_scientific_doodle_changes_at_same_world_location(self):
        frames = []
        for time in (0.0, 1.8):
            surface = pygame.Surface((WIDTH, HEIGHT))
            self.renderer.background(surface, 2)
            draw_notebook_sites(surface, CameraStub(400), 2, time, self.renderer)
            frames.append(pygame.image.tobytes(surface, "RGB"))
        self.assertNotEqual(*frames)

    def test_interaction_heavy_openings_keep_large_sites_offscreen(self):
        for page in (0, 3, 4):
            surface = pygame.Surface((WIDTH, HEIGHT))
            self.renderer.background(surface, page)
            before = pygame.image.tobytes(surface, "RGB")
            draw_notebook_sites(surface, CameraStub(0), page, 1.0, self.renderer)
            self.assertEqual(pygame.image.tobytes(surface, "RGB"), before)


if __name__ == "__main__":
    unittest.main()
