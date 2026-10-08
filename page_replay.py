"""Completed notebooks retain a direct route to each page and the afterword."""
import pygame
from sketches import PAGE_NAMES, draw_sketch_icon
from settings import WIDTH, INK, INK_LIGHT


def replay_rects():
    return tuple(pygame.Rect(150 + (i % 2)*420, 205 + (i // 2)*126, 400, 106)
                 for i in range(6))


def draw_replay_pages(surface, renderer, selected, controller=False):
    renderer.background(surface, 5)
    renderer.doodle_text(surface, 'REPLAY PAGES', (150, 90), INK, renderer.font_big)
    renderer.doodle_text(surface, 'Your learned sketches stay with you.',
                         (155, 156), INK_LIGHT, renderer.font_small)
    icons = ('kite', 'spur', 'moon', 'badge', 'homework', 'figure')
    labels = PAGE_NAMES + ('AFTERWORD',)
    for i, (rect, label) in enumerate(zip(replay_rects(), labels)):
        color = (150, 63, 56) if i == selected else INK_LIGHT
        renderer.rough_rect(surface, color, rect, 3 if i == selected else 1, 41100+i)
        draw_sketch_icon(surface, icons[i], (rect.x+53, rect.centery), 52, accent=color)
        image = renderer.font.render(label, True, color)
        if image.get_width() > rect.width-105:
            image = pygame.transform.smoothscale(image, (rect.width-105, image.get_height()))
        surface.blit(image, image.get_rect(midleft=(rect.x+94, rect.centery)))
    footer = renderer.font_small.render('PAD-A: choose' if controller
                                       else 'Enter / click: choose', True, INK_LIGHT)
    surface.blit(footer, footer.get_rect(center=(WIDTH//2, 636)))
