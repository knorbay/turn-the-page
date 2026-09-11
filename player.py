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
        cx = self.center_x
        bottom = self.y + self.HEIGHT
        hip = bottom - 16
        shoulder = hip - 24
        head_y = shoulder - 9
        if p < .20:
            angle = -math.pi / 2 + math.tau * (p / .20)
            return cx + math.cos(angle) * 7, head_y + math.sin(angle) * 7
        if p < .40:
            t = (p - .20) / .20
            return cx, shoulder + (hip - shoulder) * t
        if p < .55:
            t = (p - .40) / .15
            return cx + 12 * t, shoulder + 7 + 14 * t
        if p < .70:
            t = (p - .55) / .15
            return cx - 12 * t, shoulder + 7 + 14 * t
        if p < .85:
            t = (p - .70) / .15
            return cx - 9 * t, hip + (bottom - hip) * t
        t = (p - .85) / .15
        return cx + 9 * t, hip + (bottom - hip) * t

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
        cx = camera.screen_x(self.center_x)
        bottom = round(self.y + self.HEIGHT + camera.offset_y)
        speed = min(1.0, abs(self.vx) / 260)
        phase = self.anim_time * (4 + speed * 10)
        squash = self.land_squash
        stretch_y = 1.0 - squash
        stretch_x = 1.0 + squash * .65
        variant = self.redraw_variant
        leg_scale = 1.22 if variant == "long_leg" else .92 if variant == "rushed" else 1.0
        left_arm_scale = 1.42 if variant == "long_arm" else 1.0
        right_arm_scale = .78 if variant == "long_arm" else 1.0
        body_h = (22 if variant == "rushed" else 24) * stretch_y
        hip_y = bottom - 16 * stretch_y * leg_scale
        shoulder_y = hip_y - body_h
        head_y = shoulder_y - 9 * stretch_y
        head_x = cx + (4 * self.facing if variant == "crooked_head" else
                       -2 if variant == "rushed" else 0)
        head_r = max(5, round(7 * stretch_x))
        base_ink = (135, 48, 48) if self.hurt_flash > 0 and int(self.hurt_flash * 40) % 2 else INK
        ink = tuple(round(c * (.55 + .45 * self.redraw_alpha)) for c in base_ink)

        leg_swing = (4*self.facing + math.sin(phase)*8*speed
                     if self.on_ground else 4*self.facing)
        if self.on_ground and self.combat_swing is not None:
            leg_swing += self.facing*max(0,self.combat_swing[2])*4
        arm_swing = -leg_swing * .75
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
        stroke((cx, shoulder_y), (cx, hip_y), .16, .36, 3)
        arm_y = shoulder_y + 7
        if self.draw_amount < .82:
            stroke((cx, arm_y),
                   (cx + arm_swing * left_arm_scale, arm_y + 14 * left_arm_scale),
                   .32, .52, 2)
            stroke((cx, arm_y),
                   (cx - arm_swing * right_arm_scale, arm_y + 14 * right_arm_scale),
                   .46, .66, 2)
        stroke((cx, hip_y), (cx - leg_swing, bottom), .60, .82, 3)
        stroke((cx, hip_y), (cx + leg_swing, bottom), .76, 1.0, 3)
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
            self._draw_weapon_and_hands(surface, cx, shoulder_y, hip_y, ink,
                                        self.rect.centery - 5 + camera.offset_y)
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

    def _draw_weapon_and_hands(self, surface, cx, shoulder_y, hip_y, ink, combat_y):
        """Small grips keep the stick-figure hands readable during combat."""
        if self.current_weapon == "pencil_blade" and self.combat_swing is not None:
            angle, reach, power = self.combat_swing
            vector=pygame.Vector2(math.cos(angle),math.sin(angle))
            normal=pygame.Vector2(-vector.y,vector.x)
            origin=pygame.Vector2(cx,combat_y)
            hand=origin+vector*13
            tip=origin+vector*reach
            elbow=pygame.Vector2(cx-self.facing*3,shoulder_y+17)
            pygame.draw.lines(surface,ink,False,[(cx,shoulder_y+7),elbow,hand],2)
            support=hand-vector*6+normal*2
            pygame.draw.lines(surface,ink,False,
                [(cx,shoulder_y+10),(cx-self.facing*8,shoulder_y+19),support],2)
            page = getattr(self, "arsenal_page", None)
            shape = profile_for(page, "pencil_blade").silhouette
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
