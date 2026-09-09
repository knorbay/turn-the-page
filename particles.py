from __future__ import annotations

from dataclasses import dataclass
import math
import random
import pygame


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple[int, int, int]
    gravity: float = 0.0
    kind: str = "dot"


class ParticleSystem:
    def __init__(self):
        self.items: list[Particle] = []
        self.layer = None

    def pencil_speck(self, x: float, y: float) -> None:
        self.items.append(Particle(x, y, random.uniform(-22, 10), random.uniform(-26, 5),
                                   .38, .38, random.uniform(1, 2.4), (48, 46, 44), 70))

    def eraser_dust(self, x: float, y: float, amount: int = 5) -> None:
        colors = [(210, 169, 151), (231, 204, 188), (105, 100, 94)]
        for _ in range(amount):
            self.items.append(Particle(x + random.uniform(-12, 12), y + random.uniform(-5, 7),
                                       random.uniform(-70, 70), random.uniform(-95, -18),
                                       random.uniform(.45, .9), .9, random.uniform(2, 5),
                                       random.choice(colors), 180, "crumb"))

    def paper_puff(self, x: float, y: float, amount: int = 8) -> None:
        for _ in range(amount):
            angle = random.uniform(math.pi, math.tau)
            speed = random.uniform(25, 90)
            self.items.append(Particle(x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                                       random.uniform(.25, .55), .55, random.uniform(1, 3),
                                       (187, 180, 161), 150, "paper"))

    def combat_hit(self, x: float, y: float, direction: float = 1,
                   heavy: bool = False, amount: int | None = None) -> None:
        """Directional graphite splinters make a landed hit readable.

        Paper/eraser particles already communicate the material of the world,
        but they expand evenly and therefore do not show the force of an
        attack.  These short streaks travel away from the weapon and give
        melee, bullets, and finishers one shared impact language.
        """
        direction = 1 if direction >= 0 else -1
        count = amount if amount is not None else (12 if heavy else 7)
        for _ in range(max(1, int(count))):
            speed = random.uniform(115, 285 if heavy else 215)
            self.items.append(Particle(
                x + random.uniform(-4, 4),
                y + random.uniform(-9, 9),
                direction * speed * random.uniform(.45, 1.0),
                random.uniform(-175, 105),
                random.uniform(.12, .27 if heavy else .22),
                .27 if heavy else .22,
                random.uniform(2.2, 4.8 if heavy else 3.6),
                random.choice(((43, 42, 45), (91, 84, 79), (151, 63, 60))),
                320,
                "slash",
            ))

    def enemy_break(self, x: float, y: float, direction: float = 1,
                    amount: int = 18) -> None:
        """A compact mixture of torn paper and ink for enemy deaths."""
        direction = 1 if direction >= 0 else -1
        for index in range(max(1, int(amount))):
            angle = random.uniform(math.pi * 1.08, math.pi * 1.92)
            speed = random.uniform(70, 240)
            kind = "paper" if index % 3 else "slash"
            color = (184, 176, 157) if kind == "paper" else (51, 49, 53)
            self.items.append(Particle(
                x + random.uniform(-10, 10),
                y + random.uniform(-12, 10),
                math.cos(angle) * speed + direction * random.uniform(25, 95),
                math.sin(angle) * speed,
                random.uniform(.28, .62),
                .62,
                random.uniform(2.0, 5.0),
                color,
                390,
                kind,
            ))

    def update(self, dt: float) -> None:
        alive = []
        for p in self.items:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vy += p.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            alive.append(p)
        self.items = alive[-420:]

    def draw(self, surface: pygame.Surface, camera) -> None:
        if not self.items:
            return
        if self.layer is None or self.layer.get_size() != surface.get_size():
            self.layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self.layer.fill((0, 0, 0, 0))
        target = surface
        surface = self.layer
        for p in self.items:
            alpha = min(1.0, p.life / max(.001, p.max_life))
            # Preserve the material hue and fade the opacity into the page.
            # Multiplying RGB made old dust turn black before disappearing.
            color = (*p.color, round(255 * min(1, alpha * 2.5)))
            x, y = camera.screen_x(p.x), round(p.y + camera.offset_y)
            size = max(1, round(p.size * (.6 + .4 * alpha)))
            if p.kind == "return_ring":
                radius = round(10+(1-alpha)*25)
                pygame.draw.circle(surface, color, (x, y), radius, 2)
                pygame.draw.lines(surface, color, False,
                    [(x-8, y), (x-1, y+7), (x+12, y-9)], 3)
            elif p.kind == "crumb":
                pygame.draw.rect(surface, color, (x, y, size + 2, size), border_radius=1)
            elif p.kind == "paper":
                pygame.draw.line(surface, color, (x - size, y), (x + size, y + 1), 1)
            elif p.kind == "slash":
                speed = math.hypot(p.vx, p.vy)
                if speed <= .001:
                    pygame.draw.circle(surface, color, (x, y), size)
                else:
                    length = max(3, round(size * 2.2))
                    dx = round(p.vx / speed * length)
                    dy = round(p.vy / speed * length)
                    pygame.draw.line(surface, color, (x, y), (x - dx, y - dy),
                                     2 if size >= 4 else 1)
            else:
                pygame.draw.circle(surface, color, (x, y), size)
        target.blit(surface, (0, 0))
