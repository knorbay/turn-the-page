"""Four optional chapter guardians with readable, committed short duels.

These enemies use the normal weapons, dash-return and boss-opening contracts.
Each has ten health marks, three deterministic attacks and a clean two-hit
opening. Its second draft links two fully warned attacks before that opening.  No warning, idle or recovery pose deals damage.
"""
from __future__ import annotations

import math
import pygame

from advanced_enemies import (AdvancedEnemy, PaperProjectile, _dashed_line,
                              _health_scratches, _player_hit_feedback)
from localization import translate
from paper_renderer import jitter_line
from settings import INK, PAPER, RED_RULE


BRASS = (156, 112, 56)
ORBIT = (77, 123, 145)
CARBON = (81, 83, 93)
VIOLET = (113, 87, 133)
OPEN_BLUE = (64, 108, 126)


class GuardianProjectile(PaperProjectile):
    """Chapter-specific ink geometry retaining the real dash-return API."""

    def draw(self, surface, camera):
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        colors = {"brass_spur": BRASS, "orbit_ring": ORBIT,
                  "carbon_slip": CARBON, "moth_dust": VIOLET}
        color = colors.get(self.kind, INK) if self.damage_enabled else (158, 155, 148)
        if self.kind == "brass_spur":
            points = []
            for index in range(16):
                angle = self.life * 7 + index * math.pi / 8
                radius = self.radius if index % 2 == 0 else self.radius * .58
                points.append((x + math.cos(angle) * radius,
                               y + math.sin(angle) * radius))
            pygame.draw.polygon(surface, color, points, 2)
            pygame.draw.circle(surface, color, (x, y), 4, 2)
        elif self.kind == "orbit_ring":
            pygame.draw.circle(surface, PAPER, (x, y), self.radius)
            pygame.draw.circle(surface, color, (x, y), self.radius, 3)
            pygame.draw.ellipse(surface, color,
                                (x-self.radius-5, y-5, self.radius*2+10, 10), 2)
            pygame.draw.circle(surface, (219, 178, 88), (x+5, y-4), 3)
        elif self.kind == "carbon_slip":
            direction = 1 if self.vx >= 0 else -1
            points = [(x-direction*12, y-7), (x+direction*12, y-2),
                      (x+direction*8, y+7), (x-direction*12, y+2)]
            pygame.draw.polygon(surface, PAPER, points)
            pygame.draw.lines(surface, color, True, points, 2)
            pygame.draw.line(surface, color, (x-direction*5, y-2),
                             (x+direction*5, y), 2)
        else:
            # Loose page dust forms a paper diamond, not another ink bullet.
            points = [(x, y-10), (x+9, y), (x, y+10), (x-9, y)]
            pygame.draw.polygon(surface, (187, 155, 187), points)
            pygame.draw.lines(surface, color, True, points, 2)
            pygame.draw.line(surface, color, (x-3, y-2), (x+3, y+2), 1)


class MarginGuardian(AdvancedEnemy):
    """Shared pacing only; silhouettes and attack geometry remain distinct."""

    base_hp = 10
    uses_gravity = False
    is_boss = True
    # (warning, active state, warning seconds, active seconds, short cue)
    patterns = ()
    accent = OPEN_BLUE
    opening_cue = "OPEN — HIT"
    contact_states = ()
    followup_patterns = (1, 2, 0)
    warning_sound = "enemy_telegraph_heavy"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.pattern_index = 0
        self.active_pattern = 0
        self.phase = 1
        self.phase_announced = False
        self.combo_remaining = 0
        self.cycle_pattern = 0
        self.window_hits = 0
        self.target_x = float(x)
        self.target_y = ground_y - 28
        self.attack_bounds = (x-240, x+240)
        self.attack_origin = (self.x, self.y)
        self.shot_vectors = ()
        self.strike_used = False
        self._set_state("idle", .65)

    def _is_vulnerable(self):
        return self.state == "recover" and self.window_hits < 2

    def opening_status(self):
        if self.dead or self.state != "recover" or self.state_time <= 0:
            return None
        return (max(0, 2-self.window_hits), 2,
                max(0, min(1, self.state_time/self.state_duration)))

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        # A single cannon shell cannot erase a whole mini boss. Heavy tools
        # retain a real advantage, while every drawing must expose its second
        # draft; the two visible punish marks remain the shared hit budget.
        heavy = bool({"heavy", "finisher", "eraser", "marker", "maul_finisher"} & set(tags))
        amount = min(float(amount), 1.4 if heavy else 1.0)
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
            self.vx *= .25
            if not self.dead and self.hp <= self.max_hp*.5:
                self.phase = 2
        return dealt

    def _begin_pattern(self, ctx, bounds, follow_up=False):
        self.attack_bounds = tuple(bounds)
        self.x = max(bounds[0]+self.radius, min(bounds[1]-self.radius, self.x))
        self.vx = self.vy = 0
        self.y = self.ground_y
        self.target_x = max(bounds[0]+56, min(bounds[1]-56, ctx.player.center_x))
        self.target_y = ctx.player.rect.centery
        self.facing = 1 if self.target_x >= self.x else -1
        self.attack_origin = (self.x, self.y)
        if follow_up:
            self.active_pattern = self.followup_patterns[self.cycle_pattern]
        else:
            self.active_pattern = self.pattern_index % 3
            self.cycle_pattern = self.active_pattern
            self.pattern_index += 1
            self.combo_remaining = 1 if self.phase == 2 else 0
            if self.phase == 2 and not self.phase_announced:
                self.phase_announced = True
                ctx.level.toast = "SECOND DRAFT"
                ctx.level.toast_time = 2.0
        self.strike_used = False
        self.shot_vectors = ()
        self._prepare_pattern()
        warning, _, duration, _, _ = self.patterns[self.active_pattern]
        self._set_state(warning, max(.90, duration*.90) if self.phase == 2 else duration)
        ctx.sounds.play(self.warning_sound)

    def _prepare_pattern(self):
        pass

    def _open(self, ctx):
        self.projectiles.clear()
        self.y = self.ground_y
        self.vx = self.vy = 0
        self.window_hits = 0
        self._set_state("recover", 1.40 if self.phase == 2 else 1.65)
        ctx.sounds.play("boss_opening")

    def _strike_once(self, ctx, rects):
        if self.strike_used or self.attack_suppressed > 0:
            return
        self.strike_used = True
        if (any(rect.colliderect(ctx.player.rect) for rect in rects)
                and ctx.player.hurt(self.target_x)):
            ctx.sounds.play("ink")
            ctx.camera.kick(3.5, .13)
            _player_hit_feedback(ctx, self.target_x)

    def _fan(self, origin, speed, angles, kind):
        del kind
        # Distant marks must be reached before the clean recovery clears ink.
        # A nearby fan retains its gentler authored speed.
        active_duration = self.patterns[self.active_pattern][3]
        distance = math.hypot(self.target_x-origin[0], self.target_y-origin[1])
        speed = max(speed, distance/max(.5, active_duration-.3))
        angle = math.atan2(self.target_y-origin[1], self.target_x-origin[0])
        self.shot_vectors = tuple((math.cos(angle+offset)*speed,
                                   math.sin(angle+offset)*speed) for offset in angles)

    def _shoot(self, origin, kind, radius=9, life=2.0):
        for vx, vy in self.shot_vectors:
            self.projectiles.append(GuardianProjectile(
                origin[0], origin[1], vx, vy, kind, life=life,
                radius=radius, gravity=0, terrain_collision=False))

    def _start_attack(self, ctx):
        pass

    def _animate_attack(self, dt, ctx):
        pass

    def _animate_warning(self):
        pass

    def _think(self, dt, ctx, bounds):
        if self.state == "idle":
            if self.state_time <= 0:
                self._begin_pattern(ctx, bounds)
            return
        if self.state == "recover":
            if self.state_time <= 0:
                self._set_state("idle", .22 if self.phase == 2 else .28)
            return
        warning, active, _, duration, _ = self.patterns[self.active_pattern]
        if self.state == warning:
            self._animate_warning()
            if self.state_time <= 0:
                self._set_state(active, duration)
                self.attack_origin = (self.x, self.y)
                self._start_attack(ctx)
            return
        if self.state == active:
            self._animate_attack(dt, ctx)
            if self.state_time <= 0:
                if self.combo_remaining:
                    # The first ink clears before the next target is marked.
                    # Nothing homes during a combination: the next warning
                    # commits once and supplies a full dodge interval.
                    self.combo_remaining -= 1
                    self.projectiles.clear()
                    self._begin_pattern(ctx, bounds, follow_up=True)
                else:
                    self._open(ctx)

    def _world_rect(self, center_x, width, height):
        return pygame.Rect(round(center_x-width/2), round(self.ground_y-height),
                           width, height)

    def _draw_rect(self, surface, camera, rect, active=False):
        rect = rect.move(round(-camera.x+camera.offset_x), round(camera.offset_y))
        if active:
            wash = pygame.Surface(rect.size, pygame.SRCALPHA)
            wash.fill((*self.accent, 58))
            surface.blit(wash, rect.topleft)
        pygame.draw.rect(surface, self.accent if active else RED_RULE, rect, 2)
        pygame.draw.line(surface, RED_RULE, (rect.left+4, rect.bottom-4),
                         (rect.right-4, rect.bottom-4), 2)

    def _draw_lane(self, surface, camera, start, end):
        a = (camera.screen_x(start[0]), round(start[1]+camera.offset_y))
        b = (camera.screen_x(end[0]), round(end[1]+camera.offset_y))
        _dashed_line(surface, RED_RULE, a, b, 2, 8, 6)
        pygame.draw.circle(surface, RED_RULE, b, 6, 2)

    def _draw_fan(self, surface, camera, origin):
        for vx, vy in self.shot_vectors:
            length = max(.001, math.hypot(vx, vy))
            self._draw_lane(surface, camera, origin,
                            (origin[0]+vx/length*235, origin[1]+vy/length*235))

    def _draw_attacks(self, surface, camera):
        pass

    def _draw_body(self, surface, camera):
        pass

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        self._draw_attacks(surface, camera)
        self._draw_body(surface, camera)
        if self.phase == 2:
            center = (camera.screen_x(self.x), round(self.y-self.height*.5+camera.offset_y))
            for side in (-1, 1):
                pygame.draw.line(surface, RED_RULE,
                    (center[0]+side*(self.width*.5+7), center[1]-12),
                    (center[0]+side*(self.width*.5+13), center[1]+10), 3)
        warning, _, _, _, cue = self.patterns[self.active_pattern]
        if self.state == warning:
            self._draw_telegraph(surface, camera, renderer, translate(cue),
                                 label_offset=self.height+38)
        elif self.state == "recover":
            center = (camera.screen_x(self.x), round(self.y-self.height*.52+camera.offset_y))
            self._draw_opening(surface, center, 26)
            if self.vulnerable:
                label = renderer.font_small.render(translate(self.opening_cue), True, OPEN_BLUE)
                sx = max(12, min(surface.get_width()-label.get_width()-12,
                                 center[0]-label.get_width()//2))
                surface.blit(label, (sx, max(12, round(self.y-self.height-35+camera.offset_y))))
        _health_scratches(surface, camera, self, self.height+18)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class BrassTumbleweedGuardian(MarginGuardian):
    """A bramble wheel with a sheriff star: roll, lasso, then a low spur."""

    kind = "brass_tumbleweed"
    width, height, radius = 70, 70, 35
    accent = BRASS
    contact_states = ("tumble_roll",)
    opening_cue = "LOOSE SPOKES — HIT"
    patterns = (("tumble_warn", "tumble_roll", 1.05, .8, "ROLL — JUMP"),
                ("lasso_warn", "lasso_snap", 1.1, .26, "LEAVE THE LASSO"),
                ("spur_warn", "spur_shot", 1.0, 1.7, "JUMP THE SPUR"))

    @property
    def lasso_rect(self):
        return self._world_rect(self.target_x, 92, 76)

    def _prepare_pattern(self):
        if self.active_pattern == 2:
            speed = max(280, abs(self.target_x-self.x-self.facing*42)/1.4)
            self.shot_vectors = ((self.facing*speed, 0),)

    def _start_attack(self, ctx):
        if self.state == "spur_shot":
            self._shoot((self.x+self.facing*42, self.ground_y-18), "brass_spur", 14)
            ctx.sounds.play("enemy_attack_ranged")
        elif self.state == "tumble_roll":
            ctx.sounds.play("enemy_attack_charge")

    def _animate_attack(self, dt, ctx):
        if self.state == "tumble_roll":
            self.x = self.attack_origin[0]+(self.target_x-self.attack_origin[0])*self.pose_progress
        elif self.state == "lasso_snap":
            self._strike_once(ctx, (self.lasso_rect,))

    def _draw_attacks(self, surface, camera):
        floor = self.ground_y
        if self.state in {"tumble_warn", "tumble_roll"}:
            self._draw_lane(surface, camera, (self.attack_origin[0], floor-9),
                            (self.target_x, floor-9))
        elif self.state in {"lasso_warn", "lasso_snap"}:
            self._draw_rect(surface, camera, self.lasso_rect, self.state == "lasso_snap")
            self._draw_lane(surface, camera, (self.x, self.y-42),
                            (self.target_x, floor-38))
            if self.state == "lasso_snap":
                pygame.draw.ellipse(surface, BRASS,
                    (camera.screen_x(self.target_x)-46, round(floor-72+camera.offset_y), 92, 68), 4)
        elif self.state == "spur_warn":
            edge = self.attack_bounds[1]-18 if self.facing > 0 else self.attack_bounds[0]+18
            self._draw_lane(surface, camera, (self.x+self.facing*42, floor-18), (edge, floor-18))

    def _draw_body(self, surface, camera):
        x, bottom = camera.screen_x(self.x), round(self.y+camera.offset_y)
        y, color = bottom-35, self._base_color()
        pygame.draw.circle(surface, (219, 191, 129), (x, y), 31)
        phase = self.time*2 if self.state == "tumble_roll" else .2
        for index in range(7):
            angle = phase+index*math.tau/7
            dx, dy = math.cos(angle), math.sin(angle)
            a, b = (x+dx*11, y+dy*11), (x+dx*35, y+dy*35)
            jitter_line(surface, color, a, b, 2, self.seed+index, 1, .8)
            pygame.draw.line(surface, BRASS, b,
                             (b[0]-dy*8-dx*3, b[1]+dx*8-dy*3), 2)
        pygame.draw.circle(surface, color, (x, y), 31, 2)
        pygame.draw.arc(surface, BRASS, (x-25, y-29, 45, 58), -.7, 3.8, 2)
        pygame.draw.arc(surface, color, (x-33, y-21, 66, 42), .3, 5.2, 2)
        # A stamped sheriff star stays upright even while the bramble rolls.
        star = []
        for index in range(10):
            angle = -math.pi/2+index*math.pi/5
            radius = 16 if index % 2 == 0 else 7
            star.append((x+math.cos(angle)*radius, y+math.sin(angle)*radius))
        pygame.draw.polygon(surface, PAPER, star)
        pygame.draw.lines(surface, color, True, star, 2)
        pygame.draw.line(surface, color, (x-5, y-3), (x+5, y-3), 2)
        pygame.draw.polygon(surface, (169, 75, 59),
            [(x-13, y+18), (x+15, y+16), (x+8, y+27), (x+21, y+31), (x+3, y+30)])


class OrbitCrabGuardian(MarginGuardian):
    """A ring-backed lunar crab: satellite wheel, claw, marked crater drop."""

    kind = "orbit_crab"
    width, height, radius = 82, 74, 41
    accent = ORBIT
    contact_states = ("crater_fall",)
    followup_patterns = (2, 0, 1)
    opening_cue = "CRACKED SHELL — HIT"
    patterns = (("satellite_warn", "satellite_sweep", 1.05, 1.7, "JUMP THE ORBIT"),
                ("claw_warn", "claw_snap", 1.0, .28, "BACK FROM THE CLAW"),
                ("crater_warn", "crater_fall", 1.1, .65, "LEAVE THE CRATER"))

    @property
    def claw_rect(self):
        return self._world_rect(self.x+self.facing*68, 112, 66)

    def _prepare_pattern(self):
        if self.active_pattern == 0:
            speed = max(265, abs(self.target_x-self.x-self.facing*53)/1.4)
            self.shot_vectors = ((self.facing*speed, 0),)

    def _animate_warning(self):
        if self.state == "crater_warn":
            self.y = self.ground_y-95*self.pose_progress

    def _start_attack(self, ctx):
        if self.state == "satellite_sweep":
            self._shoot((self.x+self.facing*53, self.ground_y-21), "orbit_ring", 17)
            ctx.sounds.play("enemy_attack_ranged")
        elif self.state == "crater_fall":
            ctx.sounds.play("enemy_attack_charge")

    def _animate_attack(self, dt, ctx):
        if self.state == "claw_snap":
            self._strike_once(ctx, (self.claw_rect,))
        elif self.state == "crater_fall":
            p = self.pose_progress
            self.x = self.attack_origin[0]+(self.target_x-self.attack_origin[0])*p
            self.y = self.attack_origin[1]+(self.ground_y-self.attack_origin[1])*p*p

    def _draw_attacks(self, surface, camera):
        if self.state == "satellite_warn":
            edge = self.attack_bounds[1]-18 if self.facing > 0 else self.attack_bounds[0]+18
            self._draw_lane(surface, camera, (self.x+self.facing*53, self.ground_y-21),
                            (edge, self.ground_y-21))
        elif self.state in {"claw_warn", "claw_snap"}:
            self._draw_rect(surface, camera, self.claw_rect, self.state == "claw_snap")
        elif self.state in {"crater_warn", "crater_fall"}:
            self._draw_lane(surface, camera, (self.attack_origin[0], self.ground_y-152),
                            (self.target_x, self.ground_y-18))
            pygame.draw.ellipse(surface, RED_RULE,
                (camera.screen_x(self.target_x)-42, round(self.ground_y-10+camera.offset_y), 84, 15), 2)

    def _draw_body(self, surface, camera):
        x, bottom = camera.screen_x(self.x), round(self.y+camera.offset_y)
        y, color = bottom-38, self._base_color()
        pygame.draw.ellipse(surface, (175, 199, 196), (x-28, y-25, 56, 48))
        pygame.draw.ellipse(surface, color, (x-28, y-25, 56, 48), 2)
        pygame.draw.ellipse(surface, ORBIT, (x-40, y-10, 80, 25), 3)
        pygame.draw.circle(surface, PAPER, (x+28, y-1), 6)
        pygame.draw.circle(surface, color, (x+28, y-1), 6, 2)
        for side in (-1, 1):
            for index in range(2):
                yy = y+13+index*8
                pygame.draw.lines(surface, color, False,
                    [(x+side*21, yy), (x+side*(36+index*3), yy+6),
                     (x+side*(31+index*6), bottom-2)], 3)
            extension = 23 if self.state == "claw_snap" and side == self.facing else 0
            cx, cy = x+side*(48+extension), y-8
            pygame.draw.line(surface, color, (x+side*24, y), (cx, cy+8), 3)
            pygame.draw.arc(surface, color, (cx-15, cy-14, 30, 32),
                            -.4 if side < 0 else 2.2, 3.5 if side < 0 else 6.2, 4)
            pygame.draw.line(surface, color, (cx-side*10, cy-9), (cx+side*2, cy), 2)
            pygame.draw.line(surface, color, (x+side*12, y-21), (x+side*14, y-33), 2)
            pygame.draw.circle(surface, color, (x+side*14, y-33), 4, 2)
        pygame.draw.arc(surface, ORBIT, (x-10, y-6, 20, 16), .2, 2.9, 2)
        if self.state == "recover":
            pygame.draw.lines(surface, PAPER, False,
                [(x-1, y-24), (x+5, y-13), (x-4, y-4), (x+3, y+5)], 4)
            pygame.draw.lines(surface, color, False,
                [(x-1, y-24), (x+5, y-13), (x-4, y-4), (x+3, y+5)], 1)


class CarbonHoundGuardian(MarginGuardian):
    """A carbon-copy tracking hound: straight rush, stamp, fixed receipt fan."""

    kind = "carbon_hound"
    width, height, radius = 86, 67, 43
    accent = CARBON
    contact_states = ("carbon_rush",)
    opening_cue = "TORN COLLAR — HIT"
    patterns = (("rush_warn", "carbon_rush", 1.05, .82, "RUSH — JUMP"),
                ("stamp_warn", "stamp_press", 1.1, .3, "LEAVE THE STAMP"),
                ("receipt_warn", "receipt_burst", 1.1, 1.6, "DODGE THE COPIES"))

    @property
    def stamp_rect(self):
        return self._world_rect(self.target_x, 88, 74)

    @property
    def shot_origin(self):
        return (self.x+self.facing*48, self.ground_y-43)

    def _prepare_pattern(self):
        if self.active_pattern == 0:
            # The hound passes through the marked feet, never turns after them.
            self.target_x = max(self.attack_bounds[0]+self.radius,
                min(self.attack_bounds[1]-self.radius, self.target_x+self.facing*72))
        elif self.active_pattern == 2:
            self._fan(self.shot_origin, 235, (-.2, 0, .2), "carbon_slip")

    def _start_attack(self, ctx):
        if self.state == "receipt_burst":
            self._shoot(self.shot_origin, "carbon_slip", 8)
            ctx.sounds.play("enemy_attack_ranged")
        elif self.state == "carbon_rush":
            ctx.sounds.play("enemy_attack_charge")

    def _animate_attack(self, dt, ctx):
        if self.state == "carbon_rush":
            p = self.pose_progress
            self.x = self.attack_origin[0]+(self.target_x-self.attack_origin[0])*p
        elif self.state == "stamp_press":
            self._strike_once(ctx, (self.stamp_rect,))

    def _draw_attacks(self, surface, camera):
        if self.state in {"rush_warn", "carbon_rush"}:
            self._draw_lane(surface, camera, (self.attack_origin[0], self.ground_y-12),
                            (self.target_x, self.ground_y-12))
        elif self.state in {"stamp_warn", "stamp_press"}:
            self._draw_rect(surface, camera, self.stamp_rect, self.state == "stamp_press")
            if self.state == "stamp_press":
                tx, gy = camera.screen_x(self.target_x), round(self.ground_y+camera.offset_y)
                pygame.draw.line(surface, CARBON, (tx, gy-95), (tx, gy-68), 8)
                pygame.draw.rect(surface, CARBON, (tx-38, gy-70, 76, 20), 4)
        elif self.state == "receipt_warn":
            self._draw_fan(surface, camera, self.shot_origin)

    def _draw_body(self, surface, camera):
        x, bottom = camera.screen_x(self.x), round(self.y+camera.offset_y)
        direction, color = self.facing, self._base_color()
        def point(dx, dy):
            return (x+direction*dx, bottom+dy)
        # Long folded muzzle, triangular ears, back carbon sheet and tie.
        body = [point(-35, -42), point(-11, -56), point(21, -51),
                point(29, -35), point(36, -21), point(-30, -20)]
        pygame.draw.polygon(surface, (131, 130, 137), body)
        pygame.draw.lines(surface, color, True, body, 3)
        pygame.draw.polygon(surface, (190, 186, 190),
            [point(-26, -43), point(-9, -54), point(6, -41), point(-10, -24)])
        pygame.draw.line(surface, color, point(-9, -54), point(-10, -24), 2)
        head = [point(15, -54), point(22, -67), point(33, -48),
                point(48, -43), point(46, -31), point(24, -29)]
        pygame.draw.polygon(surface, PAPER, head)
        pygame.draw.lines(surface, color, True, head, 3)
        pygame.draw.line(surface, color, point(27, -47), point(35, -47), 3)
        pygame.draw.circle(surface, color, point(47, -40), 4)
        for dx in (-23, -7, 18, 29):
            bend = 7 if self.state == "carbon_rush" else 0
            pygame.draw.lines(surface, color, False,
                [point(dx, -22), point(dx-bend, -9), point(dx+9, -3)], 3)
        pygame.draw.lines(surface, color, False,
            [point(-33, -33), point(-47, -48), point(-42, -59)], 3)
        tie = [point(20, -29), point(27, -30), point(32, -12), point(26, -7), point(23, -17)]
        pygame.draw.polygon(surface, (163, 73, 68), tie)
        if self.state == "recover":
            pygame.draw.line(surface, PAPER, point(19, -28), point(27, -25), 4)


class DraftMothGuardian(MarginGuardian):
    """A moth made from rejected pages: twin margins, ink dust, wing clap.

The twin page cuts leave a clearly marked safe gap where the player stood.
Its dust fan commits to the player's old position; its clap only reaches the
visible wing outline.  These are different choices from another dive boss.
"""

    kind = "draft_moth"
    width, height, radius = 78, 86, 39
    accent = VIOLET
    opening_cue = "FOLDED WINGS — HIT"
    patterns = (("margin_warn", "margin_cut", 1.1, .28, "BETWEEN THE PAGES"),
                ("dust_warn", "dust_fan", 1.15, 1.75, "DODGE THE INK DUST"),
                ("wing_warn", "wing_clap", 1.05, .3, "OUTSIDE THE WINGS"))

    @property
    def page_rects(self):
        return tuple(self._world_rect(max(self.attack_bounds[0]+19,
                         min(self.attack_bounds[1]-19, self.target_x+side*70)), 38, 122)
                     for side in (-1, 1))

    @property
    def wing_rect(self):
        return self._world_rect(self.x, 144, 78)

    @property
    def shot_origin(self):
        return (self.x+self.facing*15, self.ground_y-62)

    def _prepare_pattern(self):
        if self.active_pattern == 1:
            self._fan(self.shot_origin, 190, (-.3, 0, .3), "moth_dust")

    def _start_attack(self, ctx):
        if self.state == "dust_fan":
            self._shoot(self.shot_origin, "moth_dust", 9, 2.4)
            ctx.sounds.play("enemy_attack_ranged")

    def _animate_attack(self, dt, ctx):
        if self.state == "margin_cut":
            self._strike_once(ctx, self.page_rects)
        elif self.state == "wing_clap":
            self._strike_once(ctx, (self.wing_rect,))

    def _draw_attacks(self, surface, camera):
        if self.state in {"margin_warn", "margin_cut"}:
            for rect in self.page_rects:
                self._draw_rect(surface, camera, rect, self.state == "margin_cut")
            if self.state == "margin_warn":
                tx, gy = camera.screen_x(self.target_x), round(self.ground_y+camera.offset_y)
                pygame.draw.line(surface, OPEN_BLUE, (tx-32, gy-5), (tx+32, gy-5), 3)
        elif self.state == "dust_warn":
            self._draw_fan(surface, camera, self.shot_origin)
        elif self.state in {"wing_warn", "wing_clap"}:
            self._draw_rect(surface, camera, self.wing_rect, self.state == "wing_clap")

    def _draw_body(self, surface, camera):
        x, bottom = camera.screen_x(self.x), round(self.y+camera.offset_y)
        y, color = bottom-47, self._base_color()
        folded = self.state == "recover"
        spread = 33 if folded else 68
        flutter = round(math.sin(self.time*4)*3) if not folded else 0
        for side in (-1, 1):
            wing = [(x+side*5, y-4), (x+side*spread, y-37+flutter),
                    (x+side*(spread-7), y+17), (x+side*31, y+36), (x+side*5, y+14)]
            pygame.draw.polygon(surface, (211, 192, 203) if side < 0 else (228, 215, 193), wing)
            pygame.draw.lines(surface, color, True, wing, 2)
            jitter_line(surface, color, wing[0], wing[2], 1, self.seed+side, 1, .5)
            for index in range(3):
                yy = y-7+index*10
                pygame.draw.line(surface, VIOLET,
                    (x+side*19, yy), (x+side*(spread-15), yy-8), 1)
            pygame.draw.lines(surface, (161, 103, 102), False,
                [(x+side*25, y+7), (x+side*37, y+15), (x+side*24, y+23)], 2)
        pygame.draw.ellipse(surface, (125, 112, 127), (x-8, y-16, 16, 45))
        pygame.draw.ellipse(surface, color, (x-8, y-16, 16, 45), 2)
        pygame.draw.circle(surface, PAPER, (x, y-20), 10)
        pygame.draw.circle(surface, color, (x, y-20), 10, 2)
        for side in (-1, 1):
            pygame.draw.lines(surface, color, False,
                [(x+side*4, y-28), (x+side*12, y-39), (x+side*22, y-41)], 2)
            pygame.draw.circle(surface, VIOLET, (x+side*22, y-41), 3)
            pygame.draw.circle(surface, color, (x+side*4, y-21), 2)


GUARDIAN_CLASSES = {
    cls.kind: cls for cls in (BrassTumbleweedGuardian, OrbitCrabGuardian,
                             CarbonHoundGuardian, DraftMothGuardian)
}
