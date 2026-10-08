"""Cloth must cover the torso when the head leans away from its centre."""
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import unittest
import pygame
from player import Player


class CostumeAttachmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_head_lean_does_not_move_cloth_off_the_torso(self):
        player = Player(0, 0)
        player.draw_amount = 1
        for style in ('ronin', 'cowboy', 'astronaut', 'ink_agent'):
            for facing in (-1, 1):
                with self.subTest(style=style, facing=facing):
                    player.page_style = style
                    player.facing = facing
                    layer = pygame.Surface((230, 130), pygame.SRCALPHA)
                    player._draw_page_costume(layer, 155, 25, 48, 85, (45, 43, 40), 95, 80)
                    # Ronin's open coat leaves its centre deliberately bare.
                    cloth_x = 78 if style == 'ronin' else 86
                    self.assertGreater(layer.get_at((cloth_x, 70)).a, 0)
                    self.assertEqual(layer.get_at((155, 70)).a, 0)

    def test_cloth_remains_absent_before_the_redraw_reaches_the_body(self):
        player = Player(0, 0)
        player.page_style = 'ink_agent'
        player.draw_amount = .7
        layer = pygame.Surface((230, 130), pygame.SRCALPHA)
        player._draw_page_costume(layer, 155, 25, 48, 85, (45, 43, 40), 95, 80)
        self.assertEqual(pygame.mask.from_surface(layer).count(), 0)


if __name__ == '__main__':
    unittest.main()
