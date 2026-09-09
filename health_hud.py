"""Three readable ink hearts, always present during play."""
import math
import pygame


def _heart(surface, center, size, filled, flash=0.0, fresh=0.0):
    cx, cy = center
    points = []
    for i in range(48):
        t = math.tau * i / 48
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2*t)
              - 2 * math.cos(3*t) - math.cos(4*t))
        points.append((round(cx + x*size/32), round(cy + y*size/32)))
    ink = (144, 60, 58) if filled else (160, 151, 133)
    fill = (190, 96, 83) if filled else (229, 222, 202)
    if filled and fresh > 0:
        fill = (round(190 - 37*fresh), round(96 + 31*fresh), round(83 + 12*fresh))
    pygame.draw.polygon(surface, fill, points)
    pygame.draw.lines(surface, ink, True, points, 2)
    if filled:
        # Three light pencil strokes keep filled and empty shapes distinct
        # even when the paper is viewed without colour.
        for i in range(3):
            pygame.draw.line(surface, (225, 164, 130),
                             (round(cx-7+i*4),round(cy-5)),
                             (round(cx-10+i*4),round(cy+2)), 1)
    else:
        pygame.draw.lines(surface, ink, False,
                          [(cx+1,cy-8),(cx-3,cy-2),(cx+2,cy+2),(cx-2,cy+9)],1)
        if flash > 0:
            for angle in (-2.4, -.7, 1.25):
                start=(round(cx+math.cos(angle)*19),round(cy+math.sin(angle)*19))
                end=(round(cx+math.cos(angle)*(19+8*flash)),
                     round(cy+math.sin(angle)*(19+8*flash)))
                pygame.draw.line(surface,(176,67,56),start,end,2)


def draw_health(surface, renderer, player, time):
    rect = pygame.Rect(24, 20, 216, 78)
    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    plate.fill((247, 242, 222, 239))
    surface.blit(plate, rect)
    renderer.rough_rect(surface, (156, 144, 120), rect, 1, 1903)
    fresh = min(1.0, getattr(player, "health_restore_flash", 0.0))
    health = max(0, min(player.max_health, player.health))
    label = "FRESH INK" if fresh else "VITAL INK"
    color = (89, 114, 84) if fresh else (94, 82, 69)
    surface.blit(renderer.font_small.render(label, True, color), (38, 27))
    for index in range(3):
        filled = index < health
        flash = (min(1.0, player.hurt_flash * 2.4)
                 if index == health and not filled else 0.0)
        offset = math.sin(time*36) * flash * 1.5
        _heart(surface, (round(51+index*36+offset),66), 27, filled, flash, fresh)
    count = renderer.font.render(f"{health} / 3", True, (96, 65, 55))
    surface.blit(count, count.get_rect(center=(185,65)))
    return rect
