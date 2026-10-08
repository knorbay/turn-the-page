"""A tap keeps its shorter arc when press/release share a simulation frame."""
import os
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from particles import ParticleSystem
from player import Player
from world import PaperWorld


class BufferedJumpContracts(unittest.TestCase):
    def setUp(self):
        self.world = PaperWorld(page=0, build_legacy=False)
        self.world.add(0, 1000, 590, 18, "jump_floor", 1404)
        self.particles = ParticleSystem()

    def apex(self, player):
        highest = player.y
        for _ in range(180):
            player.update(1 / 120, 0, self.world, self.particles)
            highest = min(highest, player.y)
            if player.on_ground and player.jump_buffer == 0:
                break
        return highest

    def test_fast_tap_is_shorter_than_a_held_jump(self):
        held, tapped = Player(100, 542), Player(100, 542)
        for player in (held, tapped):
            player.on_ground = True
            player.queue_jump()
        tapped.release_jump()
        held_apex, tapped_apex = self.apex(held), self.apex(tapped)
        self.assertLess(held_apex, tapped_apex - 60)
        self.assertLess(tapped_apex, 542 - 12, "a tap must still leave the floor")

    def test_release_before_landing_stays_attached_to_buffered_jump(self):
        held, tapped = Player(100, 535), Player(100, 535)
        for player in (held, tapped):
            player.vy = 180
            player.queue_jump()
        tapped.release_jump()
        held_apex, tapped_apex = self.apex(held), self.apex(tapped)
        self.assertLess(held_apex, tapped_apex - 60)
        self.assertLess(tapped_apex, 520)

    def test_fresh_press_after_expired_tap_restores_the_full_arc(self):
        held, expired = Player(100, 542), Player(100, 400)
        expired.queue_jump()
        expired.release_jump()
        for _ in range(20):
            expired.update(1 / 120, 0, self.world, self.particles)
        self.assertEqual(expired.jump_buffer, 0)
        expired.y, expired.vy = 542, 0
        for player in (held, expired):
            player.on_ground = True
            player.queue_jump()
        self.assertAlmostEqual(self.apex(held), self.apex(expired))


if __name__ == "__main__":
    unittest.main()
