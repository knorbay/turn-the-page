"""Layered pen-and-paper scenery, cached independently of combat and language.

Scenery never supplies colliders or uses the foreground ink palette. The two
parallax planes follow a climb as well as a walk, leaving the playable band
quiet enough to read a sword warning or a small bullet.
"""
from __future__ import annotations

from collections import OrderedDict
import math
import random
import pygame


PAGE_SCENES = (
    "brush mountains and shrine garden",
    "dust town and railway",
    "orbital station and planet survey",
    "carbon city and records office",
    "the surviving drafts",
)


class ScenicBackgrounds:
    TILE_WIDTH = 1440
    TILE_HEIGHT = 820
    TOP = -100
    CACHE_LIMIT = 12
    PLANES = ((.12, .18), (.39, .48))

    def __init__(self):
        self.tiles = OrderedDict()
        self.tiles_built = 0

    def clear(self):
        self.tiles.clear()

    def _tile(self, page, plane, index):
        # Three authored arrangements produce a long journey without keeping
        # every travelled screen in memory. All tiles are deterministic.
        key = (page, plane, index % 3)
        if key in self.tiles:
            self.tiles.move_to_end(key)
            return self.tiles[key]
        tile = pygame.Surface((self.TILE_WIDTH, self.TILE_HEIGHT), pygame.SRCALPHA)
        rng = random.Random(31091 + page * 997 + plane * 83 + key[2] * 173)
        draw = (self._ronin, self._western, self._orbital,
                self._carbon, self._final)[page]
        draw(tile, plane, key[2], rng)
        self.tiles[key] = tile
        self.tiles_built += 1
        while len(self.tiles) > self.CACHE_LIMIT:
            self.tiles.popitem(last=False)
        return tile

    def draw(self, surface, camera, page, time=0.0, arena=None):
        page = max(0, min(4, int(page)))
        for plane, (horizontal, vertical) in enumerate(self.PLANES):
            travel = camera.x * horizontal
            first = math.floor(travel / self.TILE_WIDTH)
            count = math.ceil(surface.get_width() / self.TILE_WIDTH) + 1
            y = self.TOP + round(getattr(camera, "offset_y", 0) * vertical)
            for index in range(first, first + count):
                x = round(index * self.TILE_WIDTH - travel
                          + getattr(camera, "offset_x", 0) * horizontal)
                surface.blit(self._tile(page, plane, index), (x, y))
        if arena is not None and getattr(arena, "boss", False):
            self.draw_boss_setting(surface, camera, page, arena)
        # Small motion belongs in the sky, outside the attack-reading band.
        if page in (0, 1, 4):
            self._drifting_scraps(surface, camera, page, time)

    @classmethod
    def _line(cls, surface, color, a, b, width=1, seed=0):
        rng = random.Random(seed)
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        points = []
        for i in range(max(2, int(length / 22)) + 1):
            t = i / max(2, int(length / 22))
            bend = math.sin(t * math.pi)
            points.append((round(a[0] + (b[0] - a[0]) * t + rng.uniform(-1, 1) * bend),
                           round(a[1] + (b[1] - a[1]) * t + rng.uniform(-1, 1) * bend)) )
        pygame.draw.lines(surface, color, False, points, width)

    @classmethod
    def _outline(cls, s, points, color, width=1, seed=0, closed=True):
        count = len(points) if closed else len(points) - 1
        for i in range(count):
            cls._line(s, color, points[i], points[(i + 1) % len(points)], width, seed + i * 17)

    @classmethod
    def _hatch(cls, s, rect, color, spacing=16):
        clip = s.get_clip()
        s.set_clip(rect)
        for x in range(rect.left - rect.height, rect.right, spacing):
            pygame.draw.line(s, color, (x, rect.bottom), (x + rect.height, rect.top), 1)
        s.set_clip(clip)

    def _ronin(self, s, plane, variant, rng):
        if plane == 0:
            sun = (1000 - variant * 185, 248)
            pygame.draw.circle(s, (163, 75, 67, 32), sun, 108)
            pygame.draw.circle(s, (153, 73, 65, 105), sun, 108, 2)
            for y in range(sun[1] - 89, sun[1] + 90, 15):
                half = round(math.sqrt(max(0, 108 ** 2 - (y - sun[1]) ** 2)))
                pygame.draw.line(s, (152, 77, 65, 30), (sun[0] - half + 10, y),
                                 (sun[0] + half - 10, y - 1), 1)
            for row, (baseline, fill, edge) in enumerate((
                    (530, (106, 124, 112, 30), (107, 120, 105, 77)),
                    (610, (102, 116, 100, 23), (107, 117, 98, 64)))):
                points = [(0, baseline)]
                for x in range(0, self.TILE_WIDTH, 288):
                    peak = baseline - rng.randrange(110, 200)
                    points.extend(((x + 95, peak + 28), (x + 137, peak),
                                   (x + 196, peak + 83), (x + 288, baseline)))
                pygame.draw.polygon(s, fill, points + [(self.TILE_WIDTH, 760), (0, 760)])
                self._outline(s, points, edge, 2, variant * 97 + row, closed=False)
                for x, y in points[1:-1:4]:
                    self._line(s, (110, 119, 100, 49), (x + 6, y + 35),
                               (x + 73, y + 138), 1, x + row)
            return
        # Bamboo is drawn as foliage, with no heavy baseline that could look
        # like a reachable platform. A shrine has a silhouette in perspective.
        for group, x in enumerate((70, 975, 1280)):
            for stalk in range(2):
                bx = x + stalk * 26
                top = 279 + rng.randrange(-38, 50)
                self._line(s, (93, 118, 81, 108), (bx, 636), (bx - 9, top), 3, bx)
                self._line(s, (167, 170, 128, 135), (bx + 2, 633), (bx - 7, top), 1, bx + 1)
                for node, y in enumerate(range(top + 32, 619, 62)):
                    pygame.draw.line(s, (103, 125, 86, 111), (bx - 9, y), (bx + 8, y), 2)
                    if node % 2:
                        continue
                    for side in (-1, 1):
                        leaf = [(bx - 2, y - 5), (bx + side * 47, y - 34),
                                (bx + side * 27, y - 5)]
                        pygame.draw.polygon(s, (110, 132, 91, 85), leaf)
        cx = 550 + variant * 43
        roof = [(cx - 177, 398), (cx - 143, 387), (cx - 84, 346),
                (cx - 27, 313), (cx + 17, 343), (cx + 143, 383),
                (cx + 184, 391), (cx + 160, 414), (cx - 164, 421)]
        pygame.draw.polygon(s, (143, 104, 86, 27), roof)
        self._outline(s, roof, (126, 90, 76, 130), 2, 702 + variant)
        self._line(s, (143, 107, 88, 106), (cx - 148, 399), (cx + 166, 394), 1, 703)
        walls = [(cx - 123, 420), (cx + 132, 417), (cx + 137, 605), (cx - 129, 612)]
        pygame.draw.polygon(s, (155, 133, 105, 18), walls)
        self._outline(s, walls, (134, 114, 91, 92), 2, 704)
        for dx in (-86, 1, 91):
            self._line(s, (132, 117, 89, 70), (cx + dx, 431), (cx + dx + 3, 598), 1, dx)
        for y in (517,):
            self._line(s, (139, 119, 95, 61), (cx - 115, y), (cx + 126, y - 4), 1, y)
        # Hanging paper lanterns only occupy the upper corners.
        for lx in (cx - 169, cx + 172):
            pygame.draw.line(s, (134, 98, 77, 93), (lx, 402), (lx, 446), 1)
            pygame.draw.ellipse(s, (169, 85, 66, 41), (lx - 13, 444, 26, 36))
            pygame.draw.ellipse(s, (143, 79, 63, 117), (lx - 13, 444, 26, 36), 1)
            for dy in (451, 459, 469):
                pygame.draw.line(s, (143, 79, 63, 72), (lx - 10, dy), (lx + 10, dy), 1)

    def _western(self, s, plane, variant, rng):
        if plane == 0:
            pygame.draw.circle(s, (191, 116, 58, 30), (1080 - variant * 200, 266), 91)
            for x in range(-50, self.TILE_WIDTH, 480):
                top = 410 + rng.randrange(-33, 45)
                mesa = [(x, 605), (x + 68, top + 57), (x + 111, top + 56),
                        (x + 135, top), (x + 298, top), (x + 327, top + 44),
                        (x + 385, top + 45), (x + 459, 605)]
                pygame.draw.polygon(s, (142, 93, 54, 28), mesa)
                self._outline(s, mesa, (135, 88, 52, 58), 2, x, closed=False)
                for cut in range(5):
                    y = top + 66 + cut * 21
                    self._line(s, (132, 91, 54, 35), (x + 89 + cut * 10, y),
                               (x + 346 + cut * 11, y - 3), 1, x + cut)
            return
        # Uneven frontier facades and a train make the western page a place,
        # while diluted window ink leaves the actual shooters easy to see.
        for building, (x, w, top) in enumerate(((120, 258, 395), (410, 298, 355), (757, 225, 416))):
            top += variant * 8 - 8
            points = [(x, 624), (x - 4, top + 22), (x + 25, top + 18),
                      (x + 25, top), (x + w - 29, top + 2), (x + w - 27, top + 18),
                      (x + w, top + 22), (x + w + 5, 624)]
            pygame.draw.polygon(s, (129, 96, 67, 19), points)
            self._outline(s, points, (131, 91, 61, 89), 2, x)
            for plank in range(top + 36, 621, 60):
                self._line(s, (144, 107, 73, 40), (x + 4, plank), (x + w - 3, plank + 1), 1, plank)
            for wx in (x + 35, x + w - 81):
                pygame.draw.rect(s, (132, 100, 64, 22), (wx, top + 53, 46, 65))
                pygame.draw.rect(s, (133, 94, 62, 94), (wx, top + 53, 46, 65), 1)
                pygame.draw.line(s, (138, 100, 69, 67), (wx + 23, top + 55), (wx + 23, top + 116), 1)
            awning = [(x - 10, top + 139), (x + w + 11, top + 139),
                      (x + w + 24, top + 157), (x - 19, top + 157)]
            pygame.draw.polygon(s, (157, 104, 74, 25), awning)
            self._outline(s, awning, (132, 92, 59, 75), 1, x + 3)
            # Blank sign: the location names remain in the translated notes.
            pygame.draw.rect(s, (129, 94, 66, 48), (x + 55, top + 30, w - 110, 11), 1)
        tx = 1038
        rail = (139, 102, 67, 60)
        pygame.draw.line(s, rail, (1020, 638), (1440, 638), 1)
        for wheel in (1062, 1115, 1238, 1310):
            pygame.draw.circle(s, (133, 93, 62, 74), (wheel, 616), 15, 2)
            pygame.draw.circle(s, (142, 106, 74, 68), (wheel, 616), 4, 1)
        body = [(tx, 599), (tx, 530), (tx + 122, 530), (tx + 122, 599)]
        pygame.draw.polygon(s, (147, 98, 65, 16), body)
        self._outline(s, body, (127, 91, 62, 93), 2, tx)
        loco = [(tx + 140, 600), (tx + 140, 507), (tx + 190, 507),
                (tx + 190, 544), (tx + 265, 544), (tx + 298, 600)]
        self._outline(s, loco, (127, 91, 62, 94), 2, tx + 1)
        pygame.draw.rect(s, (127, 91, 62, 80), (tx + 150, 518, 29, 31), 1)
        for smoke in range(3):
            pygame.draw.ellipse(s, (151, 117, 83, 43),
                                (tx + 213 + smoke * 25, 503 - smoke * 31, 33 + smoke * 10, 26 + smoke * 7), 1)

    def _orbital(self, s, plane, variant, rng):
        if plane == 0:
            cx, cy = 1050 - variant * 255, 308
            pygame.draw.circle(s, (99, 122, 152, 20), (cx, cy), 155)
            pygame.draw.circle(s, (76, 105, 139, 88), (cx, cy), 155, 2)
            pygame.draw.ellipse(s, (137, 94, 119, 96), (cx - 246, cy - 74, 492, 148), 2)
            for dy in (-81, 38):
                half = round(math.sqrt(155 ** 2 - dy ** 2))
                pygame.draw.arc(s, (95, 123, 151, 45), (cx - half, cy + dy - 12, half * 2, 24), 0, math.pi, 1)
            for _ in range(14):
                x, y = rng.randrange(self.TILE_WIDTH), rng.randrange(151, 416)
                color = (103, 128, 145, 70)
                pygame.draw.line(s, color, (x - 3, y), (x + 3, y), 1)
                pygame.draw.line(s, color, (x, y - 3), (x, y + 3), 1)
            return
        blue = (82, 110, 137, 100)
        pale = (113, 145, 161, 32)
        # A ring and connected modules read as a station, rather than five
        # unrelated satellite doodles repeated in the combat corridor.
        cx, cy = 449 + variant * 52, 453
        pygame.draw.ellipse(s, pale, (cx - 207, cy - 111, 414, 222))
        pygame.draw.ellipse(s, blue, (cx - 207, cy - 111, 414, 222), 2)
        pygame.draw.ellipse(s, (103, 131, 153, 91), (cx - 170, cy - 88, 340, 176), 1)
        for i in range(4):
            angle = i * math.tau / 4
            a = (cx + math.cos(angle) * 170, cy + math.sin(angle) * 88)
            b = (cx + math.cos(angle) * 206, cy + math.sin(angle) * 110)
            pygame.draw.line(s, (93, 123, 147, 65), a, b, 1)
        pygame.draw.rect(s, (93, 125, 145, 100), (cx - 66, cy - 39, 132, 78), 2)
        for ox in (-12,):
            pygame.draw.circle(s, (93, 125, 145, 70), (cx + ox, cy), 11, 1)
        pygame.draw.line(s, blue, (cx + 65, cy), (1038, cy), 2)
        pygame.draw.line(s, (95, 127, 146, 50), (cx + 65, cy + 5), (1038, cy + 5), 1)
        for x in (765, 993):
            module = [(x, cy - 33), (x + 18, cy - 51), (x + 112, cy - 51),
                      (x + 130, cy - 33), (x + 130, cy + 33), (x + 112, cy + 51),
                      (x + 18, cy + 51), (x, cy + 33)]
            pygame.draw.polygon(s, pale, module)
            self._outline(s, module, blue, 2, x)
            for wx in (x + 56,):
                pygame.draw.rect(s, (99, 130, 149, 78), (wx, cy - 11, 15, 22), 1)
            for side in (-1, 1):
                y = cy + side * 97
                pygame.draw.line(s, blue, (x + 65, cy + side * 51), (x + 65, y), 1)
                pygame.draw.rect(s, (103, 137, 158, 62), (x + 7, y - 15, 117, 30), 1)
                for dx in (42, 86):
                    pygame.draw.line(s, (105, 140, 159, 49), (x + dx, y - 13), (x + dx, y + 13), 1)

    def _carbon(self, s, plane, variant, rng):
        if plane == 0:
            for x in range(-28, self.TILE_WIDTH, 145):
                top = rng.randrange(334, 475)
                width = rng.randrange(98, 145)
                rect = pygame.Rect(x, top, width, 680 - top)
                pygame.draw.rect(s, (95, 114, 117, 18), rect)
                pygame.draw.rect(s, (91, 110, 116, 58), rect, 1)
                for wy in range(top + 20, 610, 86):
                    for wx in range(x + 14, x + width - 12, 58):
                        if rng.random() > .55:
                            pygame.draw.rect(s, (106, 121, 120, 35), (wx, wy, 10, 18), 1)
            return
        ink = (104, 116, 119, 98)
        ghost = (126, 138, 134, 38)
        # Offset carbon marks are part of each object, never screen jitter.
        for x in (146, 910):
            w = 250 if x != 910 else 286
            top = 303 + rng.randrange(-15, 39)
            frame = [(x, 622), (x, top), (x + w, top + 2), (x + w, 622)]
            self._outline(s, [(xx + 5, yy + 4) for xx, yy in frame], ghost, 2, x)
            self._outline(s, frame, ink, 2, x)
            for dy in (73,):
                self._line(s, ghost, (x + 5, top + dy + 4), (x + w + 5, top + dy + 4), 2, dy)
                self._line(s, ink, (x, top + dy), (x + w, top + dy), 1, dy)
            for dx in (83,):
                self._line(s, ink, (x + dx, top), (x + dx, 601), 1, dx)
            # A redacted pane retains the office motif; blank paper replaces
            # the blind grid and central facade behind moving characters.
            pygame.draw.rect(s, (151, 109, 101, 39), (x + 15, top + 87, 57, 7))
            self._line(s, (109, 118, 115, 77), (x - 15, 579), (x + w + 18, 579), 2, x + 1)
            for lx in (x + 17, x + w - 22):
                self._line(s, (109, 118, 115, 65), (lx, 581), (lx - 3, 629), 2, lx)
            pygame.draw.rect(s, (113, 127, 124, 58), (x + 106, 547, 65, 30), 1)
            self._line(s, (113, 127, 124, 61), (x + 123, 566), (x + 152, 566), 2, x + 2)
        # A wiring conduit and tied archive stack hint at the secret office.
        pygame.draw.lines(s, (125, 130, 123, 50), False,
                          [(0, 380), (84, 380), (84, 275), (1414, 275)], 1)
        for dy in range(3):
            pygame.draw.rect(s, (116, 124, 118, 59), (1278 + dy * 3, 584 - dy * 18, 111, 15), 1)
        pygame.draw.line(s, (145, 103, 94, 72), (1328, 543), (1328, 599), 2)

    def _final(self, s, plane, variant, rng):
        if plane == 0:
            # Torn page layers form a panorama of remembered shapes, drawn
            # sparsely enough that the original schoolwork still reads.
            for i, (x, w, top) in enumerate(((72, 435, 351), (572, 358, 400), (988, 352, 328))):
                top += variant * 15
                points = [(x, 684), (x - 7, top + 23), (x + 26, top),
                          (x + w - 34, top - 8), (x + w + 4, top + 31),
                          (x + w - 3, 681)]
                pygame.draw.polygon(s, (162, 152, 121, 20), points)
                self._outline(s, points, (155, 144, 115, 72), 1, x)
                for fold in range(1):
                    self._line(s, (160, 151, 125, 30), (x + 25, top + 48 + fold * 55),
                               (x + w - 22, top + 45 + fold * 55), 1, fold)
            pygame.draw.circle(s, (152, 141, 114, 78), (1180 - variant * 280, 256), 57, 2)
            for i in range(12):
                a = i * math.tau / 12
                center = (1180 - variant * 280, 256)
                pygame.draw.line(s, (152, 141, 114, 72),
                                 (center[0] + math.cos(a) * 48, center[1] + math.sin(a) * 48),
                                 (center[0] + math.cos(a) * 53, center[1] + math.sin(a) * 53), 1)
            return
        # A small memory from each earlier page shares the last sheet.
        ink = (137, 123, 98, 98)
        red = (163, 102, 87, 65)
        for x in (138, 536, 980):
            cx = x + 128
            if x == 138:
                self._outline(s, [(x, 445), (cx, 370), (x + 273, 440), (x, 445)], red, 2, x)
                for dx in (-76, 76):
                    self._line(s, ink, (cx + dx, 448), (cx + dx, 597), 2, dx)
                self._line(s, ink, (cx - 109, 474), (cx + 112, 474), 2, x + 1)
            elif x == 536:
                for dy in (549, 571):
                    self._line(s, ink, (x, dy), (x + 294, dy), 1, dy)
                for wx in range(x + 13, x + 290, 61):
                    self._line(s, (137, 123, 98, 51), (wx, 550), (wx + 6, 572), 1, wx)
                pygame.draw.rect(s, (146, 131, 105, 19), (x + 36, 463, 131, 74))
                pygame.draw.rect(s, ink, (x + 36, 463, 131, 74), 1)
                for wheel in (x + 63, x + 142):
                    pygame.draw.circle(s, ink, (wheel, 543), 13, 1)
            else:
                pygame.draw.ellipse(s, (122, 138, 145, 83), (x, 391, 280, 157), 2)
                pygame.draw.ellipse(s, (151, 104, 96, 73), (x - 14, 435, 310, 59), 1)
                pygame.draw.circle(s, (126, 143, 149, 49), (cx + 12, 470), 57, 1)
            # Real paper clips and seams tie the collage together.
            pygame.draw.arc(s, (137, 131, 115, 83), (x + 231, 323, 16, 51), -math.pi * .5, math.pi * .95, 2)
            pygame.draw.arc(s, (137, 131, 115, 83), (x + 237, 329, 10, 38), -math.pi * .5, math.pi * .93, 1)
        # A deliberate empty lower corridor provides room for the final cast.

    def _drifting_scraps(self, s, camera, page, time):
        color = ((127, 115, 89, 72), (151, 114, 77, 66), (145, 131, 104, 66))[0 if page == 0 else 1 if page == 1 else 2]
        layer = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        for i in range(4):
            x = round((i * 367 + 152 - camera.x * .22 + time * (7 + i)) % (s.get_width() + 40) - 20)
            y = round(272 + i % 3 * 23 + math.sin(time * .8 + i * 2.1) * 8
                      + getattr(camera, "offset_y", 0) * .35)
            pygame.draw.lines(layer, color, False, [(x, y), (x + 8, y - 4), (x + 14, y + 1)], 1)
        s.blit(layer, (0, 0))

    def draw_boss_setting(self, surface, camera, page, arena):
        """The architecture belongs to the room, so it cannot drift or gate play."""
        left = camera.screen_x(arena.start_x - 58)
        right = camera.screen_x(arena.end_x + 18)
        if right < -130 or left > surface.get_width() + 130:
            return
        oy = getattr(camera, "offset_y", 0)
        top, bottom = 232 + oy, 588 + oy
        colors = ((141, 94, 81), (146, 104, 68), (106, 139, 155),
                  (126, 137, 132), (148, 129, 108))
        color = colors[page]
        layer = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        span = right - left
        # The backdrop has a thin roof and two side columns. It never adds a
        # dark box over the combat lane, and scales to a wider authored room.
        for x in (left, right):
            pygame.draw.rect(layer, (*color, 36), (x - 9, top + 20, 18, bottom - top - 20))
            pygame.draw.line(layer, (*color, 117), (x - 9, top + 20), (x - 9, bottom), 2)
            pygame.draw.line(layer, (*color, 81), (x + 9, top + 20), (x + 9, bottom), 1)
        if page == 0:
            points = [(left - 41, top + 25), (left + 9, top + 8),
                      (left + span * .5, top - 36), (right - 9, top + 8), (right + 41, top + 25)]
            self._outline(layer, points, (*color, 100), 3, 681, closed=False)
            self._line(layer, (*color, 77), (left - 29, top + 32), (right + 29, top + 32), 2, 682)
        elif page == 1:
            self._line(layer, (*color, 94), (left - 22, top), (right + 22, top + 1), 3, 731)
            for x in range(left + 35, right, 125):
                pygame.draw.line(layer, (*color, 64), (x, top + 2), (x, top + 18), 1)
            for x in (left, right):
                pygame.draw.lines(layer, (*color, 84), False,
                                  [(x - 26, top - 3), (x, top - 30), (x + 26, top - 3)], 2)
        elif page == 2:
            self._outline(layer, [(left, top + 62), (left + 71, top),
                                  (right - 71, top), (right, top + 62)], (*color, 107), 2, 832, closed=False)
            self._line(layer, (*color, 62), (left + 88, top + 16), (right - 88, top + 16), 1, 833)
            for x in (left + 94, right - 94):
                pygame.draw.circle(layer, (*color, 112), (x, top + 43), 7, 1)
        elif page == 3:
            pygame.draw.line(layer, (*color, 102), (left, top), (right, top), 2)
            pygame.draw.line(layer, (*color, 43), (left + 5, top + 5), (right + 5, top + 5), 2)
            for x in (left + 45, right - 45):
                pygame.draw.rect(layer, (*color, 61), (x - 15, top + 27, 30, 74), 1)
                pygame.draw.line(layer, (164, 106, 96, 65), (x - 11, top + 44), (x + 11, top + 44), 3)
        else:
            self._line(layer, (*color, 95), (left, top + 7), (right, top - 5), 2, 932)
            for x in range(left + 65, right, 132):
                pygame.draw.lines(layer, (*color, 64), False,
                                  [(x, top + 6), (x + 8, top + 20), (x + 14, top + 5)], 1)
        surface.blit(layer, (0, 0))
