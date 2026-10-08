"""Quiet page scenery and one short, optional heart route per page."""
from __future__ import annotations

import math
import pygame

from action_content import claim_artist_canvas, release_artist_canvas
from scripted_events import ArtistTool
from settings import INK, INK_LIGHT


STYLES = ("handwriting", "torn_edge", "construction", "carbon", "annotation")

# (left, width, height): each page keeps its own climbing rhythm. Only the
# marked landings ask for interaction; passing scenery never becomes a chore.
HEART_LANDINGS = (
    ((100, 185, 525), (300, 185, 465), (500, 205, 405)),
    ((100, 185, 530), (315, 195, 470), (540, 205, 410)),
    ((100, 185, 525), (300, 205, 455), (530, 205, 505)),
    ((100, 185, 525), (300, 185, 460), (500, 205, 395)),
    ((100, 205, 530), (325, 195, 475), (540, 205, 420)),
)
HEART_MARKS = ((2,), (0, 2), (1,), (0, 2), (2,))


class RouteScenery:
    active = True
    mandatory = False
    layer = 0
    is_quiet_route = True

    def __init__(self, runtime, left, width, index, *, heart_route=False):
        self.page, self.left, self.width, self.index = runtime.index, left, width, index
        self.obstacles = []
        if heart_route:
            layout = HEART_LANDINGS[self.page]
        else:
            # Quiet gaps offer a low terrace, an arch, or descending shelves.
            # Their unobstructed floor remains the direct path to the fight.
            layouts = (
                ((150, 285, 525), (555, 315, 525)),
                ((160, 190, 535), (390, 285, 475), (715, 190, 535)),
                ((160, 220, 505), (425, 245, 540)),
            )
            layout = layouts[(index+self.page) % len(layouts)]
        self.landings = []
        for step, (offset, span, y) in enumerate(layout):
            p = runtime.world.add(left+offset, left+offset+span, y, 10,
                f"pacing_option_{self.page}_{index}_{step}", 23100+self.page*100+index*10+step)
            p.appearance = STYLES[self.page]
            self.landings.append(p)

    def update(self, dt, ctx, interact=False):
        pass

    def draw(self, surface, camera, renderer):
        left, right = camera.screen_x(self.left), camera.screen_x(self.left+self.width)
        if right < -80 or left > surface.get_width()+80:
            return
        oy = camera.offset_y
        color = (143, 143, 120)
        for i in range(4+(self.index % 2)):
            sx = camera.screen_x(self.left+900+i*155)
            y = round(410+oy)
            variation = (i+self.index) % 3
            if self.page == 0:
                top = y-95-variation*25
                pygame.draw.line(surface, color, (sx, y+130), (sx-12, top), 2)
                for n in range(4):
                    by = top+30+n*42
                    pygame.draw.line(surface, color, (sx-9, by), (sx+36, by-24), 1)
            elif self.page == 1:
                pygame.draw.arc(surface, color, (sx, y-20+variation*8, 135, 150), 0, math.pi, 2)
                pygame.draw.line(surface, color, (sx, y+48), (sx, y+160), 2)
                pygame.draw.line(surface, color, (sx-10, y-25), (sx+145, y-25), 1)
            elif self.page == 2:
                sy, radius = y-variation*28, 24+variation*7
                pygame.draw.circle(surface, color, (sx, sy), radius, 2)
                pygame.draw.line(surface, color, (sx-54, sy+28), (sx+54, sy-28), 2)
                pygame.draw.line(surface, color, (sx, sy+radius), (sx, y+150), 1)
            elif self.page == 3:
                top = y-65-variation*40
                pygame.draw.rect(surface, color, (sx, top, 95, y+95-top), 1)
                pygame.draw.line(surface, color, (sx-5, top-8), (sx+101, top-8), 2)
                for n in range(2+variation):
                    pygame.draw.line(surface, color, (sx+12, top+22+n*30), (sx+78, top+22+n*30), 1)
            else:
                pygame.draw.line(surface, color, (sx, y+150), (sx, y+10), 2)
                for n in range(3+variation):
                    by = y+20+n*24
                    pygame.draw.ellipse(surface, color, (sx-37, by-18, 37, 20), 1)
                    pygame.draw.ellipse(surface, color, (sx, by-30, 37, 20), 1)


class RouteExpedition(RouteScenery):
    is_route_expedition = True
    TITLES = ("BAMBOO WALK", "THE OLD VIADUCT", "SATELLITE WALK",
              "THE ROOFTOP ARCHIVE", "THE UNWRITTEN GARDEN")

    def __init__(self, runtime, left, width, index):
        super().__init__(runtime, left, width, index, heart_route=True)
        self.title = self.TITLES[self.page]
        self.mark_positions = tuple(((self.landings[i].x1+self.landings[i].x2)/2,
                                      self.landings[i].y) for i in HEART_MARKS[self.page])
        self.marks = set()
        self.completed = False
        self.reward_time = 0.0
        self.hand = None
        final = self.landings[-1]
        self.bridge = runtime.world.add(final.x2+15, final.x2+375, final.y, 12,
            f"expedition_bridge_{self.page}_{index}", 24100+self.page*100+index)
        self.bridge.begin_drawing()
        self.bridge.appearance = "handwriting"

    def update(self, dt, ctx, interact=False):
        self.hand = None
        player = ctx.player
        nearby = self.left-90 <= player.center_x <= self.left+self.width+90
        if player.health <= 0 or self.completed or getattr(player, "locked", False) or not nearby:
            release_artist_canvas(ctx, self)
            return
        for i, (x, y) in enumerate(self.mark_positions):
            if i not in self.marks and abs(player.center_x-x) < 65 and abs(player.rect.bottom-y) < 24:
                ctx.level.interaction_hint = "E / trace the blue mark"
                if interact:
                    self.marks.add(i)
                    ctx.sounds.play("pencil")
        if len(self.marks) == len(self.mark_positions):
            if not claim_artist_canvas(ctx, self):
                return
            self.reward_time += dt
            self.bridge.draw_progress = min(1, self.reward_time/.8)
            self.hand = ArtistTool("pencil", self.bridge.visible_x2, self.bridge.y, True)
            ctx.director.tool = self.hand
            if self.reward_time >= .8:
                self.completed = True
                restored = player.health < player.max_health
                player.health = min(player.max_health, player.health+1)
                if restored:
                    player.health_restore_flash = .8
                ctx.level.toast = "Route drawn. +1 heart." if restored else "Route drawn."
                ctx.level.toast_time = 2.5
                ctx.sounds.play("pickup")
                release_artist_canvas(ctx, self)

    def draw(self, surface, camera, renderer):
        super().draw(surface, camera, renderer)
        oy = camera.offset_y
        # A reward label and visible blue circles replace the instruction box
        # and repeated jump-key signs. The interaction hint appears nearby.
        if not self.completed:
            x, y = self.mark_positions[-1]
            sx = camera.screen_x(x)
            renderer.doodle_text(surface, "+1 HEART", (sx-43, y-87+oy), INK_LIGHT, renderer.font_small)
        for i, (x, y) in enumerate(self.mark_positions):
            if self.completed:
                break
            sx, sy = camera.screen_x(x), round(y-25+oy)
            color = (70, 112, 130) if i not in self.marks else (106, 129, 78)
            pygame.draw.circle(surface, color, (sx, sy), 16, 2)
            if i in self.marks:
                pygame.draw.lines(surface, color, False, [(sx-7, sy), (sx-1, sy+6), (sx+9, sy-7)], 2)
            else:
                renderer.doodle_text(surface, "E", (sx-5, sy-9), INK, renderer.font_small)

    def draw_overlay(self, surface, camera, renderer):
        pass  # The shared ArtistDirector renders the claimed pencil stroke.
