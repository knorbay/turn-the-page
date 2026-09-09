from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT, WIDTH


@dataclass
class InkPlatform:
    x1: float
    x2: float
    y: float
    thickness: int = 12
    name: str = "ink"
    draw_progress: float = 1.0
    erased: list[tuple[float, float]] = field(default_factory=list)
    seed: int = 1
    enabled: bool = True
    layer: int = 0
    end_y: float | None = None
    graphite: int = 38
    appearance: str = "ink_stroke"
    collidable: bool = True

    @property
    def one_way(self):
        return self.thickness <= 40

    @property
    def visible_x2(self):
        return self.x1 + (self.x2 - self.x1) * self.draw_progress

    def erase(self, start: float, end: float):
        start, end = max(self.x1, start), min(self.x2, end)
        if start < end:
            self.erased.append((start, end))
            self._merge_erased()

    def _merge_erased(self):
        merged = []
        for start, end in sorted(self.erased):
            if merged and start <= merged[-1][1] + 2:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        self.erased = merged

    def visible_intervals(self):
        if not self.enabled:
            return
        end = self.visible_x2
        cursor = self.x1
        for a, b in self.erased:
            if a > cursor:
                yield cursor, min(a, end)
            cursor = max(cursor, b)
        if cursor < end:
            yield cursor, end

    def collision_rects(self):
        rects = []
        if not self.collidable:
            return rects
        for a, b in self.visible_intervals():
            if b - a <= 2:
                continue
            if self.end_y is None or abs(self.end_y - self.y) < 1:
                rects.append(pygame.Rect(round(a), round(self.y), max(1, round(b - a)), self.thickness + 9))
                continue
            # Short overlapping steps approximate a hand-drawn ramp while keeping
            # the existing robust AABB player collision.
            cursor = a
            while cursor < b:
                right = min(b, cursor + 18)
                t = ((cursor + right) * .5 - self.x1) / max(1, self.x2 - self.x1)
                y = self.y + (self.end_y - self.y) * t
                rects.append(pygame.Rect(round(cursor), round(y), max(2, round(right - cursor) + 2), self.thickness + 10))
                cursor = right
        return rects

    def y_at(self, x):
        if self.end_y is None:
            return self.y
        t = max(0.0, min(1.0, (x - self.x1) / max(1.0, self.x2 - self.x1)))
        return self.y + (self.end_y - self.y) * t

    def draw(self, surface, camera):
        for index, (a, b) in enumerate(self.visible_intervals()):
            if b < camera.x - 30 or a > camera.x + WIDTH + 30:
                continue
            sx1, sx2 = camera.screen_x(a), camera.screen_x(b)
            y1 = round(self.y_at(a) + camera.offset_y)
            y2 = round(self.y_at(b) + camera.offset_y)
            ink = (self.graphite, self.graphite, min(55, self.graphite + 4))
            style = getattr(self, "appearance", "ink_stroke")
            if not self.collidable:
                # Pencil construction is scenery, never a dark landing edge.
                for px in range(sx1, sx2, 24):
                    pygame.draw.line(surface, (161, 159, 150),
                                     (px, y1+5), (min(px+9, sx2), y1+9), 1)
                continue
            if style == "arena_border":
                cx = round((sx1 + sx2) * .5)
                top, bottom = min(y1, y2), max(y1, y2) + self.thickness
                jitter_line(surface, (139, 54, 57), (cx, top), (cx, bottom),
                            5, self.seed + index, 3, 2.8)
                for mark_y in range(top + 10, bottom, 23):
                    pygame.draw.line(surface, (139, 54, 57),
                                     (cx - 8, mark_y + 6), (cx + 8, mark_y - 6), 2)
                continue
            if style == "ruler_line":
                jitter_line(surface, (62, 66, 72), (sx1, y1), (sx2, y2),
                            3, self.seed, 1, .45)
                for tick in range(sx1 + 18, sx2, 34):
                    height = 12 if ((tick - sx1) // 34) % 5 == 0 else 7
                    pygame.draw.line(surface, (82, 84, 87),
                                     (tick, y1), (tick, y1 + height), 1)
            elif style == "graph_axis":
                jitter_line(surface, (66, 84, 101), (sx1, y1), (sx2, y2),
                            3, self.seed, 2, .65)
                for tick in range(sx1 + 22, sx2, 42):
                    pygame.draw.line(surface, (92, 111, 126),
                                     (tick, y1 - 5), (tick, y1 + 7), 1)
                if sx2 - sx1 > 140:
                    pygame.draw.line(surface, (92, 111, 126),
                                     (sx1 + 26, y1 - 54), (sx1 + 26, y1 + 5), 2)
                    pygame.draw.polygon(surface, (92, 111, 126),
                                        [(sx1 + 26, y1 - 60), (sx1 + 22, y1 - 51),
                                         (sx1 + 30, y1 - 51)])
            elif style == "equation_box":
                jitter_line(surface, ink, (sx1, y1), (sx2, y2),
                            3, self.seed, 2, 1.0)
                pygame.draw.line(surface, INK_LIGHT, (sx1, y1), (sx1, y1 - 27), 2)
                pygame.draw.line(surface, INK_LIGHT, (sx2, y2), (sx2, y2 - 27), 2)
                if sx2 - sx1 > 120:
                    mid = (sx1 + sx2) // 2
                    pygame.draw.line(surface, INK_LIGHT,
                                     (mid - 18, y1 - 17), (mid + 18, y1 - 17), 1)
                    pygame.draw.line(surface, INK_LIGHT,
                                     (mid - 18, y1 - 11), (mid + 18, y1 - 11), 1)
            elif style == "margin_rule":
                jitter_line(surface, (164, 66, 68), (sx1, y1), (sx2, y2),
                            4, self.seed, 2, 1.2)
                for tick in range(sx1 + 15, sx2, 55):
                    pygame.draw.circle(surface, (164, 66, 68), (tick, y1), 3, 1)
            elif style == "construction":
                cursor = sx1
                while cursor < sx2:
                    end = min(sx2, cursor + 18)
                    pygame.draw.line(surface, (83, 105, 122), (cursor, y1), (end, y1), 2)
                    cursor += 28
                pygame.draw.line(surface, (171, 72, 72),
                                 (sx1 + 8, y1 - 7), (sx1 + 23, y1 + 7), 1)
            elif style == "crossed_out":
                jitter_line(surface, ink, (sx1, y1), (sx2, y2),
                            3, self.seed, 2, 1.7)
                jitter_line(surface, (148, 58, 61), (sx1, y1 + 8), (sx2, y2 - 9),
                            2, self.seed + 91, 2, 2.2)
            elif style == "torn_edge":
                rng = random.Random(self.seed + round(a))
                points = [(sx1, y1)]
                cursor = sx1
                while cursor < sx2:
                    cursor = min(sx2, cursor + rng.randint(12, 25))
                    points.append((cursor, y1 + rng.randint(-5, 6)))
                pygame.draw.lines(surface, (91, 86, 78), False, points, 3)
                pygame.draw.lines(surface, (194, 187, 169), False,
                                  [(x, y + 11) for x, y in points], 2)
            elif style in ("carbon", "ghost_line"):
                color = (112, 113, 124) if style == "carbon" else (145, 143, 137)
                for echo in range(3):
                    jitter_line(surface, color, (sx1 + echo * 3, y1 + echo * 2),
                                (sx2 + echo * 3, y2 + echo * 2), 1,
                                self.seed + echo, 1, 1.8)
            elif style == "fold_edge":
                for cursor in range(sx1, sx2, 24):
                    pygame.draw.line(surface, (111, 105, 96),
                                     (cursor, y1), (min(sx2, cursor + 13), y1), 2)
            elif style == "handwriting":
                jitter_line(surface, ink, (sx1, y1), (sx2, y2),
                            3, self.seed, 2, 1.5)
                for loop_x in range(sx1 + 25, sx2 - 15, 48):
                    pygame.draw.arc(surface, INK_LIGHT,
                                    (loop_x, y1 - 18, 30, 21), 0, math.tau, 1)
            elif style == "annotation":
                jitter_line(surface, (69, 68, 65), (sx1, y1), (sx2, y2),
                            4, self.seed, 2, 1.8)
                if sx2 - sx1 > 60:
                    pygame.draw.polygon(surface, (69, 68, 65),
                                        [(sx2, y2), (sx2 - 13, y2 - 7), (sx2 - 11, y2 + 7)])
            else:
                jitter_line(surface, ink, (sx1, y1), (sx2, y2),
                            3, self.seed + index * 13, 2, 1.7)
                jitter_line(surface, INK_LIGHT,
                            (sx1, y1 + self.thickness), (sx2, y2 + self.thickness),
                            2, self.seed + 100 + index, 1, 1.2)
            # Sparse graphite hatching binds every motif to its collision edge.
            rng = random.Random(self.seed + round(a))
            x = sx1 + rng.randint(4, 12)
            while x < sx2 - 2:
                t = (x - sx1) / max(1, sx2 - sx1)
                y = y1 + (y2 - y1) * t
                pygame.draw.line(surface, (74, 72, 69), (x, y + 3), (x + rng.randint(-2, 3), y + self.thickness - 2), 1)
                x += rng.randint(16, 29)


@dataclass
class MaterialZone:
    rect: pygame.Rect
    kind: str
    label: str = ""
    strength: float = 1.0
    color: tuple[int, int, int, int] = (80, 45, 30, 45)
    layer: int = 0


@dataclass
class PaperNote:
    x: float
    y: float
    text: str
    size: str = "small"
    color: tuple[int, int, int] = INK_LIGHT
    angle: float = 0
    crossed: bool = False
    backing: bool = False


class PaperWorld:
    def __init__(self, page: int = 1, build_legacy: bool = True):
        self.page = page
        self.width = 6700 if page == 1 else 1120
        self.platforms: list[InkPlatform] = []
        self.zones: list[MaterialZone] = []
        self.notes: list[PaperNote] = []
        self.active_layer = 0
        self.coffee_rect = pygame.Rect(4250, 390, 760, 250)
        self.artist_bridge: InkPlatform | None = None
        self.eraser_bridge: InkPlatform | None = None
        self.doodles = []
        if build_legacy:
            if page == 1:
                self._build_main()
            else:
                self._build_second()

    def add(self, x1, x2, y, thickness=12, name="ink", seed=1, layer=0, end_y=None):
        p = InkPlatform(x1, x2, y, thickness, name, 1.0, [], seed,
                        True, layer, end_y)
        self.platforms.append(p)
        return p

    def _build_main(self):
        self.add(-100, 1210, 590, 18, "start", 2)
        self.artist_bridge = self.add(1210, 1690, 590, 10, "artist_bridge", 13)
        self.artist_bridge.draw_progress = 0.0
        self.add(1690, 2150, 590, 18, "after_bridge", 3)
        self.add(1990, 2170, 500, 12, "step", 4)
        self.add(2220, 2390, 445, 12, "step", 5)
        self.add(2440, 2620, 510, 12, "step", 6)
        self.add(2630, 2940, 590, 18, "approach", 7)
        self.eraser_bridge = self.add(2940, 3690, 535, 14, "eraser_bridge", 8)
        self.add(3690, 4250, 590, 18, "landing", 9)
        self.add(4250, 5050, 590, 18, "coffee_ground", 10)
        self.add(5090, 5310, 550, 12, "coffee_step", 11)
        self.add(5360, 5590, 495, 12, "late_step", 12)
        self.add(5640, 6700, 590, 18, "ending", 14)
        self.doodles = [
            (290, 245, "a tiny life, page 7"),
            (1790, 270, "someone is still drawing...") ,
            (4050, 265, "CAREFUL"),
            (4500, 335, "coffee / Tuesday"),
            (6010, 250, "turn over ->"),
        ]

    def _build_second(self):
        self.add(-30, 1160, 590, 18, "new_page", 101)
        self.add(640, 850, 500, 12, "last_doodle", 102)
        self.doodles = [(180, 245, "Chapter two: not drawn yet."), (775, 420, "♡")]

    def collision_rects(self):
        for platform in self.platforms:
            if platform.layer != self.active_layer:
                continue
            for rect in platform.collision_rects():
                yield rect

    def collision_entries(self):
        for platform in self.platforms:
            if platform.layer == self.active_layer:
                for rect in platform.collision_rects():
                    yield rect, platform.one_way

    def in_coffee(self, rect: pygame.Rect) -> bool:
        return any(z.kind.startswith("coffee") and rect.colliderect(z.rect) for z in self.zones) or (
            self.page == 1 and rect.colliderect(self.coffee_rect)
        )

    def material_at(self, rect: pygame.Rect):
        return [z for z in self.zones if z.layer == self.active_layer and rect.colliderect(z.rect)]

    def draw(self, surface, camera, renderer, time):
        if self.page == 1 and not self.zones:
            renderer.draw_coffee_stain(surface, camera, self.coffee_rect, time)
        for zone in self.zones:
            if zone.layer == self.active_layer:
                renderer.draw_material_zone(surface, camera, zone)
        for platform in self.platforms:
            if platform.layer != self.active_layer:
                continue
            platform.draw(surface, camera)
            # A continuous dark top edge means physical support, on every page.
            if platform.collidable and platform.one_way:
                for a, b in platform.visible_intervals():
                    if b < camera.x or a > camera.x + WIDTH:
                        continue
                    a, b = max(a, camera.x-10), min(b, camera.x+WIDTH+10)
                    pygame.draw.line(surface, (48, 48, 51),
                        (camera.screen_x(a), round(platform.y_at(a)+camera.offset_y)),
                        (camera.screen_x(b), round(platform.y_at(b)+camera.offset_y)), 3)
        for i, (x, y, text) in enumerate(self.doodles):
            sx = camera.screen_x(x)
            if -350 < sx < WIDTH + 100:
                renderer.doodle_text(surface, text, (sx, y + camera.offset_y), INK_LIGHT,
                                     renderer.font_small, (-2, 1, -1, 2, 0)[i % 5])
        for i, paper_note in enumerate(self.notes):
            sx = camera.screen_x(paper_note.x)
            if -500 < sx < WIDTH + 120:
                font = renderer.font if paper_note.size == "large" else renderer.font_small
                if paper_note.backing:
                    width, height = font.size(paper_note.text)
                    sy = round(paper_note.y + camera.offset_y)
                    pygame.draw.polygon(surface, (241, 233, 207),
                        [(sx-9, sy-5), (sx+width+11, sy-3),
                         (sx+width+7, sy+height+5), (sx-7, sy+height+3)])
                renderer.doodle_text(surface, paper_note.text, (sx, paper_note.y + camera.offset_y),
                                     paper_note.color, font, paper_note.angle)
                if paper_note.crossed:
                    width = font.size(paper_note.text)[0]
                    jitter_line(surface, paper_note.color, (sx - 4, paper_note.y + 12 + camera.offset_y),
                                (sx + width + 5, paper_note.y + 8 + camera.offset_y), 2, 800 + i, 2, 1.4)
        self._draw_margin_doodles(surface, camera)

    def platform_named(self, name):
        return next((p for p in self.platforms if p.name == name), None)

    def _draw_margin_doodles(self, surface, camera):
        # A few diagram-like marks sell the notebook more than a texture alone.
        sun_x = camera.screen_x(850)
        if -80 < sun_x < WIDTH + 80:
            pygame.draw.circle(surface, (86, 83, 78), (sun_x, 178), 22, 2)
            for i in range(8):
                a = math.tau * i / 8
                pygame.draw.line(surface, (86, 83, 78),
                                 (sun_x + math.cos(a) * 29, 178 + math.sin(a) * 29),
                                 (sun_x + math.cos(a) * 39, 178 + math.sin(a) * 39), 1)
        if self.page == 2:
            sx = camera.screen_x(930)
            pygame.draw.arc(surface, INK_LIGHT, (sx - 40, 410, 80, 80), 0, math.pi, 2)
