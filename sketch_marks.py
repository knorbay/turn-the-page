"""A tiny, deterministic mark vocabulary for intentionally handmade sprites.

The helpers avoid generated raster art and avoid the opposite failure too:
perfect vector primitives.  Every actor chooses only a few marks, materials,
and construction mistakes so the drawing stays readable at gameplay scale.
"""
from __future__ import annotations

import math
import random

import pygame


def rough_circle(surface, color, center, radius, seed, width=2,
                 copies=2, squash=(1.0, 1.0), wobble=1.6):
    rng = random.Random(seed)
    for copy in range(copies):
        points = []
        for index in range(25):
            angle = math.tau * index / 24
            r = radius + rng.uniform(-wobble, wobble)
            points.append((
                round(center[0] + math.cos(angle) * r * squash[0]),
                round(center[1] + math.sin(angle) * r * squash[1]),
            ))
        pygame.draw.lines(surface, color, True, points, max(1, width - copy))


def wax_disc(surface, center, radius, seed, colors):
    """Several imperfect pressure rings, like a child coloring too hard."""
    rng = random.Random(seed)
    for inset in range(0, max(4, radius - 2), 3):
        ring = max(2, radius - inset)
        color = colors[(inset // 3) % len(colors)]
        offset = (rng.randrange(-1, 2), rng.randrange(-1, 2))
        rough_circle(surface, color,
                     (center[0] + offset[0], center[1] + offset[1]),
                     ring, seed + inset * 13, 2, 1, wobble=2.2)


def hatch(surface, color, rect, seed, spacing=8, slant=5, width=1):
    rng = random.Random(seed)
    for x in range(rect.left - rect.h, rect.right + rect.h, spacing):
        y1 = rect.top + rng.randrange(-2, 3)
        y2 = rect.bottom + rng.randrange(-2, 3)
        pygame.draw.line(surface, color,
                         (x, y1), (x + rect.h + slant, y2), width)


def correction_cross(surface, center, size, seed, color=(165, 65, 67), width=2):
    rng = random.Random(seed)
    dx = rng.randrange(-2, 3)
    dy = rng.randrange(-2, 3)
    pygame.draw.line(surface, color,
                     (center[0] - size + dx, center[1] - size + dy),
                     (center[0] + size, center[1] + size), width)
    pygame.draw.line(surface, color,
                     (center[0] + size + dx, center[1] - size),
                     (center[0] - size, center[1] + size + dy), width)


def pivot(surface, center, radius, seed, color, paper):
    rough_circle(surface, color, center, radius, seed, 2, 2, wobble=1.0)
    pygame.draw.circle(surface, paper, center, max(1, radius - 3))
    pygame.draw.circle(surface, color, center, 2)


def staples(surface, points, color=(82, 79, 75)):
    for x, y in points:
        pygame.draw.lines(surface, color, False,
                          [(x - 4, y + 2), (x - 4, y - 2),
                           (x + 4, y - 2), (x + 4, y + 2)], 1)


def torn_wing(surface, points, color, paper, seed):
    rng = random.Random(seed)
    torn = []
    for index, point in enumerate(points):
        torn.append((point[0] + rng.randrange(-2, 3),
                     point[1] + rng.randrange(-2, 3)))
        if index < len(points) - 1:
            next_point = points[index + 1]
            torn.append(((point[0] + next_point[0]) // 2 + rng.randrange(-3, 4),
                         (point[1] + next_point[1]) // 2 + rng.randrange(-3, 4)))
    pygame.draw.polygon(surface, paper, torn)
    pygame.draw.lines(surface, color, True, torn, 2)
    return torn
