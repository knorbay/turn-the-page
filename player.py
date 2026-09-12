from __future__ import annotations

import math
import pygame

from settings import GRAVITY, INK, MAX_FALL
from page_arsenal import draw_weapon, profile_for


class Player:
    WIDTH = 24
    HEIGHT = 48

    def __init__(self, x=180, y=500):
        self.x = float(x)
        self.y = float(y)
        self.vx = 0.0
        self.vy = 0.0
        self.on_ground = False
        self.coyote = 0.0
        self.jump_buffer = 0.0
        self.facing = 1
        self.anim_time = 0.0
        self.land_squash = 0.0
        self.was_grounded = False
        self.in_stain = False
        self.material = "paper"
        self.control_locks: set[str] = set()
        self.draw_amount = 1.0
        self.redraw_alpha = 1.0
        self.look_target: tuple[float, float] | None = None
        self.max_health = 3
        self.health = self.max_health
        self.health_restore_flash = 0.0
        self.attack_timer = 0.0
        self.attack_cooldown = 0.0
        self.attack_serial = 0
        self.invulnerable = 0.0
        self.hurt_flash = 0.0
        self.dash_timer = 0.0
        self.dash_cooldown = 0.0
        self.dash_direction = 1
        self.return_used = False
        self.current_weapon = "pencil_blade"
        self.aim_angle = 0.0
        self.weapon_recoil = 0.0
        self.combat_swing = None
        self.redraw_variant = "clean"
        self.page_style = "plain"
        # Animation follows distance travelled; collision and attack timing
        # remain owned by the controller and weapon system.
        self.stride_phase = 0.0
        self.motion_speed = 0.0
        self.dash_impressions = []
        self._impression_clock = 0.0
        self._motion_last_position = (self.x, self.y)

    @property
    def locked(self):
        return bool(self.control_locks)

    @locked.setter
    def locked(self, value):
        if value:
            self.control_locks.add("legacy")
        else:
            self.control_locks.discard("legacy")

    def acquire_lock(self, owner):
        self.control_locks.add(str(owner))

    def release_lock(self, owner):
        self.control_locks.discard(str(owner))

    def release_all_locks(self):
        self.control_locks.clear()

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.WIDTH, self.HEIGHT)

    @property
    def center_x(self):
        return self.x + self.WIDTH / 2

    def queue_jump(self):
        self.jump_buffer = .12

    def release_jump(self):
        # Variable height without making tap-jumps feel anaemic.
        if self.vy < -245:
            self.vy *= .48

    def attack(self):
        if self.attack_cooldown <= 0 and not self.locked and self.health > 0:
            self.attack_serial += 1
            self.attack_timer = .20
            self.attack_cooldown = .32
            return True
        return False

    def start_dash(self, direction=0, particles=None):
        if self.dash_cooldown > 0 or self.locked or self.health <= 0:
            return False
        self.dash_direction = int(direction) or self.facing or 1
        self.facing = 1 if self.dash_direction > 0 else -1
        self.dash_timer = .16
        self.return_used = False
        self.dash_cooldown = .68 - getattr(self, "sketch_dash_recovery", 0.0)
        self.invulnerable = max(self.invulnerable, .20)
        self.vx = self.dash_direction * 690
        self.vy *= .15
        if particles is not None:
            particles.paper_puff(self.center_x, self.rect.bottom, 10)
        return True

    @property
    def dashing(self):
        return self.dash_timer > 0

    @property
    def dash_ready(self):
        return self.dash_cooldown <= 0

    def set_weapon_pose(self, weapon_id, aim_angle=0.0, recoil=0.0):
        self.current_weapon = str(weapon_id)
        self.aim_angle = float(aim_angle)
        self.weapon_recoil = max(self.weapon_recoil, float(recoil))

    def redraw_tip(self):
        """World-space endpoint of the currently active redraw stroke."""
        p = max(0.0, min(1.0, self.draw_amount))
        pose = self._body_pose()
        for start, end, begin, finish, _ in reversed(self._redraw_strokes(pose)):
            if p >= begin:
                t = min(1.0, (p - begin) / (finish - begin))
                return (start[0] + (end[0] - start[0]) * t,
                        start[1] + (end[1] - start[1]) * t)
        if p < .16:
            angle = -math.pi / 2 + math.tau * (p / .20)
            return (pose["head"][0] + math.cos(angle) * pose["radius"],
                    pose["head"][1] - math.sin(angle) * pose["radius"])

    def _redraw_strokes(self, pose):
        """The Artist and the visible body follow the same articulated lines."""
        shoulder, hip = pose["shoulder"], pose["hip"]
        arm = (shoulder[0], shoulder[1] + 7)
        swing = -math.sin(self.stride_phase) * 7 * self.motion_speed
        left, right = (1.42, .78) if self.redraw_variant == "long_arm" else (1, 1)
        strokes = [
            (shoulder, hip, .16, .36, 3),
            (arm, (arm[0] + swing*left, arm[1] + 14*left), .32, .52, 2),
            (arm, (arm[0] - swing*right, arm[1] + 14*right), .46, .66, 2),
        ]
        for index, (knee, foot) in enumerate(pose["legs"]):
            begin, finish = (.60, .82) if index == 0 else (.76, 1.0)
            middle = (begin + finish) / 2
            strokes.extend(((hip, knee, begin, middle, 3),
                            (knee, foot, middle, finish, 3)))
        return sorted(strokes, key=lambda stroke: stroke[2])

    @property
    def attack_active(self):
        return .055 < self.attack_timer < .17

    @property
    def attack_rect(self):
        if self.facing > 0:
            return pygame.Rect(self.rect.right - 2, self.rect.y + 8, 48, 34)
        return pygame.Rect(self.rect.left - 46, self.rect.y + 8, 48, 34)

    def hurt(self, source_x):
        if self.health <= 0 or self.invulnerable > 0 or self.locked or self.dashing:
            return False
        self.health -= 1
        self.health_restore_flash = 0.0
        self.invulnerable = 1.05
        # The red pencil flicker lasts for the full invulnerability window so
        # the player can read exactly when another hit becomes possible.
        self.hurt_flash = self.invulnerable
        direction = -1 if source_x > self.center_x else 1
        self.vx = direction * 265
        self.vy = -285
        return True

    def begin_fight(self):
        """Every new arena (and named boss) starts with three intact marks.

        A lethal hit must finish its redraw; crossing a trigger in that frame
        cannot silently revive the figure.
        """
        if self.health <= 0:
            return False
        changed = self.health < self.max_health
        self.health = self.max_health
        self.health_restore_flash = 1.6
        self.hurt_flash = 0.0
        return changed

    def update(self, dt, move_axis, world, particles):
        motion_start = (self.x, self.y)
        discontinuity = math.dist(motion_start, self._motion_last_position) > 80
        self.anim_time += dt
        self.attack_timer = max(0.0, self.attack_timer - dt)
        self.attack_cooldown = max(0.0, self.attack_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.health_restore_flash = max(0.0, self.health_restore_flash - dt)
        self.dash_timer = max(0.0, self.dash_timer - dt)
        self.dash_cooldown = max(0.0, self.dash_cooldown - dt)
        self.weapon_recoil = max(0.0, self.weapon_recoil - dt * 7)
        self.jump_buffer = max(0.0, self.jump_buffer - dt)
        self.coyote = (.11 + getattr(self, "sketch_coyote_bonus", 0.0)
                       if self.on_ground else max(0.0, self.coyote - dt))
        zones = world.material_at(self.rect)
        kinds = {z.kind for z in zones}
        self.in_stain = any(k.startswith("coffee") for k in kinds) or world.in_coffee(self.rect)
        if "coffee_sticky" in kinds or "ink_sticky" in kinds:
            self.material = "sticky"
        elif "coffee_slippery" in kinds:
            self.material = "slippery"
        elif "margin_gravity" in kinds or "dust_updraft" in kinds:
            self.material = "margin"
        else:
            self.material = "paper"

        if self.locked:
            move_axis = 0
        if move_axis:
            self.facing = 1 if move_axis > 0 else -1

        max_speed = 285.0
        acceleration = 2200.0 if self.on_ground else 1250.0
        if not self.on_ground:
            acceleration *= getattr(self, "sketch_air_control", 1.0)
        deceleration = 2600.0
        if self.material == "slippery":
            max_speed, acceleration, deceleration = 315.0, 1450.0, 420.0
        elif self.material == "sticky":
            max_speed, acceleration, deceleration = 172.0, 980.0, 1750.0
        if self.dashing:
            self.vx = self.dash_direction * 690
        else:
            target = move_axis * max_speed
            rate = acceleration if move_axis else deceleration
            self.vx = self._approach(self.vx, target, rate * dt)

        if self.jump_buffer > 0 and self.coyote > 0 and not self.locked:
            jump_speed = 650.0 if self.material != "sticky" else 535.0
            self.vy = -jump_speed
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buffer = 0.0
            self.land_squash = -.12
            particles.paper_puff(self.center_x, self.y + self.HEIGHT, 5)

        gravity_scale = .12 if self.dashing else .58 if self.material == "margin" else 1.0
        self.vy = min(MAX_FALL, self.vy + GRAVITY * gravity_scale * dt)
        self._move_x(dt, world)
        self._move_y(dt, world)
        if self.on_ground and not self.was_grounded:
            self.land_squash = .18
            particles.paper_puff(self.center_x, self.y + self.HEIGHT, 7)
        self.was_grounded = self.on_ground
        self.land_squash = self._approach(self.land_squash, 0.0, dt * 1.5)
        self._update_motion(dt, motion_start, discontinuity)

    def _update_motion(self, dt, previous, discontinuity=False):
        """Bounded, world-space pencil impressions never survive a redraw."""
        dx = self.x - previous[0]
        self._motion_last_position = (self.x, self.y)
        self.motion_speed = self._approach(self.motion_speed,
                                           min(1.0, abs(self.vx) / 285), dt * 8)
        if self.on_ground and not self.dashing:
            self.stride_phase = (self.stride_phase + abs(dx) * math.tau / 72) % math.tau
        if discontinuity or self.draw_amount < 1 or self.redraw_alpha < .8 \
                or self.health <= 0 or self.locked:
            self.dash_impressions.clear()
            self._impression_clock = 0.0
            return
        self.dash_impressions = [(pose, life - dt) for pose, life in self.dash_impressions
                                 if life > dt]
        self._impression_clock = max(0.0, self._impression_clock - dt)
        if self.dashing and abs(dx) >= 4 and self._impression_clock <= 0:
            self.dash_impressions.append((self._body_pose(), .15))
            self.dash_impressions = self.dash_impressions[-5:]
            self._impression_clock = .027

    def _body_pose(self):
        """An articulated ink skeleton; all positions are visual/world-space."""
        cx, bottom = self.center_x, self.y + self.HEIGHT
        facing, speed = self.facing, self.motion_speed
        squash = self.land_squash
        stretch = 1.0 - squash
        leg_scale = 1.22 if self.redraw_variant == "long_leg" else .92 if self.redraw_variant == "rushed" else 1.0
        hip_y = bottom - 16 * stretch * leg_scale
        shoulder_y = hip_y - (22 if self.redraw_variant == "rushed" else 24) * stretch
        hip_x = cx
        lean = facing * speed * 4 if self.on_ground else max(-4, min(4, self.vx / 70))
        legs = []
        if self.on_ground:
            bob = abs(math.sin(self.stride_phase)) * speed * 1.8
            hip_y -= bob
            shoulder_y -= bob
            for offset in (0, math.pi):
                cycle = ((self.stride_phase + offset) % math.tau) / math.tau
                if cycle < .5:
                    # During stance the sole travels backwards at ground speed.
                    foot_x, lift = 18 - cycle * 72, 0
                else:
                    t = (cycle - .5) * 2
                    foot_x = -18 + 36 * (t*t*(3-2*t))
                    lift = math.sin(t * math.pi) * 10
                rest = -7 if offset == 0 else 7
                foot_x = cx + facing * (rest * (1-speed) + foot_x * speed)
                foot_y = bottom - lift * speed
                knee = (cx + (foot_x-cx)*.42 + facing*3*speed,
                        hip_y + (foot_y-hip_y)*.50 - lift*speed*.30)
                legs.append((knee, (foot_x, foot_y)))
        else:
            # Rise folds one knee, the apex opens the silhouette, and a fall
            # reaches a toe down before the landing compression takes over.
            rise = max(0.0, min(1.0, -self.vy / 450))
            fall = max(0.0, min(1.0, self.vy / 500))
            legs = [((cx + facing*(6 + rise*3), hip_y + 6 - rise*4),
                     (cx + facing*(9 + rise*3), bottom - 4 - rise*10)),
                    ((cx - facing*6, hip_y + 8),
                     (cx - facing*(8-fall*4), bottom - 5 + fall*5))]
            shoulder_y -= rise * 1.5

        if self.dashing and self.draw_amount >= 1:
            hip_y = bottom - 13
            shoulder_y = hip_y - 19
            lean = facing * 12
            legs = [((cx-facing*9, hip_y+3), (cx-facing*24, bottom-4)),
                    ((cx+facing*9, hip_y+6), (cx+facing*3, bottom-2))]
        elif self.combat_swing is not None and self.draw_amount >= 1:
            angle, _, power = self.combat_swing
            shape = profile_for(getattr(self, "arsenal_page", None), "pencil_blade").silhouette
            weight, crouch, stance = {
                "katana": (6, 2, 17), "bowie": (9, 4, 16),
                "field_knife": (11, 6, 18), "ion_blade": (4, -1, 20),
                "redraw_pencil": (5, 1, 13),
            }.get(shape, (5, 1, 15))
            force = max(0, power)
            lean = facing * (weight * power + 2)
            hip_x += facing * force * 2
            shoulder_y += crouch * force
            hip_y += max(0, crouch) * force * .5
            if shape == "katana":
                shoulder_y += math.sin(angle) * force * 2
            if self.on_ground:
                legs = [((cx+facing*8, hip_y+8), (cx+facing*stance, bottom)),
                        ((cx-facing*8, hip_y+7), (cx-facing*(stance-3), bottom))]

        shoulder = (hip_x + lean, shoulder_y)
        head_x = shoulder[0] + (4*facing if self.redraw_variant == "crooked_head" else
                                -2 if self.redraw_variant == "rushed" else 0)
        if self.dashing:
            head_x += facing * 3
        head = (head_x, shoulder_y - 9*stretch)
        return {"head": head, "radius": max(5, round(7*(1+squash*.65))),
                "shoulder": shoulder, "hip": (hip_x, hip_y), "legs": legs,
                "facing": facing}

    def _draw_dash_impressions(self, surface, camera):
        if self.draw_amount < 1 or self.redraw_alpha < .8 or self.locked or self.health <= 0:
            return
        def screen(point):
            return (round(camera.screen_x(point[0])), round(point[1]+camera.offset_y))
        for pose, life in self.dash_impressions:
            # Pale retraced pencil lines, with no fullscreen alpha surfaces.
            fade = 1 - min(1, life / .15)
            ink = (round(163+fade*62), round(158+fade*61), round(150+fade*61))
            head, shoulder, hip = pose["head"], pose["shoulder"], pose["hip"]
            pygame.draw.circle(surface, ink, screen(head), pose["radius"], 1)
            pygame.draw.line(surface, ink, screen(shoulder), screen(hip), 1)
            for knee, foot in pose["legs"]:
                pygame.draw.lines(surface, ink, False, [screen(hip), screen(knee), screen(foot)], 1)
            elbow = (shoulder[0]-pose["facing"]*11, shoulder[1]+10)
            hand = (elbow[0]-pose["facing"]*6, elbow[1]-3)
            pygame.draw.lines(surface, ink, False, [screen(shoulder), screen(elbow), screen(hand)], 1)

    @staticmethod
    def _approach(value, target, amount):
        if value < target:
            return min(target, value + amount)
        return max(target, value - amount)

    def _move_x(self, dt, world):
        distance = self.vx * dt
        # Dash speed can cross a thin arena/puzzle stroke in one 30 fps frame.
        # Small deterministic substeps retain the handmade AABB controller but
        # make every drawn gate physically trustworthy.
        steps = max(1, math.ceil(abs(distance) / 9.0))
        step = distance / steps
        for _ in range(steps):
            self.x += step
            rect = self.rect
            collided = False
            for platform, one_way in world.collision_entries():
                if one_way:
                    continue
                if rect.colliderect(platform):
                    # Ink strokes act as one-way floors near the feet. This prevents
                    # tiny rough/ramp segments from behaving like vertical brick walls.
                    if rect.bottom <= platform.top + 12:
                        continue
                    if step > 0:
                        self.x = platform.left - self.WIDTH
                    elif step < 0:
                        self.x = platform.right
                    self.vx = 0
                    collided = True
                    break
            if collided:
                break

    def _move_y(self, dt, world):
        previous_top = self.y
        previous_bottom = self.y + self.HEIGHT
        self.y += self.vy * dt
        self.on_ground = False
        rect = self.rect
        entries = sorted(world.collision_entries(), key=lambda item: item[0].top)
        for platform, one_way in entries:
            forgiving = platform.inflate(6, 0)
            if rect.right <= forgiving.left or rect.left >= forgiving.right:
                continue
            if self.vy >= 0 and previous_bottom <= platform.top + 7 and rect.bottom >= platform.top:
                self.y = platform.top - self.HEIGHT
                self.vy = 0
                self.on_ground = True
                rect = self.rect
                break
            elif not one_way and self.vy < 0 and previous_top >= platform.bottom-4 and rect.top <= platform.bottom:
                self.y = platform.bottom
                self.vy = 0
                rect = self.rect

    def draw(self, surface, camera):
        self._draw_dash_impressions(surface, camera)
        cx = camera.screen_x(self.center_x)
        pose = self._body_pose()
        def screen(point):
            return (camera.screen_x(point[0]), point[1]+camera.offset_y)
        shoulder_x, shoulder_y = screen(pose["shoulder"])
        hip_x, hip_y = screen(pose["hip"])
        head_x, head_y = screen(pose["head"])
        head_r = pose["radius"]
        base_ink = (135, 48, 48) if self.hurt_flash > 0 and int(self.hurt_flash * 40) % 2 else INK
        ink = tuple(round(c * (.55 + .45 * self.redraw_alpha)) for c in base_ink)

        def stroke(start, end, begin, finish, width):
            progress = max(0.0, min(1.0, (self.draw_amount - begin) / max(.001, finish - begin)))
            if progress <= 0:
                return
            target = (round(start[0] + (end[0] - start[0]) * progress),
                      round(start[1] + (end[1] - start[1]) * progress))
            pygame.draw.line(surface, ink, (round(start[0]), round(start[1])), target, width)

        # One ordered stroke plan is shared by the opening and every redraw.
        head_progress = max(0.0, min(1.0, self.draw_amount / .20))
        if head_progress > 0:
            head_rect = pygame.Rect(round(head_x - head_r), round(head_y - head_r),
                                    head_r * 2, head_r * 2)
            pygame.draw.arc(surface, ink, head_rect, -math.pi / 2,
                            -math.pi / 2 + math.tau * head_progress, 2)
        for start, end, begin, finish, width in self._redraw_strokes(pose):
            if width == 2 and self.draw_amount >= .82:
                continue
            stroke(screen(start), screen(end), begin, finish, width)
        for index, (knee, foot) in enumerate(pose["legs"]):
            finish = .82 if index == 0 else 1.0
            if self.draw_amount >= finish:
                fx, fy = screen(foot)
                # A short sole makes the planted contact readable at game scale.
                pygame.draw.line(surface, ink, (round(fx), round(fy)),
                                 (round(fx+self.facing*4), round(fy)), 2)
        # single face tick gives direction without turning the figure into vector art
        if self.draw_amount >= .18:
            look_y = -2 if self.look_target and self.look_target[1] < self.y else 1
            pygame.draw.line(surface, ink, (round(head_x + self.facing * 3), round(head_y + look_y)),
                             (round(head_x + self.facing * 6), round(head_y + look_y)), 1)
        self._draw_page_costume(surface, head_x, head_y, shoulder_y, hip_y, ink)
        if self.attack_timer > 0 and self.draw_amount >= .8:
            reach = 42 * self.facing
            start = (cx + self.facing * 7, round(shoulder_y + 9))
            end = (cx + reach, round(shoulder_y + 2 + math.sin(self.attack_timer * 28) * 8))
            pygame.draw.line(surface, (55, 53, 51), start, end, 3)
            arc_rect = pygame.Rect(min(cx, cx + reach) - 10, round(shoulder_y - 17), abs(round(reach)) + 20, 52)
            if self.facing > 0:
                pygame.draw.arc(surface, (78, 75, 71), arc_rect, -1.1, 1.1, 2)
            else:
                pygame.draw.arc(surface, (78, 75, 71), arc_rect, math.pi - 1.1, math.pi + 1.1, 2)
        if self.draw_amount >= .42:
            self._draw_weapon_and_hands(surface, shoulder_x, shoulder_y, hip_y, ink,
                                        self.rect.centery - 5 + camera.offset_y, cx)
        if self.dashing and self.draw_amount >= .8:
            for index in range(3):
                offset = self.facing * (27 + index * 17)
                fade = 124 + index * 28
                pygame.draw.line(surface, (fade, fade - 3, fade - 8),
                                 (cx - offset, round(shoulder_y + 4 + index * 5)),
                                 (cx - offset - self.facing * 19, round(shoulder_y + 4 + index * 5)), 1)

    def _draw_page_costume(self, surface, head_x, head_y, shoulder_y, hip_y, ink):
        if self.draw_amount < .82:
            return
        if self.page_style == "ronin":
            # Small top-knot, head band and open haori.  The weapon remains a
            # separate page tool, so losing it at the page turn still reads.
            pygame.draw.circle(surface, ink, (round(head_x - self.facing * 4),
                                               round(head_y - 13)), 4, 2)
            pygame.draw.line(surface, (142, 55, 55),
                             (round(head_x - 9), round(head_y - 6)),
                             (round(head_x + 10), round(head_y - 6)), 3)
            # The two loose cloth ends drag behind motion, then settle.
            flutter = math.sin(self.anim_time*17)*min(5,abs(self.vx)/65)
            bx,by=round(head_x-self.facing*8),round(head_y-5)
            for dy in (0,5):
                pygame.draw.lines(surface,(142,55,55),False,
                    [(bx,by),(bx-self.facing*10,round(by+dy+flutter)),
                     (bx-self.facing*23,round(by+dy+3-flutter))],2)
            pygame.draw.line(surface, ink,
                             (round(head_x - 10), round(shoulder_y + 1)),
                             (round(head_x - 14), round(hip_y + 1)), 2)
            pygame.draw.line(surface, ink,
                             (round(head_x + 10), round(shoulder_y + 1)),
                             (round(head_x + 14), round(hip_y + 1)), 2)
            pygame.draw.line(surface, (142, 55, 55),
                             (round(head_x - 12), round(shoulder_y + 8)),
                             (round(head_x + 12), round(shoulder_y + 8)), 2)
        elif self.page_style == "cowboy":
            # The requested hat deliberately dominates the tiny head.
            brim_y = round(head_y - 8)
            pygame.draw.line(surface, ink, (round(head_x - 16), brim_y),
                             (round(head_x + 16), brim_y), 4)
            pygame.draw.arc(surface, ink,
                            (round(head_x - 10), round(head_y - 20), 20, 15),
                            math.pi, math.tau, 3)
            pygame.draw.line(surface, (147, 58, 54),
                             (round(head_x - 8), round(shoulder_y + 2)),
                             (round(head_x + 7), round(shoulder_y + 7)), 3)
            pygame.draw.line(surface, ink,
                             (round(head_x - 12), round(hip_y - 3)),
                             (round(head_x + 12), round(hip_y - 3)), 2)
        elif self.page_style == "astronaut":
            pygame.draw.circle(surface, (82, 104, 129),
                               (round(head_x), round(head_y)), 12, 2)
            pygame.draw.arc(surface, (142, 65, 67),
                            (round(head_x - 9), round(head_y - 8), 18, 14),
                            .1, math.pi - .1, 2)
            pygame.draw.rect(surface, (82, 104, 129),
                             (round(head_x - self.facing * 13), round(shoulder_y), 7, 19), 2)
            pygame.draw.circle(surface, (142, 65, 67),
                               (round(head_x + 5), round(shoulder_y + 8)), 2)
        elif self.page_style == "ink_agent":
            # The Artist's cheap disguise: two heavy marker lenses and a tie.
            lens_y = round(head_y - 1)
            pygame.draw.line(surface, (29, 30, 36),
                             (round(head_x - 7), lens_y), (round(head_x + 7), lens_y), 3)
            pygame.draw.rect(surface, (29, 30, 36),
                             (round(head_x - 7), lens_y - 3, 6, 5), 1)
            pygame.draw.rect(surface, (29, 30, 36),
                             (round(head_x + 1), lens_y - 3, 6, 5), 1)
            pygame.draw.polygon(surface, (64, 55, 64),
                                [(round(head_x), round(shoulder_y + 4)),
                                 (round(head_x - 3), round(shoulder_y + 12)),
                                 (round(head_x), round(hip_y - 2)),
                                 (round(head_x + 3), round(shoulder_y + 12))], 1)
        elif self.page_style == "bad_drawing":
            # Visible correction marks make the bad anatomy intentional.
            red = (149, 60, 61)
            pygame.draw.arc(surface, red,
                            (round(head_x - 12), round(head_y - 13), 25, 25),
                            -.55, .55, 1)
            pygame.draw.line(surface, red,
                             (round(head_x + 13), round(head_y - 7)),
                             (round(head_x + 22), round(head_y - 13)), 1)
        elif self.page_style == "underpage":
            pygame.draw.line(surface, (125, 126, 133),
                             (round(head_x - 5), round(hip_y + 3)),
                             (round(head_x + 5), round(shoulder_y - 2)), 1)

    def _draw_weapon_and_hands(self, surface, cx, shoulder_y, hip_y, ink, combat_y,
                               combat_x=None):
        """Small grips keep the stick-figure hands readable during combat."""
        if self.current_weapon == "pencil_blade" and self.combat_swing is not None:
            angle, reach, power = self.combat_swing
            vector=pygame.Vector2(math.cos(angle),math.sin(angle))
            normal=pygame.Vector2(-vector.y,vector.x)
            origin=pygame.Vector2(cx if combat_x is None else combat_x,combat_y)
            hand=origin+vector*13
            page = getattr(self, "arsenal_page", None)
            shape = profile_for(page, "pencil_blade").silhouette
            close_grip = shape in ("bowie", "field_knife")
            elbow=pygame.Vector2(cx+self.facing*(5 if close_grip else -3),shoulder_y+17)
            pygame.draw.lines(surface,ink,False,[(cx,shoulder_y+7),elbow,hand],2)
            support = (pygame.Vector2(cx-self.facing*4, shoulder_y+10) if close_grip else
                       pygame.Vector2(cx-self.facing*10, shoulder_y+15)
                       if shape == "redraw_pencil" else hand-vector*6+normal*2)
            pygame.draw.lines(surface,ink,False,
                [(cx,shoulder_y+10),(cx-self.facing*8,shoulder_y+19),support],2)
            length = {"katana":47, "bowie":27, "field_knife":24,
                      "ion_blade":43, "pencil":40, "redraw_pencil":44}.get(shape, 40)
            draw_weapon(surface, "pencil_blade", page, hand, angle,
                        scale=max(.55, (reach - 13) / length), ink=ink)
            pygame.draw.circle(surface,ink,hand,3,1)
            return
        # Vertical aim is the sine for both facings. Clamping atan2 made a
        # horizontal left shot point the drawn muzzle down by 19 pixels.
        angle = math.sin(self.aim_angle)
        direction = self.facing
        recoil = self.weapon_recoil
        hand_x = cx + direction * (15 - recoil * 8)
        hand_y = round(shoulder_y + 10 + angle * 7 - recoil*3)
        support_x = cx + direction * 8
        support_y = round(shoulder_y + 17)
        pygame.draw.line(surface, ink, (cx, round(shoulder_y + 7)), (hand_x, hand_y), 2)
        pygame.draw.line(surface, ink, (cx, round(shoulder_y + 10)), (support_x, support_y), 2)
        pygame.draw.circle(surface, ink, (hand_x, hand_y), 3, 1)
        pygame.draw.circle(surface, ink, (support_x, support_y), 2, 1)

        weapon = self.current_weapon
        if weapon != "excalibur" and weapon != "ink_brush":
            page = getattr(self, "arsenal_page", None)
            held_angle = self.aim_angle - direction * recoil * .12
            if weapon == "pencil_blade":
                # The idle pose previews each starter's handling before the
                # first hit: sheathed katana, close Bowie, floating ion edge,
                # reverse-grip field knife, and the final page's writing grip.
                shape = profile_for(page, weapon).silhouette
                carry = {
                    "katana": .28,
                    "bowie": -.22,
                    "ion_blade": .04,
                    "field_knife": 1.02,
                    "redraw_pencil": .70,
                }.get(shape, .60)
                held_angle = carry if direction > 0 else math.pi - carry
            draw_weapon(surface, weapon, page, (hand_x, hand_y), held_angle, ink=ink)
            return
        muzzle_x = hand_x + direction * 30
        muzzle_y = hand_y + round(angle * 12 - recoil*5)
        if weapon == "pencil_blade":
            pygame.draw.line(surface, (67, 62, 55), (hand_x, hand_y), (muzzle_x + direction * 10, muzzle_y), 4)
            pygame.draw.line(surface, (213, 151, 48), (hand_x, hand_y - 1), (muzzle_x, muzzle_y - 1), 2)
        elif weapon == "ink_pistol":
            pygame.draw.line(surface, (34, 35, 42), (hand_x, hand_y), (muzzle_x, muzzle_y), 6)
            pygame.draw.line(surface, ink, (hand_x + direction * 7, hand_y + 2),
                             (hand_x + direction * 4, hand_y + 12), 4)
        elif weapon == "marker_shotgun":
            pygame.draw.line(surface, (45, 43, 48), (support_x, support_y), (muzzle_x + direction * 8, muzzle_y), 9)
            pygame.draw.line(surface, (113, 62, 103), (hand_x, hand_y - 2),
                             (muzzle_x + direction * 8, muzzle_y - 2), 3)
        elif weapon == "eraser_cannon":
            body = pygame.Rect(0, 0, 38, 15)
            body.center = ((hand_x + muzzle_x) // 2, (hand_y + muzzle_y) // 2)
            pygame.draw.rect(surface, (218, 155, 153), body, border_radius=3)
            pygame.draw.rect(surface, ink, body, 2, border_radius=3)
        elif weapon == "rubber_band":
            pygame.draw.line(surface, ink, (hand_x, hand_y - 8), (hand_x, hand_y + 8), 3)
            pygame.draw.line(surface, (157, 92, 61), (hand_x, hand_y - 7), (muzzle_x, muzzle_y), 2)
            pygame.draw.line(surface, (157, 92, 61), (hand_x, hand_y + 7), (muzzle_x, muzzle_y), 2)
        elif weapon == "ink_brush":
            pygame.draw.line(surface, (94, 62, 42), (support_x, support_y),
                             (muzzle_x + direction * 9, muzzle_y), 5)
            pygame.draw.circle(surface, (24, 26, 34), (muzzle_x + direction * 12, muzzle_y), 7)
        elif weapon == "excalibur":
            tip_x = muzzle_x + direction * 28
            tip_y = muzzle_y - 6
            pygame.draw.line(surface, (49, 50, 57), (hand_x, hand_y),
                             (tip_x, tip_y), 7)
            pygame.draw.line(surface, (228, 202, 109),
                             (hand_x + direction * 4, hand_y - 2),
                             (tip_x, tip_y - 2), 2)
            pygame.draw.line(surface, (141, 55, 56),
                             (hand_x - direction * 5, hand_y - 8),
                             (hand_x + direction * 9, hand_y + 8), 4)
