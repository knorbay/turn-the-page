from __future__ import annotations

import math
import random
import pygame

from settings import BLUE_RULE, HEIGHT, INK, INK_LIGHT, PAPER, PAPER_2, RED_RULE, WIDTH


def jitter_line(surface: pygame.Surface, color, start, end, width=2, seed=0, copies=2, jitter=1.2):
    """A deterministic wobbly line: stable like ink, never computer-perfect."""
    rng = random.Random(seed)
    x1, y1 = start
    x2, y2 = end
    length = max(1, math.hypot(x2 - x1, y2 - y1))
    steps = max(2, int(length / 13))
    for copy in range(copies):
        points = []
        for i in range(steps + 1):
            t = i / steps
            envelope = math.sin(t * math.pi)
            ox = rng.uniform(-jitter, jitter) * envelope
            oy = rng.uniform(-jitter, jitter) * envelope
            points.append((round(x1 + (x2 - x1) * t + ox), round(y1 + (y2 - y1) * t + oy)))
        pygame.draw.lines(surface, color, False, points, max(1, width - copy))


class PaperRenderer:
    def __init__(self):
        recipes = [
            ((242, 235, 211), "samurai_collage"),
            ((235, 215, 174), "wild_west"),
            ((218, 228, 232), "space_age"),
            ((232, 230, 218), "carbon_underpage"),
            ((249, 246, 229), "blank_sheet"),
        ]
        self.pages = [self._make_paper(base, 11 + i * 18, style)
                      for i, (base, style) in enumerate(recipes)]
        self.page_styles = [style for _, style in recipes]
        self.paper = self.pages[1]
        self.paper_two = self.pages[2]
        self.font_small = pygame.font.Font(None, 24)
        self.font = pygame.font.Font(None, 34)
        self.font_big = pygame.font.Font(None, 72)
        from notebook_notes import NotebookAnnotations
        self.notebook_notes = NotebookAnnotations()

    def _make_paper(self, base, seed, style="first_line"):
        surf = pygame.Surface((WIDTH, HEIGHT))
        surf.fill(base)
        rng = random.Random(seed)
        for _ in range(2200):
            shade = rng.choice([-7, -4, 3, 5])
            color = tuple(max(0, min(255, c + shade)) for c in base)
            surf.set_at((rng.randrange(WIDTH), rng.randrange(HEIGHT)), color)
        if style == "samurai_collage":
            # Long pale fibres belong to the sheet. World motifs are drawn in
            # camera space below so the same sun/torii is not stamped on every
            # screen of a ten-thousand-unit route.
            for _ in range(34):
                y = rng.randrange(22, HEIGHT - 18)
                x = rng.randrange(-40, WIDTH - 80)
                pygame.draw.line(surf, (219, 211, 187),
                                 (x, y), (x + rng.randrange(90, 330), y + rng.randrange(-2, 3)), 1)
        elif style == "wild_west":
            # Only the ruled ledger is baked into the sheet. The desert and
            # railroad now travel through authored world space.
            for y in range(96, HEIGHT, 48):
                pygame.draw.line(surf, (205, 181, 137), (0, y), (WIDTH, y), 1)
            pygame.draw.line(surf, (155, 78, 59), (88, 0), (88, HEIGHT), 2)
        elif style == "space_age":
            # A pale engineering sheet stays readable behind dark graphite.
            # Planets, satellites and coordinates move in the world backdrop.
            for x in range(32, WIDTH, 64):
                pygame.draw.line(surf, (197, 211, 218), (x, 0), (x, HEIGHT), 1)
            for y in range(30, HEIGHT, 64):
                pygame.draw.line(surf, (197, 211, 218), (0, y), (WIDTH, y), 1)
        elif style == "carbon_underpage":
            for y in range(70, HEIGHT, 42):
                pygame.draw.line(surf, (182, 187, 193), (0, y), (WIDTH, y), 1)
                pygame.draw.line(surf, (205, 205, 199), (4, y + 3), (WIDTH, y + 3), 1)
            for _ in range(18):
                x, y = rng.randrange(85, WIDTH), rng.randrange(35, HEIGHT - 35)
                length = rng.randrange(35, 140)
                pygame.draw.line(surf, (142, 143, 151), (x, y),
                                 (x + length, y + rng.randrange(-5, 6)), 1)
                pygame.draw.line(surf, (191, 190, 184), (x + 4, y + 4),
                                 (x + length + 4, y + rng.randrange(-1, 9)), 1)
        elif style == "blank_sheet":
            # Fibres only.  A blank page is visually louder after dense drafts.
            pygame.draw.line(surf, (224, 220, 205), (0, HEIGHT - 84),
                             (WIDTH, HEIGHT - 84), 1)
        return surf

    def background(self, surface, page=1):
        surface.blit(self.pages[max(0, min(len(self.pages) - 1, page))], (0, 0))

    @staticmethod
    def _scroll_positions(camera, spacing, factor, seed_offset=0):
        travelled = camera.x * factor
        first = math.floor(travelled / spacing) - 1
        for index in range(first, first + math.ceil(WIDTH / spacing) + 3):
            yield index, round(index * spacing - travelled + seed_offset)

    def draw_world_backdrop(self, surface, camera, page, time=0.0):
        """Draw sparse, world-moving scenery instead of a repeated wallpaper."""
        if page == 0:
            self._draw_ronin_backdrop(surface, camera)
        elif page == 1:
            self._draw_western_backdrop(surface, camera)
        elif page == 2:
            self._draw_space_backdrop(surface, camera)
        elif page == 3:
            self._draw_agent_backdrop(surface, camera, time)
        elif page == 4:
            self._draw_final_backdrop(surface, camera, time)
        self.notebook_notes.draw(surface, camera, page)

    def _draw_agent_backdrop(self, surface, camera, time):
        # Pale architecture is behind the page; solid playable tops are dark.
        for i, x in self._scroll_positions(camera, 210, .23):
            top = 230 + (i*43 % 150)
            rect = pygame.Rect(x, top, 170, 560-top)
            pygame.draw.rect(surface, (211, 213, 208), rect)
            pygame.draw.rect(surface, (160, 167, 165), rect, 1)
            for wy in range(top+18, 540, 38):
                for wx in range(x+18, x+150, 38):
                    pygame.draw.rect(surface, (181, 186, 178), (wx, wy, 17, 22), 1)
        for i, x in self._scroll_positions(camera, 1550, .8):
            pygame.draw.line(surface, (146, 150, 144), (x+160, 345), (x+160, 522), 1)
            pygame.draw.polygon(surface, (183, 187, 180),
                [(x+115, 352), (x+196, 352), (x+165, 379)])
            angle = math.sin(time*.7+i)*.3
            tip = (x+165+round(math.sin(angle)*50), 379+round(math.cos(angle)*70))
            pygame.draw.line(surface, (171, 159, 145), (x+165,379), tip, 1)
            label = self.font_small.render('CLASSIFIED / carbon copy', True, (135, 122, 118))
            surface.blit(label,(x,165))
            pygame.draw.line(surface,(174,134,128),(x,188),(x+250,188),2)

    def _draw_final_backdrop(self, surface, camera, time):
        # Half-finished schoolwork, desk rings and a clock drifting past.
        for i,x in self._scroll_positions(camera, 960, .32):
            pygame.draw.arc(surface,(207,199,177),(x+80,140,210,140),.3,4.7,2)
            pygame.draw.line(surface,(196,194,176),(x+100,295),(x+345,295),1)
            pygame.draw.line(surface,(196,194,176),(x+100,295),(x+100,190),1)
            pygame.draw.lines(surface,(174,179,167),False,
                [(x+100,295),(x+160,245),(x+220,265),(x+300,206)],1)
            text=('F = ma ... maybe','x + y = another problem','DO NOT ERASE THE HERO')[i%3]
            surface.blit(self.font_small.render(text,True,(170,167,148)),(x+78,320))
            # Three erased rubs interrupt the equation without resembling floors.
            for rub in range(3):
                pygame.draw.line(surface,(235,229,208),(x+175,324+rub*7),(x+260,327+rub*7),5)
        cx=round(850-camera.x*.065)
        pygame.draw.circle(surface,(172,166,146),(cx,114),45,2)
        for i in range(12):
            a=i*math.tau/12
            pygame.draw.line(surface,(172,166,146),
                (cx+round(math.cos(a)*36),114+round(math.sin(a)*36)),
                (cx+round(math.cos(a)*40),114+round(math.sin(a)*40)),1)
        a=time*.25
        pygame.draw.line(surface,(123,120,109),(cx,114),(cx+round(math.sin(a)*29),114-round(math.cos(a)*29)),2)
        pygame.draw.line(surface,(161,91,82),(cx,114),(cx-17,102),2)

    def _draw_ronin_backdrop(self, surface, camera):
        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        sun_x = round(865 - camera.x * .055)
        pygame.draw.circle(wash, (178, 65, 59, 38), (sun_x, 150), 104)
        pygame.draw.circle(wash, (153, 55, 52, 105), (sun_x, 150), 104, 3)
        # Two sumi-e ridges move at different speeds and leave quiet sky above.
        for layer, (factor, baseline, color) in enumerate((
                (.10, 410, (77, 83, 72, 28)),
                (.19, 465, (57, 66, 59, 43)))):
            points = [(-80, HEIGHT)]
            offset = -((camera.x * factor) % 520)
            for index in range(-1, 5):
                x = round(offset + index * 320)
                peak = baseline - (115 if (index + layer) % 3 == 0 else 62)
                points.extend([(x, baseline), (x + 125, peak), (x + 300, baseline + 8)])
            points.extend([(WIDTH + 80, HEIGHT), (-80, HEIGHT)])
            pygame.draw.polygon(wash, color, points)
            pygame.draw.lines(wash, (67, 72, 64, color[3] + 28), False, points[1:-2], 2)
        surface.blit(wash, (0, 0))

        for index, x in self._scroll_positions(camera, 780, .48, 90):
            rng = random.Random(2200 + index)
            base_y = 535
            for stalk in range(2 + abs(index) % 3):
                bx = x + stalk * 25 + rng.randrange(-8, 9)
                top = rng.randrange(170, 300)
                pygame.draw.line(surface, (75, 88, 61), (bx, base_y), (bx - 11, top), 3)
                for node_y in range(top + 40, base_y, 70):
                    pygame.draw.line(surface, (75, 88, 61),
                                     (bx - 8, node_y), (bx + 9, node_y), 2)
                    direction = -1 if (node_y // 70 + stalk) % 2 else 1
                    pygame.draw.arc(surface, (91, 100, 70),
                                    (bx - 37 if direction < 0 else bx - 1,
                                     node_y - 36, 39, 38),
                                    .15 if direction > 0 else 1.4,
                                    1.7 if direction > 0 else 3.0, 2)
        for index, x in self._scroll_positions(camera, 2460, .72, 1180):
            if -240 < x < WIDTH + 240:
                color = (112, 52, 50)
                pygame.draw.line(surface, color, (x - 105, 348), (x + 105, 348), 6)
                pygame.draw.line(surface, color, (x - 78, 349), (x - 78, 520), 5)
                pygame.draw.line(surface, color, (x + 78, 349), (x + 78, 520), 5)
                pygame.draw.line(surface, color, (x - 126, 330), (x + 126, 330), 4)

    def _draw_western_backdrop(self, surface, camera):
        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        sun_x = round(930 - (camera.x * .045) % 1750)
        pygame.draw.circle(wash, (190, 116, 54, 42), (sun_x, 178), 86)
        pygame.draw.circle(wash, (151, 81, 45, 90), (sun_x, 178), 86, 2)
        offset = -((camera.x * .13) % 760)
        for index in range(-1, 4):
            x = round(offset + index * 520)
            top = 290 + (index % 2) * 34
            mesa = [(x, 440), (x + 70, top + 32), (x + 118, top + 32),
                    (x + 145, top), (x + 315, top), (x + 352, top + 52),
                    (x + 455, 440)]
            pygame.draw.polygon(wash, (137, 96, 58, 38), mesa)
            pygame.draw.lines(wash, (119, 82, 54, 96), False, mesa, 2)
        surface.blit(wash, (0, 0))

        for index, x in self._scroll_positions(camera, 690, .56, 170):
            if index % 3 == 0:
                pygame.draw.line(surface, (88, 91, 60), (x, 365), (x, 531), 5)
                pygame.draw.arc(surface, (88, 91, 60), (x - 42, 398, 44, 68),
                                math.pi * .5, math.pi * 1.5, 4)
                pygame.draw.arc(surface, (88, 91, 60), (x, 420, 45, 70),
                                -math.pi * .5, math.pi * .5, 4)
            else:
                pygame.draw.line(surface, (105, 81, 58), (x, 405), (x, 535), 3)
                pygame.draw.line(surface, (105, 81, 58), (x - 34, 433), (x + 34, 433), 2)
                pygame.draw.line(surface, (105, 81, 58), (x - 39, 470), (x + 39, 470), 2)
        # Telegraph wire becomes railroad rhythm as the camera advances.
        poles = list(self._scroll_positions(camera, 330, .82, 50))
        for (_, x1), (_, x2) in zip(poles, poles[1:]):
            pygame.draw.line(surface, (102, 77, 56), (x1, 382), (x1, 540), 3)
            pygame.draw.line(surface, (102, 77, 56), (x1 - 18, 398), (x1 + 18, 398), 2)
            pygame.draw.arc(surface, (114, 91, 68),
                            (x1, 392, max(1, x2 - x1), 26), 0, math.pi, 1)

    def _draw_space_backdrop(self, surface, camera):
        wash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        planet_x = round(980 - (camera.x * .08) % 2300)
        planet_y = 190
        pygame.draw.circle(wash, (79, 101, 127, 22), (planet_x, planet_y), 132)
        pygame.draw.circle(wash, (72, 94, 121, 115), (planet_x, planet_y), 132, 3)
        pygame.draw.ellipse(wash, (145, 67, 69, 100),
                            (planet_x - 205, planet_y - 72, 410, 144), 2)
        surface.blit(wash, (0, 0))

        for index, x in self._scroll_positions(camera, 520, .28, 80):
            rng = random.Random(5100 + index)
            points = []
            for star in range(5):
                point = (x + star * rng.randrange(35, 61), rng.randrange(85, 315))
                points.append(point)
            pygame.draw.lines(surface, (104, 122, 142), False, points, 1)
            for star, point in enumerate(points):
                pygame.draw.circle(surface, (79, 99, 123), point, 2 + star % 2, 1)
        for index, x in self._scroll_positions(camera, 1380, .64, 540):
            y = 305 + (abs(index) % 2) * 55
            body = pygame.Rect(x - 24, y - 14, 48, 28)
            pygame.draw.rect(surface, (89, 102, 118), body, 2)
            pygame.draw.line(surface, (89, 102, 118), (x - 70, y), (x + 70, y), 2)
            for panel_x in (x - 64, x + 35):
                pygame.draw.rect(surface, (99, 124, 145), (panel_x, y - 18, 29, 36), 2)
                pygame.draw.line(surface, (99, 124, 145),
                                 (panel_x, y), (panel_x + 29, y), 1)
            label = f"SAT-{abs(index) % 97:02d}"
            self.doodle_text(surface, label, (x - 32, y + 25),
                             (104, 121, 138), self.font_small, -1)

    def doodle_text(self, surface, text, pos, color=INK, font=None, angle=0):
        img = (font or self.font).render(text, True, color)
        if angle:
            img = pygame.transform.rotate(img, angle)
        surface.blit(img, pos)

    def draw_coffee_stain(self, surface, camera, rect: pygame.Rect, time: float):
        sx = camera.screen_x(rect.x)
        if sx > WIDTH + 100 or sx + rect.w < -100:
            return
        stain = pygame.Surface((rect.w + 80, rect.h + 70), pygame.SRCALPHA)
        center = (rect.w // 2 + 40, rect.h // 2 + 35)
        rng = random.Random(77)
        points = []
        for i in range(42):
            a = math.tau * i / 42
            radius_x = rect.w * .48 + rng.uniform(-20, 18)
            radius_y = rect.h * .43 + rng.uniform(-12, 12)
            points.append((center[0] + math.cos(a) * radius_x, center[1] + math.sin(a) * radius_y))
        pygame.draw.polygon(stain, (116, 66, 31, 22), points)
        pygame.draw.lines(stain, (110, 61, 29, 92), True, points, 5)
        pygame.draw.lines(stain, (141, 86, 44, 55), True,
                          [(x + 7 * math.sin(i), y + 4 * math.cos(i * 2)) for i, (x, y) in enumerate(points)], 2)
        for _ in range(7):
            x = rng.randrange(30, rect.w + 40)
            y = rng.randrange(20, rect.h + 50)
            pygame.draw.circle(stain, (105, 59, 31, rng.randrange(18, 42)), (x, y), rng.randrange(2, 9))
        surface.blit(stain, (sx - 40, rect.y - 35 + camera.offset_y))

    def draw_material_zone(self, surface, camera, zone):
        rect = zone.rect
        sx = camera.screen_x(rect.x)
        if sx > WIDTH + 80 or sx + rect.w < -80:
            return
        if zone.kind.startswith("coffee"):
            self.draw_coffee_stain(surface, camera, rect, 0)
            if zone.kind == "coffee_sticky":
                veil = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.ellipse(veil, (84, 44, 25, 26), veil.get_rect().inflate(-20, -18))
                surface.blit(veil, (sx, rect.y + camera.offset_y))
        elif zone.kind.startswith("ink"):
            layer = pygame.Surface((rect.w + 20, rect.h + 12), pygame.SRCALPHA)
            rng = random.Random(rect.x + rect.y)
            points = [(0, rect.h)]
            x = 0
            while x <= rect.w + 20:
                points.append((x, rng.randint(8, 26)))
                x += rng.randint(18, 42)
            points.extend([(rect.w + 20, rect.h), (0, rect.h)])
            pygame.draw.polygon(layer, zone.color, points)
            for _ in range(10):
                pygame.draw.circle(layer, (23, 23, 29, 80),
                                   (rng.randrange(rect.w + 20), rng.randrange(5, max(6, rect.h))), rng.randrange(1, 5))
            surface.blit(layer, (sx - 10, rect.y + camera.offset_y))
        elif zone.kind == "margin_gravity":
            veil = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            veil.fill(zone.color)
            surface.blit(veil, (sx, rect.y + camera.offset_y))
            jitter_line(surface, (193, 85, 85), (sx + rect.w // 2, rect.y),
                        (sx + rect.w // 2, rect.bottom), 2, rect.x, 2, 1)
        elif zone.kind == "dust_updraft":
            veil = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            veil.fill(zone.color)
            surface.blit(veil, (sx, rect.y + camera.offset_y))
            rng = random.Random(rect.x + 907)
            for index in range(7):
                center_x = sx + rng.randrange(20, max(21, rect.w - 18))
                top = rect.y + rng.randrange(15, 170)
                height = rng.randrange(115, 260)
                pygame.draw.arc(surface, (157, 109, 63),
                                (center_x - 28, top, 56, height),
                                -.9, 2.15, 1 + index % 2)

    def rough_rect(self, surface, color, rect, width=2, seed=1):
        jitter_line(surface, color, rect.topleft, rect.topright, width, seed, 2, 1.2)
        jitter_line(surface, color, rect.topright, rect.bottomright, width, seed + 1, 2, 1.2)
        jitter_line(surface, color, rect.bottomright, rect.bottomleft, width, seed + 2, 2, 1.2)
        jitter_line(surface, color, rect.bottomleft, rect.topleft, width, seed + 3, 2, 1.2)

    def scribble(self, surface, center, radius=24, seed=1, turns=3, color=INK_LIGHT):
        rng = random.Random(seed)
        points = []
        for i in range(55):
            t = i / 54
            a = t * math.tau * turns
            r = radius * (.25 + .75 * t) + rng.uniform(-3, 3)
            points.append((center[0] + math.cos(a) * r, center[1] + math.sin(a) * r * .7))
        pygame.draw.lines(surface, color, False, points, 1)

    def page_turn(self, target: pygame.Surface, current: pygame.Surface, next_page: pygame.Surface, progress: float):
        """Simplified curl: the old sheet compresses, casts a shadow, and shows a folded edge."""
        target.blit(next_page, (0, 0))
        p = max(0.0, min(1.0, progress))
        edge = round(WIDTH * (1.0 - p))
        if edge > 3:
            old = current.subsurface((0, 0, edge, HEIGHT))
            target.blit(old, (0, 0))
        shadow_w = max(3, round(48 * math.sin(p * math.pi)))
        shadow = pygame.Surface((shadow_w, HEIGHT), pygame.SRCALPHA)
        for x in range(shadow_w):
            alpha = round(75 * (1 - x / shadow_w))
            pygame.draw.line(shadow, (40, 37, 32, alpha), (x, 0), (x, HEIGHT))
        target.blit(shadow, (edge, 0))
        curl_w = max(0, round(170 * math.sin(p * math.pi)))
        if curl_w:
            curl = [(edge, 0), (min(WIDTH, edge + curl_w), HEIGHT // 2), (edge, HEIGHT)]
            pygame.draw.polygon(target, (224, 219, 198), curl)
            pygame.draw.line(target, (112, 106, 94), (edge, 0), (min(WIDTH, edge + curl_w), HEIGHT // 2), 2)
            pygame.draw.line(target, (112, 106, 94), (min(WIDTH, edge + curl_w), HEIGHT // 2), (edge, HEIGHT), 2)
