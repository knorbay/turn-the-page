from __future__ import annotations

import math
import pygame

from settings import GRAVITY, INK, MAX_FALL
from page_arsenal import draw_weapon, profile_for, held_weapon_pose


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
        self._buffered_jump_released = False
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
        self.current_weapon = "unarmed"
        self.aim_angle = 0.0
        self.weapon_recoil = 0.0
        self.weapon_reload_progress = None
        self.combat_swing = None
        self.redraw_variant = "clean"
        # Visual only.  The collision box remains stable while the Artist's
        # rejected drawing buckles and is then redrawn at the checkpoint.
        self.death_progress = 0.0
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

    def drop_through(self, world):
        """Leave an elevated thin line deliberately, retaining the solid floor."""
        if self.locked or not self.on_ground or self.health <= 0:
            return False
        for platform, one_way in world.collision_entries():
            if (one_way and platform.top < 580 and platform.height <= 49
                    and abs(platform.top-self.rect.bottom) <= 3
                    and platform.left <= self.center_x <= platform.right):
                self.y += platform.height + 8
                self.vy = 110
                self.on_ground = False
                self.coyote = self.jump_buffer = 0
                return True
        return False

    def queue_jump(self):
        self.jump_buffer = .12
        self._buffered_jump_released = False

    def release_jump(self):
        # Variable height without making tap-jumps feel anaemic.
        # A fast tap can release before a buffered jump actually launches.
        # Retain that release so hit-stop/landing cannot turn it into a hold.
        if self.jump_buffer > 0:
            self._buffered_jump_released = True
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

    def set_weapon_pose(self, weapon_id, aim_angle=0.0, recoil=0.0,
                        reload_progress=None):
        self.current_weapon = str(weapon_id)
        self.aim_angle = float(aim_angle)
        self.weapon_recoil = max(self.weapon_recoil, float(recoil))
        self.weapon_reload_progress = (None if reload_progress is None else
                                       max(0.0, min(1.0, float(reload_progress))))

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
        left, right = (1.58, .72) if self.redraw_variant == "long_arm" else (1, 1)
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
            if self._buffered_jump_released:
                self.vy *= .48
            self.on_ground = False
            self.coyote = 0.0
            self.jump_buffer = 0.0
            self._buffered_jump_released = False
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
        leg_scale = 1.42 if self.redraw_variant == "long_leg" else .79 if self.redraw_variant == "rushed" else 1.0
        hip_y = bottom - 16 * stretch * leg_scale
        shoulder_y = hip_y - (19 if self.redraw_variant == "rushed" else 24) * stretch
        hip_x = cx
        lean = facing * speed * 4 if self.on_ground else max(-4, min(4, self.vx / 70))
        if self.on_ground and speed < .08 and not self.dashing:
            shoulder_y += math.sin(self.anim_time * 2.4) * .8
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
        elif self.draw_amount >= 1 and self.current_weapon not in ("unarmed", "pencil_blade", "margin_maul"):
            shape = profile_for(getattr(self, "arsenal_page", None), self.current_weapon).silhouette
            heavy = shape in ("marker", "double_barrel", "breach", "eraser", "null_cannon", "carbon_rifle")
            if self.weapon_reload_progress is not None:
                shoulder_y += 3
                lean -= facing * 3
            elif self.weapon_recoil > .04:
                lean -= facing * self.weapon_recoil * (10 if heavy else 5)
                shoulder_y += self.weapon_recoil * (2 if heavy else 1)
            if heavy and self.on_ground:
                legs = [((cx+facing*8, hip_y+7), (cx+facing*15, bottom)),
                        ((cx-facing*8, hip_y+8), (cx-facing*13, bottom))]

        shoulder = (hip_x + lean, shoulder_y)
        head_x = shoulder[0] + (10*facing if self.redraw_variant == "crooked_head" else
                                -5*facing if self.redraw_variant == "rushed" else 0)
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
        if self.death_progress > 0:
            self._draw_broken_draft(surface, camera)
            return
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
            from paper_renderer import jitter_line
            jitter_line(surface, ink, (round(start[0]), round(start[1])), target, width,
                        round(begin*1000), 2, 1.3)

        # One ordered stroke plan is shared by the opening and every redraw.
        head_progress = max(0.0, min(1.0, self.draw_amount / .20))
        if head_progress > 0:
            head_rect = pygame.Rect(round(head_x - head_r), round(head_y - head_r),
                                    head_r * 2, head_r * 2)
            if head_progress >= 1:
                from sketch_marks import rough_circle
                pygame.draw.circle(surface, (246, 237, 215),
                                   (round(head_x), round(head_y)), head_r)
                rough_circle(surface, ink, (head_x,head_y),head_r,441,2,2,wobble=1.1)
            else:
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
        self._draw_page_costume(surface, head_x, head_y, shoulder_y, hip_y, ink,
                                shoulder_x, hip_x)
        if self.combat_swing is not None and self.draw_amount >= .8:
            self._draw_melee_motion(surface, camera, cx)
        elif self.attack_timer > 0 and self.draw_amount >= .8:
            # The old standalone Player.attack path is still used by a few
            # scripted encounters. Real weapons use the stroke below instead.
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

    def _draw_melee_motion(self, surface, camera, cx):
        """Draw the *kind* of cut around the real weapon tip, not a generic arc.

        This is a visual layer over the existing MeleeSwing timing and hitbox.
        A few opaque graphite strokes are deliberately used instead of a
        translucent screen-sized layer: the marks stay crisp on macOS too.
        """
        angle, reach, power = self.combat_swing
        force = min(1.0, max(0.0, power))
        if force < .08:
            return
        profile = profile_for(getattr(self, "arsenal_page", None),
                              self.current_weapon)
        shape, accent = profile.silhouette, profile.accent
        origin = pygame.Vector2(cx, self.rect.centery - 5 + camera.offset_y)
        direction = pygame.Vector2(math.cos(angle), math.sin(angle))
        normal = pygame.Vector2(-direction.y, direction.x)
        tip = origin + direction * reach
        graphite = (58, 54, 52)
        faded = (166, 158, 145)
        from paper_renderer import jitter_line

        def point(value):
            return round(value.x), round(value.y)

        def stroke(a, b, color=graphite, width=2, seed=591):
            jitter_line(surface, color, point(a), point(b), width,
                        seed, 2, .8)

        if shape == "katana":
            # A long single sweep and its light pressure ghost.
            for radius, color, width in ((reach, accent, 3),
                                         (reach - 9, faded, 1)):
                path = [origin + pygame.Vector2(math.cos(angle + offset),
                                                 math.sin(angle + offset)) * radius
                        for offset in (-.36, -.22, -.08, .06, .19)]
                for index in range(len(path) - 1):
                    stroke(path[index], path[index + 1], color, width, 592 + index)
            stroke(tip - normal * 9, tip + normal * 9, graphite, 2, 598)
        elif shape == "bowie":
            # A short, weighty cross-cut close to the fist.
            start = origin + direction * (reach * .43) - normal * 16
            middle = tip + normal * 7
            stroke(start, middle, graphite, 4, 601)
            stroke(start + direction * 9 + normal * 11,
                   tip + normal * 17, accent, 2, 602)
            stroke(tip - direction * 12 - normal * 10,
                   tip + direction * 5 + normal * 4, faded, 2, 603)
        elif shape == "field_knife":
            # Three narrow puncture trails remain distinct from a broad sword.
            for index, side in enumerate((-9, 0, 9)):
                start = origin + direction * (reach * (.47 + .07 * index)) + normal * side
                end = tip + direction * (4 if index == 1 else 0) + normal * (side * .55)
                stroke(start, end, accent if index == 1 else graphite,
                       2 if index == 1 else 1, 608 + index)
            pygame.draw.circle(surface, graphite, point(tip + direction * 6), 2)
        elif shape == "ion_blade":
            # Blue doubled charge with a jagged lead, in the same pencil world.
            for side in (-7, 7):
                stroke(origin + direction * (reach * .56) + normal * side,
                       tip + normal * (side * .55), accent, 2, 612 + side)
            spark = [tip - direction * 9 - normal * 7,
                     tip - direction * 2 + normal * 5,
                     tip + direction * 8 - normal * 3,
                     tip + direction * 13 + normal * 4]
            for index in range(3):
                stroke(spark[index], spark[index + 1], graphite, 2, 620 + index)
        elif shape == "redraw_pencil":
            # Misregistered correction stroke foreshadows the delayed echo.
            for side, color in ((-10, faded), (5, accent)):
                stroke(origin + direction * (reach * .38) + normal * side,
                       tip + normal * side, color, 2, 626 + side)
            for center in (tip - direction * 18, tip + direction * 4):
                stroke(center - normal * 6, center + normal * 6, accent, 1, 640)
        elif shape == "pencil_maul":
            # The oversized point drags a broad graphite wedge and splinters.
            near = origin + direction * (reach * .61)
            pygame.draw.polygon(surface, (191, 174, 137),
                                [point(near - normal * 10), point(tip + normal * 13),
                                 point(tip - normal * 13)])
            stroke(near - normal * 10, tip + normal * 13, graphite, 3, 645)
            stroke(near + normal * 9, tip - normal * 13, graphite, 3, 646)
            for index, side in enumerate((-16, 0, 16)):
                stroke(tip + normal * side,
                       tip + normal * side + direction * (8 + index * 4),
                       faded, 2, 648 + index)
        else:
            # Original pencil blade keeps a handmade graphite slash.
            stroke(origin + direction * (reach * .58) - normal * 10,
                   tip + normal * 10, graphite, 3, 653)
            stroke(origin + direction * (reach * .67) + normal * 2,
                   tip + normal * 16, faded, 1, 654)

    def _draw_broken_draft(self, surface, camera):
        """The dying figure visibly folds into a rejected, detached sketch.

        This changes only pixels.  The same normal pose drives the remnant and
        the death overlay, so it remains attached to the point of impact.
        """
        from paper_renderer import jitter_line
        from sketch_marks import rough_circle

        p = min(1.0, max(0.0, self.death_progress))
        pose = self._body_pose()
        facing = self.facing
        def screen(point):
            return (round(camera.screen_x(point[0])), round(point[1] + camera.offset_y))
        shoulder = screen(pose["shoulder"])
        hip = screen(pose["hip"])
        head = screen(pose["head"])
        displaced_head = (round(head[0] + facing * 23 * p), round(head[1] - 12 * p))
        bent_shoulder = (round(shoulder[0] - facing * 13 * p),
                         round(shoulder[1] + 8 * p))
        bent_hip = (round(hip[0] + facing * 9 * p), round(hip[1] + 6 * p))
        faint = (185, 178, 166)
        ink = (73 + round(p * 83), 68 + round(p * 75), 65 + round(p * 69))
        red = (149, 68, 66)

        # The previous, correct stroke remains like a rubbed-out afterimage.
        rough_circle(surface, faint, head, pose["radius"], 453, 1, 1, wobble=2)
        jitter_line(surface, faint, shoulder, hip, 1, 454, 1, 1.4)
        rough_circle(surface, ink, displaced_head, pose["radius"], 455, 2, 2, wobble=2.2)
        jitter_line(surface, ink, bent_shoulder, bent_hip, 3, 456, 2, 2.2)
        pygame.draw.line(surface, red,
                         (displaced_head[0] - 4, displaced_head[1] - 3),
                         (displaced_head[0] + 5, displaced_head[1] + 4), 2)
        pygame.draw.line(surface, red,
                         (displaced_head[0] - 3, displaced_head[1] + 4),
                         (displaced_head[0] + 5, displaced_head[1] - 3), 2)
        for index, (knee, foot) in enumerate(pose["legs"]):
            sknee, sfoot = screen(knee), screen(foot)
            gap = facing * (6 + index * 5) * p
            knee_end = (round(sknee[0] - gap), round(sknee[1] - p * 3))
            foot_start = (round(sknee[0] + gap), round(sknee[1] + p * 3))
            jitter_line(surface, ink, bent_hip, knee_end, 2, 460 + index, 2, 2)
            jitter_line(surface, ink, foot_start,
                        (round(sfoot[0] + facing * (index * 7 - 4) * p),
                         round(sfoot[1] - (index + 1) * p * 4)),
                        2, 464 + index, 2, 2)
        for index, direction in enumerate((-1, 1)):
            arm_start = (round(bent_shoulder[0] + direction * 4), bent_shoulder[1] + 5)
            arm_end = (round(arm_start[0] + direction * (12 + 11 * p)),
                       round(arm_start[1] + 12 + (index * 8 - 3) * p))
            jitter_line(surface, ink, arm_start, arm_end, 2, 468 + index, 2, 2)
        # The rejection crosses the misdrawn pose rather than the entire view.
        if p > .38:
            slash = min(1.0, (p - .38) / .4)
            length = round(24 * slash)
            jitter_line(surface, red,
                        (bent_hip[0] - length, bent_hip[1] + 11),
                        (bent_hip[0] + length, bent_shoulder[1] - 16),
                        2, 471, 2, 1.8)

    def _draw_page_costume(self, surface, head_x, head_y, shoulder_y, hip_y, ink,
                           shoulder_x=None, hip_x=None):
        if self.draw_amount < .82:
            return
        # Headgear follows the head; cloth follows the articulated torso.
        # Using head_x for both made coats float sideways during a lean.
        shoulder_x = head_x if shoulder_x is None else shoulder_x
        hip_x = shoulder_x if hip_x is None else hip_x
        def torso(offset, y):
            t = (y-shoulder_y)/max(1.0, hip_y-shoulder_y)
            return (round(shoulder_x+(hip_x-shoulder_x)*t+offset), round(y))

        if self.page_style == "ronin":
            haori = [torso(-10, shoulder_y+1),
                     torso(-14, hip_y+2),
                     torso(-3, hip_y-1),
                     torso(0, shoulder_y+5),
                     torso(3, hip_y-1),
                     torso(14, hip_y+2),
                     torso(10, shoulder_y+1)]
            pygame.draw.polygon(surface, (109, 114, 99), haori)
            pygame.draw.lines(surface, ink, True, haori, 1)
            pygame.draw.line(surface, (203, 196, 167),
                             torso(-8, shoulder_y+3),
                             torso(-10, hip_y-2), 1)
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
                             torso(- 10, shoulder_y + 1),
                             torso(- 14, hip_y + 1), 2)
            pygame.draw.line(surface, ink,
                             torso(10, shoulder_y + 1),
                             torso(14, hip_y + 1), 2)
            pygame.draw.line(surface, (142, 55, 55),
                             torso(- 12, shoulder_y + 8),
                             torso(12, shoulder_y + 8), 2)
        elif self.page_style == "cowboy":
            # The requested hat deliberately dominates the tiny head.
            brim_y = round(head_y - 8)
            hat = [(round(head_x-11), brim_y-1), (round(head_x-8), brim_y-10),
                   (round(head_x+1), brim_y-12), (round(head_x+9), brim_y-9),
                   (round(head_x+11), brim_y)]
            pygame.draw.polygon(surface, (131, 96, 58), hat)
            pygame.draw.lines(surface, ink, False, hat, 2)
            pygame.draw.line(surface, (202, 163, 104),
                             (round(head_x-6), brim_y-9), (round(head_x+5), brim_y-10), 1)
            vest = [torso(-8, shoulder_y+3),
                    torso(-10, hip_y-4),
                    torso(9, hip_y-4),
                    torso(7, shoulder_y+3)]
            pygame.draw.polygon(surface, (183, 141, 91), vest)
            pygame.draw.lines(surface, ink, True, vest, 1)
            pygame.draw.line(surface, ink, torso(0, shoulder_y+7),
                             torso(0, hip_y-4), 1)
            pygame.draw.line(surface, ink, (round(head_x - 16), brim_y),
                             (round(head_x + 16), brim_y), 4)
            pygame.draw.arc(surface, ink,
                            (round(head_x - 10), round(head_y - 20), 20, 15),
                            math.pi, math.tau, 3)
            pygame.draw.line(surface, (147, 58, 54),
                             torso(- 8, shoulder_y + 2),
                             torso(7, shoulder_y + 7), 3)
            pygame.draw.line(surface, ink,
                             torso(- 12, hip_y - 3),
                             torso(12, hip_y - 3), 2)
        elif self.page_style == "astronaut":
            suit = [torso(-7, shoulder_y),
                    torso(-10, hip_y),
                    torso(9, hip_y),
                    torso(7, shoulder_y)]
            pygame.draw.polygon(surface, (220, 225, 217), suit)
            pygame.draw.lines(surface, ink, True, suit, 1)
            visor = pygame.Rect(round(head_x-8), round(head_y-6), 17, 10)
            pygame.draw.ellipse(surface, (67, 93, 110), visor)
            pygame.draw.line(surface, (208, 228, 224),
                             (round(head_x-5), round(head_y-4)),
                             (round(head_x+1), round(head_y-4)), 1)
            pygame.draw.circle(surface, (82, 104, 129),
                               (round(head_x), round(head_y)), 12, 2)
            pygame.draw.arc(surface, (142, 65, 67),
                            (round(head_x - 9), round(head_y - 8), 18, 14),
                            .1, math.pi - .1, 2)
            pack = [torso(-self.facing*13, shoulder_y),
                    torso(-self.facing*13+7, shoulder_y),
                    torso(-self.facing*13+7, shoulder_y+19),
                    torso(-self.facing*13, shoulder_y+19)]
            pygame.draw.lines(surface, (82, 104, 129), True, pack, 2)
            pygame.draw.circle(surface, (142, 65, 67),
                               torso(5, shoulder_y + 8), 2)
        elif self.page_style == "ink_agent":
            # The Artist's cheap disguise: two heavy marker lenses and a tie.
            coat = [torso(-8, shoulder_y+1),
                    torso(-12, hip_y+3),
                    torso(11, hip_y+3),
                    torso(8, shoulder_y+1)]
            pygame.draw.polygon(surface, (85, 92, 86), coat)
            pygame.draw.lines(surface, ink, True, coat, 1)
            pygame.draw.lines(surface, (221, 214, 190), False,
                              [torso(-4, shoulder_y+3),
                               torso(0, shoulder_y+11),
                               torso(4, shoulder_y+3)], 1)
            lens_y = round(head_y - 1)
            pygame.draw.line(surface, (29, 30, 36),
                             (round(head_x - 7), lens_y), (round(head_x + 7), lens_y), 3)
            pygame.draw.rect(surface, (29, 30, 36),
                             (round(head_x - 7), lens_y - 3, 6, 5), 1)
            pygame.draw.rect(surface, (29, 30, 36),
                             (round(head_x + 1), lens_y - 3, 6, 5), 1)
            pygame.draw.polygon(surface, (146, 63, 62),
                                [torso(0, shoulder_y + 4),
                                 torso(- 3, shoulder_y + 12),
                                 torso(0, hip_y - 2),
                                 torso(3, shoulder_y + 12)])
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
                             torso(- 5, hip_y + 3),
                             torso(5, shoulder_y - 2), 1)

    def weapon_attachment(self, aim_angle=None):
        """Shared world-space grip and barrel; rendering adds only the camera."""
        return held_weapon_pose(self, aim_angle=aim_angle)

    def _draw_weapon_and_hands(self, surface, cx, shoulder_y, hip_y, ink, combat_y,
                               combat_x=None):
        """Attach a sized tool to articulated wrists and a real support point."""
        if self.current_weapon == "unarmed":
            swing = math.sin(self.stride_phase) * 6 * self.motion_speed
            for side in (-1, 1):
                hand = (round(cx + side * 9 + swing * side), round(shoulder_y + 25))
                pygame.draw.lines(surface, ink, False,
                    [(round(cx), round(shoulder_y + 6)),
                     (round(cx + side * 8), round(shoulder_y + 15)), hand], 2)
                pygame.draw.circle(surface, ink, hand, 2, 1)
            return
        pose = self.weapon_attachment()
        body = self._body_pose()
        # Screen translation is shared by wrists, weapon and barrel. The
        # attachment itself stays in world coordinates for projectile spawning.
        offset = pygame.Vector2(cx - body["shoulder"][0], shoulder_y - body["shoulder"][1])
        def screen(point):
            point = pygame.Vector2(point) + offset
            return round(point.x), round(point.y)
        shoulder = pygame.Vector2(body["shoulder"])
        facing = self.facing
        primary_start = shoulder + pygame.Vector2(0, 6)
        support_start = shoulder + pygame.Vector2(-facing * 2, 8)
        primary_elbow = primary_start.lerp(pose.grip, .52) + pygame.Vector2(-facing * 2, 4)
        support_elbow = support_start.lerp(pose.support, .52) + pygame.Vector2(-facing * 4, 5)
        pygame.draw.lines(surface, ink, False,
                          [screen(primary_start), screen(primary_elbow), screen(pose.grip)], 2)
        pygame.draw.lines(surface, ink, False,
                          [screen(support_start), screen(support_elbow), screen(pose.support)], 2)
        page = getattr(self, "arsenal_page", None)
        profile = profile_for(page, self.current_weapon)
        if self.current_weapon == "ink_brush":
            tip = pose.grip + pygame.Vector2(facing * 28, -3)
            pygame.draw.line(surface, (94, 62, 42), screen(pose.grip), screen(tip), 3)
            pygame.draw.circle(surface, (24, 26, 34), screen(tip), 4)
        else:
            draw_weapon(surface, self.current_weapon, page, screen(pose.draw_origin),
                        pose.angle, scale=pose.scale, ink=ink)
        # Small solid wrist contacts read cleanly at1x, without the former
        # hollow six-pixel rings looking larger than the entire forearm.
        pygame.draw.circle(surface, (225, 207, 169), screen(pose.grip), 2)
        pygame.draw.circle(surface, ink, screen(pose.grip), 2, 1)
        if pose.two_handed or self.weapon_reload_progress is not None:
            pygame.draw.circle(surface, (225, 207, 169), screen(pose.support), 2)
            pygame.draw.circle(surface, ink, screen(pose.support), 2, 1)
        else:
            pygame.draw.circle(surface, ink, screen(pose.support), 1)
        if self.weapon_reload_progress is not None:
            point = screen(pose.support)
            shape = profile.silhouette
            if shape in ("revolver", "chalk_bomb"):
                pygame.draw.circle(surface, profile.accent, (point[0], point[1] + 3), 3, 1)
            else:
                pygame.draw.rect(surface, profile.accent,
                                 (point[0] - 2, point[1] + 1, 4, 6), 1)
