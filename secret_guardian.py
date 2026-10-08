"""An optional cloud guardian with its own silhouette and committed attacks.

The kite uses the normal enemy/weapon contract. Its eight-mark duel reads a
gust, a fixed tail mark and a diagonal dive. The second draft links two fully
warned attacks before a projectile-free opening.
"""
from __future__ import annotations

import math
import pygame

from advanced_enemies import PaperProjectile, _dashed_line, _health_scratches
from margin_guardians import MarginGuardian
from localization import get_language, translate
from paper_renderer import jitter_line
from settings import INK, PAPER, RED_RULE


BLUE = (64, 108, 126)


def _label(english, turkish):
    return turkish if get_language() == "tr" else translate(english)


class CloudGust(PaperProjectile):
    """A low curl of wind; the normal dash-return API still applies."""

    def draw(self, surface, camera):
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        direction = 1 if self.vx >= 0 else -1
        color = BLUE if self.damage_enabled else (153, 160, 151)
        for index in range(3):
            yy = y + (index - 1) * 7
            pygame.draw.lines(surface, color, False,
                [(x-direction*22, yy+4), (x-direction*11, yy),
                 (x+direction*8, yy), (x+direction*15, yy-5)], 2)
        pygame.draw.arc(surface, color, (x-9, y-12, 20, 22), -.7, 2.7, 2)


class CloudKiteGuardian(MarginGuardian):
    """A folded kite, never a reskinned compass or another campaign boss.

    Creation API: ``CloudKiteGuardian(x, ground_y=590, seed=1)``.
    Warnings last at least .95 s, and aim/landing positions stay locked until
    impact. Phase one opens after one attack; phase two opens after a warned
    pair. Both keep two visible punish marks and the normal weapon API.
    """

    kind = "cloud_kite"
    width, height, radius = 66, 76, 33
    base_hp = 8
    uses_gravity = False
    is_boss = True
    contact_states = ("kite_dive",)
    warning_sound = "enemy_telegraph_air"

    patterns = (("gust_warn", "gust", 1.05, 1.85, "JUMP THE GUST"),
                ("tail_warn", "tail_snap", .95, .24, "LEAVE THE TAIL MARK"),
                ("dive_warn", "kite_dive", 1.05, .62, "DIVE — STEP ASIDE"))
    opening_cue = "LOOSE STRING — HIT"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.dive_origin = (self.x, self.y)
        self.tail_hit = False

    def _prepare_pattern(self):
        self.tail_hit = False
        if self.active_pattern == 2:
            self.dive_origin = (self.x, self.y)

    @property
    def tail_danger(self):
        return pygame.Rect(round(self.target_x-40), round(self.ground_y-62), 80, 62)

    def _animate_warning(self):
        if self.state == "dive_warn":
            self.y = self.ground_y-82*self.pose_progress

    def _start_attack(self, ctx):
        if self.state == "gust":
            self.projectiles.append(CloudGust(
                self.x+self.facing*42, self.ground_y-21,
                self.facing*280, 0, "cloud_gust", life=2.3,
                radius=12, gravity=0, terrain_collision=False))
            ctx.sounds.play("ink")
        elif self.state == "kite_dive":
            self.dive_origin = (self.x, self.y)
            ctx.sounds.play("enemy_attack_charge")

    def _animate_attack(self, dt, ctx):
        if self.state == "tail_snap":
            self._strike_once(ctx, (self.tail_danger,))
            self.tail_hit = self.strike_used
        elif self.state == "kite_dive":
            progress = self.pose_progress
            self.x = self.dive_origin[0]+(self.target_x-self.dive_origin[0])*progress
            self.y = self.dive_origin[1]+(self.ground_y-self.dive_origin[1])*progress
            self.vx = 0

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x = camera.screen_x(self.x)
        bottom = round(self.y+camera.offset_y)
        center = (x, bottom-39)
        color = self._base_color()
        shape = [(x, bottom-76), (x+33, bottom-43),
                 (x, bottom-7), (x-33, bottom-43)]
        # Sharp folded cloth, blue left facet, ochre right facet, graphite ribs.
        pygame.draw.polygon(surface, PAPER, shape)
        pygame.draw.polygon(surface, (124, 161, 169),
                            [shape[0], shape[3], shape[2], center])
        pygame.draw.polygon(surface, (221, 179, 100),
                            [shape[0], center, shape[2], shape[1]])
        pygame.draw.lines(surface, color, True, shape, 3)
        jitter_line(surface, color, shape[0], shape[2], 2, self.seed, 1, .7)
        jitter_line(surface, color, shape[3], shape[1], 2, self.seed+1, 1, .7)
        pygame.draw.circle(surface, PAPER, center, 8)
        pygame.draw.circle(surface, color, center, 8, 2)
        pygame.draw.line(surface, color, (x-4, bottom-42), (x-1, bottom-42), 2)
        pygame.draw.line(surface, color, (x+2, bottom-42), (x+5, bottom-42), 2)
        if self.state == "recover":
            pygame.draw.line(surface, BLUE, (x-4, bottom-35), (x+4, bottom-35), 2)
        else:
            pygame.draw.lines(surface, color, False,
                              [(x-4, bottom-35), (x, bottom-38), (x+4, bottom-35)], 2)

        tail_points = [(x, bottom-7)]
        for index in range(1, 5):
            tail_points.append((x+round(math.sin(self.time*3-index)*11),
                                bottom-7+index*9))
        pygame.draw.lines(surface, color, False, tail_points, 2)
        for index in (1, 3):
            tx, ty = tail_points[index]
            pygame.draw.polygon(surface, (164, 72, 63),
                [(tx-9, ty-4), (tx, ty), (tx+9, ty-4),
                 (tx+9, ty+4), (tx, ty), (tx-9, ty+4)])

        floor = round(self.ground_y+camera.offset_y)
        left, right = map(camera.screen_x, self.attack_bounds)
        target = camera.screen_x(self.target_x)
        if self.state == "gust_warn":
            self._draw_telegraph(surface, camera, renderer,
                _label("JUMP THE GUST", "RÜZGÂRDAN ZIPLA"), label_offset=116)
            endpoint = right-18 if self.facing > 0 else left+18
            _dashed_line(surface, RED_RULE, (x+self.facing*42, floor-21),
                         (endpoint, floor-21), 2, 9, 7)
            pygame.draw.lines(surface, RED_RULE, False,
                [(endpoint-self.facing*10, floor-27), (endpoint, floor-21),
                 (endpoint-self.facing*10, floor-15)], 2)
        elif self.state in {"tail_warn", "tail_snap"}:
            self._draw_telegraph(surface, camera, renderer,
                _label("LEAVE THE TAIL MARK", "KUYRUK İZİNDEN ÇIK"), label_offset=116)
            danger = self.tail_danger.move(round(-camera.x+camera.offset_x), camera.offset_y)
            pygame.draw.rect(surface, RED_RULE, danger, 2)
            _dashed_line(surface, RED_RULE, (x, bottom-7),
                         (target, floor-31), 1, 8, 6)
            if self.state == "tail_snap":
                pygame.draw.lines(surface, color, False,
                    [(x, bottom-7), (target-40, floor-40),
                     (target, floor-62), (target+40, floor-12)], 4)
        elif self.state in {"dive_warn", "kite_dive"}:
            if self.state == "dive_warn":
                self._draw_telegraph(surface, camera, renderer,
                    _label("DIVE — STEP ASIDE", "DALIŞ — YANA KAÇ"), label_offset=116)
            origin_x = camera.screen_x(self.dive_origin[0])
            _dashed_line(surface, RED_RULE, (origin_x, floor-120),
                         (target, floor-38), 2, 8, 6)
            pygame.draw.line(surface, RED_RULE, (target-23, floor-6),
                             (target+23, floor-6), 3)
        elif self.state == "recover":
            self._draw_opening(surface, center, 24)
            if self.vulnerable:
                text = _label("LOOSE STRING — HIT", "İP GEVŞEDİ — VUR")
                label = renderer.font_small.render(text, True, BLUE)
                sx = max(12, min(surface.get_width()-label.get_width()-12,
                                 x-label.get_width()//2))
                surface.blit(label, (sx, max(12, bottom-115)))
        if self.phase == 2:
            for side in (-1, 1):
                pygame.draw.line(surface, RED_RULE,
                    (x+side*41, bottom-52), (x+side*46, bottom-30), 3)
        _health_scratches(surface, camera, self, 93)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)
