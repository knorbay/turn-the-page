from __future__ import annotations

import math
import pygame

from paper_renderer import jitter_line
from settings import INK, PAPER, WIDTH


class ArtistBridgeEvent:
    def __init__(self, bridge):
        self.bridge = bridge
        self.state = "waiting"
        self.timer = 0.0
        self.done = False

    def update(self, dt, player, camera, particles, sounds):
        if self.state == "waiting" and player.x > 1030:
            self.state = "pause"
            self.timer = 0.0
            player.locked = True
        elif self.state == "pause":
            self.timer += dt
            player.vx *= .8
            if self.timer > .55:
                self.state = "drawing"
                self.timer = 0.0
                sounds.play("pencil")
        elif self.state == "drawing":
            self.timer += dt
            eased = min(1.0, self.timer / 2.6)
            self.bridge.draw_progress = eased
            tip_x = self.bridge.x1 + (self.bridge.x2 - self.bridge.x1) * eased
            particles.pencil_speck(tip_x, self.bridge.y)
            if eased >= 1:
                self.state = "settle"
                self.timer = 0.0
                camera.kick(3, .18)
        elif self.state == "settle":
            self.timer += dt
            if self.timer > .32:
                self.done = True
                self.state = "done"
                player.locked = False

    def draw(self, surface, camera):
        if self.state not in ("pause", "drawing", "settle"):
            return
        if self.state == "pause":
            p = min(1.0, self.timer / .55)
            tip_world_x = self.bridge.x1
        else:
            p = 1.0
            tip_world_x = self.bridge.visible_x2
        tip_x = camera.screen_x(tip_world_x)
        tip_y = round(self.bridge.y - 2 + camera.offset_y)
        enter = (1 - p) * 390
        angle = -.58
        length = 360
        end_x = tip_x + math.cos(angle) * length + enter
        end_y = tip_y + math.sin(angle) * length - enter * .25
        # pencil wooden body, graphite tip, and a hint of an outside hand
        pygame.draw.line(surface, (214, 151, 51), (tip_x + 12, tip_y - 10), (end_x, end_y), 28)
        pygame.draw.line(surface, (239, 195, 90), (tip_x + 12, tip_y - 15), (end_x, end_y - 5), 7)
        pygame.draw.polygon(surface, (218, 183, 127),
                            [(tip_x, tip_y), (tip_x + 27, tip_y - 23), (tip_x + 34, tip_y - 8)])
        pygame.draw.polygon(surface, (42, 40, 39),
                            [(tip_x, tip_y), (tip_x + 9, tip_y - 8), (tip_x + 11, tip_y - 2)])
        pygame.draw.circle(surface, (219, 177, 151), (round(end_x + 54), round(end_y - 4)), 68)


class EraserEvent:
    def __init__(self, bridge):
        self.bridge = bridge
        self.state = "waiting"
        self.timer = 0.0
        self.done = False
        self.erase_start = 3260
        self.erase_end = 3445
        self.erased_to = self.erase_start

    def update(self, dt, player, camera, particles, sounds):
        if self.state == "waiting" and player.x > 3025:
            self.state = "warning"
            self.timer = 0.0
        elif self.state == "warning":
            self.timer += dt
            if self.timer > .75:
                self.state = "erasing"
                self.timer = 0.0
                sounds.play("erase")
        elif self.state == "erasing":
            self.timer += dt
            progress = min(1.0, self.timer / 1.65)
            target = self.erase_start + (self.erase_end - self.erase_start) * progress
            self.bridge.erase(self.erased_to, target)
            self.erased_to = target
            particles.eraser_dust(target, self.bridge.y + 4, 3)
            if int(self.timer * 15) % 4 == 0:
                camera.kick(2.2, .12)
            if progress >= 1:
                self.state = "leaving"
                self.timer = 0.0
        elif self.state == "leaving":
            self.timer += dt
            if self.timer > .65:
                self.state = "done"
                self.done = True

    def draw(self, surface, camera):
        if self.state not in ("warning", "erasing", "leaving"):
            return
        if self.state == "warning":
            p = min(1.0, self.timer / .75)
            x = WIDTH + 180 - 230 * p
        elif self.state == "erasing":
            x = camera.screen_x(self.erased_to) - 47
        else:
            x = camera.screen_x(self.erase_end) - 47 + self.timer * 360
        y = round(self.bridge.y - 56 + math.sin(self.timer * 30) * 3)
        eraser = pygame.Surface((105, 62), pygame.SRCALPHA)
        pygame.draw.polygon(eraser, (222, 150, 150), [(5, 12), (87, 2), (101, 45), (20, 59)])
        pygame.draw.polygon(eraser, (238, 188, 178), [(5, 12), (21, 31), (20, 59), (0, 37)])
        pygame.draw.line(eraser, (116, 92, 88), (21, 31), (101, 18), 2)
        surface.blit(eraser, (x, y))


class PageTurnEvent:
    def __init__(self):
        self.active = False
        self.done = False
        self.timer = 0.0
        self.progress = 0.0

    def update(self, dt, player, sounds):
        if not self.active and not self.done and player.x > 6410:
            self.active = True
            player.locked = True
            sounds.play("page")
        if self.active:
            self.timer += dt
            self.progress = min(1.0, self.timer / 2.25)
            if self.progress >= 1:
                self.active = False
                self.done = True
                return True
        return False
