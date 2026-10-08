"""Backgrounds follow the journey while keeping attacks readable and memory bounded."""
import hashlib
import os
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from camera import Camera
from scenic_backgrounds import ScenicBackgrounds
from settings import WIDTH, HEIGHT


class ScenicBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def frame(self, scenes, page, camera=None, time=2.0, arena=None):
        surface = pygame.Surface((WIDTH, HEIGHT))
        surface.fill((242, 235, 211))
        scenes.draw(surface, camera or Camera(WIDTH), page, time, arena)
        return surface

    def digest(self, surface):
        return hashlib.sha256(pygame.image.tobytes(surface, "RGB")).digest()

    def test_five_pages_are_distinct_without_random_flicker(self):
        scenes = ScenicBackgrounds()
        digests = []
        for page in range(5):
            first = self.frame(scenes, page)
            rebuilt = self.frame(ScenicBackgrounds(), page)
            self.assertEqual(self.digest(first), self.digest(rebuilt))
            digests.append(self.digest(first))
        self.assertEqual(len(set(digests)), 5)

    def test_steady_frame_reuses_surfaces_and_long_travel_does_not_grow_cache(self):
        scenes = ScenicBackgrounds()
        camera = Camera(WIDTH)
        self.frame(scenes, 0, camera)
        built = scenes.tiles_built
        for _ in range(10):
            self.frame(scenes, 0, camera)
        self.assertEqual(scenes.tiles_built, built)
        for page in range(5):
            for x in range(0, 26000, 2700):
                camera.x = x
                self.frame(scenes, page, camera)
                self.assertLessEqual(len(scenes.tiles), scenes.CACHE_LIMIT)
        self.assertLessEqual(sum(tile.get_width() * tile.get_height() * tile.get_bytesize()
                                 for tile in scenes.tiles.values()), 57_000_000)

    def test_scenery_tracks_camera_horizontally_and_during_cloud_climb(self):
        for page in range(5):
            scenes = ScenicBackgrounds()
            camera = Camera(WIDTH)
            floor = self.digest(self.frame(scenes, page, camera))
            camera.x = 980
            walk = self.digest(self.frame(scenes, page, camera))
            camera.offset_y = 330
            climb = self.digest(self.frame(scenes, page, camera))
            self.assertNotEqual(floor, walk)
            self.assertNotEqual(walk, climb)

    def test_scenery_leaves_dark_ink_to_foreground_attacks(self):
        scenes = ScenicBackgrounds()
        for page in range(5):
            for x in (0, 1900, 6800, 12200):
                camera = Camera(WIDTH)
                camera.x = x
                surface = self.frame(scenes, page, camera)
                # Sample the actual ground combat lane, including scenery
                # edges. A dark projectile (roughly40) keeps ample contrast.
                darkest = min(min(surface.get_at((sx, y))[:3])
                              for sx in range(0, WIDTH, 5)
                              for y in range(420, 592, 3))
                self.assertGreater(darkest, 125, (page, x, darkest))

    def test_boss_columns_use_room_bounds_and_vertical_camera(self):
        scenes = ScenicBackgrounds()
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        camera = Camera(WIDTH)
        camera.x = 2250
        camera.offset_y = 60
        arena = SimpleNamespace(start_x=2500, end_x=4950, boss=True)
        scenes.draw_boss_setting(surface, camera, 2, arena)
        expected_left = camera.screen_x(arena.start_x - 58)
        self.assertGreater(surface.get_at((expected_left - 9, 400 + camera.offset_y)).a, 0)
        self.assertEqual(surface.get_at((expected_left + 45, 530 + camera.offset_y)).a, 0)
        self.assertEqual(surface.get_at((1000, 580 + camera.offset_y)).a, 0)

    def test_boss_frame_does_not_replace_the_boss_with_an_opaque_card(self):
        scenes = ScenicBackgrounds()
        camera = Camera(WIDTH)
        arena = SimpleNamespace(start_x=100, end_x=850, boss=True)
        frames = []
        for page in range(5):
            plain = self.frame(scenes, page, camera)
            framed = self.frame(scenes, page, camera, arena=arena)
            self.assertNotEqual(self.digest(plain), self.digest(framed))
            for point in ((400, 455), (600, 535), (350, 588)):
                self.assertEqual(plain.get_at(point), framed.get_at(point))
            frames.append(self.digest(framed))
        self.assertEqual(len(set(frames)), 5)


if __name__ == "__main__":
    unittest.main()
