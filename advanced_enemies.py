"""Advanced hand-drawn enemies for Paper Story's action-combat campaign.

The classes in this module intentionally mirror the small interface used by
``combat.DoodleEnemy`` while remaining independent from ``combat.py``.  That
keeps the factory safe to import from ``CombatArena`` without a circular import.

Every durable enemy is paced by counter-play rather than a very large health
pool: guards expose their back, charges crumple against arena edges, tools open
after committing to an attack, and bosses unravel for a few high-value hits.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
import random
from typing import Iterable

import pygame

from paper_renderer import jitter_line
from sketch_marks import (correction_cross, pivot, rough_circle, staples,
                          torn_wing)
from settings import INK, INK_LIGHT, PAPER, RED_RULE


# ---------------------------------------------------------------------------
# Shared projectile and enemy contract


@dataclass
class PaperProjectile:
    x: float
    y: float
    vx: float
    vy: float
    kind: str = "ink"
    life: float = 3.0
    radius: int = 7
    gravity: float = 180.0
    grace: float = .14
    terrain_collision: bool = True

    @property
    def rect(self):
        if self.kind == "staple":
            return pygame.Rect(round(self.x - 10), round(self.y - 3), 20, 7)
        if self.kind == "needle":
            return pygame.Rect(round(self.x - 12), round(self.y - 3), 24, 7)
        return pygame.Rect(
            round(self.x - self.radius), round(self.y - self.radius),
            self.radius * 2, self.radius * 2,
        )

    def update(self, dt, ctx):
        self.life -= dt
        self.grace = max(0.0, self.grace - dt)
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.terrain_collision and any(
            self.rect.colliderect(stroke) for stroke in ctx.world.collision_rects()
        ):
            self.life = 0
            ctx.particles.pencil_speck(self.x, self.y)
            return
        player = ctx.player
        if (self.grace <= 0 and player.dash_timer > .08
                and not player.return_used
                and self.rect.colliderect(player.rect.inflate(10, 10))
                and getattr(ctx, "weapons", None) is not None):
            from weapons import PaperProjectile as ReturnedProjectile
            from particles import Particle
            self.life = 0
            player.return_used = True
            velocity = pygame.Vector2(-self.vx, -self.vy)
            if velocity.length_squared() < 1:
                velocity.update(player.facing, 0)
            velocity = velocity.normalize() * 620
            ctx.weapons.projectiles.append(ReturnedProjectile(
                "ink", self.x, self.y, velocity.x, velocity.y, 1, 6, 1.8, 130,
                seed=ctx.weapons.next_seed()))
            ctx.particles.combat_hit(self.x, self.y, player.facing, False, 7)
            ctx.particles.items.append(Particle(self.x, self.y, 0, 0, .26, .26,
                                                 22, (69, 99, 117), kind="return_ring"))
            ctx.sounds.play("blocked")
            ctx.camera.kick(2, .09)
            _request_hit_stop(ctx, .045)
            if getattr(ctx, "game", None):
                ctx.game.behavior.record("perfect_return", page=ctx.level.chapter_index)
                ctx.level.toast = "THE ARTIST: Nice line."
                ctx.level.toast_time = 1.2
            return
        if (
            self.grace <= 0
            and self.rect.colliderect(ctx.player.rect)
            and ctx.player.hurt(self.x)
        ):
            self.life = 0
            ctx.sounds.play("ink")
            ctx.camera.kick(3, .13)
            _player_hit_feedback(ctx, self.x)
        if self.y > 820 or self.y < -180:
            self.life = 0

    def draw(self, surface, camera):
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        if self.kind == "staple":
            pygame.draw.lines(
                surface, INK, False,
                [(x - 10, y + 3), (x - 10, y - 3), (x + 10, y - 3),
                 (x + 10, y + 3)], 2,
            )
        elif self.kind == "needle":
            pygame.draw.line(surface, INK, (x - 13, y + 2), (x + 13, y - 2), 3)
            pygame.draw.circle(surface, PAPER, (x - 9, y + 1), 2)
        elif self.kind == "paper":
            pygame.draw.polygon(
                surface, (109, 104, 95),
                [(x - 8, y + 4), (x + 9, y), (x - 2, y - 7)], 2,
            )
        elif self.kind == "moon":
            pygame.draw.circle(surface, (237, 226, 190), (x, y), self.radius)
            rough_circle(surface, INK, (x, y), self.radius, 61, 2, 1)
            pygame.draw.circle(surface, (91, 119, 126), (x - 4, y - 3), 4, 1)
            pygame.draw.arc(surface, (91, 119, 126),
                            (x + 2, y + 1, 6, 5), .2, 3.6, 1)
            speed = math.hypot(self.vx, self.vy)
            if speed > 1:
                tail = (x - self.vx / speed * 26, y - self.vy / speed * 26)
                pygame.draw.line(surface, (169, 153, 124), (x, y), tail, 1)
        elif self.kind == "gutter_drop":
            # The violet drop matches the lantern's warning column, so a
            # player can connect the locked mark to the falling attack.
            pygame.draw.polygon(
                surface, (105, 76, 122),
                [(x, y - self.radius - 4), (x + self.radius, y + 3),
                 (x, y + self.radius), (x - self.radius, y + 3)],
            )
            pygame.draw.lines(
                surface, (56, 48, 69), True,
                [(x, y - self.radius - 4), (x + self.radius, y + 3),
                 (x, y + self.radius), (x - self.radius, y + 3)], 2,
            )
        elif self.kind == "comet_ember":
            # Lingering floor sparks are cool blue rather than damage red;
            # their star silhouette remains readable on both paper palettes.
            points = []
            for index in range(8):
                angle = -math.pi / 2 + index * math.pi / 4
                radius = self.radius if index % 2 == 0 else self.radius * .42
                points.append((x + math.cos(angle) * radius,
                               y + math.sin(angle) * radius))
            pygame.draw.polygon(surface, (89, 151, 166), points)
            pygame.draw.lines(surface, (42, 65, 78), True, points, 2)
            pygame.draw.circle(surface, (238, 187, 86), (x, y), 3)
        elif self.kind == "moon_shard":
            points = [(x, y - self.radius - 3), (x + self.radius, y),
                      (x, y + self.radius + 3), (x - self.radius, y)]
            pygame.draw.polygon(surface, (137, 174, 184), points)
            pygame.draw.lines(surface, (47, 70, 82), True, points, 2)
            pygame.draw.line(surface, (237, 192, 93), (x - 3, y), (x + 3, y), 1)
        else:
            pygame.draw.circle(surface, (29, 29, 36), (x, y), self.radius)
            pygame.draw.circle(
                surface, (78, 74, 78), (x - 2, y - 2),
                max(1, self.radius // 3),
            )


def _tag_set(tags) -> set[str]:
    if tags is None:
        return set()
    if isinstance(tags, str):
        return {tags}
    return {str(tag) for tag in tags}


def _knockback_strength(knockback) -> float:
    if isinstance(knockback, (tuple, list)) and knockback:
        return abs(float(knockback[0]))
    try:
        return abs(float(knockback))
    except (TypeError, ValueError):
        return 0.0


def _ballistic_velocity(origin_x, origin_y, target_x, target_y, gravity,
                        travel_speed=390.0):
    """Return a readable arc that can reach a target anywhere in an arena."""
    dx = float(target_x) - float(origin_x)
    dy = float(target_y) - float(origin_y)
    travel_time = max(.68, min(2.7, abs(dx) / max(1.0, travel_speed) + .38))
    return dx / travel_time, (dy - .5 * gravity * travel_time ** 2) / travel_time


def _attack_id(tags) -> int | None:
    for tag in tags:
        if not str(tag).startswith("attack:"):
            continue
        try:
            return int(str(tag).split(":", 1)[1])
        except (TypeError, ValueError):
            return None
    return None


def _request_hit_stop(ctx, duration):
    game = getattr(ctx, "game", None)
    if game is None:
        return
    request = getattr(game, "request_hit_stop", None)
    if callable(request):
        request(duration)
    else:
        game.hit_stop = max(getattr(game, "hit_stop", 0), duration)


def _player_hit_feedback(ctx, source_x):
    direction = 1 if ctx.player.center_x >= source_x else -1
    ctx.particles.combat_hit(ctx.player.center_x, ctx.player.rect.centery,
                             direction, True, 8)
    game = getattr(ctx, "game", None)
    request = getattr(game, "request_player_damage_feedback", None)
    if callable(request):
        request()
    else:
        _request_hit_stop(ctx, .045)


def _health_scratches(surface, camera, enemy, y_offset=92, x_world=None):
    x = camera.screen_x(enemy.x if x_world is None else x_world)
    y = round(enemy.y - y_offset + camera.offset_y)
    spacing = 6 if enemy.max_hp <= 18 else 5
    start = x - ((enemy.max_hp - 1) * spacing) // 2
    for index in range(enemy.max_hp):
        color = INK if index < enemy.hp else (180, 172, 154)
        pygame.draw.line(
            surface, color,
            (start + index * spacing, y),
            (start + index * spacing + 3, y + 7), 2,
        )


def _dashed_line(surface, color, start, end, width=1, dash=7, gap=5):
    """Small code-drawn construction stroke used by incomplete sketches."""
    vector = pygame.Vector2(end) - pygame.Vector2(start)
    length = vector.length()
    if length <= .001:
        return
    direction = vector / length
    cursor = 0.0
    while cursor < length:
        segment_end = min(length, cursor + dash)
        a = pygame.Vector2(start) + direction * cursor
        b = pygame.Vector2(start) + direction * segment_end
        pygame.draw.line(surface, color, a, b, width)
        cursor += dash + gap


class AdvancedEnemy:
    """Common API and readable hit feedback shared by all advanced doodles."""

    kind = "advanced"
    width = 42
    height = 48
    radius = 21
    base_hp = 3
    uses_gravity = True
    drag = 5.0
    is_boss = False
    block_hint = ""
    contact_states: tuple[str, ...] = ()

    def __init__(self, x, ground_y=590, seed=1):
        self.x = float(x)
        self.ground_y = float(ground_y)
        self.y = float(ground_y)
        self.vx = self.vy = 0.0
        self.seed = int(seed)
        self.rng = random.Random(self.seed)
        self.time = 0.0
        self.state = "idle"
        self.state_time = self.rng.uniform(.35, .65)
        self.state_duration = self.state_time
        self.aim_target = None
        self.dead = False
        self.hp = self.max_hp = int(self.base_hp)
        self.projectiles: list[PaperProjectile] = []
        self.facing = -1
        self.hit_flash = 0.0
        self.invulnerable = 0.0
        self.hit_stun = 0.0
        self.attack_suppressed = 0.0
        self.last_attack_id: int | None = None
        self.last_attack_hits = 0
        self.last_attack_serial = -1
        self.block_hint_cooldown = 0.0
        self._temporary_erases: list[dict] = []

    @property
    def rect(self):
        return pygame.Rect(
            round(self.x - self.width / 2), round(self.y - self.height),
            self.width, self.height,
        )

    @property
    def vulnerable(self):
        return self._is_vulnerable()

    def _is_vulnerable(self):
        return True

    def _set_state(self, name, duration):
        admission = getattr(self, "attack_admission", None)
        if admission is not None and not admission(self, name):
            return False
        self.state = name
        self.state_time = float(duration)
        self.state_duration = max(.001, float(duration))
        return True

    @property
    def pose_progress(self):
        return max(0.0, min(1.0, 1 - self.state_time / self.state_duration))

    def opening_status(self):
        """Visible punish marks share the health-damage window's hit budget."""
        windows = {
            "moon_compass": (("stuck",), 2),
            "wanted_sketch": (("bounty_draw", "bounty_volley", "unravel"), 1),
            "railroad_stapler": (("reload",), 2),
            "orbital_mistake": (("unravel",), 3),
            "scissor_director": (("open_hinge",), 3),
            "final_editor": (("proof_window",), 2),
        }
        states, total = windows.get(self.kind, ((), 0))
        if self.dead or self.state not in states or self.state_time <= 0:
            return None
        remaining = max(0, total - getattr(self, "window_hits", 0))
        if not self._is_vulnerable():
            remaining = 0
        return remaining, total, max(0.0, min(1.0, self.state_time / self.state_duration))

    def _draw_opening(self, surface, center, radius=22):
        status = self.opening_status()
        if status is None:
            return
        remaining, total, time_left = status
        x, y = round(center[0]), round(center[1])
        blue, spent = (68, 111, 130), (159, 148, 128)
        if remaining:
            pygame.draw.arc(surface, blue, (x-radius, y-radius, radius*2, radius*2),
                            -math.pi/2, -math.pi/2 + max(.02, time_left*math.tau), 2)
        for index in range(total):
            tx = x + (index-(total-1)/2)*8
            pygame.draw.line(surface, blue if index < remaining else spent,
                             (tx+2, y+radius+4), (tx-1, y+radius+10), 2)
        if not remaining:
            pygame.draw.line(surface, spent, (x-7, y-5), (x+7, y+5), 2)
            pygame.draw.line(surface, spent, (x-7, y+5), (x+7, y-5), 2)

    def _blocked_feedback(self, ctx, x=None, y=None):
        x = self.x if x is None else x
        y = self.y - self.height * .55 if y is None else y
        ctx.particles.pencil_speck(x, y)
        ctx.sounds.play("blocked")
        ctx.camera.kick(1.25, .07)
        if self.block_hint and self.block_hint_cooldown <= 0:
            ctx.level.toast = self.block_hint
            ctx.level.toast_time = 2.15
            self.block_hint_cooldown = 1.15

    def hit_from_weapon(
        self, amount, knockback, source_x, tags, ctx
    ) -> bool:
        """Apply a weapon hit and return whether it dealt health damage."""

        tags = _tag_set(tags)
        attack_id = _attack_id(tags)
        same_marker_volley = (
            "marker" in tags
            and attack_id is not None
            and attack_id == self.last_attack_id
            and self.last_attack_hits < 3
        )
        if self.dead:
            return False
        # A short post-hit i-frame prevents accidental double application; it
        # is not armor, so it must not emit a misleading block clang for every
        # extra pellet in the same frame.
        if self.invulnerable > 0 and not same_marker_volley:
            return False
        if not self._is_vulnerable():
            self._blocked_feedback(ctx)
            return False
        if attack_id is not None:
            if attack_id == self.last_attack_id:
                self.last_attack_hits += 1
            else:
                self.last_attack_id = attack_id
                self.last_attack_hits = 1
        amount = max(1, int(amount))
        self.hp -= amount
        game = getattr(ctx, "game", None)
        behavior = getattr(game, "behavior", None)
        if behavior is not None:
            behavior.record("enemy_hit", kind=self.kind,
                            weapon=getattr(getattr(ctx, "weapons", None),
                                           "current_id", "unknown"))
        self.hit_flash = .16
        self.invulnerable = .075
        direction = 1 if float(source_x) < self.x else -1
        heavy = bool({"heavy", "finisher", "eraser", "marker"} & tags)
        self.vx += direction * min(275 if heavy else 215, _knockback_strength(knockback))
        self.hit_stun = max(self.hit_stun,
                            .075 if self.is_boss and heavy else
                            .045 if self.is_boss else .15 if heavy else .095)
        if heavy:
            self.attack_suppressed = max(self.attack_suppressed,
                                         .08 if self.is_boss else .20)
        hit_y = self.y - self.height * .45
        if "eraser" in tags:
            ctx.particles.eraser_dust(self.x, hit_y, 7)
        else:
            ctx.particles.combat_hit(self.x, hit_y, direction, heavy)
        ctx.sounds.play("erase" if "eraser" in tags else "heavy_hit" if heavy else "hit")
        ctx.camera.kick(4.0 if heavy else 2.5, .15 if heavy else .1)
        _request_hit_stop(ctx, .055 if heavy else .026)
        if self.hp <= 0:
            self.hp = 0
            self.dead = True
            self.projectiles.clear()
            self._restore_temporary_erases(force=True)
            death_y = self.y - self.height * .3
            ctx.particles.paper_puff(self.x, death_y, 24 if self.is_boss else 14)
            ctx.particles.enemy_break(self.x, death_y, direction,
                                      30 if self.is_boss else 18)
            ctx.sounds.play("enemy_break")
            _request_hit_stop(ctx, .082 if self.is_boss or heavy else .065)
            if behavior is not None:
                behavior.record("enemy_defeated", kind=self.kind,
                                weapon=getattr(getattr(ctx, "weapons", None),
                                               "current_id", "unknown"))
        return True

    def _read_player_weapon(self, ctx):
        player = ctx.player
        if not player.attack_active or not player.attack_rect.colliderect(self.rect):
            return
        serial = getattr(player, "attack_serial", 0)
        if serial == self.last_attack_serial:
            return
        self.last_attack_serial = serial
        self.hit_from_weapon(
            1, 190, player.center_x,
            {"melee", "front" if player.facing == self.facing else "back"},
            ctx,
        )

    def _tick(self, dt):
        self.time += dt
        self.hit_stun = max(0.0, self.hit_stun - dt)
        self.attack_suppressed = max(0.0, self.attack_suppressed - dt)
        self.state_time -= dt
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.block_hint_cooldown = max(0.0, self.block_hint_cooldown - dt)

    def _think(self, dt, ctx, bounds):
        del dt, ctx, bounds

    def _integrate(self, dt, bounds):
        unclamped_x = self.x + self.vx * dt
        left = bounds[0] + self.radius
        right = bounds[1] - self.radius
        self.x = max(left, min(right, unclamped_x))
        hit_wall = abs(self.x - unclamped_x) > .01

        landed = False
        if self.uses_gravity:
            was_airborne = self.y < self.ground_y - .5 or abs(self.vy) > 1
            falling = self.vy > 0
            self.vy += 1150 * dt
            self.y += self.vy * dt
            if self.y >= self.ground_y:
                self.y = self.ground_y
                landed = was_airborne and falling
                self.vy = 0
        self.vx *= max(0.0, 1 - dt * self.drag)
        return hit_wall, landed

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, ctx, bounds, hit_wall, landed

    def _attack_rect(self):
        return self.rect

    def _deal_contact_damage(self, ctx, attack_state=None):
        # Several attacks commit and enter recovery on the exact landing/wall
        # frame. Preserve the state that began that frame so the dangerous
        # impact cannot become harmless merely because the state label changed
        # before collision was evaluated.
        active_state = self.state in self.contact_states or attack_state in self.contact_states
        if self.attack_suppressed > 0 or not active_state:
            return
        rect_for_state = getattr(self, "attack_rect_for_state", None)
        rect = (rect_for_state(attack_state if attack_state in self.contact_states else self.state)
                if rect_for_state else self._attack_rect())
        if rect.colliderect(ctx.player.rect) and ctx.player.hurt(self.x):
            ctx.sounds.play("ink")
            ctx.camera.kick(4, .16)
            _player_hit_feedback(ctx, self.x)

    def _update_projectiles(self, dt, ctx):
        for projectile in self.projectiles:
            projectile.update(dt, ctx)
        self.projectiles = [p for p in self.projectiles if p.life > 0]

    def update(self, dt, ctx, bounds):
        if self.dead:
            return
        self._tick(dt)
        self._update_temporary_erases(dt)
        self._read_player_weapon(ctx)
        if self.dead:
            return
        attack_state = self.state
        if self.state not in {"scan", "quickdraw", "lock", "charge", "agent_aim", "agent_burst"}:
            self.aim_target = (ctx.player.center_x, ctx.player.rect.centery)
        staggered = self.hit_stun > 0 and (
            self.attack_suppressed > 0 or self.state not in self.contact_states)
        if staggered:
            # Let knockback move the body while freezing its attack timeline.
            # Light hits do not cancel already committed contact attacks.
            self.state_time += dt
        else:
            self._think(dt, ctx, bounds)
        if not self.is_boss and self.state != attack_state:
            if self.state in {"drop_warn", "flare", "dive_telegraph"}:
                ctx.sounds.play("enemy_telegraph_air")
            elif self.state in {"prickle", "agent_aim", "quickdraw", "aim", "scan"}:
                ctx.sounds.play("enemy_telegraph_ranged")
            elif self.state in {"tail_warn", "ram_warn", "slam_telegraph", "charge_telegraph"}:
                ctx.sounds.play("enemy_telegraph_heavy")
        hit_wall, landed = self._integrate(dt, bounds)
        self._after_integrate(dt, ctx, bounds, hit_wall, landed)
        self._deal_contact_damage(ctx, attack_state)
        self._update_projectiles(dt, ctx)

    def _erase_floor_temporarily(self, ctx, center_x, width=125, duration=2.0):
        """Erase a safe floor interval, restoring it without clobbering edits."""

        if self._temporary_erases:
            return False
        candidates = []
        for platform in getattr(ctx.world, "platforms", ()):
            if not platform.enabled or platform.layer != ctx.world.active_layer:
                continue
            if platform.thickness > 70 or platform.x2 - platform.x1 < width + 30:
                continue
            if "gate" in platform.name or "entrance" in platform.name or "exit" in platform.name:
                continue
            if platform.x1 + 20 <= center_x <= platform.visible_x2 - 20:
                distance = abs(platform.y_at(center_x) - self.ground_y)
                if distance < 75:
                    candidates.append((distance, platform))
        if not candidates:
            return False
        platform = min(candidates, key=lambda item: item[0])[1]
        # A committed eraser edit may threaten the player's route, but it must
        # never delete the pixels already beneath both feet in the landing
        # frame.  Shift the cut to the nearest valid side; the resulting hole
        # still removes collision and demands a jump/dash on the next beat.
        player_x = ctx.player.center_x
        safe_radius = width * .5 + ctx.player.WIDTH + 24
        if abs(center_x - player_x) < safe_radius:
            minimum = platform.x1 + width * .5 + 10
            maximum = platform.visible_x2 - width * .5 - 10
            options = [max(minimum, min(maximum, player_x - safe_radius)),
                       max(minimum, min(maximum, player_x + safe_radius))]
            options = [value for value in options
                       if minimum <= value <= maximum and abs(value - player_x) >= safe_radius - 2]
            if options:
                center_x = min(options, key=lambda value: abs(value - center_x))
        start = max(platform.x1 + 8, center_x - width / 2)
        end = min(platform.visible_x2 - 8, center_x + width / 2)
        before = list(platform.erased)
        platform.erase(start, end)
        after = list(platform.erased)
        self._temporary_erases.append({
            "platform": platform,
            "before": before,
            "after": after,
            "time": float(duration),
        })
        for index in range(9):
            x = start + (end - start) * (index + .5) / 9
            ctx.particles.eraser_dust(x, platform.y_at(x), 2)
        return True

    def _update_temporary_erases(self, dt):
        keep = []
        for effect in self._temporary_erases:
            effect["time"] -= dt
            if effect["time"] > 0:
                keep.append(effect)
                continue
            platform = effect["platform"]
            # Restore only if nobody else edited the same stroke meanwhile.
            if platform.erased == effect["after"]:
                platform.erased = list(effect["before"])
        self._temporary_erases = keep

    def _restore_temporary_erases(self, force=False):
        for effect in self._temporary_erases:
            platform = effect["platform"]
            if force and platform.erased == effect["after"]:
                platform.erased = list(effect["before"])
        self._temporary_erases.clear()

    def _base_color(self):
        return (151, 47, 49) if self.hit_flash > 0 else INK

    def _draw_telegraph(self, surface, camera, renderer, cue="!"):
        x = camera.screen_x(self.x)
        y = round(self.y - self.height / 2 + camera.offset_y)
        # A tightening construction arc communicates the time until impact.
        progress = self.pose_progress
        radius = self.radius + 9 + round((1-progress)*9)
        rect = pygame.Rect(x-radius, y-radius, radius*2, radius*2)
        pygame.draw.arc(surface, (151, 66, 62), rect, -math.pi/2,
                        -math.pi/2 + max(.05, progress*math.tau), 3)
        for side in (-1, 1):
            pygame.draw.line(surface, (151, 66, 62),
                             (x+side*(radius+3), y), (x+side*(radius+9), y), 2)
        label = renderer.font_small.render(cue, True, (145, 57, 55))
        surface.blit(label, (x-label.get_width()//2, y-radius-25))
        if self.state in {"scan", "quickdraw", "lock", "charge", "agent_aim", "agent_burst"} and self.aim_target:
            origin = (x, round(self.y-self.height*.55+camera.offset_y))
            target = (camera.screen_x(self.aim_target[0]),
                      round(self.aim_target[1]+camera.offset_y))
            _dashed_line(surface, (164, 90, 83), origin, target, 1, 8, 8)
            pygame.draw.circle(surface, (151, 66, 62), target, 7, 1)
        if self.state in {"sheath", "tail_warn", "ram_warn", "rustle"}:
            end = x+self.facing*(125 if self.state == "sheath" else 175)
            floor = round(self.ground_y+camera.offset_y)-4
            _dashed_line(surface, (151, 66, 62), (x, floor), (end, floor), 2)
            pygame.draw.lines(surface, (151, 66, 62), False,
                [(end-self.facing*9, floor-5), (end, floor),
                 (end-self.facing*9, floor+5)], 2)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        renderer.scribble(surface, (x, y - self.height // 2), self.radius,
                          self.seed, 4, self._base_color())
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# ---------------------------------------------------------------------------
# Distinct regular combat roles


class RulerGuard(AdvancedEnemy):
    kind = "ruler_guard"
    width, height, radius = 34, 70, 18
    base_hp = 3
    contact_states = ("thrust",)

    def _is_front_hit(self, source_x):
        return (float(source_x) - self.x) * self.facing >= -2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        tags = _tag_set(tags)
        if self._is_front_hit(source_x) and not ({"pierce", "backstab", "eraser",
                                                  "finisher", "heroic"} & tags):
            self._blocked_feedback(ctx, self.x + self.facing * 18, self.y - 37)
            self.vx -= self.facing * 35
            return False
        return super().hit_from_weapon(amount, knockback, source_x, tags, ctx)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            if abs(distance) > 24:
                self.facing = 1 if distance > 0 else -1
            self.vx += self.facing * 760 * dt
            if self.state_time <= 0 and abs(distance) > 165:
                self.state_time = .14
            elif self.state_time <= 0 or abs(distance) < 105:
                self._set_state("brace", .52)
        elif self.state == "brace":
            self.vx *= .55
            if self.state_time <= 0:
                self._set_state("thrust", .32)
                self.vx = self.facing * 390
        elif self.state == "thrust" and self.state_time <= 0:
            self._set_state("recover", .72)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .5)

    def _attack_rect(self):
        rect = self.rect
        if self.facing > 0:
            return pygame.Rect(rect.centerx, rect.y + 10, 64, rect.height - 15)
        return pygame.Rect(rect.centerx - 64, rect.y + 10, 64, rect.height - 15)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        if self.state == "brace":
            self._draw_telegraph(surface, camera, renderer, "BACK")
        # The ruler is the shield and most of the body. A separate pencil
        # spear on the unprotected side makes the flank rule visible at once.
        shield_x = x + self.facing * 10
        ruler = pygame.Rect(shield_x - 7, y - 69, 14, 67)
        pygame.draw.rect(surface, (191, 153, 93), ruler)
        pygame.draw.rect(surface, color, ruler, 2)
        for mark in range(8):
            py = y - 64 + mark * 8
            reach = 6 if mark % 2 else 10
            pygame.draw.line(surface, color, (shield_x, py),
                             (shield_x - self.facing * reach, py), 1)
        head = (x - self.facing * 7, y - 51)
        rough_circle(surface, color, head, 7, self.seed + 31, 2, 2,
                     wobble=.8)
        pygame.draw.circle(surface, color,
                           (head[0] + self.facing * 2, head[1]), 2)
        spear_x = x - self.facing * 15
        pygame.draw.line(surface, (128, 92, 45),
                         (spear_x, y - 59), (spear_x, y + 1), 3)
        pygame.draw.polygon(surface, PAPER,
                            [(spear_x, y - 70), (spear_x - 5, y - 58),
                             (spear_x + 5, y - 58)])
        pygame.draw.polygon(surface, color,
                            [(spear_x, y - 70), (spear_x - 5, y - 58),
                             (spear_x + 5, y - 58)], 1)
        pygame.draw.line(surface, color, (x - self.facing * 4, y - 13),
                         (x - self.facing * 13, y), 3)
        if self.state == "recover":
            renderer.doodle_text(surface, "< back", (x - 36, y - 91),
                                 INK_LIGHT, renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class PaperWasp(AdvancedEnemy):
    kind = "paper_wasp"
    width, height, radius = 46, 34, 22
    base_hp = 3
    uses_gravity = False
    drag = 2.3
    contact_states = ("dive",)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.hover_y = self.ground_y - self.rng.randint(135, 185)
        self.y = self.hover_y
        self.target_x = self.x
        self.dive_vx = 0.0
        self._set_state("hover", .85)

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        if self.state == "stuck":
            amount = max(2, int(amount))
        return super().hit_from_weapon(amount, knockback, source_x, tags, ctx)

    def _think(self, dt, ctx, bounds):
        del bounds
        if self.state == "hover":
            desired = ctx.player.center_x + (-125 if ctx.player.center_x > self.x else 125)
            self.vx += max(-90, min(90, desired - self.x)) * dt * 1.6
            self.y += (self.hover_y + math.sin(self.time * 4 + self.seed) * 16 - self.y) * min(1, dt * 5)
            if self.state_time <= 0:
                self.target_x = ctx.player.center_x
                self._set_state("dive_telegraph", .62)
        elif self.state == "dive_telegraph":
            self.vx *= .65
            if self.state_time <= 0:
                self._set_state("dive", .9)
                drop = max(1.0, self.ground_y - self.y)
                impact_time = (
                    -430 + math.sqrt(430 ** 2 + 2 * 370 * drop)
                ) / 370
                self.dive_vx = (self.target_x - self.x) / max(.18, impact_time)
                self.vx = self.dive_vx
                self.vy = 430
        elif self.state == "dive":
            self.vx = self.dive_vx
            self.y += self.vy * dt
            self.vy += 370 * dt
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.vx = self.vy = 0
                self._set_state("stuck", .82)
                ctx.camera.kick(3, .13)
                ctx.particles.paper_puff(self.x, self.y, 9)
        elif self.state == "stuck":
            if self.state_time <= 0:
                self._set_state("rise", .7)
        elif self.state == "rise":
            self.y += (self.hover_y - self.y) * min(1, dt * 6)
            if self.state_time <= 0:
                self.y = self.hover_y
                self._set_state("hover", .85)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        wing = 8 + round(math.sin(self.time * 18) * 5)
        left_wing = torn_wing(
            surface, [(x - 2, y - 20), (x - 33, y - 28 - wing),
                      (x - 23, y - 14), (x - 17, y - 3)],
            color, PAPER, self.seed + 50,
        )
        right_wing = torn_wing(
            surface, [(x + 2, y - 20), (x + 33, y - 28 + wing),
                      (x + 23, y - 14), (x + 17, y - 3)],
            color, PAPER, self.seed + 70,
        )
        del left_wing, right_wing
        body = [(x - 12, y - 24), (x + 2, y - 32),
                (x + 16, y - 18), (x + 5, y - 6), (x - 11, y - 9)]
        pygame.draw.polygon(surface, (220, 214, 194), body)
        pygame.draw.lines(surface, color, True, body, 2)
        pygame.draw.line(surface, color, (x - 7, y - 25), (x + 9, y - 9), 1)
        staples(surface, [(x - 3, y - 18), (x + 8, y - 17)])
        pygame.draw.line(surface, color, (x + self.facing * 10, y - 20),
                         (x + self.facing * 23, y - 22), 2)
        if self.state == "dive_telegraph":
            self._draw_telegraph(surface, camera, renderer, "v")
            tx = camera.screen_x(self.target_x)
            jitter_line(surface, RED_RULE, (tx - 22, round(self.ground_y + camera.offset_y)),
                        (tx + 22, round(self.ground_y + camera.offset_y)), 2,
                        self.seed + 400, 2, 1.4)
        elif self.state == "stuck":
            renderer.doodle_text(surface, "STUCK", (x - 28, y - 62),
                                 INK_LIGHT, renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class EraserBrute(AdvancedEnemy):
    kind = "eraser_brute"
    width, height, radius = 72, 64, 35
    base_hp = 5
    contact_states = ("slam",)

    def _is_vulnerable(self):
        return self.state == "recover"

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
            self.vx += self.facing * 720 * dt
            if self.state_time <= 0 and abs(distance) > 115:
                self.state_time = .14
            elif self.state_time <= 0:
                self._set_state("slam_telegraph", .78)
        elif self.state == "slam_telegraph":
            self.vx *= .45
            if self.state_time <= 0:
                self._set_state("slam", 1.1)
                self.vy = -355
                self.vx = self.facing * min(310, max(175, abs(distance) * 1.6))
        elif self.state == "slam":
            self.vx = self.facing * min(310, max(150, abs(distance) * 1.6))
            if self.state_time <= 0:
                self._set_state("recover", 1.25)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .65)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds, hit_wall
        if self.state == "slam" and landed:
            self._erase_floor_temporarily(ctx, self.x, 128, 2.25)
            ctx.camera.kick(7, .25)
            ctx.sounds.play("erase")
            self._set_state("recover", 1.28)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        if self.state == "slam_telegraph":
            self._draw_telegraph(surface, camera, renderer, "ERASE")
            pygame.draw.ellipse(surface, RED_RULE,
                                (x - 68, round(self.ground_y - 12 + camera.offset_y), 136, 18), 2)
        angle = -4 if self.state == "slam" else 2
        body = pygame.Surface((80, 58), pygame.SRCALPHA)
        pygame.draw.polygon(body, (218, 145, 145), [(4, 10), (72, 2), (79, 43), (12, 55)])
        pygame.draw.polygon(body, (239, 192, 181), [(4, 10), (16, 25), (12, 55), (0, 38)])
        pygame.draw.lines(body, color, True, [(4, 10), (72, 2), (79, 43), (12, 55)], 2)
        body = pygame.transform.rotate(body, angle)
        surface.blit(body, body.get_rect(center=(x, y - 31)))
        if self.state == "recover":
            renderer.doodle_text(surface, "soft side exposed", (x - 71, y - 92),
                                 INK_LIGHT, renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class CrumpledOne(AdvancedEnemy):
    kind = "crumpled_one"
    width, height, radius = 58, 54, 28
    base_hp = 5
    drag = 1.2
    contact_states = ("charge",)

    def _is_vulnerable(self):
        return self.state == "stunned"

    def _stun(self, ctx):
        if self.state == "stunned":
            return
        self.vx = -self.facing * 125
        self._set_state("stunned", 1.5)
        ctx.camera.kick(6, .22)
        ctx.sounds.play("paper_step")
        ctx.particles.paper_puff(self.x, self.y - 18, 15)

    def _think(self, dt, ctx, bounds):
        del dt, bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
            if self.state_time <= 0:
                self._set_state("charge_telegraph", .66)
        elif self.state == "charge_telegraph":
            self.vx *= .35
            if self.state_time <= 0:
                self._set_state("charge", 1.7)
                self.vx = self.facing * 520
        elif self.state == "charge":
            self.vx = self.facing * 520
            if self.state_time <= 0:
                # Wide rooms used to let the ball stop a few pixels before a
                # gate, drift into it while idle, then charge away forever
                # without ever exposing its only damage window.
                self._stun(ctx)
        elif self.state == "stunned":
            self.vx *= .5
            if self.state_time <= 0:
                self._set_state("idle", .62)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds, landed
        if self.state == "charge" and hit_wall:
            self._stun(ctx)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        rng = random.Random(self.seed)
        paper_ball = []
        for index in range(14):
            angle = math.tau * index / 14
            radius = rng.randrange(23, 31)
            paper_ball.append((round(x + math.cos(angle) * radius),
                               round(y - 27 + math.sin(angle) * radius * .86)))
        pygame.draw.polygon(surface, (225, 220, 202), paper_ball)
        pygame.draw.lines(surface, color, True, paper_ball, 3)
        # Creases all terminate at real folds; this is crumpled paper, not a
        # generic circular scribble with eyes pasted on it.
        for index in (1, 3, 6, 9, 12):
            point = paper_ball[index]
            kink = (round((point[0] + x) / 2 + rng.randrange(-5, 6)),
                    round((point[1] + y - 27) / 2 + rng.randrange(-4, 5)))
            pygame.draw.lines(surface, INK_LIGHT, False,
                              [point, kink, (x + rng.randrange(-5, 6),
                                             y - 27 + rng.randrange(-4, 5))], 1)
        eye_y = y - 34
        pygame.draw.ellipse(surface, color, (x - 14, eye_y - 4, 8, 7))
        pygame.draw.ellipse(surface, color, (x + 6, eye_y - 4, 8, 7))
        pygame.draw.circle(surface, PAPER,
                           (x - 10 + self.facing, eye_y - 1), 1)
        pygame.draw.circle(surface, PAPER,
                           (x + 10 + self.facing, eye_y - 1), 1)
        if self.state == "charge_telegraph":
            self._draw_telegraph(surface, camera, renderer, ">>>" if self.facing > 0 else "<<<")
        elif self.state == "stunned":
            for index in range(3):
                a = self.time * 3 + index * math.tau / 3
                pygame.draw.line(surface, INK_LIGHT,
                                 (x + math.cos(a) * 30, y - 65 + math.sin(a) * 8),
                                 (x + math.cos(a) * 36, y - 69 + math.sin(a) * 9), 2)
            renderer.doodle_text(surface, "UNCRUMPLED", (x - 64, y - 94),
                                 INK_LIGHT, renderer.font_small, 1)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class InkClone(AdvancedEnemy):
    kind = "ink_clone"
    width, height, radius = 28, 50, 17
    base_hp = 4
    contact_states = ("echo_slash",)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.memory = deque()
        self.echo_vx = 0.0
        self.echo_facing = -1
        self.echo_attack_serial = None
        self.echo_jump_serial = 0
        self.was_sample_airborne = False
        self.pressure_timer = 1.15

    def _think(self, dt, ctx, bounds):
        del bounds
        player = ctx.player
        self.pressure_timer = max(0.0, self.pressure_timer - dt)
        airborne = player.vy < -180
        jump_edge = airborne and not self.was_sample_airborne
        self.was_sample_airborne = airborne
        self.memory.append((
            self.time + .48,
            float(player.vx), int(player.facing),
            int(getattr(getattr(ctx, "weapons", None), "attack_serial",
                        getattr(player, "attack_serial", 0))), jump_edge,
        ))
        while self.memory and self.memory[0][0] <= self.time:
            _, sample_vx, sample_facing, attack_serial, jump_edge = self.memory.popleft()
            self.echo_vx = -sample_vx * .78
            self.echo_facing = -sample_facing
            if jump_edge and self.y >= self.ground_y:
                self.vy = -430
            if self.echo_attack_serial is None:
                self.echo_attack_serial = attack_serial
            elif attack_serial != self.echo_attack_serial:
                self.echo_attack_serial = attack_serial
                self.facing = self.echo_facing
                if self._set_state("echo_telegraph", .18):
                    self.pressure_timer = 1.25

        if self.state == "echo_telegraph":
            self.vx *= .5
            if self.state_time <= 0:
                self._set_state("echo_slash", .22)
        elif self.state == "echo_slash":
            if self.state_time <= 0:
                self._set_state("copy", .18)
        else:
            self.state = "copy"
            self.facing = self.echo_facing
            distance = player.center_x - self.x
            desired_vx = self.echo_vx
            # Mirroring a stationary corner camper used to leave the clone
            # motionless forever. It still copies ordinary movement, but adds
            # an imperfect catch-up stroke when the mirrored sample would
            # create a non-interactive safe pocket.
            if abs(distance) > 55:
                desired_vx = (1 if distance > 0 else -1) * max(190, abs(desired_vx))
                self.facing = 1 if distance > 0 else -1
            self.vx += (desired_vx - self.vx) * min(1, dt * 6)
            if self.pressure_timer <= 0 and abs(distance) < 62:
                self.facing = 1 if distance > 0 else -1
                if self._set_state("echo_telegraph", .24):
                    self.pressure_timer = 1.35

    def _attack_rect(self):
        rect = self.rect
        return pygame.Rect(
            rect.centerx if self.facing > 0 else rect.centerx - 52,
            rect.y + 5, 52, 38,
        )

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        # An imperfect mirrored stick figure, visibly denser than the player.
        head_y = y - 42
        pygame.draw.circle(surface, color, (x, head_y), 8, 3)
        pygame.draw.line(surface, color, (x, head_y + 8), (x, y - 16), 4)
        stride = math.sin(self.time * 11) * 8 if abs(self.vx) > 20 else 3
        pygame.draw.line(surface, color, (x, y - 16), (x - stride, y), 3)
        pygame.draw.line(surface, color, (x, y - 16), (x + stride, y), 3)
        pygame.draw.line(surface, color, (x, y - 29), (x - stride, y - 16), 3)
        pygame.draw.line(surface, color, (x, y - 29), (x + stride, y - 16), 3)
        pygame.draw.circle(surface, (92, 88, 89), (x + self.facing * 4, head_y - 1), 2)
        if self.state == "echo_telegraph":
            renderer.doodle_text(surface, "copy...", (x - 30, y - 82),
                                 INK_LIGHT, renderer.font_small, -1)
        if self.state == "echo_slash":
            end = x + self.facing * 48
            pygame.draw.arc(surface, RED_RULE,
                            (min(x, end) - 9, y - 55, abs(end - x) + 18, 54),
                            -1.0 if self.facing > 0 else math.pi - 1,
                            1.0 if self.facing > 0 else math.pi + 1, 2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class DoodleTurret(AdvancedEnemy):
    kind = "doodle_turret"
    width, height, radius = 48, 48, 24
    base_hp = 3
    uses_gravity = False

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.y = self.ground_y
        self.shot_count = 0
        self._set_state("idle", .7)

    def _think(self, dt, ctx, bounds):
        del dt, bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "idle" and self.state_time <= 0:
            self._set_state("aim", .58)
        elif self.state == "aim" and self.state_time <= 0:
            self.shot_count += 1
            origin_x, origin_y = self.x + self.facing * 20, self.y - 31
            speed, lift = _ballistic_velocity(
                origin_x, origin_y,
                ctx.player.center_x, ctx.player.rect.centery,
                210, 410,
            )
            self.projectiles.append(PaperProjectile(
                origin_x, origin_y, speed, lift, "ink", 3.2, 7, 210,
            ))
            if self.shot_count % 3 == 0:
                paper_speed, paper_lift = _ballistic_velocity(
                    self.x + self.facing * 18, self.y - 27,
                    ctx.player.center_x, ctx.player.rect.centery - 16,
                    260, 385,
                )
                self.projectiles.append(PaperProjectile(
                    self.x + self.facing * 18, self.y - 27,
                    paper_speed, paper_lift, "paper", 3.0, 7, 260,
                ))
            self._set_state("idle", 1.0)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        note = [(x - 25, y), (x - 20, y - 43), (x + 17, y - 41),
                (x + 25, y - 4), (x + 15, y), (x + 9, y - 9), (x + 2, y)]
        pygame.draw.polygon(surface, (233, 228, 208), note)
        pygame.draw.lines(surface, color, True, note, 3)
        # A single wet ink reservoir drives a ruler-straight nib barrel.
        pygame.draw.circle(surface, (58, 47, 72), (x - self.facing * 5, y - 26), 11)
        rough_circle(surface, color, (x - self.facing * 5, y - 26), 12,
                     self.seed + 88, 2, 1, wobble=1.1)
        barrel_start = x + self.facing * 5
        barrel_end = x + self.facing * 25
        pygame.draw.line(surface, color, (barrel_start, y - 27),
                         (barrel_end, y - 29), 5)
        pygame.draw.polygon(surface, PAPER,
                            [(barrel_end, y - 35),
                             (barrel_end + self.facing * 10, y - 29),
                             (barrel_end, y - 23)])
        pygame.draw.polygon(surface, color,
                            [(barrel_end, y - 35),
                             (barrel_end + self.facing * 10, y - 29),
                             (barrel_end, y - 23)], 2)
        pygame.draw.line(surface, INK_LIGHT, (x - 13, y - 11), (x + 8, y - 11), 1)
        if self.state == "aim":
            self._draw_telegraph(surface, camera, renderer, "o")
            px, py = camera.screen_x(self.x + self.facing * 120), y - 31
            jitter_line(surface, (153, 70, 67), (x + self.facing * 20, y - 31),
                        (px, py), 1, self.seed + 90, 1, .6)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# ---------------------------------------------------------------------------
# Mini-boss tools


class CompassBoss(AdvancedEnemy):
    kind = "compass"
    width, height, radius = 96, 112, 47
    base_hp = 6
    uses_gravity = False
    is_boss = True

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.angle = -2.5
        self.window_hits = 0
        self._set_state("idle", .75)

    def _is_vulnerable(self):
        return self.state == "stuck" and self.window_hits < 2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
        return dealt

    def _think(self, dt, ctx, bounds):
        del bounds
        if self.state == "idle":
            distance = ctx.player.center_x - self.x
            self.facing = 1 if distance > 0 else -1
            if abs(distance) > 118:
                self.vx += self.facing * 980 * dt
            if self.state_time <= 0 and abs(distance) > 125:
                self.state_time = .12
            elif self.state_time <= 0:
                self.vx *= .25
                self._set_state("sweep_telegraph", .72)
        elif self.state == "sweep_telegraph" and self.state_time <= 0:
            self._set_state("sweep", 1.28)
        elif self.state == "sweep":
            progress = 1 - max(0, self.state_time) / 1.28
            # Positive sine values put the needle in the player's ground lane.
            # The old negative arc swept entirely above a standing stickman.
            self.angle = (2.8 - progress * 2.45) if self.facing > 0 else (.35 + progress * 2.45)
            center = (self.x, self.y - 75)
            tip = (center[0] + math.cos(self.angle) * 105,
                   center[1] + math.sin(self.angle) * 105)
            danger = pygame.Rect(round(tip[0] - 13), round(tip[1] - 13), 26, 26)
            if danger.colliderect(ctx.player.rect) and ctx.player.hurt(self.x):
                ctx.sounds.play("ink")
                ctx.camera.kick(4, .15)
                _player_hit_feedback(ctx, self.x)
            if self.state_time <= 0:
                self.angle = math.pi / 2
                self.window_hits = 0
                self._set_state("stuck", 1.42)
                ctx.camera.kick(5, .2)
        elif self.state == "stuck" and self.state_time <= 0:
            self._set_state("idle", .68)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        pivot = (x, y - 76)
        if self.state == "sweep_telegraph":
            self._draw_telegraph(surface, camera, renderer, "ARC")
            pygame.draw.arc(surface, RED_RULE, (x - 116, y - 187, 232, 210), .1, math.pi - .1, 2)
        left_tip = (x - 53, y)
        moving_tip = (round(x + math.cos(self.angle) * 105),
                      round(y - 76 + math.sin(self.angle) * 105))
        pygame.draw.line(surface, color, pivot, left_tip, 5)
        pygame.draw.line(surface, color, pivot, moving_tip, 5)
        pygame.draw.circle(surface, PAPER, pivot, 11)
        pygame.draw.circle(surface, color, pivot, 11, 3)
        pygame.draw.circle(surface, color, left_tip, 4)
        pygame.draw.line(surface, color, moving_tip,
                         (moving_tip[0], moving_tip[1] + 12), 3)
        if self.state == "stuck":
            renderer.doodle_text(surface, "NEEDLE STUCK — HIT", (x - 93, y - 151),
                                 INK_LIGHT, renderer.font_small, -2)
        _health_scratches(surface, camera, self, 143)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class StaplerBoss(AdvancedEnemy):
    kind = "stapler"
    width, height, radius = 120, 72, 56
    base_hp = 7
    uses_gravity = False
    is_boss = True

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.window_hits = 0
        self.snap_done = False
        self._set_state("idle", .8)

    def _is_vulnerable(self):
        return self.state == "reload" and self.window_hits < 3

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
        return dealt

    def _snap_rect(self):
        if self.facing > 0:
            return pygame.Rect(round(self.x), round(self.ground_y - 54), 142, 58)
        return pygame.Rect(round(self.x - 142), round(self.ground_y - 54), 142, 58)

    def _think(self, dt, ctx, bounds):
        del bounds
        if self.state == "idle":
            distance = ctx.player.center_x - self.x
            self.facing = 1 if distance > 0 else -1
            if abs(distance) > 155:
                self.vx += self.facing * 1050 * dt
            if self.state_time <= 0 and abs(distance) > 170:
                self.state_time = .12
            elif self.state_time <= 0:
                self.vx *= .2
                self._set_state("snap_telegraph", .72)
        elif self.state == "snap_telegraph" and self.state_time <= 0:
            self.snap_done = False
            self._set_state("snap", .28)
        elif self.state == "snap":
            if not self.snap_done:
                self.snap_done = True
                if self._snap_rect().colliderect(ctx.player.rect) and ctx.player.hurt(self.x):
                    ctx.sounds.play("ink")
                    ctx.camera.kick(7, .22)
                    _player_hit_feedback(ctx, self.x)
                if self.hp <= 4:
                    for vy in (-220, -135):
                        self.projectiles.append(PaperProjectile(
                            self.x + self.facing * 50, self.y - 24,
                            self.facing * 300, vy, "staple", 2.6, 5, 260,
                        ))
            if self.state_time <= 0:
                self.window_hits = 0
                self._set_state("reload", 1.85)
        elif self.state == "reload" and self.state_time <= 0:
            self._set_state("idle", .7)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        open_amount = .75 if self.state == "reload" else .42 if self.state == "snap_telegraph" else .12
        direction = self.facing
        base_start = (x - direction * 54, y - 4)
        base_end = (x + direction * 65, y - 4)
        pygame.draw.line(surface, color, base_start, base_end, 10)
        hinge = (x - direction * 48, y - 13)
        top_end = (round(x + direction * 64), round(y - 17 - open_amount * 65))
        pygame.draw.line(surface, (76, 74, 72), hinge, top_end, 16)
        pygame.draw.line(surface, color, hinge, top_end, 3)
        pygame.draw.circle(surface, PAPER, hinge, 7)
        pygame.draw.circle(surface, color, hinge, 7, 2)
        if self.state == "snap_telegraph":
            self._draw_telegraph(surface, camera, renderer, "SNAP")
            danger = self._snap_rect()
            pygame.draw.line(surface, RED_RULE,
                             (camera.screen_x(danger.left), round(danger.bottom + camera.offset_y)),
                             (camera.screen_x(danger.right), round(danger.bottom + camera.offset_y)), 3)
        elif self.state == "reload":
            renderer.doodle_text(surface, "OPEN", (x - 22, y - 121),
                                 INK_LIGHT, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 130)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class FailedSketchBoss(AdvancedEnemy):
    kind = "failed_sketch"
    width, height, radius = 86, 88, 43
    base_hp = 8
    is_boss = True
    contact_states = ("charge", "slam")

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.patterns = ("charge", "ink_rain", "slam")
        self.pattern_index = -1
        self.pattern = "charge"
        self.shot_timer = 0.0
        self.mirror_weapon = "pencil_blade"
        self.window_hits = 0
        self._set_state("sketching", .85)

    def _is_vulnerable(self):
        return self.state == "unravel" and self.window_hits < 3

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
        return dealt

    def _choose_pattern(self, ctx):
        self.pattern_index = (self.pattern_index + 1) % len(self.patterns)
        self.pattern = self.patterns[self.pattern_index]
        self.facing = 1 if ctx.player.center_x > self.x else -1
        self._set_state("telegraph", .68)

    def _unravel(self, ctx):
        self.vx = 0
        self.window_hits = 0
        self._set_state("unravel", 1.45)
        ctx.particles.paper_puff(self.x, self.y - 38, 14)

    def _think(self, dt, ctx, bounds):
        del bounds
        if self.state == "sketching" and self.state_time <= 0:
            self._choose_pattern(ctx)
        elif self.state == "telegraph" and self.state_time <= 0:
            if self.pattern == "charge":
                # Continue to the arena stroke instead of expiring halfway to
                # a player who waited at the far margin.
                self._set_state("charge", 3.4)
                self.vx = self.facing * 460
            elif self.pattern == "ink_rain":
                self.shot_timer = 0
                self._set_state("ink_rain", 1.3)
            else:
                self._set_state("slam", 1.2)
                self.vy = -440
                self.vx = self.facing * 150
        elif self.state == "charge":
            self.vx = self.facing * 460
            if self.state_time <= 0:
                self._unravel(ctx)
        elif self.state == "ink_rain":
            self.shot_timer -= dt
            if self.shot_timer <= 0:
                self.shot_timer = .28
                target_x = ctx.player.center_x + self.rng.uniform(-95, 95)
                self.projectiles.append(PaperProjectile(
                    target_x, 165, self.rng.uniform(-20, 20), 85,
                    "ink", 3.0, 8, 390,
                ))
            if self.state_time <= 0:
                self._unravel(ctx)
        elif self.state == "slam" and self.state_time <= 0:
            self._unravel(ctx)
        elif self.state == "unravel" and self.state_time <= 0:
            self._set_state("sketching", .55)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds
        if self.state == "charge" and hit_wall:
            self._unravel(ctx)
        elif self.state == "slam" and landed:
            ctx.camera.kick(6, .22)
            self._unravel(ctx)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        draft = (102, 133, 146)
        correction = (151, 66, 62)
        head = (x - 5, y - 77)
        shoulder = (x, y - 53)
        hip = (x + 7, y - 24)

        # This boss is a rejected construction drawing, not another ink ball:
        # blue guide geometry remains visible beneath a crooked partial body.
        pygame.draw.circle(surface, draft, head, 19, 1)
        pygame.draw.line(surface, draft, (head[0] - 22, head[1]),
                         (head[0] + 22, head[1]), 1)
        pygame.draw.line(surface, draft, (head[0], head[1] - 22),
                         (head[0], head[1] + 22), 1)
        pygame.draw.arc(surface, color, (head[0] - 17, head[1] - 18, 35, 37),
                        .15, math.tau - .55, 3)
        pygame.draw.circle(surface, color,
                           (head[0] + self.facing * 6, head[1] - 2), 3)
        jitter_line(surface, color, (head[0], head[1] + 18), shoulder,
                    3, self.seed + 701, 2, 1.3)
        jitter_line(surface, color, shoulder, hip, 4,
                    self.seed + 702, 2, 1.5)
        pygame.draw.ellipse(surface, draft, (x - 22, y - 57, 45, 35), 1)

        left_elbow, left_hand = (x - 29, y - 39), (x - 53, y - 12)
        right_elbow, right_hand = (x + 34, y - 43), (x + 58, y - 20)
        if self.pattern == "charge":
            _dashed_line(surface, correction, shoulder, left_hand, 2)
            pygame.draw.circle(surface, correction, left_elbow, 8, 1)
        else:
            pygame.draw.lines(surface, color, False,
                              [shoulder, left_elbow, left_hand], 4)
        if self.pattern == "ink_rain":
            _dashed_line(surface, correction, shoulder, right_hand, 2)
            pygame.draw.circle(surface, correction, right_elbow, 8, 1)
        else:
            pygame.draw.lines(surface, color, False,
                              [shoulder, right_elbow, right_hand], 4)

        left_knee, left_foot = (x - 18, y - 9), (x - 39, y + 1)
        right_knee, right_foot = (x + 29, y - 7), (x + 47, y + 1)
        pygame.draw.lines(surface, color, False, [hip, left_knee, left_foot], 4)
        if self.pattern == "slam":
            _dashed_line(surface, correction, hip, right_foot, 2)
            pygame.draw.circle(surface, correction, right_knee, 8, 1)
        else:
            pygame.draw.lines(surface, color, False, [hip, right_knee, right_foot], 4)

        # A rejected shoulder joint and an off-register correction arrow make
        # the reason for the name readable even while the boss is idle.
        pygame.draw.circle(surface, correction, shoulder, 10, 1)
        _dashed_line(surface, correction, (x + 61, y - 91), (x + 25, y - 62), 2, 6, 4)
        pygame.draw.lines(surface, correction, False,
                          [(x + 30, y - 72), (x + 25, y - 62), (x + 36, y - 63)], 2)
        if self.state == "telegraph":
            cue = {"charge": ">>>", "ink_rain": "INK v", "slam": "!"}[self.pattern]
            self._draw_telegraph(surface, camera, renderer, cue)
        elif self.state == "unravel":
            renderer.doodle_text(surface, "LOOSE LINES", (x - 64, y - 116),
                                 INK_LIGHT, renderer.font_small, -2)
        _health_scratches(surface, camera, self, 125)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# ---------------------------------------------------------------------------
# Major pre-finale boss


class ArtistMistakeBoss(AdvancedEnemy):
    """Three-phase boss whose own committed edits expose its loose graphite.

    Phase 1 uses a cross-out charge.  Phase 2 chains a charge and an erasing
    slam before opening.  Phase 3 chains charge, erasing slam, and mirrored ink
    storm.  Only the subsequent ``unravel`` state takes damage, capped at two
    hits per opening.  Even a perfect player therefore has to master repeated
    mechanics cycles; first encounters generally last one to two minutes
    without an inflated health pool.
    """

    kind = "artist_mistake"
    width, height, radius = 112, 116, 55
    base_hp = 15
    is_boss = True
    contact_states = ("crossout", "erase_slam")
    drag = 2.0

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.window_hits = 0
        self.combo_done = 0
        self.pattern_cursor = -1
        self.pattern = "crossout"
        self.shot_timer = 0.0
        self._set_state("intro", 1.15)

    def _phase_for_hp(self):
        return 1 if self.hp > 10 else 2 if self.hp > 5 else 3

    def _is_vulnerable(self):
        return self.state == "unravel" and self.window_hits < 2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        old_phase = self.phase
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if not dealt or self.dead:
            return dealt
        self.window_hits += 1
        new_phase = self._phase_for_hp()
        if new_phase > old_phase:
            self.phase = new_phase
            self.combo_done = 0
            self.pattern_cursor = -1
            self._set_state("phase_shift", 1.15)
            ctx.level.toast = "the graphite cracks — a new pattern"
            ctx.level.toast_time = 2.4
            ctx.particles.paper_puff(self.x, self.y - 55, 20)
            ctx.camera.kick(6, .24)
        return dealt

    def _start_next_pattern(self, ctx):
        patterns = {
            1: ("crossout",),
            2: ("crossout", "erase_slam"),
            3: ("crossout", "erase_slam", "mirror_storm"),
        }[self.phase]
        self.pattern_cursor = (self.pattern_cursor + 1) % len(patterns)
        self.pattern = patterns[self.pattern_cursor]
        if self.pattern == "proof_volley":
            self.mirror_weapon = getattr(getattr(ctx, "weapons", None),
                                         "current_id", "pencil_blade")
        self.facing = 1 if ctx.player.center_x > self.x else -1
        duration = .72 if self.phase == 1 else .62
        self._set_state("boss_telegraph", duration)

    def _launch_pattern(self, ctx):
        self.facing = 1 if ctx.player.center_x > self.x else -1
        if self.pattern == "crossout":
            # The charge resolves on a wall collision. A generous failsafe
            # duration keeps even the widest authored boss arena reachable.
            self._set_state("crossout", 3.5)
            self.vx = self.facing * (470 + self.phase * 28)
        elif self.pattern == "erase_slam":
            self._set_state("erase_slam", 1.35)
            self.vy = -485
            self.vx = self.facing * 185
        else:
            self.shot_timer = 0
            self.vx = 0
            self._set_state("mirror_storm", 1.55)

    def _pattern_finished(self, ctx):
        self.combo_done += 1
        if self.combo_done >= self.phase:
            self.combo_done = 0
            self.window_hits = 0
            self.vx = 0
            # A correct dash-through leaves player and boss on opposite sides
            # of a wide arena. This window covers the run-back plus one clear
            # attack decision; the old 1.72 s expired just before weapon range.
            self._set_state("unravel", 2.65)
            ctx.particles.paper_puff(self.x, self.y - 48, 18)
            ctx.level.toast = "the mistake's outline has come loose"
            ctx.level.toast_time = 1.8
        else:
            # A charge that ends at an arena stroke can leave the player
            # between the boss and the closed gate. Back away before chaining
            # the next edit so corner pressure stays threatening but fair.
            self.vx = -self.facing * 520
            self._set_state("combo_reset", .66)

    def _think(self, dt, ctx, bounds):
        if self.state in ("intro", "phase_shift") and self.state_time <= 0:
            self._start_next_pattern(ctx)
        elif self.state == "combo_reset" and self.state_time <= 0:
            self.vx = 0
            self._start_next_pattern(ctx)
        elif self.state == "boss_telegraph" and self.state_time <= 0:
            self._launch_pattern(ctx)
        elif self.state == "crossout":
            self.vx = self.facing * (470 + self.phase * 28)
            if self.state_time <= 0:
                self._pattern_finished(ctx)
        elif self.state == "erase_slam" and self.state_time <= 0:
            self._erase_boss_floor(ctx, bounds)
            self._pattern_finished(ctx)
        elif self.state == "mirror_storm":
            self.shot_timer -= dt
            if self.shot_timer <= 0:
                self.shot_timer = .24
                # Alternating mirrored diagonals leave a readable centre gap.
                direction = -1 if int(self.time / .24) % 2 else 1
                self.projectiles.append(PaperProjectile(
                    self.x + direction * 38, self.y - 72,
                    direction * (190 + self.phase * 20), -270,
                    "ink", 3.2, 9, 310,
                ))
                self.projectiles.append(PaperProjectile(
                    self.x - direction * 32, self.y - 52,
                    -direction * 145, -190,
                    "paper", 3.0, 7, 280,
                ))
            if self.state_time <= 0:
                self._pattern_finished(ctx)
        elif self.state == "unravel" and self.state_time <= 0:
            self._start_next_pattern(ctx)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt
        if self.state == "crossout" and hit_wall:
            ctx.camera.kick(7, .24)
            ctx.sounds.play("paper_step")
            self._pattern_finished(ctx)
        elif self.state == "erase_slam" and landed:
            self._erase_boss_floor(ctx, bounds)
            ctx.camera.kick(8, .28)
            ctx.sounds.play("erase")
            self._pattern_finished(ctx)

    def _erase_boss_floor(self, ctx, bounds):
        # Never cut the only floor directly against a locked arena gate.  The
        # red ellipse still demands a dash, but both sides always retain a
        # visible landing strip instead of creating a checkpoint death loop.
        center = max(bounds[0] + 170, min(bounds[1] - 170, self.x))
        return self._erase_floor_temporarily(ctx, center, 145, 2.25)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        correction = (139, 57, 58)
        body = [
            (x - 58, y - 53), (x - 43, y - 90), (x - 12, y - 105),
            (x + 17, y - 91), (x + 53, y - 71), (x + 58, y - 35),
            (x + 31, y - 21), (x - 31, y - 24),
        ]
        # A recognisable but anatomically impossible notebook creature: paper
        # remains inside its outline, unlike the dense final Scribble Giant.
        pygame.draw.polygon(surface, PAPER, body)
        pygame.draw.lines(surface, color, True, body, 4)
        renderer.scribble(surface, (x + 3, y - 59), 20,
                          self.seed + self.phase, 4, color)
        # Mismatched heads face in incompatible directions.
        pygame.draw.ellipse(surface, PAPER, (x - 54, y - 112, 38, 34))
        pygame.draw.ellipse(surface, color, (x - 54, y - 112, 38, 34), 3)
        pygame.draw.polygon(surface, PAPER,
                            [(x + 26, y - 91), (x + 62, y - 103),
                             (x + 51, y - 67)])
        pygame.draw.lines(surface, color, True,
                          [(x + 26, y - 91), (x + 62, y - 103),
                           (x + 51, y - 67)], 3)
        pygame.draw.circle(surface, color,
                           (x - 35 + self.facing * 2, y - 98), 3)
        pygame.draw.circle(surface, color,
                           (x + 47 + self.facing * 2, y - 87), 3)
        # Four legs disagree about where the ground is; phase shifts add one
        # more bad idea instead of merely recolouring the same silhouette.
        legs = [(-43, -31, -55), (-15, -25, -7), (21, -24, 12), (45, -37, 57)]
        for index, (top_x, knee_x, foot_x) in enumerate(legs):
            pygame.draw.lines(surface, color, False,
                              [(x + top_x, y - 29),
                               (x + knee_x, y - 7 - (index % 2) * 7),
                               (x + foot_x, y + 1)], 4)
        jitter_line(surface, color, (x - 54, y - 61), (x - 91, y - 79),
                    4, self.seed + 880, 2, 2.0)
        if self.phase >= 2:
            pygame.draw.lines(surface, color, False,
                              [(x - 11, y - 104), (x - 2, y - 130),
                               (x + 7, y - 103)], 3)
        if self.phase >= 3:
            pygame.draw.circle(surface, PAPER, (x + 8, y - 106), 11)
            pygame.draw.circle(surface, color, (x + 8, y - 106), 11, 3)
            pygame.draw.circle(surface, color, (x + 11, y - 108), 2)

        renderer.doodle_text(surface, "NO.", (x + 61, y - 132),
                             correction, renderer.font_small, -2)
        jitter_line(surface, correction, (x - 67, y - 116), (x + 66, y - 10),
                    3, self.seed + 900, 2, 2.0)
        jitter_line(surface, correction, (x + 62, y - 118), (x - 64, y - 12),
                    3, self.seed + 901, 2, 2.0)

        if self.state == "boss_telegraph":
            cue = {
                "crossout": "CROSS OUT >>>" if self.facing > 0 else "<<< CROSS OUT",
                "erase_slam": "ERASE BELOW",
                "mirror_storm": "COPY BOTH SIDES",
            }[self.pattern]
            self._draw_telegraph(surface, camera, renderer, cue)
            if self.pattern == "erase_slam":
                pygame.draw.ellipse(surface, RED_RULE,
                                    (x - 82, round(self.ground_y - 12 + camera.offset_y), 164, 20), 3)
        elif self.state == "unravel":
            renderer.doodle_text(surface, "LOOSE — ERASE NOW", (x - 103, y - 153),
                                 (132, 56, 57), renderer.font_small, -2)
            pygame.draw.arc(surface, INK_LIGHT, (x - 69, y - 127, 138, 127), .1, 2.4, 2)
            pygame.draw.arc(surface, INK_LIGHT, (x - 69, y - 127, 138, 127), 3.2, 5.7, 2)
        elif self.state == "phase_shift":
            renderer.doodle_text(surface, f"PHASE {self.phase}", (x - 42, y - 147),
                                 INK_LIGHT, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 154)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class BabyFaceGiant(AdvancedEnemy):
    """A scripted three-attempt gag encounter, deliberately not a real boss."""

    kind = "baby_face_giant"
    width, height, radius = 188, 266, 88
    base_hp = 12
    uses_gravity = False
    is_boss = False
    block_hint = "THIS DRAWING IS UNFAIR ON PURPOSE"
    contact_states = ("page_slap",)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.empowered = False
        self.moustache_progress = 0.0
        self.pattern_index = 0
        self.attack_done = False
        self.step_clock = 0.0
        self.artist_paused = False
        self.signature_attempt = 1
        self._set_state("entrance", .82)

    def trigger_unfair_slap(self):
        """Guarantee the two authored losses even against perfect dodging."""
        if self.empowered or self.state in ("page_slap_warn", "page_slap"):
            return False
        self.attack_done = False
        self.vx = 0
        self._set_state("page_slap_warn", .72)
        return True

    def _is_vulnerable(self):
        # The joke does not nerf the boss; the Artist changes the player tool.
        return self.empowered

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        tags = _tag_set(tags)
        if self.empowered and "heroic" in tags:
            amount = max(self.hp, amount)
        return super().hit_from_weapon(amount, knockback, source_x, tags, ctx)

    def _hurt_twice(self, ctx, rect):
        if self.attack_done or not rect.colliderect(ctx.player.rect):
            return
        if ctx.player.hurt(self.x):
            self.attack_done = True
            # Attempts one and two are authored failures. The third attempt is
            # a real, survivable reversal once the Artist gives up being fair.
            if not self.empowered:
                ctx.player.health = 0
            else:
                ctx.player.health = max(0, ctx.player.health - 1)
            ctx.sounds.play("giant_stomp")
            ctx.camera.kick(10, .32)
            _player_hit_feedback(ctx, self.x)

    def _think(self, dt, ctx, bounds):
        if self.artist_paused:
            self.vx = 0
            self.state_time += dt
            return
        if self.state == "page_slap_warn":
            self.vx = 0
            if self.state_time <= 0:
                self.attack_done = False
                self._set_state("page_slap", .28)
            return
        if self.state == "page_slap":
            danger = pygame.Rect(round(bounds[0]), 320,
                                 round(bounds[1] - bounds[0]), 300)
            self._hurt_twice(ctx, danger)
            if self.state_time <= 0:
                self._set_state("recover", .72)
            return
        center = (bounds[0] + bounds[1]) * .5
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "entrance":
            target = ctx.player.center_x
            self.vx += (1 if target > self.x else -1) * 1650 * dt
            self.step_clock += dt
            if self.step_clock >= .36:
                self.step_clock = 0
                ctx.camera.kick(5.5, .18)
                ctx.sounds.play("giant_step")
            if self.state_time <= 0:
                self.vx *= .15
                self._set_state("stomp_warn", .78)
        elif self.state == "idle":
            if abs(distance) > 190:
                self.vx += self.facing * 1850 * dt
                self.state_time = max(self.state_time, .14)
            elif self.state_time <= 0:
                self.attack_done = False
                self.pattern_index += 1
                self._set_state("sweep_warn" if self.pattern_index % 2 else "stomp_warn",
                                .72)
        elif self.state == "stomp_warn" and self.state_time <= 0:
            self.attack_done = False
            self._set_state("stomp", .34)
        elif self.state == "stomp":
            foot_x = self.x + self.facing * 61
            danger = pygame.Rect(round(foot_x - 74), round(self.ground_y - 55), 148, 65)
            self._hurt_twice(ctx, danger)
            if self.state_time <= 0:
                ctx.camera.kick(11, .28)
                ctx.sounds.play("giant_stomp")
                self._set_state("recover", .62)
        elif self.state == "sweep_warn" and self.state_time <= 0:
            self.attack_done = False
            self._set_state("sweep", .42)
        elif self.state == "sweep":
            reach = 255
            danger = pygame.Rect(round(self.x if self.facing > 0 else self.x - reach),
                                 round(self.ground_y - 178), reach, 92)
            self._hurt_twice(ctx, danger)
            if self.state_time <= 0:
                self._set_state("recover", .72)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .55 if self.empowered else .38)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.ground_y + camera.offset_y)
        color = self._base_color()
        # Construction ghosts show two rejected proportions behind the final
        # body. They are thin and sparse: history, not decorative AI-detail.
        rough_circle(surface, (172, 183, 184), (x - 8, y - 133), 79,
                     self.seed + 401, 1, 1, squash=(1.0, .92), wobble=2.4)
        correction_cross(surface, (x - 74, y - 115), 13,
                         self.seed + 402, RED_RULE, 2)
        body = [
            (x - 57, y - 190), (x - 73, y - 139), (x - 62, y - 78),
            (x - 31, y - 52), (x + 47, y - 57), (x + 73, y - 105),
            (x + 66, y - 165), (x + 37, y - 194),
        ]
        pygame.draw.polygon(surface, PAPER, body)
        pygame.draw.lines(surface, color, True, body, 5)
        # Five hurried shade strokes are enough to make the torso dense.
        for index in range(5):
            pygame.draw.line(surface, INK_LIGHT,
                             (x - 48 + index * 17, y - 174),
                             (x - 35 + index * 16, y - 74), 2)
        # A diagonal school-bag-like strap, then three ugly repair stitches.
        pygame.draw.line(surface, color, (x - 49, y - 176),
                         (x + 48, y - 75), 8)
        for index in range(3):
            sx = x - 7 + index * 10
            pygame.draw.line(surface, RED_RULE, (sx, y - 129),
                             (sx + 7, y - 121), 2)

        # The near arm is one impossible heavy stroke; the other was assembled
        # from ruler scraps and compass pivots. Their anatomy cannot be mistaken.
        attack_reach = 108 if self.state not in ("sweep_warn", "sweep") else 173
        shoulder = (x + self.facing * 58, y - 163)
        fist = (x + self.facing * attack_reach, y - 113)
        pygame.draw.line(surface, color, shoulder, fist, 20)
        rough_circle(surface, color, fist, 17, self.seed + 410, 4, 2,
                     squash=(1.12, .88), wobble=2.2)
        other_shoulder = (x - self.facing * 54, y - 161)
        elbow = (x - self.facing * 91, y - 131)
        hand = (x - self.facing * 104, y - 91)
        pygame.draw.line(surface, (72, 72, 74), other_shoulder, elbow, 10)
        pygame.draw.line(surface, (72, 72, 74), elbow, hand, 12)
        pivot(surface, elbow, 8, self.seed + 411, color, PAPER)
        pygame.draw.rect(surface, PAPER, (hand[0] - 10, hand[1] - 10, 20, 25))
        pygame.draw.rect(surface, color, (hand[0] - 10, hand[1] - 10, 20, 25), 3)

        # One boot, one peg. The hit box stays stable; this mismatch is character.
        pygame.draw.line(surface, color, (x - 34, y - 61), (x - 62, y - 4), 18)
        pygame.draw.line(surface, color, (x + 35, y - 59), (x + 57, y - 7), 11)
        pygame.draw.line(surface, color, (x - 78, y - 3), (x - 44, y - 3), 9)
        pygame.draw.polygon(surface, PAPER,
                            [(x + 50, y - 9), (x + 67, y - 9), (x + 60, y + 2)])
        pygame.draw.lines(surface, color, True,
                          [(x + 50, y - 9), (x + 67, y - 9), (x + 60, y + 2)], 3)
        head = (x, y - 226)
        pygame.draw.circle(surface, PAPER, head, 45)
        rough_circle(surface, color, head, 45, self.seed + 420, 4, 2,
                     squash=(1.0, .96), wobble=1.7)
        pygame.draw.arc(surface, color, (x - 10, y - 276, 22, 24), .1, 4.7, 3)
        pygame.draw.circle(surface, color, (x - 15, y - 236), 4)
        pygame.draw.circle(surface, color, (x + 15, y - 236), 4)
        pygame.draw.circle(surface, PAPER, (x - 16, y - 237), 1)
        pygame.draw.circle(surface, PAPER, (x + 14, y - 237), 1)
        pygame.draw.polygon(surface, PAPER,
                            [(x, y - 226), (x - 4, y - 218), (x + 4, y - 218)])
        pygame.draw.lines(surface, color, True,
                          [(x, y - 226), (x - 4, y - 218), (x + 4, y - 218)], 1)
        if self.moustache_progress <= 0:
            pygame.draw.arc(surface, color, (x - 13, y - 215, 26, 17),
                            .15, math.pi - .15, 2)
        pygame.draw.circle(surface, (190, 94, 90), (x - 29, y - 219), 6, 1)
        pygame.draw.circle(surface, (190, 94, 90), (x + 29, y - 219), 6, 1)
        if self.moustache_progress > 0:
            # Sit the moustache directly beneath the nose. The old paired arcs
            # floated across the mouth and looked like another misplaced smile.
            spread = round(24 * min(1, self.moustache_progress))
            moustache_y = y - 214
            left = [(x - 2, moustache_y), (x - 8, moustache_y - 5),
                    (x - spread, moustache_y - 1), (x - 13, moustache_y + 7)]
            right = [(x + 2, moustache_y), (x + 8, moustache_y - 5),
                     (x + spread, moustache_y - 1), (x + 13, moustache_y + 7)]
            pygame.draw.polygon(surface, INK, left)
            pygame.draw.polygon(surface, INK, right)
            pygame.draw.arc(surface, INK, (x - spread - 5, moustache_y - 7, 12, 12),
                            math.pi * .6, math.pi * 1.55, 2)
            pygame.draw.arc(surface, INK, (x + spread - 7, moustache_y - 7, 12, 12),
                            -math.pi * .55, math.pi * .4, 2)
            pygame.draw.arc(surface, color, (x - 9, y - 207, 18, 10),
                            .15, math.pi - .15, 1)
        if self.state in ("stomp_warn", "sweep_warn", "page_slap_warn"):
            cue = ("BIG FOOT" if self.state == "stomp_warn" else
                   "TINY TANTRUM" if self.state == "sweep_warn" else
                   "WHOLE PAGE")
            self._draw_telegraph(surface, camera, renderer, cue)
            if self.state == "page_slap_warn":
                pygame.draw.line(surface, RED_RULE, (0, y - 188),
                                 (surface.get_width(), y - 188), 7)
                pygame.draw.line(surface, RED_RULE, (0, y - 42),
                                 (surface.get_width(), y - 42), 4)
            elif self.state == "stomp_warn":
                pygame.draw.ellipse(surface, RED_RULE,
                                    (x + self.facing * 61 - 76, y - 17, 152, 24), 3)
            else:
                end = x + self.facing * 252
                jitter_line(surface, RED_RULE, (x, y - 112), (end, y - 112),
                            3, self.seed + 300, 2, 1.4)
        if not self.empowered:
            attempt = max(1, min(3, int(self.signature_attempt)))
            renderer.doodle_text(surface, f"ATTEMPT {attempt} / 3", (x - 54, y - 312),
                                 (144, 55, 57), renderer.font_small, -3)
        _health_scratches(surface, camera, self, 320)



# ---------------------------------------------------------------------------
# Page-world cast: historical collage, western, and badly researched space


def _aimed_projectile(enemy, ctx, speed, kind="ink", gravity=0.0, radius=6,
                      terrain_collision=True):
    origin = pygame.Vector2(enemy.x, enemy.y - enemy.height * .55)
    target = pygame.Vector2(enemy.aim_target or (ctx.player.center_x, ctx.player.rect.centery))
    direction = target - origin
    if direction.length_squared() < 1:
        direction.update(enemy.facing, 0)
    direction = direction.normalize()
    enemy.projectiles.append(PaperProjectile(
        origin.x, origin.y, direction.x * speed, direction.y * speed,
        kind=kind, gravity=gravity, radius=radius, life=2.8,
        terrain_collision=terrain_collision,
    ))


class InkSamurai(AdvancedEnemy):
    kind = "ink_samurai"
    width, height, radius = 50, 76, 24
    base_hp = 4
    contact_states = ("draw_cut",)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
            self.vx += self.facing * 2200 * dt
            if abs(distance) < 135 and self.state_time <= 0:
                self._set_state("sheath", .68)
                ctx.sounds.play("katana_draw")
            elif self.state_time <= 0:
                self.state_time = .18
        elif self.state == "sheath":
            self.vx *= .45
            if self.state_time <= 0:
                self._set_state("draw_cut", .32)
                ctx.sounds.play("katana_cut")
                self.vx = self.facing * 520
                if ctx.player.rect.bottom < self.y - 45:
                    self.vy = -470
        elif self.state == "draw_cut" and self.state_time <= 0:
            self._set_state("recover", .82)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .58)

    def _attack_rect(self):
        rect = self.rect
        return pygame.Rect(rect.centerx if self.facing > 0 else rect.centerx - 126,
                           rect.y + 8, 126, rect.height - 6)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        # Wide sleeves, split hakama, top-knot, and the sheathed katana make
        # the silhouette readable before any animation starts.
        pygame.draw.polygon(surface, (225, 218, 198),
                            [(x, y - 61), (x - 23, y - 43), (x - 15, y - 8),
                             (x, y - 19), (x + 16, y - 8), (x + 23, y - 43)])
        pygame.draw.lines(surface, color, True,
                          [(x, y - 61), (x - 23, y - 43), (x - 15, y - 8),
                           (x, y - 19), (x + 16, y - 8), (x + 23, y - 43)], 3)
        rough_circle(surface, color, (x, y - 66), 11, self.seed + 7, 3, 2, wobble=1.0)
        pygame.draw.circle(surface, color, (x + self.facing * 3, y - 67), 2)
        pygame.draw.circle(surface, color, (x - self.facing * 5, y - 82), 5, 2)
        stride = round(math.sin(self.time*13)*min(8, abs(self.vx)*.02))
        for side in (-1, 1):
            foot = x+side*23+side*stride
            pygame.draw.lines(surface, color, False,
                [(x+side*12, y-18), (x+side*18-side*stride//2, y-9), (foot, y)], 4)
        p = self.pose_progress
        if self.state == "draw_cut":
            swing = 1-(1-min(1, p*2.5))**3
            sword_y = y-19-round(18*swing)
            reach = 41+round(42*swing)
            pygame.draw.arc(surface, (163, 81, 69),
                (x-91, y-100, 182, 119), -.2 if self.facing > 0 else 2.1,
                1.0 if self.facing > 0 else 3.3, 3)
        elif self.state == "sheath":
            sword_y = y-19+round(math.sin(p*math.pi/2)*5)
            reach = 41-round(p*13)
        elif self.state == "recover":
            ease = p*p*(3-2*p)
            sword_y = y-37+round(ease*18)
            reach = 83-round(ease*42)
        else:
            sword_y, reach = y-19, 41
        pygame.draw.line(surface, (75, 73, 72), (x - self.facing * 9, sword_y),
                         (x + self.facing * reach, sword_y - (17 if self.state == "draw_cut" else 4)), 5)
        pygame.draw.line(surface, (177, 67, 64), (x - self.facing * 15, sword_y - 7),
                         (x + self.facing * 3, sword_y + 7), 3)
        if self.state == "sheath":
            self._draw_telegraph(surface, camera, renderer, "DRAW")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class OrigamiDrone(AdvancedEnemy):
    kind = "origami_drone"
    width, height, radius = 58, 36, 27
    base_hp = 3
    uses_gravity = False
    drag = 2.8

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.hover_y = ground_y - self.rng.randint(135, 190)
        self.y = self.hover_y
        self._set_state("hover", .9)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "hover":
            self.vx += max(-100, min(100, distance)) * dt * 1.1
            self.y += (self.hover_y + math.sin(self.time * 4.4 + self.seed) * 13 - self.y) * min(1, dt * 5)
            if self.state_time <= 0:
                self._set_state("scan", 1.0)
        elif self.state == "scan":
            self.vx *= .5
            if self.state_time <= 0:
                _aimed_projectile(self, ctx, 390, "needle", 0, 4)
                self._set_state("overheat", 1.55)
        elif self.state == "overheat":
            # The impossible drone still obeys a readable paper rule: after a
            # shot it droops into blade range while its folded motor cools.
            self.vx *= .35
            self.y += (self.ground_y - 12 - self.y) * min(1, dt * 7)
            if self.state_time <= 0:
                self._set_state("rise", .72)
        elif self.state == "rise":
            self.y += (self.hover_y - self.y) * min(1, dt * 6)
            if self.state_time <= 0:
                self.y = self.hover_y
                self._set_state("hover", 1.6)
        if abs(distance) < 92:
            self.vx -= self.facing * 95 * dt

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        wing = (round(9*self.pose_progress) if self.state == "scan" else
                -12 if self.state == "overheat" else round(math.sin(self.time * 15) * 5))
        body = [(x, y - 30), (x + 25, y - 14), (x, y - 5), (x - 25, y - 14)]
        pygame.draw.polygon(surface, (216, 218, 207), body)
        pygame.draw.lines(surface, color, True, body, 2)
        pygame.draw.line(surface, color, (x - 25, y - 14), (x - 37, y - 25 - wing), 2)
        pygame.draw.line(surface, color, (x + 25, y - 14), (x + 37, y - 25 + wing), 2)
        pygame.draw.circle(surface, (159, 55, 58), (x, y - 15), 6, 2)
        pygame.draw.circle(surface, color, (x, y - 15), 2)
        if self.state == "scan":
            self._draw_telegraph(surface, camera, renderer, "BEEP")
            pygame.draw.line(surface, (159, 55, 58), (x, y - 15),
                             (camera.screen_x(self.x + self.facing * 150), y + 4), 1)
        elif self.state == "overheat":
            renderer.doodle_text(surface, "HOT", (x - 18, y - 58),
                                 (151, 66, 62), renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class GoblinScribble(AdvancedEnemy):
    kind = "goblin_scribble"
    width, height, radius = 48, 52, 23
    base_hp = 3
    contact_states = ("pounce",)

    def _attack_rect(self):
        rect = self.rect
        return pygame.Rect(rect.centerx if self.facing > 0 else rect.centerx - 122,
                           rect.y + 4, 122, rect.height)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
        if self.state == "idle":
            self.vx += self.facing * 2200 * dt
            if abs(distance) < 145 and self.state_time <= 0:
                self._set_state("snicker", .62)
            elif self.state_time <= 0:
                self.state_time = .18
        elif self.state == "snicker":
            self.vx *= .5
            if self.state_time <= 0:
                self._set_state("pounce", .72)
                self.vx = self.facing * 560
                self.vy = -430
        elif self.state == "pounce" and self.state_time <= 0:
            self._set_state("recover", .7)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .55)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        head = [(x - 18, y - 42), (x - 34, y - 48), (x - 22, y - 29),
                (x - 12, y - 17), (x + 19, y - 22), (x + 28, y - 46),
                (x + 11, y - 40)]
        pygame.draw.polygon(surface, (221, 214, 188), head)
        pygame.draw.lines(surface, color, True, head, 3)
        pygame.draw.circle(surface, color, (x + self.facing * 8, y - 33), 3)
        pygame.draw.arc(surface, color, (x - 11, y - 30, 22, 13), 0, math.pi, 2)
        pygame.draw.line(surface, color, (x - 12, y - 17), (x - 19, y), 4)
        pygame.draw.line(surface, color, (x + 12, y - 17), (x + 20, y), 4)
        pygame.draw.line(surface, (102, 74, 45), (x - self.facing * 7, y - 24),
                         (x + self.facing * 32, y - 48), 6)
        if self.state == "snicker":
            self._draw_telegraph(surface, camera, renderer, "HEH")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class InkOutlaw(AdvancedEnemy):
    kind = "ink_outlaw"
    width, height, radius = 48, 68, 23
    base_hp = 3

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "idle":
            if abs(distance) < 210:
                self.vx -= self.facing * 520 * dt
            elif abs(distance) > 410:
                self.vx += self.facing * 420 * dt
            if self.state_time <= 0:
                self._set_state("quickdraw", .82)
        elif self.state == "quickdraw":
            self.vx *= .5
            if self.state_time <= 0:
                _aimed_projectile(self, ctx, 470, "needle", 18, 4)
                self._set_state("recover", .95)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .75)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        pygame.draw.polygon(surface, (218, 204, 169),
                            [(x - 16, y - 45), (x + 16, y - 45),
                             (x + 12, y - 8), (x - 12, y - 8)])
        pygame.draw.lines(surface, color, True,
                          [(x - 16, y - 45), (x + 16, y - 45),
                           (x + 12, y - 8), (x - 12, y - 8)], 3)
        rough_circle(surface, color, (x, y - 55), 10, self.seed + 20, 2, 2, wobble=.8)
        # Hat is wider than the body so this cannot read as the samurai.
        pygame.draw.line(surface, color, (x - 27, y - 65), (x + 27, y - 65), 4)
        pygame.draw.arc(surface, color, (x - 17, y - 78, 34, 18), math.pi, math.tau, 3)
        pygame.draw.line(surface, (137, 58, 52), (x - 14, y - 42), (x + 14, y - 34), 3)
        p = self.pose_progress
        raise_gun = p*p*(3-2*p) if self.state == "quickdraw" else 1-self.pose_progress if self.state == "recover" else 0
        recoil = max(0, 1-p*6)*8 if self.state == "recover" else 0
        gun_x = x + self.facing * round(25 + raise_gun*6-recoil)
        gun_y = y-17-round(raise_gun*19)
        pygame.draw.line(surface, color, (x + self.facing * 8, y - 32), (gun_x, gun_y), 5)
        pygame.draw.line(surface, color, (gun_x, gun_y), (gun_x + self.facing * 14, gun_y), 3)
        pygame.draw.line(surface, color, (x - 10, y - 8), (x - 15, y), 4)
        pygame.draw.line(surface, color, (x + 10, y - 8), (x + 15, y), 4)
        if self.state == "quickdraw":
            self._draw_telegraph(surface, camera, renderer, "DRAW")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class TumbleweedThing(AdvancedEnemy):
    kind = "tumbleweed_thing"
    width, height, radius = 58, 58, 28
    base_hp = 4
    contact_states = ("roll",)
    drag = 2.0

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "idle" and self.state_time <= 0:
            self._set_state("rustle", .72)
        elif self.state == "rustle":
            self.vx *= .45
            if self.state_time <= 0:
                self._set_state("roll", 1.0)
                self.vx = self.facing * 470
        elif self.state == "roll":
            self.vx += self.facing * 170 * dt
            if self.state_time <= 0:
                self._set_state("recover", .8)
        elif self.state == "recover" and self.state_time <= 0:
            self._set_state("idle", .55)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        for index in range(7):
            angle = self.time * (5 if self.state == "roll" else 1) + index * math.tau / 7
            center = (x + round(math.cos(angle) * 9), y - 29 + round(math.sin(angle) * 8))
            pygame.draw.circle(surface, (112, 79, 46), center, 19 + index % 3, 2)
        pygame.draw.circle(surface, color, (x - 7, y - 32), 2)
        pygame.draw.circle(surface, color, (x + 7, y - 32), 2)
        if self.state == "rustle":
            self._draw_telegraph(surface, camera, renderer, "ROLL")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class StarScout(AdvancedEnemy):
    kind = "star_scout"
    width, height, radius = 54, 42, 26
    base_hp = 3
    uses_gravity = False
    drag = 2.4

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.hover_y = ground_y - self.rng.randint(120, 195)
        self.y = self.hover_y
        self._set_state("orbit", 1.0)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "orbit":
            self.vx += max(-120, min(120, distance)) * dt
            self.y += (self.hover_y + math.sin(self.time * 3.2 + self.seed) * 22 - self.y) * min(1, dt * 4)
            if self.state_time <= 0:
                self._set_state("lock", .9)
        elif self.state == "lock":
            self.vx *= .4
            if self.state_time <= 0:
                _aimed_projectile(self, ctx, 335, "ink", 0, 7)
                self._set_state("orbit", 1.25)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        pygame.draw.ellipse(surface, (204, 218, 221), (x - 25, y - 31, 50, 31))
        pygame.draw.ellipse(surface, color, (x - 25, y - 31, 50, 31), 2)
        pygame.draw.arc(surface, (81, 103, 128), (x - 39, y - 37, 78, 42), .1, math.pi - .1, 2)
        pygame.draw.arc(surface, (81, 103, 128), (x - 39, y - 37, 78, 42), math.pi + .1, math.tau - .1, 2)
        pygame.draw.circle(surface, (159, 55, 58), (x, y - 16), 5, 2)
        pygame.draw.circle(surface, color, (x, y - 16), 2)
        if self.state == "lock":
            self._draw_telegraph(surface, camera, renderer, "LOCK")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class MoonBot(AdvancedEnemy):
    kind = "moon_bot"
    width, height, radius = 68, 72, 33
    base_hp = 5
    contact_states = ("ram",)

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "idle":
            self.vx += self.facing * (1120 if abs(distance) > 125 else -190) * dt
            if abs(distance) < 105 and self.state_time <= 0:
                self._set_state("ram_warn", .52)
            elif self.state_time <= 0:
                self._set_state("charge", 1.05)
        elif self.state == "ram_warn":
            self.vx *= .35
            if self.state_time <= 0:
                self._set_state("ram", .42)
                self.vx = self.facing * 390
        elif self.state == "ram" and self.state_time <= 0:
            self._set_state("cool", .85)
        elif self.state == "charge":
            self.vx *= .35
            if self.state_time <= 0:
                _aimed_projectile(self, ctx, 340, "ink", 0, 10,
                                  terrain_collision=False)
                self._set_state("cool", 1.15)
        elif self.state == "cool" and self.state_time <= 0:
            self._set_state("idle", .8)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        pygame.draw.rect(surface, (205, 213, 211), (x - 27, y - 58, 54, 49), border_radius=9)
        pygame.draw.rect(surface, color, (x - 27, y - 58, 54, 49), 3, border_radius=9)
        pygame.draw.ellipse(surface, (231, 232, 216), (x - 20, y - 67, 40, 27))
        pygame.draw.ellipse(surface, (82, 104, 126), (x - 20, y - 67, 40, 27), 3)
        pygame.draw.circle(surface, (159, 55, 58), (x + self.facing * 8, y - 54), 4)
        pygame.draw.line(surface, color, (x - 18, y - 9), (x - 24, y), 6)
        pygame.draw.line(surface, color, (x + 18, y - 9), (x + 24, y), 6)
        p = self.pose_progress
        reach = (48-round(p*12) if self.state == "ram_warn" else
                 36+round(min(1,p*4)*30) if self.state == "ram" else
                 48+round((1-p)*18) if self.state == "cool" else 48)
        pygame.draw.line(surface, color, (x + self.facing * 27, y - 42),
                         (x + self.facing * reach, y - 42), 7)
        pygame.draw.line(surface, (91,110,123),
                         (x+self.facing*(reach-6), y-49),
                         (x+self.facing*(reach-6), y-35), 3)
        if self.state == "charge":
            self._draw_telegraph(surface, camera, renderer, "3..2..")
        elif self.state == "ram_warn":
            self._draw_telegraph(surface, camera, renderer, "RAM")
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# ---------------------------------------------------------------------------
# Extra world-specific regulars


class LanternYokai(AdvancedEnemy):
    """A floating paper lantern that turns its flame into a readable fan."""

    kind = "lantern_yokai"
    width, height, radius = 44, 62, 23
    base_hp = 3
    uses_gravity = False
    drag = 2.6

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.hover_y = ground_y - self.rng.randint(105, 155)
        self.y = self.hover_y
        self._set_state("drift", .85)

    def _fire_fan(self, ctx):
        origin = pygame.Vector2(self.x, self.y - 28)
        target = pygame.Vector2(ctx.player.center_x, ctx.player.rect.centery)
        direction = target - origin
        if direction.length_squared() < 1:
            direction.update(self.facing, 0)
        direction = direction.normalize()
        for angle in (-.16, 0, .16):
            ca, sa = math.cos(angle), math.sin(angle)
            dx = direction.x * ca - direction.y * sa
            dy = direction.x * sa + direction.y * ca
            self.projectiles.append(PaperProjectile(
                origin.x, origin.y, dx * 305, dy * 305,
                "ink", 2.6, 6, 32, terrain_collision=False,
            ))

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        self.facing = 1 if distance > 0 else -1
        if self.state == "drift":
            desired = ctx.player.center_x - self.facing * 185
            self.vx += max(-90, min(90, desired - self.x)) * dt
            self.y += (self.hover_y + math.sin(self.time * 3.7 + self.seed) * 15 - self.y) * min(1, dt * 5)
            if self.state_time <= 0:
                self._set_state("flare", .78)
        elif self.state == "flare":
            self.vx *= .45
            if self.state_time <= 0:
                self._fire_fan(ctx)
                ctx.sounds.play("ink_burst")
                self._set_state("smoke", 1.15)
        elif self.state == "smoke":
            # Like the drone's overheat, the lantern must enter the Page 1
            # blade lane after its ranged fan.  This is counter-play, not a
            # demand that the player guess a pixel-perfect aerial jump.
            self.y += (self.ground_y - 9 - self.y) * min(1, dt * 7)
            if self.state_time <= 0:
                self._set_state("rise", .68)
        elif self.state == "rise":
            self.y += (self.hover_y - self.y) * min(1, dt * 6)
            if self.state_time <= 0:
                self.y = self.hover_y
                self._set_state("drift", 1.05)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        breath = self.pose_progress if self.state == "flare" else 0
        squash = round(7 * breath)
        width = 22 + round(6 * breath)
        body = [(x - 18, y - 51 + squash), (x + 18, y - 51 + squash),
                (x + width, y - 17), (x, y - 7), (x - width, y - 17)]
        pygame.draw.polygon(surface, (224, 205, 165), body)
        pygame.draw.lines(surface, color, True, body, 3)
        for offset in (-40, -32, -24):
            pygame.draw.arc(surface, (136, 105, 72),
                            (x - width + 3, y + offset + squash // 2,
                             width * 2 - 6, 8), math.pi, math.tau, 1)
        eye_y = y - 32 + squash // 2
        for side in (-1, 1):
            pygame.draw.line(surface, color, (x + side * 7 - 3, eye_y),
                             (x + side * 7 + 3, eye_y - 2), 2)
        flame_length = 14 + round(12 * breath)
        tongue = round(math.sin(self.time * 14) * (5 + breath * 4))
        flame = [(x, y - 12), (x - 8, y + flame_length // 2),
                 (x + tongue, y + flame_length), (x + 8, y + 1)]
        pygame.draw.polygon(surface, (174, 67, 53), flame, 2)
        handle = round(math.sin(self.time * 3) * 6)
        pygame.draw.arc(surface, color, (x - 9 + handle, y - 64 + squash, 18, 15),
                        0, math.pi, 2)
        if self.state == "smoke":
            for i in range(3):
                drift = (self.time * 1.5 + i / 3) % 1
                rough_circle(surface, (160, 148, 124),
                             (x + math.sin(drift * 5 + i) * 12,
                              y - 55 - drift * 35), 4 + drift * 7,
                             self.seed + i, 1, 1)
        if self.state == "flare":
            self._draw_telegraph(surface, camera, renderer, "FWOOSH")
        elif self.state == "smoke":
            renderer.doodle_text(surface, "smoke", (x - 25, y - 82),
                                 INK_LIGHT, renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class CactusGunner(AdvancedEnemy):
    """A rooted western space-controller that announces a three-needle fan."""

    kind = "cactus_gunner"
    width, height, radius = 58, 76, 27
    base_hp = 4
    drag = 7.0

    def _needle_fan(self, ctx):
        origin = pygame.Vector2(self.x + self.facing * 24, self.y - 48)
        target = pygame.Vector2(getattr(self, "needle_target",
                                       (ctx.player.center_x, ctx.player.rect.centery)))
        direction = target - origin
        if direction.length_squared() < 1:
            direction.update(self.facing, 0)
        direction = direction.normalize()
        for angle in (-.18, 0, .18):
            ca, sa = math.cos(angle), math.sin(angle)
            dx = direction.x * ca - direction.y * sa
            dy = direction.x * sa + direction.y * ca
            self.projectiles.append(PaperProjectile(
                origin.x, origin.y, dx * 420, dy * 420,
                "needle", 2.5, 4, 0, terrain_collision=False,
            ))

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
            if abs(distance) > 370:
                self.vx += self.facing * 310 * dt
            if self.state_time <= 0:
                self.needle_target = (ctx.player.center_x, ctx.player.rect.centery)
                self._set_state("prickle", .88)
        elif self.state == "prickle":
            self.vx *= .25
            if self.state_time <= 0:
                self._needle_fan(ctx)
                ctx.sounds.play("ink_burst")
                self._set_state("pluck", 1.1)
        elif self.state == "pluck" and self.state_time <= 0:
            self._set_state("idle", .82)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        recoil = (round(math.sin(min(1, self.pose_progress * 4) * math.pi) * 7)
                  if self.state == "pluck" else 0)
        x -= self.facing * recoil
        pygame.draw.line(surface, (73, 103, 69), (x, y - 66), (x, y - 4), 14)
        pygame.draw.line(surface, color, (x, y - 68), (x, y - 2), 3)
        pygame.draw.lines(surface, color, False,
                          [(x - 2, y - 47), (x - 21, y - 47),
                           (x - 21, y - 63)], 6)
        pygame.draw.lines(surface, color, False,
                          [(x + 2, y - 31), (x + 22, y - 31),
                           (x + 22, y - 49)], 6)
        for px, py in ((x - 7, y - 58), (x + 7, y - 46),
                       (x - 12, y - 28), (x + 12, y - 17)):
            pygame.draw.line(surface, color, (px - 4, py - 2), (px + 4, py + 2), 1)
        pygame.draw.line(surface, color, (x - 29, y - 74), (x + 29, y - 74), 4)
        pygame.draw.arc(surface, color, (x - 18, y - 89, 36, 19), math.pi, math.tau, 3)
        pygame.draw.circle(surface, (154, 58, 52), (x + self.facing * 6, y - 55), 3)
        # A cactus flower becomes a revolver cylinder: petals visibly cock
        # back, then the branch recoils and three empty sockets remain.
        muzzle = (x + self.facing * 27, y - 48)
        cock = self.pose_progress if self.state == "prickle" else 0
        for index in range(5):
            angle = index * math.tau / 5 + cock * .4
            petal = (muzzle[0] + math.cos(angle) * (9 + cock * 4),
                     muzzle[1] + math.sin(angle) * (9 + cock * 4))
            pygame.draw.circle(surface, (188, 120, 106), petal, 5, 2)
        pygame.draw.circle(surface, color, muzzle, 5, 2)
        if self.state == "prickle":
            self._draw_telegraph(surface, camera, renderer, "THREE")
            if hasattr(self, "needle_target"):
                _dashed_line(surface, (161, 106, 88), muzzle,
                             (camera.screen_x(self.needle_target[0]),
                              round(self.needle_target[1] + camera.offset_y)), 1, 7, 10)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class CometHound(AdvancedEnemy):
    """A low four-legged rush enemy with a comet-tail attack lane."""

    kind = "comet_hound"
    width, height, radius = 78, 48, 35
    base_hp = 3
    contact_states = ("comet_dash",)
    drag = 2.2

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            self.facing = 1 if distance > 0 else -1
        if self.state == "idle":
            self.vx += self.facing * 860 * dt
            if self.state_time <= 0 and abs(distance) < 260:
                self._set_state("tail_warn", .68)
            elif self.state_time <= 0:
                self.state_time = .18
        elif self.state == "tail_warn":
            self.vx *= .25
            if self.state_time <= 0:
                self._set_state("comet_dash", 1.18)
                self.vx = self.facing * 590
        elif self.state == "comet_dash":
            self.vx = self.facing * 590
            if self.state_time <= 0:
                self._set_state("cool", .84)
        elif self.state == "cool" and self.state_time <= 0:
            self._set_state("idle", .58)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds, landed
        if self.state == "comet_dash" and hit_wall:
            ctx.camera.kick(4, .15)
            self._set_state("cool", .9)

    def _attack_rect(self):
        rect = self.rect
        return pygame.Rect(rect.centerx if self.facing > 0 else rect.centerx - 112,
                           rect.y + 6, 112, rect.height)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        body = [(x - 30, y - 35), (x + 12, y - 43),
                (x + 31, y - 27), (x + 15, y - 11), (x - 28, y - 13)]
        pygame.draw.polygon(surface, (205, 218, 221), body)
        pygame.draw.lines(surface, color, True, body, 3)
        head_x = x + self.facing * 30
        pygame.draw.polygon(surface, (229, 231, 216),
                            [(head_x, y - 44), (head_x + self.facing * 20, y - 30),
                             (head_x, y - 17), (head_x - self.facing * 9, y - 30)])
        pygame.draw.lines(surface, color, True,
                          [(head_x, y - 44), (head_x + self.facing * 20, y - 30),
                           (head_x, y - 17), (head_x - self.facing * 9, y - 30)], 3)
        pygame.draw.circle(surface, (158, 57, 55),
                           (head_x + self.facing * 7, y - 31), 3)
        for index, leg_x in enumerate((-22, -5, 12, 25)):
            stride = math.sin(self.time*(24 if self.state == "comet_dash" else 10)+index*math.pi*.7)
            step = round(stride*min(12, abs(self.vx)*.025))
            crouch = round(self.pose_progress*5) if self.state == "tail_warn" else 0
            pygame.draw.lines(surface, color, False,
                [(x+leg_x, y-13), (x+leg_x+step//2, y-7+crouch),
                 (x+leg_x-self.facing*7+step, y-max(0,step//3))], 4)
        tail_end = x - self.facing * (92 if self.state == "comet_dash" else 57)
        pygame.draw.lines(surface, (82, 105, 128), False,
                          [(x - self.facing * 29, y - 27),
                           (tail_end, y - 43), (tail_end + self.facing * 11, y - 25)], 4)
        if self.state == "tail_warn":
            self._draw_telegraph(surface, camera, renderer,
                                 ">>>" if self.facing > 0 else "<<<")


# ---------------------------------------------------------------------------
# Veteran variants: familiar silhouettes with a new movement question


class GutterLantern(LanternYokai):
    """A narrow lantern that locks a column, then rains ink through it.

    The original lantern asks the player to read a fan and close distance.
    This veteran cousin freezes the target before firing, so the answer is a
    deliberate horizontal move out of the violet column.
    """

    kind = "gutter_lantern"
    width, height, radius = 38, 78, 21
    base_hp = 4
    accent = (105, 76, 122)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.hover_y = ground_y - self.rng.randint(145, 185)
        self.y = self.hover_y
        self.target_x = self.x
        self._set_state("drift", .7)

    def _drop_column(self, ctx):
        source_y = min(self.y - 100, ctx.player.rect.top - 210)
        for offset in (-24, 0, 24):
            self.projectiles.append(PaperProjectile(
                self.target_x + offset, source_y, 0, 520,
                kind="gutter_drop", life=1.45, radius=8, gravity=0,
                grace=.08, terrain_collision=False,
            ))

    def _think(self, dt, ctx, bounds):
        distance = ctx.player.center_x - self.x
        if abs(distance) > 18:
            self.facing = 1 if distance > 0 else -1
        if self.state == "drift":
            desired = ctx.player.center_x - self.facing * 215
            self.vx += max(-100, min(100, desired - self.x)) * dt * 1.15
            hover = self.hover_y + math.sin(self.time * 3.1 + self.seed) * 12
            self.y += (hover - self.y) * min(1, dt * 5)
            if self.state_time <= 0:
                self.target_x = max(bounds[0] + 36,
                                    min(bounds[1] - 36, ctx.player.center_x))
                self._set_state("drop_warn", .82)
        elif self.state == "drop_warn":
            self.vx *= .35
            if self.state_time <= 0:
                self._drop_column(ctx)
                ctx.sounds.play("ink_burst")
                self._set_state("drop", .68)
        elif self.state == "drop":
            self.vx *= .6
            if self.state_time <= 0:
                self._set_state("smoke", .78)
        elif self.state == "smoke":
            # Descending after the cast gives every starting weapon a clear
            # punish window without weakening the warning itself.
            self.y += (self.ground_y - 12 - self.y) * min(1, dt * 7)
            if self.state_time <= 0:
                self._set_state("rise", .62)
        elif self.state == "rise":
            self.y += (self.hover_y - self.y) * min(1, dt * 6)
            if self.state_time <= 0:
                self.y = self.hover_y
                self._set_state("drift", .92)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        body = [(x, y - 70), (x + 18, y - 52), (x + 14, y - 14),
                (x, y - 2), (x - 14, y - 14), (x - 18, y - 52)]
        pygame.draw.polygon(surface, (205, 190, 216), body)
        pygame.draw.lines(surface, color, True, body, 3)
        pygame.draw.line(surface, self.accent, (x, y - 66), (x, y - 8), 4)
        pygame.draw.arc(surface, color, (x - 9, y - 81, 18, 17), 0, math.pi, 2)
        for eye_x in (-7, 7):
            pygame.draw.circle(surface, color, (x + eye_x, y - 43), 2)
        # Three long tassels make the veteran readable beside the round fan
        # lantern even before either enemy begins an attack.
        for offset in (-10, 0, 10):
            sway = round(math.sin(self.time * 5 + offset) * 3)
            pygame.draw.line(surface, self.accent,
                             (x + offset, y - 9), (x + offset + sway, y + 9), 2)
        if self.state == "drop_warn":
            self._draw_telegraph(surface, camera, renderer, "MOVE")
            target_x = camera.screen_x(self.target_x)
            floor_y = round(self.ground_y + camera.offset_y)
            _dashed_line(surface, self.accent, (target_x, max(35, y - 230)),
                         (target_x, floor_y - 3), 3, 10, 7)
            pygame.draw.ellipse(surface, self.accent,
                                (target_x - 39, floor_y - 13, 78, 18), 3)
        elif self.state == "smoke":
            renderer.doodle_text(surface, "empty", (x - 23, y - 94),
                                 self.accent, renderer.font_small, -2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class RakeCactus(CactusGunner):
    """A broad cactus that fires a timed ankle-height needle rake."""

    kind = "rake_cactus"
    width, height, radius = 82, 66, 36
    base_hp = 4
    accent = (202, 151, 61)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.volley_shots = 0
        self.volley_clock = 0.0
        self._set_state("idle", .62)

    def _fire_low_needle(self, ctx):
        origin_x = self.x + self.facing * 38
        self.projectiles.append(PaperProjectile(
            origin_x, self.ground_y - 14, self.facing * 545, 0,
            kind="needle", life=3.0, radius=4, gravity=0,
            grace=.06, terrain_collision=False,
        ))
        ctx.sounds.play("ink_burst")

    def _think(self, dt, ctx, bounds):
        del bounds
        distance = ctx.player.center_x - self.x
        if self.state == "idle":
            if abs(distance) > 22:
                self.facing = 1 if distance > 0 else -1
            # The rake is rooted while attacking but shuffles back into a
            # useful firing lane when a player camps at the far gate.
            if abs(distance) > 520:
                self.vx += self.facing * 520 * dt
            if self.state_time <= 0:
                self.volley_shots = 3
                self._set_state("prickle", .76)
        elif self.state == "prickle":
            self.vx *= .2
            if self.state_time <= 0:
                self.volley_clock = 0.0
                self._set_state("burst", .58)
        elif self.state == "burst":
            self.vx *= .2
            self.volley_clock -= dt
            while self.volley_shots > 0 and self.volley_clock <= 0:
                self._fire_low_needle(ctx)
                self.volley_shots -= 1
                self.volley_clock += .15
            if self.state_time <= 0:
                self._set_state("pluck", 1.0)
        elif self.state == "pluck" and self.state_time <= 0:
            self._set_state("idle", .82)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        # Wide arms and a short body keep the rake distinct from the tall
        # revolver cactus at a glance.
        pygame.draw.rect(surface, (92, 128, 82), (x - 11, y - 61, 22, 58),
                         border_radius=9)
        pygame.draw.rect(surface, color, (x - 11, y - 61, 22, 58), 3,
                         border_radius=9)
        pygame.draw.lines(surface, (92, 128, 82), False,
                          [(x - 7, y - 42), (x - 34, y - 42),
                           (x - 34, y - 25), (x - 46, y - 25)], 12)
        pygame.draw.lines(surface, color, False,
                          [(x - 7, y - 42), (x - 34, y - 42),
                           (x - 34, y - 25), (x - 46, y - 25)], 3)
        pygame.draw.lines(surface, (92, 128, 82), False,
                          [(x + 7, y - 32), (x + 34, y - 32),
                           (x + 34, y - 49), (x + 46, y - 49)], 12)
        pygame.draw.lines(surface, color, False,
                          [(x + 7, y - 32), (x + 34, y - 32),
                           (x + 34, y - 49), (x + 46, y - 49)], 3)
        for side in (-1, 1):
            pygame.draw.polygon(
                surface, self.accent,
                [(x + side * 7, y - 62), (x + side * 18, y - 70),
                 (x + side * 13, y - 56)],
            )
        pygame.draw.circle(surface, color, (x + self.facing * 5, y - 47), 3)
        muzzle_x = x + self.facing * 47
        muzzle_y = round(self.ground_y - 14 + camera.offset_y)
        if self.state == "prickle":
            self._draw_telegraph(surface, camera, renderer, "JUMP")
            end_x = muzzle_x + self.facing * 360
            _dashed_line(surface, (181, 70, 65), (muzzle_x, muzzle_y),
                         (end_x, muzzle_y), 3, 9, 6)
            for step in (95, 185, 275):
                arrow_x = muzzle_x + self.facing * step
                pygame.draw.lines(surface, self.accent, False,
                                  [(arrow_x - 7, muzzle_y - 1),
                                   (arrow_x, muzzle_y - 11),
                                   (arrow_x + 7, muzzle_y - 1)], 2)
        elif self.state == "burst":
            for index in range(self.volley_shots):
                pygame.draw.circle(surface, self.accent,
                                   (x - 10 + index * 10, y - 82), 3)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


class EmberHound(CometHound):
    """A comet hound whose dash leaves a short-lived floor hazard."""

    kind = "ember_hound"
    width, height, radius = 88, 50, 39
    base_hp = 4
    accent = (89, 151, 166)

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.trail_anchor = self.x

    def _think(self, dt, ctx, bounds):
        previous = self.state
        super()._think(dt, ctx, bounds)
        if previous != "comet_dash" and self.state == "comet_dash":
            self.trail_anchor = self.x

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        was_dashing = self.state == "comet_dash"
        super()._after_integrate(dt, ctx, bounds, hit_wall, landed)
        if not was_dashing:
            return
        distance = self.x - self.trail_anchor
        direction = 1 if distance > 0 else -1
        while abs(self.x - self.trail_anchor) >= 46:
            self.trail_anchor += direction * 46
            self.projectiles.append(PaperProjectile(
                self.trail_anchor - direction * 18, self.ground_y - 9, 0, 0,
                kind="comet_ember", life=1.55, radius=11, gravity=0,
                grace=.04, terrain_collision=False,
            ))

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        tail_x = x - self.facing * 48
        tail = [(x - self.facing * 20, y - 33),
                (tail_x, y - 49), (tail_x + self.facing * 9, y - 31),
                (tail_x - self.facing * 5, y - 18)]
        pygame.draw.polygon(surface, self.accent, tail)
        pygame.draw.lines(surface, color, True, tail, 3)
        body = pygame.Rect(x - 34, y - 43, 67, 31)
        pygame.draw.ellipse(surface, (177, 209, 215), body)
        pygame.draw.ellipse(surface, color, body, 3)
        head_x = x + self.facing * 34
        head = [(head_x - self.facing * 8, y - 43),
                (head_x + self.facing * 23, y - 32),
                (head_x + self.facing * 12, y - 15),
                (head_x - self.facing * 8, y - 20)]
        pygame.draw.polygon(surface, (230, 225, 196), head)
        pygame.draw.lines(surface, color, True, head, 3)
        pygame.draw.circle(surface, (184, 91, 55),
                           (head_x + self.facing * 8, y - 31), 4)
        for fin_x in (-18, 1, 19):
            pygame.draw.polygon(surface, (238, 187, 86),
                                [(x + fin_x, y - 42), (x + fin_x + 8, y - 56),
                                 (x + fin_x + 13, y - 40)])
        for leg_x in (-23, -4, 15, 28):
            stride = math.sin(self.time * (25 if self.state == "comet_dash" else 9)
                              + leg_x * .2)
            pygame.draw.line(surface, color, (x + leg_x, y - 15),
                             (x + leg_x + round(stride * 8), y), 4)
        if self.state == "tail_warn":
            self._draw_telegraph(surface, camera, renderer, "TRAIL")
            floor_y = round(self.ground_y + camera.offset_y) - 5
            end_x = x + self.facing * 245
            _dashed_line(surface, self.accent, (x, floor_y),
                         (end_x, floor_y), 4, 12, 6)
            for step in (62, 124, 186):
                mark_x = x + self.facing * step
                pygame.draw.circle(surface, (238, 187, 86),
                                   (mark_x, floor_y), 5, 2)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# Campaign bosses are separate performances, rather than costumes over the
# catalogue bosses above. Their silhouettes and their counter-play agree.


class MoonCompassBoss(AdvancedEnemy):
    """A hinged compass: measure, sweep a real blade, vault to a new anchor."""
    kind = "moon_compass"
    width, height, radius = 96, 130, 47
    base_hp = 6
    is_boss = True
    block_hint = "JUMP THE RED ARC — STRIKE THE PINNED HINGE"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.angle = .15
        self.window_hits = 0
        self.anchor_x = self.x
        self.vault_x = self.x
        self.sweep_count = 0
        self._set_state("compass_measure", .75)

    def _is_vulnerable(self):
        return self.state == "stuck" and self.window_hits < 2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        dealt = super().hit_from_weapon(1, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
            if self.hp <= 3 and self.phase == 1 and not self.dead:
                self.phase = 2
                self.vx = 0
                self.angle = math.pi / 2
                self._set_state("recalibrate", .95)
                ctx.level.toast = "SECOND DRAFT — THE ARC COMES BACK"
                ctx.level.toast_time = 2.2
                ctx.camera.kick(6, .22)
                ctx.sounds.play("boss_phase_shift")
        return dealt

    def _pin_needle(self, ctx):
        self.angle = math.pi / 2
        self.window_hits = 0
        self.vx = 0
        self._set_state("stuck", 2.15)
        ctx.particles.paper_puff(self.x, self.ground_y, 12)
        ctx.camera.kick(4.5, .17)
        ctx.sounds.play("boss_opening")

    def _blade_points(self, angle=None):
        angle = self.angle if angle is None else angle
        root = (self.x, self.y - 111)
        # The sliding leg shortens against the sheet; the needle never
        # protrudes below the floor while its hinge stays planted.
        length = min(150,111/max(.001,math.sin(angle))) if math.sin(angle)>0 else 150
        tip = (root[0] + math.cos(angle) * length,
               root[1] + math.sin(angle) * length)
        return root, tip

    def _think(self, dt, ctx, bounds):
        if self.state == "recalibrate":
            self.vx = 0
            self.angle += (math.pi / 2 - self.angle) * min(1, dt * 8)
            if self.state_time <= 0:
                self._set_state("compass_measure", .42)
        elif self.state == "compass_measure":
            distance = ctx.player.center_x - self.x
            self.facing = 1 if distance > 0 else -1
            self.vx = self.facing * 230 if abs(distance) > 105 else 0
            self.angle = .08 if self.facing > 0 else math.pi - .08
            if self.state_time <= 0 and abs(distance) <= 120:
                self.vx = 0
                self.anchor_x = self.x
                self._set_state("sweep_telegraph", .82)
                ctx.sounds.play("katana_draw")
        elif self.state == "sweep_telegraph" and self.state_time <= 0:
            self.sweep_count += 1
            self._set_state("sweep", .72 if self.hp > 2 else .6)
            ctx.sounds.play("compass_sweep")
        elif self.state in ("sweep", "return_sweep"):
            # The pivot stays planted; the visible needle describes exactly
            # the damaging line, including its final impact at the floor.
            self.x = self.anchor_x
            progress = self.pose_progress
            forward = self.state == "sweep"
            if self.facing > 0:
                self.angle = (.10 + progress * (math.pi - .20) if forward
                              else math.pi - .10 - progress * (math.pi - .20))
            else:
                self.angle = (math.pi - .10 - progress * (math.pi - .20) if forward
                              else .10 + progress * (math.pi - .20))
            a, b = self._blade_points()
            if (self.attack_suppressed <= 0 and
                    ctx.player.rect.inflate(6, 6).clipline(a, b) and
                    ctx.player.hurt(self.x)):
                ctx.sounds.play("ink")
                ctx.camera.kick(4, .15)
                _player_hit_feedback(ctx, self.x)
            if self.state_time <= 0:
                if self.phase >= 2 and forward:
                    self._set_state("return_telegraph", .46)
                    ctx.sounds.play("boss_signature")
                else:
                    self._pin_needle(ctx)
        elif self.state == "return_telegraph" and self.state_time <= 0:
            self._set_state("return_sweep", .58)
            ctx.sounds.play("compass_sweep")
        elif self.state == "stuck" and self.state_time <= 0:
            side = -1 if ctx.player.center_x < self.x else 1
            self.vault_x = max(bounds[0] + 75, min(bounds[1] - 75,
                                ctx.player.center_x + side * 115))
            self._set_state("compass_vault_warn", .65)
        elif self.state == "compass_vault_warn" and self.state_time <= 0:
            self.vy = -480
            self.vx = (self.vault_x - self.x) / .83
            self._set_state("compass_vault", 1.1)
        elif self.state == "compass_vault":
            # A safe reposition, visibly different from the cutting stroke.
            self.vx = (self.vault_x - self.x) * 5
            self.angle = -math.pi / 2 + math.sin(self.pose_progress * math.pi) * .7
            if self.state_time <= 0:
                self._set_state("compass_measure", .35)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds, hit_wall
        if self.state == "compass_vault" and landed:
            self.vx = 0
            self._set_state("compass_measure", .35)
            ctx.sounds.play("paper_step")
            ctx.particles.pencil_speck(self.x, self.y)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color, blue = self._base_color(), (88, 117, 131)
        red = (158, 65, 60)
        root, tip = self._blade_points()
        hinge = (x, y - 111)
        needle = (camera.screen_x(tip[0]), round(tip[1] + camera.offset_y))
        fixed_foot = (x - self.facing * 39, y)
        # A red lacquered measuring instrument, blue drafting underlines,
        # threaded adjustment wheel, and separate graphite/steel legs.
        pygame.draw.circle(surface, (231, 218, 190), hinge, 28)
        rough_circle(surface, red, hinge, 29, self.seed + 80, 2)
        for angle in range(0, 360, 30):
            a = math.radians(angle)
            pygame.draw.line(surface, red,
                             (x + math.cos(a) * 24, y - 111 + math.sin(a) * 24),
                             (x + math.cos(a) * 29, y - 111 + math.sin(a) * 29), 1)
        pygame.draw.line(surface, blue, (x + 4, y - 110), (fixed_foot[0] + 4, fixed_foot[1]), 2)
        pygame.draw.line(surface, color, hinge, fixed_foot, 7)
        pygame.draw.line(surface, (170, 69, 61), hinge, needle, 8)
        pygame.draw.line(surface, color, hinge, needle, 2)
        pygame.draw.line(surface, color, (x - 28, y - 66), (x + 25, y - 66), 2)
        pygame.draw.ellipse(surface, PAPER, (x - 8, y - 76, 16, 22))
        pygame.draw.ellipse(surface, color, (x - 8, y - 76, 16, 22), 2)
        for dy in range(-71, -55, 4):
            pygame.draw.line(surface, color, (x - 7, y + dy), (x + 7, y + dy), 1)
        pivot(surface, hinge, 11, self.seed, color, PAPER)
        pygame.draw.circle(surface, color, fixed_foot, 4)
        pygame.draw.circle(surface, color, needle, 4)
        if self.state in ("sweep_telegraph", "sweep", "return_telegraph", "return_sweep"):
            path = [(camera.screen_x(self._blade_points(i*math.pi/24)[1][0]),
                     round(self._blade_points(i*math.pi/24)[1][1]+camera.offset_y))
                    for i in range(25)]
            pygame.draw.lines(surface, red, False, path, 2)
            for i in range(0, 25, 4):
                pygame.draw.circle(surface, red, path[i], 3, 1)
            if self.state == "sweep_telegraph":
                self._draw_telegraph(surface, camera, renderer, "JUMP THE ARC")
            elif self.state == "return_telegraph":
                self._draw_telegraph(surface, camera, renderer, "THE ARC RETURNS")
            else:
                for index in range(1, 4):
                    angle = self.angle - self.facing * index * .11
                    _, end_world = self._blade_points(angle)
                    end = (camera.screen_x(end_world[0]),round(end_world[1]+camera.offset_y))
                    pygame.draw.line(surface, (169, 137, 121), hinge, end, 1)
        elif self.state in ("compass_vault_warn", "compass_vault"):
            tx = camera.screen_x(self.vault_x)
            floor = round(self.ground_y + camera.offset_y)
            _dashed_line(surface, blue, (x, floor - 8), (tx, floor - 8), 1)
            pygame.draw.circle(surface, blue, (tx, floor - 4), 9, 2)
            if self.state == "compass_vault_warn":
                renderer.doodle_text(surface, "new centre", (tx - 46, floor - 35), blue,
                                     renderer.font_small, -2)
        elif self.state == "stuck":
            renderer.doodle_text(surface, "PINNED!" if self.vulnerable else "RESETTING",
                                 (x - 38, y - 178), blue,
                                 renderer.font_small, -2)
            self._draw_opening(surface, hinge, 36)
        if self.phase == 2:
            renderer.doodle_text(surface, "II / RETRACE", (x - 45, y - 205), red,
                                 renderer.font_small, 1)
        _health_scratches(surface, camera, self, 151)


def _draw_wanted_poster(surface, camera, renderer, x_world, ground_y, seed,
                        facing, time, live=False, firing=False, torn=False):
    """The same paper target geometry is used by the live outlaw and decoys."""
    x, y = camera.screen_x(x_world), round(ground_y + camera.offset_y)
    sway = round(math.sin(time * 4 + seed) * (3 if live else 1))
    ink = INK if live else (104, 92, 74)
    border = [(x - 38, y - 113), (x + 33, y - 117), (x + 39, y - 23),
              (x + 27, y - 14), (x + 18, y - 23), (x + 5, y - 17),
              (x - 8, y - 25), (x - 22, y - 18), (x - 36, y - 26)]
    pygame.draw.polygon(surface, (231, 211, 166), border)
    pygame.draw.lines(surface, ink, True, border, 2)
    pygame.draw.line(surface, (161, 134, 98), (x - 30, y - 108), (x + 25, y - 110), 1)
    renderer.doodle_text(surface, "WANTED", (x - 30, y - 109), ink, renderer.font_small, -2)
    head = (x + sway, y - 71)
    rough_circle(surface, ink, head, 11, seed, 2, 1)
    pygame.draw.line(surface, ink, (head[0] - 19, y - 78), (head[0] + 19, y - 78), 3)
    pygame.draw.lines(surface, ink, False,
                      [(head[0] - 11, y - 79), (head[0] - 8, y - 90),
                       (head[0] + 10, y - 90), (head[0] + 13, y - 79)], 3)
    pygame.draw.line(surface, ink, (x + sway, y - 60), (x + sway, y - 35), 3)
    pygame.draw.lines(surface, ink, False,
                      [(x - 13, y - 25), (x + sway, y - 35), (x + 14, y - 26)], 3)
    arm_y = y - (56 if firing else 43)
    hand = (x + facing * (50 if firing else 25), arm_y)
    pygame.draw.lines(surface, ink, False,
                      [(x + sway, y - 55), (x + facing * 17, y - 47), hand], 3)
    pygame.draw.line(surface, ink, hand, (hand[0] + facing * 16, hand[1]), 4)
    if live:
        # A functional tell: the real drawing moves and leaks blue wet ink;
        # fake copies remain dry. Never randomise this indicator mid-volley.
        drop = (time * 32) % 35
        pygame.draw.line(surface, (61, 96, 115), (x + 21, y - 16), (x + 21, y - 5), 2)
        pygame.draw.circle(surface, (61, 96, 115), (x + 21, round(y - 12 + drop)), 3)
        pygame.draw.circle(surface, ink, (head[0] + facing * 4, y - 71), 2)
    if torn:
        correction_cross(surface, (x, y - 65), 24, seed, (162, 64, 58), 3)


class BountyDecoy:
    """A shootable one-hit paper copy; it never counts toward arena victory."""
    kind = "bounty_decoy"
    is_boss = False
    active = True
    max_hp = hp = 1

    def __init__(self, owner, x, seed):
        self.owner, self.x, self.seed = owner, float(x), seed
        self.y = owner.ground_y
        self.dead = False
        self.hit_flash = self.vx = 0

    @property
    def rect(self):
        return pygame.Rect(round(self.x - 39), round(self.y - 117), 78, 101)

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        del amount, knockback, source_x, tags
        if self.dead:
            return False
        self.dead = True
        self.hp = 0
        ctx.particles.enemy_break(self.x, self.y - 64, self.owner.facing, 9)
        ctx.sounds.play("paper_break")
        return True


class WantedSketchBoss(AdvancedEnemy):
    """Find the living bounty before the three paper gunmen finish drawing."""
    kind = "wanted_sketch"
    width, height, radius = 78, 117, 39
    base_hp = 6
    is_boss = True
    uses_gravity = False
    block_hint = "THE WET INK IS REAL — SHOOT BEFORE THE DRAW"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.combat_targets: list[BountyDecoy] = []
        self.shuffle_index = 0
        self.shot_target = (self.x, self.y - 25)
        self.shot_targets = [self.shot_target]
        self.shot_timer = 0
        self.volley = 0
        self.old_x = self.x
        self.window_hits = 0
        self._set_state("poster_shuffle", .6)

    def _is_vulnerable(self):
        return self.state in ("bounty_draw", "bounty_volley", "unravel")

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        dealt = super().hit_from_weapon(1, knockback, source_x, tags, ctx)
        if dealt:
            # Accuracy interrupts the real outlaw. Surviving paper copies
            # tear up with it, so there is no lingering invisible attack.
            for decoy in self.combat_targets:
                if not decoy.dead:
                    ctx.particles.enemy_break(decoy.x, decoy.y - 60, self.facing, 6)
                decoy.dead = True
            self.combat_targets.clear()
            self.vx = 0
            if not self.dead:
                self.old_x = self.x
                if self.hp <= 3 and self.phase == 1:
                    self.phase = 2
                    self._set_state("bounty_rewrite", .95)
                    ctx.level.toast = "DEAD OR ALIVE — FOUR POSTERS, FOUR LINES"
                    ctx.level.toast_time = 2.3
                    ctx.camera.kick(6, .22)
                    ctx.sounds.play("boss_phase_shift")
                else:
                    self._set_state("poster_escape", .55)
                    ctx.sounds.play("page")
        return dealt

    def _shuffle(self, ctx, bounds):
        self.shuffle_index += 1
        margin = 300 if self.phase >= 2 else 260
        middle = max(bounds[0] + margin, min(bounds[1] - margin,
                     ctx.player.center_x + (160 if self.shuffle_index % 2 else -160)))
        spots = ([middle - 270, middle - 90, middle + 90, middle + 270]
                 if self.phase >= 2 else [middle - 190, middle, middle + 190])
        slot = (self.seed + self.shuffle_index * 2) % len(spots)
        self.old_x = self.x
        self.x = spots[slot]
        self.facing = 1 if ctx.player.center_x > self.x else -1
        self.shot_target = (ctx.player.center_x, ctx.player.rect.centery)
        self.combat_targets = [BountyDecoy(self, pos, self.seed + i * 7)
                               for i, pos in enumerate(spots) if i != slot]
        actors = [self] + self.combat_targets
        # Phase two turns one frozen quick-draw point into a readable crossfire.
        # Every line is committed before the guns appear; moving afterward
        # cannot make the warning lie.
        offsets = ((0, 0), (-105, -78), (105, -78), (0, 42))
        self.shot_targets = []
        for index, actor in enumerate(actors):
            dx, dy = offsets[index] if self.phase >= 2 else (0, 0)
            self.shot_targets.append((
                max(bounds[0] + 30, min(bounds[1] - 30, self.shot_target[0] + dx)),
                max(self.ground_y - 190, min(self.ground_y - 18,
                                             self.shot_target[1] + dy)),
            ))
        for actor, target in zip(actors, self.shot_targets):
            actor.bounty_target = target
        self.volley = 0
        self._set_state("bounty_draw", 1.15 if self.hp > 2 else .95)
        ctx.sounds.play("stamp")
        ctx.level.toast = "The wet ink moves. The copies don't."
        ctx.level.toast_time = 2.2

    def _think(self, dt, ctx, bounds):
        self.vx = 0
        if self.state in ("poster_shuffle", "poster_escape", "bounty_rewrite") and self.state_time <= 0:
            self._shuffle(ctx, bounds)
        elif self.state == "bounty_draw" and self.state_time <= 0:
            self._set_state("bounty_volley", .7)
            self.shot_timer = 0
        elif self.state == "bounty_volley":
            self.shot_timer -= dt
            volley_limit = 3 if self.phase >= 2 else 2
            if self.shot_timer <= 0 and self.volley < volley_limit:
                self.shot_timer = .24 if self.phase >= 2 else .30
                self.volley += 1
                actors = [self] + [copy for copy in self.combat_targets if not copy.dead]
                for index, actor in enumerate(actors):
                    origin = pygame.Vector2(actor.x, actor.y - 56)
                    target = getattr(actor, "bounty_target", self.shot_target)
                    vector = pygame.Vector2(target) - origin
                    if vector.length_squared() < 1:
                        vector.update(self.facing, 0)
                    vector = vector.normalize() * 470
                    self.projectiles.append(PaperProjectile(
                        origin.x, origin.y, vector.x, vector.y, "ink", 3.1, 5, 0,
                        terrain_collision=False))
                ctx.sounds.play("ink_burst")
            if self.state_time <= 0:
                self._set_state("unravel", 1.55)
        elif self.state == "unravel" and self.state_time <= 0:
            for copy in self.combat_targets:
                copy.dead = True
            self.combat_targets.clear()
            self._set_state("poster_shuffle", .48)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        for copy in self.combat_targets:
            if not copy.dead:
                facing = 1 if self.shot_target[0] > copy.x else -1
                _draw_wanted_poster(surface, camera, renderer, copy.x, copy.y,
                                    copy.seed, facing, self.time,
                                    firing=self.state == "bounty_volley")
                # Duplicate the annotation too: a health label must not give
                # away the living poster before the player reads its ink.
                _health_scratches(surface,camera,self,151,x_world=copy.x)
        _draw_wanted_poster(surface, camera, renderer, self.x, self.y, self.seed,
                            self.facing, self.time, live=True,
                            firing=self.state == "bounty_volley",
                            torn=self.state == "poster_escape")
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        if self.state == "bounty_draw":
            # Every gun receives the same warning; wet ink is the stable tell.
            actors = [self] + [c for c in self.combat_targets if not c.dead]
            for index, actor in enumerate(actors):
                ax = camera.screen_x(actor.x)
                progress = self.pose_progress
                pygame.draw.arc(surface, RED_RULE, (ax - 43, y - 123, 86, 118),
                                -math.pi / 2, -math.pi / 2 + max(.04, progress * math.tau), 2)
                target_world = getattr(actor, "bounty_target", self.shot_target)
                target = (camera.screen_x(target_world[0]),
                          round(target_world[1] + camera.offset_y))
                _dashed_line(surface, (166, 107, 84), (ax, y - 56), target, 1, 6, 9)
        # Every poster carries the same timing mark. It must not reveal which
        # of the drawings is alive; wet moving ink remains the tell.
        for actor in [self] + [copy for copy in self.combat_targets if not copy.dead]:
            self._draw_opening(surface, (camera.screen_x(actor.x), y - 54), 24)
        if self.state == "poster_escape":
            for offset in (-25, 0, 25):
                pygame.draw.line(surface, (158, 139, 110),
                                 (x + offset, y - 95), (x + offset + self.facing * 36, y - 127), 2)
        if self.phase == 2:
            renderer.doodle_text(surface, "DEAD / ALIVE", (x - 45, y - 145),
                                 RED_RULE, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 151)
        for shot in self.projectiles:
            shot.draw(surface, camera)


class RailroadStaplerBoss(AdvancedEnemy):
    """A low train pass, braking wheels, and sequential overhead staple lanes.

    The metal nose is protected. The rear can be hit even during its attack,
    giving aggressive players a positional answer rather than a timer wait.
    """
    kind = "railroad_stapler"
    width, height, radius = 166, 101, 83
    base_hp = 6
    uses_gravity = False
    is_boss = True
    contact_states = ("rail_rush",)
    block_hint = "JUMP THE RAIL — HIT THE REAR OR THE OPEN ENGINE"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.lanes = []
        self.lane_index = 0
        self.shot_timer = 0
        self.window_hits = 0
        self.rear_hit = False
        self.rush_passes = 0
        self.wheel_angle = 0
        self._set_state("rail_approach", .7)

    def _is_vulnerable(self):
        return (self.state == "reload" or self.rear_hit) and self.window_hits < 2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        self.rear_hit = (source_x - self.x) * self.facing < -24
        try:
            dealt = super().hit_from_weapon(1, knockback, source_x, tags, ctx)
            if dealt:
                self.window_hits += 1
                if self.hp <= 3 and self.phase == 1 and not self.dead:
                    self.phase = 2
                    self.vx = 0
                    self.lanes.clear()
                    self.rush_passes = 0
                    self._set_state("derail_shift", 1.0)
                    ctx.level.toast = "EXPRESS REVISION — IT COMES BACK"
                    ctx.level.toast_time = 2.25
                    ctx.camera.kick(7, .24)
                    ctx.sounds.play("boss_phase_shift")
            return dealt
        finally:
            self.rear_hit = False

    def attack_rect_for_state(self, state):
        if state == "rail_rush":
            left = self.x - 90 - (54 if self.facing < 0 else 0)
            return pygame.Rect(round(left), round(self.y - 43), 234, 43)
        return self.rect

    def _attack_rect(self):
        return self.attack_rect_for_state(self.state)

    def _brake(self, ctx, bounds):
        self.vx = 0
        self.window_hits = 0
        center = max(bounds[0] - 25, min(bounds[1] + 5, ctx.player.center_x))
        self.lanes = [center - 150, center, center + 150]
        self.lane_index = 0
        self._set_state("staple_columns_warn", 1.05)
        ctx.sounds.play("reload")
        ctx.camera.kick(3.5, .16)

    def _reverse_or_brake(self, ctx, bounds):
        if self.phase >= 2 and self.rush_passes == 0:
            self.vx = 0
            self.rush_passes = 1
            self.facing *= -1
            self._set_state("return_whistle", .58)
            ctx.sounds.play("boss_signature")
            ctx.camera.kick(4, .16)
        else:
            self._brake(ctx, bounds)

    def _think(self, dt, ctx, bounds):
        self.wheel_angle += self.vx * dt / 17
        if self.state == "derail_shift":
            self.vx = 0
            if self.state_time <= 0:
                self.window_hits = 0
                self.rush_passes = 0
                self._set_state("rail_approach", .45)
        elif self.state == "rail_approach":
            distance = ctx.player.center_x - self.x
            self.facing = 1 if distance > 0 else -1
            self.vx = self.facing * 145 if abs(distance) > 330 else 0
            if self.state_time <= 0:
                self.vx = 0
                self._set_state("rail_whistle", .92)
                ctx.sounds.play("staple")
        elif self.state == "rail_whistle" and self.state_time <= 0:
            self._set_state("rail_rush", 3.2)
        elif self.state == "return_whistle" and self.state_time <= 0:
            self._set_state("rail_rush", 3.2)
        elif self.state == "rail_rush":
            self.vx = self.facing * (520 if self.hp > 3 else 590)
            if self.state_time <= 0:
                self._reverse_or_brake(ctx, bounds)
        elif self.state == "staple_columns_warn" and self.state_time <= 0:
            self._set_state("staple_columns", 1.0)
            self.shot_timer = 0
        elif self.state == "staple_columns":
            self.shot_timer -= dt
            if self.shot_timer <= 0 and self.lane_index < len(self.lanes):
                self.shot_timer = .28
                self.projectiles.append(PaperProjectile(
                    self.lanes[self.lane_index], self.ground_y - 275,
                    0, 660, "staple", 1.1, 6, 0, grace=.08))
                self.lane_index += 1
                ctx.sounds.play("staple")
            if self.state_time <= 0:
                self._set_state("reload", 2.3)
                ctx.sounds.play("reload")
        elif self.state == "reload" and self.state_time <= 0:
            self.lanes.clear()
            self.rush_passes = 0
            self._set_state("rail_approach", .48)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, landed
        if self.state == "rail_rush" and hit_wall:
            self._reverse_or_brake(ctx, bounds)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        ink, brass = self._base_color(), (159, 122, 78)
        f = self.facing
        # A long locomotive with a hinged stapler boiler, not a stapler with
        # wheels pasted on. The cowcatcher matches the low danger rectangle.
        pygame.draw.line(surface, ink, (x - 89, y - 13), (x + 89, y - 13), 7)
        rear = x - f * 64
        pygame.draw.rect(surface, (218, 205, 174), (rear - 23, y - 93, 46, 64))
        pygame.draw.rect(surface, ink, (rear - 23, y - 93, 46, 64), 3)
        pygame.draw.rect(surface, PAPER, (rear - 14, y - 81, 25, 24))
        pygame.draw.rect(surface, ink, (rear - 14, y - 81, 25, 24), 2)
        pygame.draw.line(surface, ink, (rear - 29, y - 96), (rear + 29, y - 96), 5)
        hinge = (x - f * 24, y - 36)
        opening = (.9 * min(1, self.state_time/.25) if self.state == "reload" and self.vulnerable
                   else .16 + (.18 * self.pose_progress if self.state == "rail_whistle" else 0))
        nose = (x + f * 78, round(y - 36 - opening * 52))
        pygame.draw.line(surface, brass, hinge, nose, 25)
        pygame.draw.line(surface, ink, hinge, nose, 3)
        pygame.draw.line(surface, ink, (x - f * 28, y - 27), (x + f * 82, y - 27), 9)
        pivot(surface, hinge, 7, self.seed, ink, PAPER)
        stack = x + f * 33
        pygame.draw.rect(surface, PAPER, (stack - 10, y - 94, 20, 37))
        pygame.draw.rect(surface, ink, (stack - 10, y - 94, 20, 37), 3)
        pygame.draw.line(surface, ink, (stack - 15, y - 94), (stack + 15, y - 94), 4)
        for index in range(3):
            age = (self.time * .8 + index / 3) % 1
            cx = stack - f * age * 49
            cy = y - 101 - age * 47
            rough_circle(surface, (167, 153, 128), (cx, cy), 5 + age * 12,
                         self.seed + index, 1, 1, squash=(1.2, .8))
        for wheel_x in (x - 63, x - 6, x + 51):
            pygame.draw.circle(surface, PAPER, (wheel_x, y - 11), 17)
            rough_circle(surface, ink, (wheel_x, y - 11), 17, self.seed, 2, 1)
            for i in range(3):
                a = self.wheel_angle + i * math.tau / 3
                pygame.draw.line(surface, ink, (wheel_x, y - 11),
                                 (wheel_x + math.cos(a) * 13, y - 11 + math.sin(a) * 13), 2)
        pygame.draw.line(surface, brass, (x - 63, y - 11), (x + 51, y - 11), 3)
        catcher = [(x + f * 84, y - 42), (x + f * 144, y - 3), (x + f * 84, y - 3)]
        pygame.draw.lines(surface, ink, True, catcher, 3)
        for i in range(1, 4):
            pygame.draw.line(surface, brass, catcher[0], (x + f * (84 + i * 14), y - 3), 2)
        if self.state in ("rail_whistle", "return_whistle", "rail_rush"):
            floor = round(self.ground_y + camera.offset_y)
            start, end = x - f * 30, x + f * 370
            pygame.draw.line(surface, RED_RULE, (start, floor - 5), (end, floor - 5), 2)
            for tx in range(min(start, end), max(start, end), 23):
                pygame.draw.line(surface, (164, 113, 89), (tx, floor - 10), (tx + 5, floor), 1)
            if self.state in ("rail_whistle", "return_whistle"):
                cue = "RETURN TRAIN — JUMP!" if self.state == "return_whistle" else "ALL ABOARD — JUMP!"
                self._draw_telegraph(surface, camera, renderer, cue)
        if self.state in ("staple_columns_warn", "staple_columns"):
            for index, lane in enumerate(self.lanes):
                if index < self.lane_index:
                    continue
                lx, floor = camera.screen_x(lane), round(self.ground_y + camera.offset_y)
                _dashed_line(surface, RED_RULE, (lx, floor - 270), (lx, floor - 7), 1, 7, 10)
                pygame.draw.lines(surface, RED_RULE, False,
                                  [(lx - 14, floor - 13), (lx - 14, floor - 5),
                                   (lx + 14, floor - 5), (lx + 14, floor - 13)], 2)
                renderer.doodle_text(surface, str(index + 1), (lx - 5, floor - 300),
                                     RED_RULE, renderer.font_small, 0)
        if self.state == "reload":
            renderer.doodle_text(surface, "ENGINE OPEN" if self.vulnerable else "RELOADING",
                                 (x - 59, y - 160),
                                 (77, 112, 128), renderer.font_small, -2)
            self._draw_opening(surface, (x + f*39, y - 65), 24)
        if self.phase == 2:
            renderer.doodle_text(surface, "RETURN SERVICE", (x - 57, y - 129),
                                 RED_RULE, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 136)
        for shot in self.projectiles:
            shot.draw(surface, camera)


class OrbitalMistakeBoss(AdvancedEnemy):
    """A paper planet sheds its shielding moons, then falls onto a marked X."""
    kind = "orbital_mistake"
    width, height, radius = 110, 108, 55
    base_hp = 9
    uses_gravity = False
    is_boss = True
    contact_states = ("meteor_fall",)
    block_hint = "LET THE MOONS GO — HIT THE EXPOSED PLANET"

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.orbiters = [0, 1, 2]
        self.release_targets = {}
        self.orbit_angle = 0
        self.shot_target = (x, ground_y - 25)
        self.meteor_x = x
        self.shot_timer = 0
        self.window_hits = 0
        self._set_state("orbit_align", 1.2)

    def _phase_for_hp(self):
        return 1 if self.hp > 6 else 2 if self.hp > 3 else 3

    def _is_vulnerable(self):
        return (not self.orbiters and self.state == "unravel"
                and self.window_hits < 3)

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        old_phase = self.phase
        dealt = super().hit_from_weapon(1, knockback, source_x, tags, ctx)
        if dealt:
            self.window_hits += 1
            self.phase = self._phase_for_hp()
            # The world visibly acquires an extra orbital plane each phase.
            # No unexplained heal or restored boss health interrupts the duel.
            if self.phase > old_phase and not self.dead:
                ctx.particles.paper_puff(self.x, self.y - 54, 15)
                ctx.camera.kick(7, .24)
                self.projectiles.clear()
                self._reset_orbiters()
                self._set_state("constellation_shift", .92)
                ctx.level.toast = f"ORBIT {self.phase} / 3 — NEW CONSTELLATION"
                ctx.level.toast_time = 2.1
                ctx.sounds.play("boss_phase_shift")
        return dealt

    def _reset_orbiters(self):
        self.orbiters = list(range(2 + self.phase))
        self.release_targets = {}

    def _prepare_release_targets(self, ctx, bounds):
        self.shot_target = (ctx.player.center_x, ctx.player.rect.centery)
        offsets = ((0, 0), (-105, -72), (105, -72), (-155, 28), (155, 28))
        self.release_targets = {}
        for order, moon in enumerate(self.orbiters):
            dx, dy = offsets[order] if self.phase >= 2 else (0, 0)
            self.release_targets[moon] = (
                max(bounds[0] + 28, min(bounds[1] - 28, self.shot_target[0] + dx)),
                max(self.ground_y - 205, min(self.ground_y - 18,
                                             self.shot_target[1] + dy)),
            )

    def _impact_shards(self, ctx):
        if self.phase < 2:
            return
        count = 4 if self.phase == 2 else 6
        for index in range(count):
            angle = math.radians(202 + index * (136 / max(1, count - 1)))
            speed = 350 + index % 2 * 45
            self.projectiles.append(PaperProjectile(
                self.x, self.ground_y - 18,
                math.cos(angle) * speed, math.sin(angle) * speed,
                "moon_shard", 2.5, 7, 260, grace=.15,
                terrain_collision=False,
            ))
        ctx.sounds.play("boss_signature")

    def _moon_position(self, index):
        angle = self.orbit_angle + index * math.tau / (2 + self.phase)
        return (self.x + math.cos(angle) * 115,
                self.y - 58 + math.sin(angle) * 55)

    def _think(self, dt, ctx, bounds):
        # Once the trajectories are shown, moons keep those launch positions
        # until their volley is finished. The player's dodge can trust the ink.
        if self.state not in ("moon_release_warn", "moon_release"):
            self.orbit_angle += dt * (1.1 + self.phase * .24)
        self.vx = 0
        if self.state == "constellation_shift":
            self.y += (self.ground_y - 190 - self.y) * min(1, dt * 7)
            if self.state_time <= 0:
                self._set_state("orbit_align", .72)
        elif self.state == "orbit_align":
            distance = ctx.player.center_x - self.x
            self.facing = 1 if distance > 0 else -1
            if abs(distance) > 300:
                self.vx = self.facing * 145
            self.y += (self.ground_y - 95 + math.sin(self.time * 1.8) * 16 - self.y) * min(1, dt * 3)
            if self.state_time <= 0:
                self._prepare_release_targets(ctx, bounds)
                self._set_state("moon_release_warn", 1.0)
        elif self.state == "moon_release_warn" and self.state_time <= 0:
            self.shot_timer = 0
            self._set_state("moon_release", 1.2)
        elif self.state == "moon_release":
            self.shot_timer -= dt
            if self.orbiters and self.shot_timer <= 0:
                self.shot_timer = .32
                moon = self.orbiters.pop(0)
                origin = pygame.Vector2(self._moon_position(moon))
                target = self.release_targets.get(moon, self.shot_target)
                direction = pygame.Vector2(target) - origin
                if direction.length_squared() < 1:
                    direction.update(self.facing, 0)
                direction = direction.normalize() * (405 + self.phase * 25)
                self.projectiles.append(PaperProjectile(
                    origin.x, origin.y, direction.x, direction.y,
                    "moon", 3.9, 13, 0, terrain_collision=False))
                ctx.sounds.play("ink_burst")
            if not self.orbiters:
                self.window_hits = 0
                self._set_state("unravel", 3.0)
                ctx.sounds.play("boss_opening")
        elif self.state == "unravel":
            # The core becomes reachable to the starting blade too, even if
            # the player used all ranged ammunition before this fight.
            self.y += (self.ground_y - self.y) * min(1, dt * 6)
            if self.state_time <= 0:
                self.meteor_x = max(bounds[0] + self.radius,
                                    min(bounds[1] - self.radius, ctx.player.center_x))
                self._set_state("meteor_warn", 1.05)
                ctx.sounds.play("compass_sweep")
        elif self.state == "meteor_warn":
            self.y += (self.ground_y - 265 - self.y) * min(1, dt * 5)
            self.x += (self.meteor_x - self.x) * min(1, dt * 5)
            if self.state_time <= 0:
                self.x = self.meteor_x
                self._set_state("meteor_fall", .7)
        elif self.state == "meteor_fall":
            self.x = self.meteor_x
            self.y = min(self.ground_y, self.y + 750 * dt)
            if self.y >= self.ground_y:
                self._impact_shards(ctx)
                self._reset_orbiters()
                self._set_state("orbit_rebuild", .85)
                ctx.camera.kick(7, .22)
                ctx.sounds.play("stamp")
                ctx.particles.paper_puff(self.x, self.y - 4, 22)
        elif self.state == "orbit_rebuild" and self.state_time <= 0:
            self._set_state("orbit_align", .8)

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        ink, blue = self._base_color(), (81, 117, 133)
        red = (157, 69, 64)
        center = (x, y - 56)
        radius = 48
        if self.state == "meteor_fall":
            for index in (-1, 0, 1):
                pygame.draw.line(surface, (164, 134, 107),
                                 (x + index * 25, y - 94), (x + index * 32, y - 180), 3)
        # Back half of the orbit, a scratched paper planet, then the front
        # half and the actual moon projectiles. The broken ring exposes ink.
        pygame.draw.ellipse(surface, (141, 157, 158), (x - 116, y - 112, 232, 112), 1)
        outline = [(x + math.cos(i * math.tau / 24) * (radius + 2 * math.sin(i * 2.3)),
                    y - 56 + math.sin(i * math.tau / 24) * radius) for i in range(24)]
        pygame.draw.polygon(surface, (200, 217, 207), outline)
        pygame.draw.lines(surface, ink, True, outline, 3)
        rough_circle(surface, blue, center, 49, self.seed, 1, 1)
        for ox, oy, r in ((-17, -17, 10), (20, -1, 13), (-12, 21, 7)):
            offset = math.sin(self.time * .7 + ox) * 3
            pygame.draw.ellipse(surface, (177, 195, 188),
                                (x + ox - r + offset, y - 56 + oy - r / 2, r * 2, r))
            pygame.draw.arc(surface, blue,
                            (x + ox - r + offset, y - 56 + oy - r / 2, r * 2, r), .2, 3.8, 2)
        # A pencilled equator, coordinate ticks and wrong-size folded crown.
        pygame.draw.arc(surface, blue, (x - 44, y - 75, 88, 30), math.pi, math.tau, 1)
        pygame.draw.lines(surface, ink, False,
                          [(x - 21, y - 102), (x - 12, y - 125), (x - 2, y - 111),
                           (x + 8, y - 132), (x + 17, y - 101)], 2)
        if self.orbiters:
            pygame.draw.arc(surface, blue, (x - 116, y - 112, 232, 112), math.pi, math.tau, 2)
        else:
            pygame.draw.arc(surface, red, (x - 62, y - 115, 124, 117), .25, 2.2, 2)
            pygame.draw.arc(surface, red, (x - 62, y - 115, 124, 117), 3.45, 5.2, 2)
            renderer.doodle_text(surface, "CORE OPEN" if self.vulnerable else "CORE SEALED",
                                 (x - 48, y - 184),
                                 blue, renderer.font_small, -2)
            self._draw_opening(surface, center, 56)
        for plane in range(1, self.phase):
            pygame.draw.ellipse(surface, (147, 114, 113),
                                (x - 64 - plane * 11, y - 130 - plane * 6,
                                 128 + plane * 22, 147 + plane * 9), 1)
        for index in self.orbiters:
            mx, my = self._moon_position(index)
            sx, sy = camera.screen_x(mx), round(my + camera.offset_y)
            pygame.draw.circle(surface, (237, 226, 190), (sx, sy), 13)
            rough_circle(surface, ink, (sx, sy), 13, self.seed + index, 2, 1)
            pygame.draw.circle(surface, blue, (sx - 4, sy - 3), 4, 1)
        if self.state == "moon_release_warn":
            self._draw_telegraph(surface, camera, renderer, "MOONS AWAY")
            for index in self.orbiters:
                mx, my = self._moon_position(index)
                target = self.release_targets.get(index, self.shot_target)
                _dashed_line(surface, red,
                             (camera.screen_x(mx), round(my + camera.offset_y)),
                             (camera.screen_x(target[0]),
                              round(target[1] + camera.offset_y)), 1, 7, 10)
        if self.state in ("meteor_warn", "meteor_fall"):
            tx, floor = camera.screen_x(self.meteor_x), round(self.ground_y + camera.offset_y)
            pygame.draw.ellipse(surface, red, (tx - 61, floor - 16, 122, 22), 2)
            correction_cross(surface, (tx, floor - 8), 20, self.seed, red, 2)
            _dashed_line(surface, red, (tx, floor - 300), (tx, floor - 22), 1, 7, 10)
            if self.state == "meteor_warn":
                renderer.doodle_text(surface, "BAD LANDING", (tx - 54, floor - 44),
                                     red, renderer.font_small, -1)
        renderer.doodle_text(surface, f"ORBIT {self.phase}", (x - 34, y - 151),
                             blue, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 139)
        for shot in self.projectiles:
            shot.draw(surface, camera)


class FinalEditorBoss(AdvancedEnemy):
    """Real fifth boss with four authored responses to the recorded play style."""

    kind = "final_editor"
    width, height, radius = 138, 174, 66
    base_hp = 10
    is_boss = True
    contact_states = ("counter_cut", "red_stamp")
    block_hint = "READ THE PROOF — ATTACK WHEN THE CLIP OPENS"
    drag = 2.2

    SCENARIO_LABELS = {
        "aggressive": "THE AGGRO MAN / it counted every attack",
        "avoidant": "BRAVEMAN / the margins followed you",
        "precise": "MIRROR / it remembered the clean inputs",
        "unreadable": "MIXED REVISION / it could not classify you",
    }

    def __init__(self, x, ground_y=590, seed=1):
        super().__init__(x, ground_y, seed)
        self.phase = 1
        self.scenario = None
        self.mirror_weapon = "pencil_blade"
        self.pattern = "counter_cut"
        self.pattern_cursor = -1
        self.window_hits = 0
        self.shot_timer = 0.0
        self.attack_done = False
        self.proof_target = (self.x, self.ground_y-25)
        self.margin_lanes = [self.ground_y-25]
        self.safe_margin = (self.x - 110, self.x + 110)
        self.arena_bounds = (self.x - 500, self.x + 500)
        self.redaction_checked = False
        self.shot_index = 0
        self._set_state("intro", 1.25)

    def _phase_for_hp(self):
        return 1 if self.hp > 6 else 2 if self.hp > 3 else 3

    def _is_vulnerable(self):
        return self.state == "proof_window" and self.window_hits < 2

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        old_phase = self.phase
        dealt = super().hit_from_weapon(amount, knockback, source_x, tags, ctx)
        if not dealt or self.dead:
            return dealt
        self.window_hits += 1
        new_phase = self._phase_for_hp()
        if new_phase > old_phase:
            self.phase = new_phase
            self.pattern_cursor = -1
            self._set_state("phase_shift", 1.0)
            self._clear_proof_shots(ctx)
            ctx.level.toast = f"REVISION {self.phase} / 3"
            ctx.level.toast_time = 1.8
            ctx.camera.kick(7, .24)
            ctx.sounds.play("boss_phase_shift")
        return dealt

    def _choose_scenario(self, ctx):
        behavior = getattr(getattr(ctx, "game", None), "behavior", None)
        remembered = (getattr(behavior, "data", {}).get("final_scenario", "")
                      if behavior is not None else "")
        scenario = remembered or (behavior.broad_tendency()
                                  if behavior is not None else "unreadable")
        if scenario not in self.SCENARIO_LABELS:
            scenario = "unreadable"
        self.scenario = scenario
        ctx.level.toast = self.SCENARIO_LABELS[scenario]
        ctx.level.toast_time = 4.2
        if behavior is not None and not remembered:
            behavior.record("final_scenario", kind=scenario,
                            page=ctx.level.chapter_index)

    def _scenario_patterns(self):
        scripts = {
            "aggressive": {
                1: ("red_stamp",),
                2: ("red_stamp", "counter_cut"),
                3: ("redaction_wall", "red_stamp", "counter_cut", "proof_volley"),
            },
            "avoidant": {
                1: ("counter_cut",),
                2: ("counter_cut", "margin_burst"),
                3: ("redaction_wall", "margin_burst", "counter_cut", "red_stamp"),
            },
            "precise": {
                1: ("proof_volley",),
                2: ("proof_volley", "margin_burst"),
                3: ("redaction_wall", "proof_volley", "red_stamp", "margin_burst"),
            },
            "unreadable": {
                1: ("margin_burst",),
                2: ("proof_volley", "red_stamp"),
                3: ("redaction_wall", "counter_cut", "margin_burst", "proof_volley", "red_stamp"),
            },
        }
        return scripts[self.scenario or "unreadable"][self.phase]

    def _start_pattern(self, ctx):
        patterns = self._scenario_patterns()
        self.pattern_cursor = (self.pattern_cursor + 1) % len(patterns)
        self.pattern = patterns[self.pattern_cursor]
        self.facing = 1 if ctx.player.center_x > self.x else -1
        self.vx = 0
        self.proof_target = (ctx.player.center_x, ctx.player.rect.centery)
        self.mirror_weapon = getattr(getattr(ctx,"weapons",None),"current_id","pencil_blade")
        target_y = max(self.ground_y-190,min(self.ground_y-25,ctx.player.rect.centery))
        self.margin_lanes = [target_y]
        if self.phase == 3:
            self.margin_lanes.append(target_y-88 if target_y>self.ground_y-110 else target_y+88)
        if self.pattern == "redaction_wall":
            low, high = self.arena_bounds
            half_width = 112
            if self.scenario == "aggressive":
                center = self.x + self.facing * 155
            elif self.scenario == "avoidant":
                center = (low + high) * .5
            elif self.scenario == "precise":
                center = ctx.player.center_x
                half_width = 92
            else:
                center = low + (high - low) * (.34 if self.pattern_cursor % 2 else .66)
            center = max(low + half_width + 25, min(high - half_width - 25, center))
            self.safe_margin = (center - half_width, center + half_width)
        duration = .96 if self.pattern == "redaction_wall" else (.72 if self.phase == 1 else .58)
        self._set_state("pattern_telegraph", duration)

    def _launch_pattern(self, ctx, bounds):
        # Facing was committed with proof_target in the warning. Crossing the
        # boss is valid counterplay, not a reason to turn its attack around.
        self.attack_done = False
        self.shot_index = 0
        if self.pattern == "counter_cut":
            self.vx = self.facing * (520 + self.phase * 35)
            self._set_state("counter_cut", 3.0)
        elif self.pattern == "red_stamp":
            self.vx = self.facing * 175
            self.vy = -500
            self._set_state("red_stamp", 1.65)
        elif self.pattern == "proof_volley":
            self.shot_timer = 0
            self._set_state("proof_volley", 1.35 + self.phase * .16)
        elif self.pattern == "margin_burst":
            self.shot_timer = 0
            self._set_state("margin_burst", 1.35 + self.phase * .14)
        else:
            self.redaction_checked = False
            self._set_state("redaction_wall", 1.12)
            ctx.sounds.play("boss_signature")

    def _finish_pattern(self, ctx):
        self.vx = 0
        self.window_hits = 0
        self._clear_proof_shots(ctx)
        self._set_state("proof_window", 2.45)
        ctx.level.toast = "THE BINDER CLIP IS OPEN"
        ctx.level.toast_time = 1.6
        ctx.sounds.play("boss_opening")

    def _clear_proof_shots(self, ctx):
        # The clip opening is a real ceasefire. Convert the old edits to
        # harmless graphite so the announced attack window is trustworthy.
        for shot in self.projectiles:
            if shot.life > 0:
                ctx.particles.pencil_speck(shot.x,shot.y)
                ctx.particles.paper_puff(shot.x,shot.y,2)
            shot.life = 0
        self.projectiles.clear()

    def _aimed_proof(self, ctx, speed=330):
        origin = pygame.Vector2(self.x, self.y - 105)
        target = pygame.Vector2(self.proof_target)
        direction = target - origin
        if direction.length_squared() < 1:
            direction.update(self.facing, 0)
        direction = direction.normalize()
        weapon = self.mirror_weapon
        if weapon in ("pencil_blade", "excalibur"):
            # A clean blade user sees the proof copy the line as two offset
            # ruler cuts, instead of receiving the same generic projectile.
            for offset in (-22, 22):
                adjusted = pygame.Vector2(target.x, target.y + offset) - origin
                adjusted = adjusted.normalize() if adjusted.length_squared() else direction
                self.projectiles.append(PaperProjectile(
                    origin.x, origin.y, adjusted.x * (speed + 65), adjusted.y * (speed + 65),
                    kind="needle", life=3.1, radius=7, gravity=0,
                    terrain_collision=False,
                ))
        elif weapon == "eraser_cannon":
            self.projectiles.append(PaperProjectile(
                origin.x, origin.y, direction.x * (speed - 55), direction.y * (speed - 55),
                kind="paper", life=3.4, radius=15, gravity=95,
                terrain_collision=False,
            ))
        else:
            self.projectiles.append(PaperProjectile(
                origin.x, origin.y, direction.x * speed, direction.y * speed,
                kind="paper", life=2.7, radius=8, gravity=55,
                terrain_collision=False,
            ))

    def _think(self, dt, ctx, bounds):
        self.arena_bounds = bounds
        if self.scenario is None:
            self._choose_scenario(ctx)
        if self.state in ("intro", "phase_shift") and self.state_time <= 0:
            self._start_pattern(ctx)
        elif self.state == "pattern_telegraph" and self.state_time <= 0:
            self._launch_pattern(ctx, bounds)
        elif self.state == "counter_cut":
            self.vx = self.facing * (520 + self.phase * 35)
            if self.state_time <= 0:
                self._finish_pattern(ctx)
        elif self.state == "red_stamp" and self.state_time <= 0:
            self._finish_pattern(ctx)
        elif self.state == "proof_volley":
            self.shot_timer -= dt
            if self.shot_timer <= 0:
                self.shot_timer = max(.20, .38 - self.phase * .045)
                self._aimed_proof(ctx, 310 + self.phase * 24)
                ctx.sounds.play("ink_burst")
            if self.state_time <= 0:
                self._finish_pattern(ctx)
        elif self.state == "margin_burst":
            self.shot_timer -= dt
            if self.shot_timer <= 0:
                self.shot_timer = max(.24, .46 - self.phase * .05)
                target_y = self.margin_lanes[self.shot_index % len(self.margin_lanes)]
                self.shot_index += 1
                # Start outside the inside face of the gate so a player
                # against either margin still sees the warned line arrive.
                for source_x, velocity in ((bounds[0] - 85, 520),
                                           (bounds[1] + 85, -520)):
                    self.projectiles.append(PaperProjectile(
                        source_x, target_y, velocity, 0, kind="needle", life=4.2,
                        radius=7, gravity=0, terrain_collision=False,
                    ))
                ctx.sounds.play("staple")
            if self.state_time <= 0:
                self._finish_pattern(ctx)
        elif self.state == "redaction_wall":
            if not self.redaction_checked and self.pose_progress >= .58:
                self.redaction_checked = True
                left, right = self.safe_margin
                if not left <= ctx.player.center_x <= right and ctx.player.hurt(self.x):
                    ctx.sounds.play("ink")
                    ctx.camera.kick(6, .2)
                    _player_hit_feedback(ctx, self.x)
            if self.state_time <= 0:
                self._finish_pattern(ctx)
        elif self.state == "proof_window" and self.state_time <= 0:
            self._start_pattern(ctx)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds
        if self.state == "counter_cut" and hit_wall:
            ctx.camera.kick(8, .27)
            ctx.sounds.play("paper_break")
            self._finish_pattern(ctx)
        elif self.state == "red_stamp" and landed:
            self._erase_floor_temporarily(ctx, self.x, 118 + self.phase * 14, 1.8)
            ctx.camera.kick(9, .3)
            ctx.sounds.play("erase")
            self._finish_pattern(ctx)

    def _attack_rect(self):
        rect = self.rect
        if self.state == "counter_cut":
            return rect.inflate(52, -25)
        if self.state == "red_stamp":
            return rect.inflate(75, 18)
        return rect

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        color = self._base_color()
        body = pygame.Rect(x - 61, y - 156, 122, 146)
        pygame.draw.rect(surface, PAPER, body, border_radius=7)
        renderer.rough_rect(surface, color, body, 4, self.seed + 100)
        # The boss is a walking proof sheet held by a mechanical binder clip,
        # not another giant humanoid silhouette.
        pygame.draw.rect(surface, (83, 86, 91), (x - 34, y - 177, 68, 31), border_radius=8)
        pygame.draw.rect(surface, color, (x - 34, y - 177, 68, 31), 3, border_radius=8)
        pygame.draw.line(surface, RED_RULE, (x - 42, y - 135), (x - 42, y - 24), 3)
        pygame.draw.line(surface, (82, 112, 137), (x - 24, y - 118), (x + 45, y - 118), 2)
        pygame.draw.line(surface, (82, 112, 137), (x - 24, y - 91), (x + 45, y - 91), 2)
        pygame.draw.line(surface, (82, 112, 137), (x - 24, y - 64), (x + 45, y - 64), 2)
        correction_cross(surface, (x + 22, y - 93), 17, self.seed + 301, RED_RULE, 3)
        # Four tool configurations make the selected scenario visible even if
        # the title card has already faded.
        if self.scenario == "aggressive":
            jitter_line(surface, RED_RULE, (x - 92, y - 151), (x + 93, y - 20),
                        7, self.seed + 310, 3, 2.2)
        elif self.scenario == "avoidant":
            for side in (-1, 1):
                pygame.draw.rect(surface, (191, 153, 93),
                                 (x + side * 83 - 6, y - 151, 12, 142))
                pygame.draw.rect(surface, color,
                                 (x + side * 83 - 6, y - 151, 12, 142), 2)
        elif self.scenario == "precise":
            pygame.draw.circle(surface, color, (x, y - 83), 38, 2)
            pygame.draw.line(surface, color, (x - 48, y - 83), (x + 48, y - 83), 1)
            pygame.draw.line(surface, color, (x, y - 131), (x, y - 35), 1)
        else:
            staples(surface, [(x - 77, y - 145), (x - 77, y - 105),
                              (x - 77, y - 65), (x - 77, y - 25)], color)
            pygame.draw.polygon(surface, (218, 166, 151),
                                [(x + 55, y - 47), (x + 93, y - 35),
                                 (x + 80, y - 5), (x + 47, y - 19)])
        pygame.draw.line(surface, color, (x - 43, y - 12), (x - 62, y + 2), 6)
        pygame.draw.line(surface, color, (x + 43, y - 12), (x + 62, y + 2), 6)
        if self.state == "pattern_telegraph":
            cue = {"counter_cut": "CROSS OUT", "red_stamp": "STAMP BELOW",
                   "proof_volley": "PROOF SHOTS", "margin_burst": "MARGINS CLOSE",
                   "redaction_wall": "FIND THE CLEAN MARGIN"}[self.pattern]
            self._draw_telegraph(surface, camera, renderer, cue)
            if self.pattern in ("counter_cut", "red_stamp"):
                floor = round(self.ground_y + camera.offset_y)-5
                end = x + self.facing*235
                _dashed_line(surface, RED_RULE, (x, floor), (end, floor), 2, 9, 6)
                pygame.draw.lines(surface, RED_RULE, False,
                                  [(end-self.facing*12, floor-8), (end, floor),
                                   (end-self.facing*12, floor+8)], 3)
            if self.pattern == "proof_volley":
                _dashed_line(surface,(152,74,66),(x,y-105),
                    (camera.screen_x(self.proof_target[0]),round(self.proof_target[1]+camera.offset_y)),2)
                renderer.doodle_text(surface,
                                     f"COPY: {self.mirror_weapon.replace('_', ' ').upper()}",
                                     (x - 77, y - 246), INK_LIGHT,
                                     renderer.font_small, 1)
        if (self.pattern == "redaction_wall"
                and self.state in ("pattern_telegraph", "redaction_wall")):
            left = max(0, min(surface.get_width(), camera.screen_x(self.safe_margin[0])))
            right = max(0, min(surface.get_width(), camera.screen_x(self.safe_margin[1])))
            top, bottom = 330, min(surface.get_height(), round(self.ground_y + camera.offset_y))
            for boundary in (left, right):
                _dashed_line(surface, (151, 61, 58), (boundary, top),
                             (boundary, bottom), 3, 9, 6)
            renderer.doodle_text(surface, "CLEAN MARGIN", (left + 12, top + 12),
                                 (69, 99, 117), renderer.font_small, -1)
            if self.state == "redaction_wall":
                overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
                alpha = round(55 + 105 * min(1, self.pose_progress * 1.5))
                pygame.draw.rect(overlay, (31, 31, 35, alpha), (0, top, left, bottom - top))
                pygame.draw.rect(overlay, (31, 31, 35, alpha),
                                 (right, top, surface.get_width() - right, bottom - top))
                for start, end in ((0, left), (right, surface.get_width())):
                    for hatch_x in range(int(start) - 40, int(end) + 40, 25):
                        pygame.draw.line(overlay, (91, 47, 51, min(220, alpha + 45)),
                                         (hatch_x, bottom), (hatch_x + 95, top), 3)
                surface.blit(overlay, (0, 0))
        if self.pattern == "margin_burst" and self.state in ("pattern_telegraph","margin_burst"):
            for lane in self.margin_lanes:
                ly=round(lane+camera.offset_y)
                _dashed_line(surface,(176,103,92),(0,ly),(surface.get_width(),ly),1,8,18)
                for side in (-1,1):
                    lx=28 if side==1 else surface.get_width()-28
                    pygame.draw.lines(surface,(151,61,58),False,
                        [(lx-side*12,ly-10),(lx+side*5,ly),(lx-side*12,ly+10)],3)
        elif self.state == "proof_window":
            spread = 35 * min(1, self.state_time/.25) if self.vulnerable else 3
            pygame.draw.line(surface, RED_RULE, (x - 29, y - 173), (x - 29-spread, y - 180-spread*.7), 4)
            pygame.draw.line(surface, RED_RULE, (x + 29, y - 173), (x + 29+spread, y - 180-spread*.7), 4)
            renderer.doodle_text(surface, "OPEN PROOF" if self.vulnerable else "CLIP SHUT",
                                 (x - 46, y - 226),
                                 INK_LIGHT, renderer.font_small, -2)
            self._draw_opening(surface, (x, y-160), 25)
        label = {"aggressive": "AGGRO", "avoidant": "BRAVEMAN",
                 "precise": "MIRROR", "unreadable": "MIXED"}.get(self.scenario, "READING")
        renderer.doodle_text(surface, label,
                             (x - 40, y - 48), INK_LIGHT, renderer.font_small, -1)
        _health_scratches(surface, camera, self, 248)
        for projectile in self.projectiles:
            projectile.draw(surface, camera)


# ---------------------------------------------------------------------------
# CombatArena-facing factory


class RedactionAgent(AdvancedEnemy):
    kind = 'redaction_agent'
    width, height, radius = 44, 70, 23
    base_hp = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rounds = 0
        self.shot_timer = 0

    def _think(self, dt, ctx, bounds):
        dx = ctx.player.center_x-self.x
        if self.state == 'idle':
            self.facing = 1 if dx > 0 else -1
            self.vx += self.facing*(450 if abs(dx)>380 else -450 if abs(dx)<220 else 0)*dt
            if self.state_time <= 0:
                self.aim_target = (ctx.player.center_x, ctx.player.rect.centery)
                self._set_state('agent_aim', .95)
        elif self.state == 'agent_aim':
            self.vx *= .35
            if self.state_time <= 0:
                self.rounds, self.shot_timer = 0, 0
                self._set_state('agent_burst', .55)
        elif self.state == 'agent_burst':
            self.shot_timer -= dt
            if self.shot_timer <= 0 and self.rounds < 3:
                _aimed_projectile(self, ctx, 440, 'staple', 0, 5)
                self.rounds += 1
                self.shot_timer = .17
                ctx.sounds.play('ink_burst')
            if self.state_time <= 0:
                self._set_state('reload', 1.25)
        elif self.state == 'reload' and self.state_time <= 0:
            self._set_state('idle', .8)

    def draw(self, surface, camera, renderer):
        if self.dead:return
        x,y=camera.screen_x(self.x),round(self.y+camera.offset_y)
        ink=self._base_color()
        points=[(x-12,y-51),(x+12,y-51),(x+22,y-10),(x,y-19),(x-22,y-10)]
        pygame.draw.polygon(surface,(110,117,123),points)
        pygame.draw.lines(surface,ink,True,points,3)
        pygame.draw.circle(surface,PAPER,(x,y-60),11)
        pygame.draw.circle(surface,ink,(x,y-60),11,2)
        pygame.draw.line(surface,ink,(x-10,y-61),(x+10,y-61),5)
        pygame.draw.polygon(surface,(164,59,58),[(x,y-48),(x-3,y-39),(x,y-29),(x+3,y-39)])
        stride=round(math.sin(self.time*12)*min(8,abs(self.vx)*.025))
        for side in (-1,1):
            pygame.draw.lines(surface,ink,False,[(x+side*8,y-18),(x+side*10,y-8),(x+side*(14+stride),y)],3)
        extend=26+round(self.pose_progress*12) if self.state=='agent_aim' else 38
        pygame.draw.line(surface,ink,(x,y-34),(x+self.facing*extend,y-36),5)
        if self.state=='agent_aim':self._draw_telegraph(surface,camera,renderer,'THREE SHOTS')
        elif self.state=='reload':renderer.doodle_text(surface,'RELOAD',(x-26,y-95),(69,99,117),renderer.font_small)
        for shot in self.projectiles:shot.draw(surface,camera)

class ScissorDirector(AdvancedEnemy):
    """Three-stage scissors that cut attacks and the notebook floor itself."""

    kind = "scissor_director"
    width, height, radius = 142, 126, 68
    base_hp = 12
    is_boss = True
    contact_states = ("shear", "drop")
    block_hint = "WAIT FOR THE HANDLES TO OPEN — HIT THE HINGE"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.phase = 1
        self.pattern_index = -1
        self.window_hits = 0
        self.target_x = self.x
        self.cross_hit_done = False
        self._set_state("intro", 1.2)

    def _phase_for_hp(self):
        return 1 if self.hp > 8 else 2 if self.hp > 4 else 3

    def _is_vulnerable(self):
        return self.state == "open_hinge" and self.window_hits < 3

    def hit_from_weapon(self, amount, knockback, source_x, tags, ctx):
        old_phase = self.phase
        # Boss scratches describe successful openings, not pellet counts.
        dealt = super().hit_from_weapon(1, knockback, source_x, tags, ctx)
        if not dealt:
            return False
        self.window_hits += 1
        self.phase = self._phase_for_hp()
        if self.phase > old_phase and not self.dead:
            self.vx = self.vy = 0
            self._set_state("rethread", 1.0)
            ctx.level.toast = ("REVISION II — THE FLOOR CAN BE CUT" if self.phase == 2
                               else "REVISION III — LEAVE THE RED X")
            ctx.level.toast_time = 2.25
            ctx.camera.kick(7, .24)
            ctx.sounds.play("boss_phase_shift")
        return True

    def _begin_pattern(self, ctx, bounds):
        scripts = {
            1: ("cut", "drop"),
            2: ("cross", "cut", "drop"),
            3: ("drop", "cross", "cut", "cross"),
        }
        sequence = scripts[self.phase]
        self.pattern_index = (self.pattern_index + 1) % len(sequence)
        pattern = sequence[self.pattern_index]
        self.facing = 1 if ctx.player.center_x > self.x else -1
        self.target_x = max(bounds[0] + 115,
                            min(bounds[1] - 115, ctx.player.center_x))
        self.cross_hit_done = False
        duration = .9 if self.phase == 1 else .76
        self._set_state(f"{pattern}_warn", duration)

    def _cross_lines(self):
        top = self.ground_y - 205
        bottom = self.ground_y - 4
        return (
            ((self.target_x - 112, top), (self.target_x + 112, bottom)),
            ((self.target_x + 112, top), (self.target_x - 112, bottom)),
        )

    def _think(self, dt, ctx, bounds):
        if self.state in ("intro", "open_hinge", "rethread"):
            self.vx *= .4
            if self.state_time <= 0:
                self._begin_pattern(ctx, bounds)
        elif self.state == "cut_warn" and self.state_time <= 0:
            self._set_state("shear", 3.0)
            ctx.sounds.play("snip")
        elif self.state == "drop_warn" and self.state_time <= 0:
            ctx.sounds.play("snip")
            self.vy = -580
            self.vx = (self.target_x - self.x) / .58
            self._set_state("drop", 1.4)
        elif self.state == "cross_warn" and self.state_time <= 0:
            self.vx = 0
            self._set_state("cross_cut", .58)
            ctx.sounds.play("boss_signature")
        elif self.state == "shear":
            self.vx = self.facing * (420 if self.phase == 1 else 510)
            if self.state_time <= 0:
                self._open(ctx)
        elif self.state == "drop":
            self.vx = (self.target_x - self.x) * 4
            if self.state_time <= 0:
                self._open(ctx)
        elif self.state == "cross_cut":
            if not self.cross_hit_done and self.pose_progress >= .32:
                self.cross_hit_done = True
                player_rect = ctx.player.rect.inflate(6, 6)
                if (any(player_rect.clipline(a, b) for a, b in self._cross_lines())
                        and ctx.player.hurt(self.target_x)):
                    ctx.sounds.play("ink")
                    ctx.camera.kick(5, .17)
                    _player_hit_feedback(ctx, self.target_x)
            if self.state_time <= 0:
                self._open(ctx)

    def _open(self, ctx):
        self.vx = 0
        self.window_hits = 0
        self._set_state("open_hinge", 2.3)
        ctx.sounds.play("boss_opening")
        ctx.particles.paper_puff(self.x, self.y - 25, 10)

    def _after_integrate(self, dt, ctx, bounds, hit_wall, landed):
        del dt, bounds
        if self.state == "shear" and hit_wall:
            self._open(ctx)
        elif self.state == "drop" and landed:
            if self.phase >= 2:
                self._erase_floor_temporarily(
                    ctx, self.target_x, 104 + self.phase * 10,
                    1.65 + self.phase * .3,
                )
            ctx.camera.kick(6, .22)
            ctx.sounds.play("paper_break")
            self._open(ctx)

    def _attack_rect(self):
        return self.attack_rect_for_state(self.state)

    def attack_rect_for_state(self, state):
        if state == "shear":
            return pygame.Rect(round(self.x - 110), round(self.y - 35), 220, 35)
        return self.rect

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        ink = self._base_color()
        progress = self.pose_progress
        warning = self.state.endswith("warn")
        angle = (.2 + .55 * math.sin(progress * math.pi / 2) if warning else
                 .8 * min(1, self.state_time/.25) if self.state == "open_hinge" and self.vulnerable else
                 .58 if self.state == "cross_cut" else .16)
        cy = y - (20 if self.state == "shear" else 50)
        facing = self.facing
        for side in (-1, 1):
            tip = (x + facing * round(math.cos(angle) * 110),
                   cy + round(side * math.sin(angle) * 95))
            handle = (x - facing * 58,
                      cy + side * (12 if self.state == "shear" else 35))
            blade = [(x - facing * 5, cy - 5), tip,
                     (x + facing * 14, cy + side * 13)]
            pygame.draw.polygon(surface, (199, 207, 208), blade)
            pygame.draw.lines(surface, ink, True, blade, 3)
            pygame.draw.line(surface, ink, (x, cy), handle, 5)
            pygame.draw.ellipse(surface, (137, 57, 60),
                                (handle[0] - 28, handle[1] - 18, 56, 36), 6)
        pygame.draw.circle(surface, INK, (x, cy), 9, 3)
        pygame.draw.line(surface, INK, (x - 5, cy), (x + 5, cy), 2)
        if self.state in ("cut_warn", "drop_warn", "cross_warn"):
            cue = {"cut_warn": "JUMP THE CUT", "drop_warn": "MOVE — FLOOR CUT",
                   "cross_warn": "LEAVE THE RED X"}[self.state]
            self._draw_telegraph(surface, camera, renderer, cue)
        if self.state == "drop_warn":
            target_x = camera.screen_x(self.target_x)
            pygame.draw.line(surface, RED_RULE,
                             (target_x - 30, y), (target_x + 30, y - 27), 3)
            pygame.draw.line(surface, RED_RULE,
                             (target_x - 30, y - 27), (target_x + 30, y), 3)
            _dashed_line(surface, RED_RULE, (target_x - 64, y - 3),
                         (target_x + 64, y - 3), 2, 8, 7)
        if self.state in ("cross_warn", "cross_cut"):
            for a, b in self._cross_lines():
                screen_a = (camera.screen_x(a[0]), round(a[1] + camera.offset_y))
                screen_b = (camera.screen_x(b[0]), round(b[1] + camera.offset_y))
                if self.state == "cross_warn":
                    _dashed_line(surface, RED_RULE, screen_a, screen_b, 3, 9, 7)
                else:
                    pygame.draw.line(surface, (143, 45, 49), screen_a, screen_b, 7)
                    pygame.draw.line(surface, (224, 198, 164), screen_a, screen_b, 2)
        if self.state == "open_hinge":
            self._draw_opening(surface, (x, cy), 21)
            renderer.doodle_text(surface, "HINGE OPEN" if self.vulnerable else "HINGE SHUT",
                                 (x - 48, y - 132),
                                 (69, 99, 117), renderer.font_small, -2)
        renderer.doodle_text(surface, f"CUT {self.phase} / 3", (x - 36, y - 181),
                             RED_RULE, renderer.font_small, 1)
        _health_scratches(surface, camera, self, 155)


ENEMY_TYPES = {
    "redaction_agent": RedactionAgent,
    "scissor_director": ScissorDirector,
    "ink_samurai": InkSamurai,
    "origami_drone": OrigamiDrone,
    "goblin_scribble": GoblinScribble,
    "ink_outlaw": InkOutlaw,
    "tumbleweed_thing": TumbleweedThing,
    "star_scout": StarScout,
    "moon_bot": MoonBot,
    "lantern_yokai": LanternYokai,
    "cactus_gunner": CactusGunner,
    "comet_hound": CometHound,
    "gutter_lantern": GutterLantern,
    "rake_cactus": RakeCactus,
    "ember_hound": EmberHound,
    "ruler_guard": RulerGuard,
    "paper_wasp": PaperWasp,
    "eraser_brute": EraserBrute,
    "crumpled_one": CrumpledOne,
    "ink_clone": InkClone,
    "doodle_turret": DoodleTurret,
    "compass": CompassBoss,
    "stapler": StaplerBoss,
    "failed_sketch": FailedSketchBoss,
    "artist_mistake": ArtistMistakeBoss,
    "moon_compass": MoonCompassBoss,
    "wanted_sketch": WantedSketchBoss,
    "railroad_stapler": RailroadStaplerBoss,
    "orbital_mistake": OrbitalMistakeBoss,
    "baby_face_giant": BabyFaceGiant,
    "final_editor": FinalEditorBoss,
}

_ALIASES = {
    "ruler": "ruler_guard",
    "guard": "ruler_guard",
    "wasp": "paper_wasp",
    "brute": "eraser_brute",
    "crumple": "crumpled_one",
    "clone": "ink_clone",
    "turret": "doodle_turret",
    "compass_boss": "compass",
    "stapler_boss": "stapler",
    "failed_sketch_boss": "failed_sketch",
    "artist_mistake_boss": "artist_mistake",
    "moon_compass_boss": "moon_compass",
    "wanted_sketch_boss": "wanted_sketch",
    "railroad_stapler_boss": "railroad_stapler",
    "orbital_mistake_boss": "orbital_mistake",
    "baby_giant": "baby_face_giant",
    "baby_face": "baby_face_giant",
    "final_editor_boss": "final_editor",
}


def create_enemy(kind, x, ground_y=590, seed=1):
    """Create an advanced enemy using CombatArena-compatible arguments.

    Legacy ``crawler/hopper/spitter/boss`` kinds remain the responsibility of
    ``combat.DoodleEnemy``.  CombatArena can route only names present in
    ``ENEMY_TYPES`` through this factory and preserve its current fallback.
    """

    normalized = str(kind).strip().lower().replace("-", "_").replace(" ", "_")
    normalized = _ALIASES.get(normalized, normalized)
    enemy_type = ENEMY_TYPES.get(normalized)
    if enemy_type is None:
        available = ", ".join(sorted(ENEMY_TYPES))
        raise ValueError(f"unknown advanced enemy {kind!r}; expected one of: {available}")
    return enemy_type(x, ground_y, seed)


__all__ = [
    "AdvancedEnemy",
    "PaperProjectile",
    "RulerGuard",
    "PaperWasp",
    "EraserBrute",
    "CrumpledOne",
    "InkClone",
    "DoodleTurret",
    "CompassBoss",
    "StaplerBoss",
    "FailedSketchBoss",
    "ArtistMistakeBoss",
    "BabyFaceGiant",
    "FinalEditorBoss",
    "InkSamurai",
    "OrigamiDrone",
    "GoblinScribble",
    "InkOutlaw",
    "TumbleweedThing",
    "StarScout",
    "MoonBot",
    "LanternYokai",
    "CactusGunner",
    "CometHound",
    "GutterLantern",
    "RakeCactus",
    "EmberHound",
    "MoonCompassBoss",
    "WantedSketchBoss",
    "RailroadStaplerBoss",
    "OrbitalMistakeBoss",
    "ENEMY_TYPES",
    "create_enemy",
]
