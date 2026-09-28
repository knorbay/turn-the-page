"""Large, page-local notebook drawings anchored to distinct route locations.

The old backgrounds stay intact. These sketches give the stretches between
arenas recognisable landmarks and a little motion without becoming platforms.
"""
from __future__ import annotations

import math
import pygame

from paper_renderer import jitter_line
from sketch_marks import rough_circle


SITES = {
    0: ((2560, "bridge_plan", "BRIDGE / TRY 2"),
        (5630, "sword_study", "THE BLADE REMEMBERS"),
        (6500, "ink_tree", "A TREE I COULD NOT ERASE"),
        (7850, "lantern_rack", "FESTIVAL AFTER CLASS"),
        (9220, "duel_scroll", "THE ARC IS NOT A WALL")),
    1: ((960, "departures", "MISSED THE FIRST TRAIN"),
        (3320, "saloon", "CLOSED FOR HOMEWORK"),
        (4570, "tumble_barn", "THE WIND GOT BORED"),
        (7450, "water_tower", "WATER? / COFFEE"),
        (10650, "station", "LAST TRAIN / 23:07")),
    2: ((980, "gravity_machine", "GRAVITY / PLEASE WORK"),
        (3500, "rocket", "LAUNCH ATTEMPT 04"),
        (6120, "satellite_wreck", "SOME ASSEMBLY REQUIRED"),
        (9250, "dish", "SIGNAL LOST"),
        (13050, "moon_lab", "NOT TO SCALE"),
        (16000, "return_capsule", "RETURN TO SENDER")),
    3: ((2450, "dossier", "YOU ARE FILE 00"),
        (4600, "cabinet", "FILE 03 / ORIGINAL?"),
        (6550, "carbon_press", "THE SECOND COPY MOVES"),
        (8600, "antenna", "BLIND SPOT"),
        (10820, "vault", "EVIDENCE / DO NOT ERASE"),
        (11650, "pinboard", "NO ONE DREW THIS THREAD")),
    4: ((2410, "classroom", "ONE LAST LESSON"),
        (4400, "exam", "ANSWERS IN THE MARGIN"),
        (6400, "memory_window", "THE OTHER FOUR PAGES"),
        (8500, "crossouts", "THE OLD VERSIONS"),
        (10750, "answer_scraps", "KEEP THE WRONG ANSWER"),
        (11600, "hand", "YOUR NEXT LINE")),
}


def draw_notebook_sites(surface, camera, page, time, renderer):
    """Draw light graphite scenery behind entities, moving with the paper."""
    for world_x, kind, title in SITES.get(page, ()):
        x = camera.screen_x(world_x)
        if x < -270 or x > surface.get_width() + 270:
            continue
        ink = ((91, 83, 73), (112, 82, 60), (75, 100, 117),
               (90, 95, 91), (105, 99, 87))[page]
        pale = ((214, 199, 169), (211, 185, 149), (190, 205, 211),
                (199, 204, 198), (219, 211, 192))[page]
        red = (163, 78, 70)
        seed = int(world_x)

        def line(a, b, width=2, color=None, offset=0):
            jitter_line(surface, color or ink, a, b, width, seed + offset, 2, 1.8)

        def outline(points, color=None, width=2):
            for i, point in enumerate(points):
                line(point, points[(i + 1) % len(points)], width, color, i * 17)

        y = 483
        if kind == "sword_study":
            # An old practice sheet and its ghosted motion arc, rather than a
            # second decorative torii. The paper slips move, the blade does not.
            sheet = [(x - 116, y - 177), (x + 92, y - 184),
                     (x + 108, y - 14), (x - 111, y - 20)]
            pygame.draw.polygon(surface, pale, sheet)
            outline(sheet)
            for dy in (-149, -107, -65):
                line((x - 92, y + dy), (x + 79, y + dy - 4), 1, offset=dy)
            pygame.draw.arc(surface, red, (x - 128, y - 195, 246, 177),
                            math.pi * .18, math.pi * .77, 2)
            line((x - 88, y - 32), (x + 76, y - 157), 4, offset=9)
            line((x - 84, y - 28), (x + 79, y - 154), 1, pale, 10)
            line((x - 94, y - 27), (x - 111, y - 10), 3, red, 11)
            line((x - 108, y - 10), (x - 68, y - 40), 2, red, 12)
            for i in range(3):
                flutter = math.sin(time * 2 + i * 1.7) * 3
                outline([(x + 125 + i * 19, y - 168 + i * 23),
                         (x + 143 + i * 19, y - 157 + i * 23 + flutter),
                         (x + 127 + i * 19, y - 147 + i * 23 + flutter)], pale, 1)
        elif kind == "bridge_plan":
            # A crossed-out suspension idea, with its usable lower line nearby.
            for side in (-1, 1):
                line((x + side * 115, y - 12), (x + side * 115, y - 122), 3, offset=side)
            pygame.draw.arc(surface, ink, (x - 116, y - 170, 232, 170), 0, math.pi, 2)
            for dx in range(-96, 112, 32):
                line((x + dx, y - 85), (x + dx, y - 17), 1, pale, dx)
            line((x - 135, y - 13), (x + 135, y - 13), 2)
            line((x - 76, y - 147), (x + 69, y - 36), 2, red)
            line((x - 77, y - 34), (x + 75, y - 150), 2, red)
        elif kind == "lantern_rack":
            line((x - 122, y - 129), (x + 121, y - 129), 3)
            for dx in (-87, -29, 37, 94):
                swing = math.sin(time * 1.7 + dx) * 3
                line((x + dx, y - 129), (x + dx + swing, y - 98), 1)
                points = [(x + dx - 16 + swing, y - 97),
                          (x + dx + 17 + swing, y - 97),
                          (x + dx + 13 + swing, y - 62),
                          (x + dx - 12 + swing, y - 62)]
                pygame.draw.polygon(surface, pale, points)
                outline(points)
                rough_circle(surface, red, (x + dx + swing, y - 78), 4, seed + dx, 1)
        elif kind == "duel_scroll":
            rect = pygame.Rect(x - 111, y - 189, 222, 172)
            pygame.draw.rect(surface, pale, rect)
            renderer.rough_rect(surface, ink, rect, 2, seed)
            for dx in (-112, 112):
                rough_circle(surface, ink, (x + dx, y - 103), 12, seed + dx, 2)
            pygame.draw.arc(surface, red, (x - 71, y - 149, 142, 117),
                            math.pi * .08, math.pi * .89, 3)
            line((x - 65, y - 30), (x + 63, y - 30), 2)
            line((x - 65, y - 30), (x - 43, y - 55), 2, red)
        elif kind == "ink_tree":
            # The trunk is assembled from corrections; falling leaves drift
            # by a few pixels, leaving the platform outlines unambiguous.
            for shift in (12, 3, -5):
                line((x - 9 + shift, y - 7), (x - 10 + shift, y - 164),
                     2, pale if shift == 12 else ink, shift)
            branches = ((-112, -127), (-82, -179), (-31, -202),
                        (48, -191), (94, -141), (125, -99))
            for i, (dx, dy) in enumerate(branches):
                line((x, y - 105 + i % 3 * 13), (x + dx, y + dy), 2, offset=i)
                rough_circle(surface, ink, (x + dx, y + dy), 26 + i % 3 * 5,
                             seed + i, 1, squash=(1.5, .64))
            for i, (dx, dy) in enumerate(((-119, -74), (75, -37), (143, -130))):
                drift = math.sin(time * 1.3 + i * 2) * 6
                outline([(x + dx + drift, y + dy),
                         (x + dx + 11 + drift, y + dy + 3),
                         (x + dx + 3 + drift, y + dy + 12)], red, 1)
            line((x - 82, y - 4), (x + 76, y - 4), 1, pale)
        elif kind == "departures":
            board = [(x - 139, y - 190), (x + 142, y - 183),
                     (x + 135, y - 18), (x - 133, y - 24)]
            pygame.draw.polygon(surface, pale, board)
            outline(board)
            line((x - 122, y - 143), (x + 126, y - 140), 2, red)
            renderer.notebook.hand(surface, "TRAIN / PAGE", (x - 113, y - 177), ink, True, seed)
            for i, label in enumerate(("01    23:07", "02    ?? : ??", "03    ERASED")):
                yy = y - 127 + i * 37
                renderer.notebook.hand(surface, label, (x - 112, yy), ink, True, seed + i)
                line((x - 117, yy + 26), (x + 115, yy + 26), 1, pale, i)
            line((x + 26, y - 66), (x + 108, y - 59), 2, red)
            for dx in (-104, 104):
                line((x + dx, y - 16), (x + dx - 8, y + 17), 2)
        elif kind == "tumble_barn":
            roof = [(x - 133, y - 135), (x - 7, y - 198),
                    (x + 134, y - 127), (x + 130, y - 11),
                    (x - 125, y - 11)]
            pygame.draw.polygon(surface, pale, roof)
            outline(roof)
            for dx in (-108, -54, 0, 54, 108):
                line((x + dx, y - 112), (x + dx + 5, y - 16), 1, offset=dx)
            outline([(x - 43, y - 12), (x - 43, y - 103),
                     (x + 43, y - 103), (x + 43, y - 12)])
            line((x - 37, y - 92), (x + 35, y - 21), 2, red)
            line((x + 37, y - 92), (x - 35, y - 21), 1, red)
            for i in range(5):
                drift = math.sin(time * 1.8 + i) * 5
                line((x + 112 + i * 21, y - 85 + i * 12 + drift),
                     (x + 129 + i * 21, y - 89 + i * 12 + drift), 1, pale, i)
        elif kind == "saloon":
            body = [(x - 116, y - 130), (x + 109, y - 130),
                    (x + 109, y - 8), (x - 116, y - 8)]
            pygame.draw.polygon(surface, pale, body)
            outline(body)
            line((x - 138, y - 132), (x + 134, y - 132), 4)
            for dx in (-76, 67):
                renderer.rough_rect(surface, ink, pygame.Rect(x + dx - 19, y - 101, 38, 43), 2, seed + dx)
            line((x - 22, y - 8), (x - 22, y - 86), 2)
            line((x + 24, y - 8), (x + 24, y - 86), 2)
            line((x - 22, y - 86), (x + 24, y - 86), 2)
        elif kind == "water_tower":
            bowl = [(x - 96, y - 153), (x + 97, y - 153),
                    (x + 77, y - 86), (x - 76, y - 86)]
            pygame.draw.polygon(surface, pale, bowl)
            outline(bowl)
            for dx in (-60, 60):
                line((x + dx, y - 86), (x + dx * 1.15, y - 5), 3)
            line((x - 71, y - 22), (x + 70, y - 22), 2)
            for i in range(3):
                dy = math.sin(time * 2 + i) * 2
                rough_circle(surface, pale, (x + 91 + i * 13, y - 42 + dy), 4, seed + i, 1)
        elif kind == "station":
            line((x - 133, y - 143), (x + 124, y - 143), 4)
            line((x - 102, y - 143), (x - 102, y - 2), 3)
            line((x + 98, y - 143), (x + 98, y - 2), 3)
            pygame.draw.arc(surface, ink, (x - 40, y - 131, 80, 80), 0, math.tau, 2)
            angle = time * .7
            line((x, y - 91), (x + math.sin(angle) * 25, y - 91 - math.cos(angle) * 25), 2, red)
            for dx in (-70, -23, 24, 71):
                line((x + dx, y - 26), (x + dx + 16, y - 10), 1, pale, dx)
        elif kind == "gravity_machine":
            # Construction rings and a swinging weight make this page feel
            # like an experiment scribbled directly on graph paper.
            rough_circle(surface, ink, (x, y - 105), 89, seed, 2,
                         squash=(1.3, .84))
            rough_circle(surface, pale, (x, y - 105), 61, seed + 9, 1,
                         squash=(1.3, .84))
            line((x - 137, y - 104), (x + 137, y - 104), 1, pale)
            line((x, y - 206), (x, y - 11), 1, pale)
            angle = math.sin(time * 1.15) * .30
            bob = (x + math.sin(angle) * 59, y - 111 + math.cos(angle) * 68)
            line((x, y - 178), bob, 2, red)
            rough_circle(surface, red, bob, 12, seed + 11, 2)
            for i in range(5):
                tick = -100 + i * 50
                line((x + tick, y - 205), (x + tick, y - 195), 1, offset=i)
            line((x - 113, y - 18), (x + 112, y - 18), 2)
        elif kind == "satellite_wreck":
            hull = [(x - 43, y - 151), (x + 45, y - 166),
                    (x + 59, y - 89), (x - 29, y - 77)]
            pygame.draw.polygon(surface, pale, hull)
            outline(hull)
            rough_circle(surface, red, (x + 6, y - 124), 18, seed, 2)
            for side in (-1, 1):
                xx = x + side * 104
                panel = [(xx - 34, y - 164 + side * 12),
                         (xx + 26, y - 174 + side * 12),
                         (xx + 34, y - 102 + side * 12),
                         (xx - 27, y - 93 + side * 12)]
                pygame.draw.polygon(surface, pale, panel)
                outline(panel)
                line(panel[0], panel[2], 1, pale)
                line(panel[1], panel[3], 1, pale)
                line((x + side * 40, y - 120), (xx - side * 30, y - 131), 2)
            for i in range(3):
                drift = math.sin(time * 1.3 + i) * 4
                rough_circle(surface, red, (x + 75 + i * 25, y - 69 + i * 13 + drift),
                             3 + i, seed + i, 1)
            line((x - 82, y - 31), (x + 100, y - 31), 1, pale)
        elif kind == "rocket":
            hull = [(x - 37, y - 13), (x - 42, y - 102), (x, y - 181),
                    (x + 41, y - 102), (x + 35, y - 13)]
            pygame.draw.polygon(surface, pale, hull)
            outline(hull)
            rough_circle(surface, ink, (x, y - 104), 17, seed, 2)
            for side in (-1, 1):
                outline([(x + side * 38, y - 59), (x + side * 81, y - 8),
                         (x + side * 35, y - 14)])
            for i in range(3):
                line((x - 21 + i * 20, y - 4),
                     (x - 28 + i * 28, y + 22 + math.sin(time * 4 + i) * 7), 1, red, i)
        elif kind == "dish":
            line((x, y - 16), (x, y - 132), 3)
            for side in (-1, 1):
                line((x, y - 32), (x + side * 69, y - 7), 2)
            pygame.draw.arc(surface, ink, (x - 111, y - 220, 222, 124),
                            math.pi * .1, math.pi * .9, 3)
            line((x, y - 112), (x + math.sin(time) * 72, y - 190), 1, red)
            for i in range(4):
                rough_circle(surface, pale, (x + 115 + i * 18, y - 169 - i * 9),
                             7 + i * 2, seed + i, 1)
        elif kind == "moon_lab":
            outline([(x - 123, y - 8), (x - 96, y - 123),
                     (x - 7, y - 176), (x + 94, y - 126),
                     (x + 124, y - 8)])
            line((x - 92, y - 119), (x + 93, y - 119), 2)
            for dx in (-66, 0, 66):
                rough_circle(surface, ink, (x + dx, y - 95), 19, seed + dx, 2)
            line((x - 114, y - 8), (x + 119, y - 8), 2, red)
        elif kind == "return_capsule":
            capsule = [(x - 48, y - 202), (x + 49, y - 202),
                       (x + 112, y - 57), (x + 77, y - 17),
                       (x - 80, y - 17), (x - 110, y - 57)]
            pygame.draw.polygon(surface, pale, capsule)
            outline(capsule)
            for i in range(3):
                rough_circle(surface, ink, (x, y - 145 + i * 45),
                             22 - i * 3, seed + i, 2)
            line((x - 93, y - 67), (x + 93, y - 67), 2, red)
            for side in (-1, 1):
                for i in range(4):
                    flutter = math.sin(time * 2 + i) * 4
                    line((x + side * 70, y - 20 + i * 8),
                         (x + side * (103 + i * 7), y - 6 + i * 7 + flutter),
                         1, pale, i + side)
        elif kind == "dossier":
            folder = [(x - 132, y - 178), (x - 31, y - 178),
                      (x - 13, y - 192), (x + 121, y - 192),
                      (x + 135, y - 22), (x - 127, y - 20)]
            pygame.draw.polygon(surface, pale, folder)
            outline(folder)
            rough_circle(surface, ink, (x - 62, y - 121), 21, seed, 2)
            for dy in (-81, -60, -39):
                line((x - 105, y + dy), (x - 17, y + dy + 2), 1, offset=dy)
            for dy in (-145, -117, -89):
                line((x + 12, y + dy), (x + 103, y + dy + 1), 1, offset=dy)
            renderer.rough_rect(surface, red, pygame.Rect(x + 13, y - 68, 93, 30), 2, seed + 10)
            renderer.notebook.hand(surface, "COPY 00", (x + 18, y - 63), red, True, seed)
            line((x - 119, y - 178), (x + 124, y - 20), 2, red)
        elif kind == "carbon_press":
            for yy in (y - 199, y - 56):
                line((x - 112, yy), (x + 112, yy), 3)
            for side in (-1, 1):
                line((x + side * 112, y - 199), (x + side * 112, y - 17), 3)
            pygame.draw.ellipse(surface, pale, (x - 91, y - 165, 182, 74))
            pygame.draw.ellipse(surface, ink, (x - 91, y - 165, 182, 74), 2)
            for i in range(3):
                dx = math.sin(time * .9 + i * .9) * 4
                sheet = [(x - 82 + i * 11 + dx, y - 95 + i * 12),
                         (x + 65 + i * 11 + dx, y - 95 + i * 12),
                         (x + 78 + i * 11 + dx, y - 20 + i * 12),
                         (x - 72 + i * 11 + dx, y - 20 + i * 12)]
                pygame.draw.polygon(surface, pale, sheet)
                outline(sheet, ink if i == 2 else pale, 1)
                line(sheet[0], sheet[2], 1, red if i == 2 else pale, i)
        elif kind == "pinboard":
            board = [(x - 137, y - 190), (x + 125, y - 184),
                     (x + 130, y - 19), (x - 140, y - 25)]
            pygame.draw.polygon(surface, pale, board)
            outline(board)
            cards = ((-87, -145), (38, -154), (-17, -74), (85, -63))
            for i, (dx, dy) in enumerate(cards):
                rect = pygame.Rect(x + dx - 29, y + dy - 18, 58, 37)
                renderer.rough_rect(surface, ink, rect, 1, seed + i)
                line((x + dx - 21, y + dy - 7), (x + dx + 19, y + dy - 7), 1, pale, i)
                rough_circle(surface, red, (x + dx, y + dy - 18), 3, seed + i, 1)
            for a, b in ((0, 2), (1, 2), (2, 3)):
                ax, ay = cards[a]; bx, by = cards[b]
                line((x + ax, y + ay - 18), (x + bx, y + by - 18), 2, red, a * 3 + b)
            rough_circle(surface, red, (x - 18, y - 92),
                         9 + math.sin(time * 2) * 1.5, seed + 20, 1)
        elif kind == "cabinet":
            outline([(x - 93, y - 159), (x + 97, y - 159),
                     (x + 97, y - 9), (x - 93, y - 9)])
            for dy in (-132, -86, -40):
                renderer.rough_rect(surface, ink,
                    pygame.Rect(x - 78, y + dy, 159, 37), 1, seed + dy)
                line((x + 16, y + dy + 19), (x + 47, y + dy + 19), 2, red, dy)
            line((x - 89, y - 156), (x - 54, y - 176), 1, pale)
        elif kind == "antenna":
            line((x, y - 9), (x, y - 184), 3)
            for side in (-1, 1):
                line((x, y - 56), (x + side * 102, y - 14), 2)
            rough_circle(surface, red, (x, y - 190), 8 + math.sin(time * 3) * 2, seed, 2)
            for radius in (37, 61):
                pygame.draw.arc(surface, red,
                    (x - radius, y - 190 - radius, radius * 2, radius * 2),
                    math.pi * .17, math.pi * .83, 1)
        elif kind == "vault":
            rect = pygame.Rect(x - 108, y - 177, 216, 169)
            pygame.draw.rect(surface, pale, rect)
            renderer.rough_rect(surface, ink, rect, 3, seed)
            rough_circle(surface, ink, (x + 38, y - 84), 37, seed + 2, 3)
            for i in range(8):
                angle = i * math.tau / 8 + time * .18
                line((x + 38, y - 84),
                     (x + 38 + math.cos(angle) * 30, y - 84 + math.sin(angle) * 30), 1, offset=i)
            for dy in (-145, -120, -95):
                line((x - 82, y + dy), (x - 38, y + dy), 3, red, dy)
        elif kind == "classroom":
            # Green-black paint appears only inside the hand-drawn board. It
            # never covers the whole paper canvas or readable play surface.
            board = [(x - 142, y - 198), (x + 142, y - 203),
                     (x + 134, y - 24), (x - 139, y - 21)]
            pygame.draw.polygon(surface, (121, 133, 111), board)
            outline(board, ink, 4)
            for i, label in enumerate(("PAGE I  /  CUT", "PAGE II /  AIM",
                                       "PAGE III / FLOAT", "PAGE IV / HIDE")):
                renderer.notebook.hand(surface, label, (x - 116, y - 181 + i * 35),
                                       (229, 224, 203), True, seed + i)
            line((x - 133, y - 21), (x + 148, y - 21), 5)
            for i in range(4):
                if i < 3:
                    line((x + 49, y - 168 + i * 35),
                         (x + 103, y - 158 + i * 35), 2, red, i)
            line((x + 47, y - 55), (x + 105, y - 55), 2, red)
        elif kind == "memory_window":
            # Four torn slips repeat earlier visual motifs at a small scale,
            # while their staggered shadows imply old revisions under the page.
            symbols = ("sword", "ticket", "orbit", "file")
            for i, symbol in enumerate(symbols):
                xx = x - 139 + i * 79
                yy = y - 172 + (i % 2) * 20 + math.sin(time * 1.2 + i) * 3
                slip = [(xx, yy), (xx + 69, yy - 5),
                        (xx + 66, yy + 105), (xx + 52, yy + 99),
                        (xx + 43, yy + 108), (xx, yy + 103)]
                pygame.draw.polygon(surface, pale, slip)
                outline(slip)
                if symbol == "sword":
                    line((xx + 12, yy + 84), (xx + 50, yy + 23), 3, red)
                    line((xx + 8, yy + 68), (xx + 31, yy + 83), 2)
                elif symbol == "ticket":
                    renderer.rough_rect(surface, ink,
                        pygame.Rect(xx + 13, yy + 28, 43, 47), 1, seed + i)
                    line((xx + 20, yy + 50), (xx + 51, yy + 50), 1, red)
                elif symbol == "orbit":
                    rough_circle(surface, ink, (xx + 34, yy + 51), 21, seed + i, 1,
                                 squash=(1.2, .55))
                    rough_circle(surface, red, (xx + 51, yy + 45), 4, seed + i, 1)
                else:
                    line((xx + 13, yy + 37), (xx + 53, yy + 37), 6)
                    line((xx + 13, yy + 57), (xx + 45, yy + 57), 5)
            line((x - 144, y - 17), (x + 143, y - 17), 1, red)
        elif kind == "answer_scraps":
            scraps = (((-126, -181), (-29, -183), (-12, -84), (-117, -81)),
                      ((-6, -163), (106, -173), (119, -71), (5, -67)),
                      ((-85, -60), (46, -59), (62, -9), (-80, -11)))
            for i, paper in enumerate(scraps):
                shift = math.sin(time * 1.2 + i * 2) * 3
                polygon = [(x + dx, y + dy + shift) for dx, dy in paper]
                pygame.draw.polygon(surface, pale, polygon)
                outline(polygon)
                line((polygon[0][0] + 12, polygon[0][1] + 25),
                     (polygon[1][0] - 11, polygon[1][1] + 24), 1, pale, i)
                line((polygon[0][0] + 18, polygon[0][1] + 46),
                     (polygon[1][0] - 24, polygon[1][1] + 45), 1, red, i)
            line((x - 99, y - 96), (x + 94, y - 138), 2, red)
            line((x + 22, y - 56), (x - 39, y - 135), 2, red)
        elif kind == "exam":
            rect = pygame.Rect(x - 109, y - 172, 219, 160)
            pygame.draw.rect(surface, pale, rect)
            renderer.rough_rect(surface, ink, rect, 2, seed)
            for i in range(4):
                yy = y - 142 + i * 31
                rough_circle(surface, ink, (x - 77, yy), 8, seed + i, 1)
                line((x - 48, yy), (x + 83 - i * 9, yy), 1, pale, i)
            line((x - 91, y - 143), (x + 91, y - 36), 2, red)
        elif kind == "crossouts":
            for i in range(3):
                xx = x - 79 + i * 78
                rough_circle(surface, ink, (xx, y - 123), 15, seed + i, 2)
                line((xx, y - 107), (xx + (i - 1) * 7, y - 50), 2, offset=i)
                for side in (-1, 1):
                    line((xx, y - 92), (xx + side * 24, y - 68), 2, offset=i + side)
                    line((xx, y - 50), (xx + side * 19, y - 8), 2, offset=i + side * 3)
                if i < 2:
                    line((xx - 30, y - 147), (xx + 26, y - 7), 2, red, i)
        elif kind == "hand":
            # A margin hand points toward the real upper route, not the player.
            fingers = [(x - 114, y - 17), (x - 65, y - 77),
                       (x - 26, y - 92), (x + 76, y - 181),
                       (x + 92, y - 169), (x + 29, y - 73),
                       (x + 58, y - 77), (x + 67, y - 56),
                       (x + 7, y - 30), (x - 20, y - 5)]
            pygame.draw.polygon(surface, pale, fingers)
            outline(fingers)
            line((x - 101, y - 8), (x + 71, y - 161), 1, red)
        # The first interstitials sit near short combat/tutorial instructions.
        # Their own internal marks carry the story without another text layer.
        if kind not in {"sword_study", "departures", "gravity_machine",
                        "dossier", "classroom"}:
            renderer.notebook.hand(surface, title, (x - 117, y - 212), red, True, seed)
