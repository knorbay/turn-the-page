"""Cached, handwritten schoolwork in the quiet upper part of each sheet.

These are ink annotations, never platforms. Text and diagrams stay together
in world space; the cache avoids laying out handwriting in the render loop.
Installed handwriting fonts are used without redistributing system fonts.
"""
from __future__ import annotations

import math
import random
import pygame

BLUE = (66, 88, 112)
GRAPHITE = (101, 98, 86)
RED = (151, 68, 62)
PLAIN_GLYPHS = str.maketrans({"→": "->", "₀": "0", "₁": "1", "₂": "2",
                            "ₛ": "s", "ₓ": "x", "ₒ": "o", "ᵢ": "i", "ᵣ": "r",
                            "−": "-"})

# heading, two lines of working, teacher/margin remark, illustration
LESSONS = (
    (
        ("GEOMETRY / 04", "a² + b² = c²", "3² + 4² = 25  →  c = 5", "draw the diagram first!", "triangle"),
        ("CIRCLES", "circumference = 2πr", "area = πr²", "bring my compass back :)", "circle"),
        ("TRIANGLES", "α + β + γ = 180°", "90° + 60° + ? = 180°", "30°  ✓", "triangle"),
        ("CIRCULAR MOTION", "v = ωr", "one turn = 2π radians", "why is there a sword here?", "circle"),
    ),
    (
        ("PHYSICS / MOTION", "v = Δx / Δt", "120 m / 6 s = 20 m/s", "remember the units!", "velocity"),
        ("PROJECTILES", "x = v₀ cos(θ) · t", "y = v₀ sin(θ) · t − ½gt²", "ignore air resistance...", "trajectory"),
        ("FRICTION", "Fₛ = μ · N", "N = mg  (level ground)", "keep coffee off the notebook", "force"),
        ("THE TRAIN PROBLEM", "distance = speed × time", "60 km/h × ½ h = 30 km", "the train is not drawn yet", "velocity"),
    ),
    (
        ("PHYSICS / GRAVITY", "F = G · m₁m₂ / r²", "double r  →  one quarter F", "space was not empty after all", "orbit"),
        ("ORBITAL NOTES", "F = mv² / r", "T = 2πr / v", "the satellite needs batteries", "orbit"),
        ("VECTORS", "R = A + B", "Rₓ = Aₓ + Bₓ", "write the direction too!", "vectors"),
        ("FREE FALL", "v = g · t", "h = ½g · t²", "Earth: g ≈ 9.8 m/s²", "trajectory"),
    ),
    (
        ("OPTICS / REFLECTION", "incident angle = reflected angle", "θᵢ = θᵣ", "the mirror sees everything", "mirror"),
        ("BINARY NUMBERS", "13 = 8 + 4 + 1", "13 (decimal) = 1101 (binary)", "is this a secret message?", "binary"),
        ("COORDINATES", "y = 2x + 1", "x = 2  →  y = 5", "connect the dots", "velocity"),
        ("LENSES", "1/f = 1/dₒ + 1/dᵢ", "converging lens: f > 0", "I cannot see the blackboard", "mirror"),
    ),
    (
        ("FINAL LESSON / REVISION", "(a + b)² = a² + 2ab + b²", "(x + 3)² = x² + 6x + 9", "show your working!", "squares"),
        ("NEWTON'S THIRD LAW", "F₁₂ = −F₂₁", "action and reaction", "the paper hits back", "force"),
        ("EQUATIONS", "2x + 6 = 18", "2x = 12  →  x = 6", "revise it; do not start over", "squares"),
        ("IS CLASS OVER?", "answer = ?", "the back of this page is blank", "wait for the bell", "clock"),
    ),
)


class NotebookAnnotations:
    def __init__(self):
        face = pygame.font.match_font("noteworthy,comic sans ms,chalkboard,dejavusans")
        self.small = pygame.font.Font(face, 17)
        self.body = pygame.font.Font(face, 21)
        self.heading = pygame.font.Font(face, 18)
        self.sheets = [[self._make_note(page, index, lesson)
                        for index, lesson in enumerate(lessons)]
                       for page, lessons in enumerate(LESSONS)]

    def _hand(self, surface, text, x, y, font, color, seed):
        # Whole words retain natural kerning; their baseline wanders slightly
        # like a real student's handwriting rather than a shaky UI label.
        rng = random.Random(seed)
        for word in text.translate(PLAIN_GLYPHS).split(" "):
            if word == "✓":
                pygame.draw.lines(surface,color,False,
                                  [(x,y+10),(x+5,y+16),(x+16,y+1)],2)
                x += 23
                continue
            glyph = font.render(word, True, color)
            surface.blit(glyph, (round(x), y + rng.choice((-1, 0, 0, 1))))
            x += glyph.get_width() + font.size(" ")[0]
        return x

    def _make_note(self, page, index, lesson):
        surface = pygame.Surface((510, 165), pygame.SRCALPHA)
        # A broad eraser rub gives dark writing a quiet patch of paper without
        # introducing a rectangle that might be mistaken for playable ground.
        base = ((242, 235, 211), (235, 215, 174), (218, 228, 232),
                (232, 230, 218), (249, 246, 229))[page]
        for step in range(12):
            pygame.draw.ellipse(surface,(*base,round(180*(step+1)/12)),
                (-20+step*4,-14+step*2,550-step*8,193-step*4))
        title, line1, line2, remark, kind = lesson
        seed = page * 99 + index * 7
        self._hand(surface, title, 12, 1, self.heading, RED, seed)
        pygame.draw.lines(surface, (*RED, 150), False,
                          [(12, 31), (148, 32), (265, 30)], 1)
        self._hand(surface, line1, 17, 42, self.body, BLUE, seed + 1)
        self._hand(surface, line2, 19, 75, self.small, BLUE, seed + 2)
        self._hand(surface, remark, 27, 125, self.small, RED, seed + 3)
        pygame.draw.lines(surface, (*RED, 160), False,
                          [(16, 127), (7, 119), (9, 102)], 1)
        self._diagram(surface, kind, 395, 74, seed)
        # A faint crossed-out trial, small graphite crumbs and a pencil tick.
        self._hand(surface, "?", 350, 122, self.small, GRAPHITE, seed)
        pygame.draw.line(surface, (*GRAPHITE, 145), (345, 139), (365, 126), 1)
        for i in range(5):
            pygame.draw.line(surface, (*GRAPHITE, 90),
                             (325 + i*6, 151+i%2), (328 + i*6, 152+i%2), 1)
        return pygame.transform.rotate(surface, (1.1, -.8, .5, -1.2)[index])

    def _diagram(self, s, kind, x, y, seed):
        c = (*BLUE, 205)
        r = (*RED, 180)
        def line(a, b, color=c, width=1):
            pygame.draw.line(s, color, (x+a[0], y+a[1]), (x+b[0], y+b[1]), width)
        def text(t, dx, dy, color=BLUE):
            s.blit(self.small.render(t.translate(PLAIN_GLYPHS), True, color), (x+dx, y+dy))
        if kind == "triangle":
            for a,b in (((-28,32),(-28,-35)), ((-28,-35),(66,32)), ((66,32),(-28,32))):
                line(a,b,width=2)
            line((-28,21),(-17,21));line((-17,21),(-17,32))
            text("a",-48,-12);text("b",10,34);text("c",25,-18)
        elif kind in ("circle", "orbit"):
            pygame.draw.circle(s,c,(x+17,y),44,2)
            if kind == "orbit":
                pygame.draw.ellipse(s,c,(x-43,y-21,120,42),1)
                pygame.draw.circle(s,(*BLUE, 95),(x+17,y),12)
                pygame.draw.circle(s,r,(x+59,y-16),6,2)
            else:
                line((17,0),(59,-10),r,2);text("r",36,-29)
                line((17,-50),(17,50),(*GRAPHITE,100))
            pygame.draw.circle(s,c,(x+17,y),2)
        elif kind in ("velocity", "trajectory", "vectors"):
            line((-28,38),(77,38));line((-28,38),(-28,-47))
            line((73,34),(77,38));line((-32,-42),(-28,-47))
            text("t" if kind != "vectors" else "x",78,29)
            text("v" if kind == "velocity" else "y",-39,-66)
            if kind == "trajectory":
                points=[(x-28+i*5,y+36-round(68*math.sin(i/20*math.pi))) for i in range(21)]
                pygame.draw.lines(s,c,False,points,2)
                for i in (4,10,16):pygame.draw.circle(s,r,points[i],3,1)
            else:
                line((-28,38),(63,-29),c,2)
                line((57,-29),(63,-29));line((63,-23),(63,-29))
                if kind == "vectors":
                    line((-28,38),(42,38),r,2);line((42,38),(63,-29),r,2)
                    text("R",-5,-16)
                else:
                    for n in range(1,4):line((-32,38-n*20),(-24,38-n*20))
        elif kind == "force":
            pygame.draw.rect(s,c,(x-9,y-15,51,40),2)
            line((-28,27),(73,27),(*GRAPHITE,180))
            line((16,3),(16,-48),r,2);line((10,-39),(16,-48),r);line((22,-39),(16,-48),r)
            line((16,8),(16,58),c,2);line((10,49),(16,58));line((22,49),(16,58))
            text("N",25,-56,RED);text("mg",27,36)
        elif kind == "mirror":
            line((-36,21),(78,21),c,2)
            for i in range(-30,80,10):line((i,22),(i-7,29),(*GRAPHITE,145))
            for i in range(-48,17,9):line((20,i),(20,i+4),(*GRAPHITE,145))
            line((-29,-40),(20,20),r,2);line((20,20),(69,-40),r,2)
            text("θᵢ",-6,-16);text("θᵣ",29,-16)
        elif kind == "binary":
            for i,t in enumerate(("8","4","2","1")):
                text(t,-35+i*29,-35)
                pygame.draw.rect(s,c,(x-39+i*29,y-4,24,30),1)
                text("1101"[i],-35+i*29,-4)
        elif kind == "squares":
            pygame.draw.rect(s,c,(x-29,y-36,94,82),2)
            line((29,-36),(29,46));line((-29,16),(65,16))
            text("a²",-14,-27);text("ab",33,-23);text("ab",-12,17);text("b²",35,17)
        elif kind == "clock":
            pygame.draw.circle(s,c,(x+17,y),45,2)
            for i in range(12):
                a=i*math.tau/12
                line((17+math.sin(a)*37,math.cos(a)*37),(17+math.sin(a)*42,math.cos(a)*42))
            line((17,0),(17,-29),c,2);line((17,0),(43,12),r,2)

    def draw(self, surface, camera, page):
        page = max(0, min(4, page))
        # 1,220 world units / 0.60 parallax gives at least one piece of
        # schoolwork per ordinary view, including the opening of every page.
        travelled = camera.x * .60
        first = math.floor((travelled-600)/760)
        for i in range(first, first+4):
            if i < 0:
                continue
            x = round(220 + i*760 - travelled)
            if x > surface.get_width() or x < -530:
                continue
            y = 113 + (i%2)*19
            surface.blit(self.sheets[page][i%4], (x,y))
