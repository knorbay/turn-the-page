from __future__ import annotations

from dataclasses import dataclass
import math
import random
import pygame

from paper_renderer import jitter_line
from sketch_marks import pivot, rough_circle, wax_disc
from settings import INK, INK_LIGHT, PAPER, WIDTH

try:
    from advanced_enemies import ENEMY_TYPES as ADVANCED_ENEMY_TYPES
    from advanced_enemies import create_enemy as create_advanced_enemy
except ImportError:
    # The original three doodles are intentionally self-contained.  Keeping
    # this import optional means an incomplete checkout still has playable
    # legacy encounters instead of failing at startup.
    ADVANCED_ENEMY_TYPES = {}
    create_advanced_enemy = None


LEGACY_ENEMY_TYPES = {"crawler", "hopper", "spitter", "boss"}

# These are lanes the player answers, not difficulty tiers. Two attackers may
# overlap only when their warnings ask for different, compatible responses.
ENCOUNTER_ROLES = {
    "crawler": "close", "ruler_guard": "close", "ink_samurai": "close",
    "ink_clone": "close", "crumpled_one": "close",
    "tumbleweed_thing": "close", "comet_hound": "close",
    "hopper": "air", "paper_wasp": "air", "goblin_scribble": "air",
    "gutter_lantern": "air",
    "spitter": "ranged", "doodle_turret": "ranged",
    "origami_drone": "ranged", "ink_outlaw": "ranged",
    "star_scout": "ranged", "lantern_yokai": "ranged",
    "redaction_agent": "ranged",
    "eraser_brute": "area", "moon_bot": "area",
    "rake_cactus": "area", "cactus_gunner": "area", "ember_hound": "area",
}
ATTACK_WARNINGS = frozenset({
    "telegraph", "brace", "echo_telegraph", "charge_telegraph",
    "dive_telegraph", "slam_telegraph", "stomp_warn", "sweep_warn",
    "snap_telegraph", "aim", "sheath", "snicker", "quickdraw", "rustle",
    "lock", "scan", "flare", "prickle", "tail_warn", "ram_warn",
    "agent_aim", "drop_warn", "boss_telegraph", "pattern_telegraph",
    "sweep_telegraph", "bounty_draw", "rail_whistle", "staple_columns_warn",
    "moon_release_warn", "meteor_warn", "return_whistle", "return_telegraph",
    "cross_warn", "cut_warn", "page_slap_warn",
})
ATTACK_COMMITMENTS = frozenset({
    "lunge", "thrust", "charge", "dive", "slam", "stomp", "sweep", "snap",
    "burst", "crossout", "erase_slam", "mirror_storm", "boss_attack",
    "draw_cut", "pounce", "roll", "ram", "comet_dash", "counter_cut",
    "red_stamp", "proof_volley", "margin_burst", "agent_burst", "shear",
    "drop", "echo_slash", "bounty_volley", "rail_rush", "staple_columns",
    "moon_release", "meteor_fall", "return_sweep", "cross_cut",
    "redaction_wall", "ink_rain", "page_slap",
})


def _ballistic_velocity(origin_x, origin_y, target_x, target_y, gravity,
                        travel_speed=390.0):
    dx = float(target_x) - float(origin_x)
    dy = float(target_y) - float(origin_y)
    travel_time = max(.68, min(2.7, abs(dx) / max(1.0, travel_speed) + .38))
    return dx / travel_time, (dy - .5 * gravity * travel_time ** 2) / travel_time


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


@dataclass
class InkBlob:
    x: float
    y: float
    vx: float
    vy: float
    life: float = 3.0
    radius: int = 7
    grace: float = .16

    @property
    def rect(self):
        return pygame.Rect(round(self.x - self.radius), round(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def update(self, dt, ctx):
        self.life -= dt
        self.grace = max(0, self.grace - dt)
        self.vy += 250 * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        if any(self.rect.colliderect(stroke) for stroke in ctx.world.collision_rects()):
            self.life = 0
            ctx.particles.pencil_speck(self.x, self.y)
            return
        if self.grace <= 0 and self.rect.colliderect(ctx.player.rect) and ctx.player.hurt(self.x):
            self.life = 0
            ctx.sounds.play("ink")
            ctx.camera.kick(3, .13)
            _player_hit_feedback(ctx, self.x)
        if self.y > 650:
            self.life = 0

    def draw(self, surface, camera):
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        pygame.draw.circle(surface, (29, 29, 36), (x, y), self.radius)
        pygame.draw.circle(surface, (73, 70, 76), (x - 2, y - 2), max(1, self.radius // 3))


class DoodleEnemy:
    def __init__(self, kind, x, ground_y=590, seed=1, boss=False):
        self.kind = "boss" if boss else kind
        self.x = float(x)
        self.ground_y = ground_y
        self.y = float(ground_y)
        self.vx = self.vy = 0.0
        self.seed = seed
        self.time = 0.0
        self.state = "arrive"
        self.state_time = .55
        self.dead = False
        self.hit_flash = 0.0
        self.stagger_cooldown = 0.0
        self.last_attack_serial = -1
        self.facing = -1
        self.projectiles: list[InkBlob] = []
        self.last_phase = 1
        self.armor = 0
        hp = {"crawler": 2, "hopper": 3, "spitter": 2, "boss": 16}
        self.max_hp = hp.get(self.kind, 2)
        self.hp = self.max_hp
        self.radius = 72 if self.kind == "boss" else 18

    @property
    def rect(self):
        h = 150 if self.kind == "boss" else 36
        w = 144 if self.kind == "boss" else 38
        return pygame.Rect(round(self.x - w / 2), round(self.y - h), w, h)

    def update(self, dt, ctx, bounds):
        if self.dead:
            return
        self.time += dt
        self.state_time -= dt
        self.hit_flash = max(0, self.hit_flash - dt)
        self.stagger_cooldown = max(0, self.stagger_cooldown - dt)
        player = ctx.player
        distance = player.center_x - self.x
        self.facing = 1 if distance > 0 else -1

        if player.attack_active and player.attack_rect.colliderect(self.rect):
            serial = getattr(player, "attack_serial", 0)
            if serial != self.last_attack_serial:
                self.last_attack_serial = serial
                self.hit_from_weapon(1, 185, player.center_x, {"melee"}, ctx)
                if self.dead:
                    return

        attack_state = self.state
        if self.state == "arrive":
            if self.state_time <= 0:
                self.state = "idle"
                self.state_time = random.Random(self.seed).uniform(.35, .65)
        elif self.kind == "crawler":
            self._crawler(dt, distance)
        elif self.kind == "hopper":
            self._hopper(dt, distance)
        elif self.kind == "spitter":
            self._spitter(dt, distance, player)
        else:
            self._boss(dt, distance, player, ctx)

        self.x += self.vx * dt
        self.x = max(bounds[0] + self.radius, min(bounds[1] - self.radius, self.x))
        self.vx *= max(0, 1 - dt * 5)
        if self.kind in ("hopper", "boss"):
            self.vy += 1150 * dt
            self.y += self.vy * dt
            if self.y >= self.ground_y:
                self.y = self.ground_y
                self.vy = 0

        # Contact is harmless outside a clearly telegraphed attack. This keeps
        # the sketchy silhouettes readable instead of turning every overlap
        # into unavoidable touch damage in the narrow notebook arenas.
        damaging = (
            self.state in ("lunge", "slam")
            or attack_state in ("lunge", "slam")
            or (self.state == "drop" and self.vy > 90)
            or attack_state == "drop"
        )
        if damaging and self.rect.colliderect(player.rect) and not player.locked:
            if player.hurt(self.x):
                ctx.sounds.play("ink")
                ctx.camera.kick(4, .16)
                _player_hit_feedback(ctx, self.x)
        for blob in self.projectiles:
            blob.update(dt, ctx)
        self.projectiles = [b for b in self.projectiles if b.life > 0]

    def hit_from_weapon(self, amount, knockback, source_x, tags=None, ctx=None):
        """Duck-typed damage API shared by melee and the modular weapon system."""
        if self.dead:
            return False
        tags = set(tags or ())
        if self.kind == "boss" and self.state != "recover" and "eraser" not in tags:
            if ctx is not None:
                ctx.particles.pencil_speck(self.x + self.facing * 16, self.y - 38)
                ctx.camera.kick(1.2, .06)
                ctx.sounds.play("paper_step")
            return False
        if self.armor > 0 and "eraser" not in tags and "heavy" not in tags:
            if ctx is not None:
                ctx.particles.pencil_speck(self.x, self.y - 25)
                ctx.sounds.play("paper_step")
            return False
        if "eraser" in tags and self.armor > 0:
            self.armor = max(0, self.armor - 1)
        damage = max(1, int(round(amount)))
        self.hp -= damage
        self.hit_flash = .15
        direction = 1 if self.x >= source_x else -1
        self.vx = direction * abs(float(knockback))
        if (self.kind != "boss" and self.stagger_cooldown <= 0 and
                self.state not in ("telegraph", "lunge", "drop", "slam")):
            self.state = "idle"
            self.state_time = .12 if "heavy" in tags or "finisher" in tags else .18
            self.stagger_cooldown = .55 if "heavy" in tags else .75
        if self.kind == "boss" and "eraser" in tags and self.state != "recover":
            self.state, self.state_time = "recover", .30
        heavy = bool({"heavy", "finisher", "eraser", "marker"} & tags)
        if ctx is not None:
            hit_y = self.y - 16
            if "eraser" in tags:
                ctx.particles.eraser_dust(self.x, hit_y, 7)
            else:
                ctx.particles.combat_hit(self.x, hit_y, direction, heavy)
            ctx.camera.kick(4 if heavy else 2.5, .15 if heavy else .1)
            ctx.sounds.play("erase" if "eraser" in tags else "heavy_hit" if heavy else "hit")
            _request_hit_stop(ctx, .055 if heavy else .026)
        if self.hp <= 0:
            self.dead = True
            self.projectiles.clear()
            if ctx is not None:
                ctx.particles.paper_puff(self.x, self.y, 24 if self.kind == "boss" else 14)
                ctx.particles.enemy_break(self.x, self.y - 14, direction,
                                          28 if self.kind == "boss" else 18)
                ctx.sounds.play("enemy_break")
                _request_hit_stop(ctx, .082 if self.kind == "boss" or heavy else .065)
            return True
        return True

    def _start_telegraph(self, duration):
        admit = getattr(self, "attack_admission", None)
        if admit is None or admit(self, "telegraph"):
            self.state, self.state_time = "telegraph", duration

    def _crawler(self, dt, distance):
        if self.state == "idle":
            self.vx += self.facing * 900 * dt
            if abs(distance) < 92 and self.state_time <= 0:
                self._start_telegraph(.38)
        elif self.state == "telegraph":
            self.vx *= .65
            if self.state_time <= 0:
                self.state, self.state_time = "lunge", .24
                self.vx = self.facing * 360
        elif self.state == "lunge" and self.state_time <= 0:
            self.state, self.state_time = "idle", .45

    def _hopper(self, dt, distance):
        if self.state == "idle" and self.y >= self.ground_y:
            if self.state_time <= 0:
                self._start_telegraph(.42)
        elif self.state == "telegraph" and self.state_time <= 0:
            self.state, self.state_time = "drop", .75
            self.vy = -470
            self.vx = self.facing * min(310, max(170, abs(distance) * 1.25))
        elif self.state == "drop":
            self.vx = self.facing * min(310, max(150, abs(distance) * 1.25))
            if self.y >= self.ground_y and self.vy == 0:
                self.state, self.state_time = "idle", .55

    def _spitter(self, dt, distance, player):
        if abs(distance) < 180:
            self.vx -= self.facing * 620 * dt
        elif abs(distance) > 330:
            self.vx += self.facing * 860 * dt
        if self.state == "idle" and self.state_time <= 0:
            self._start_telegraph(.52)
        elif self.state == "telegraph" and self.state_time <= 0:
            self.state, self.state_time = "idle", 1.1
            origin_y = self.y - 28
            shot_vx, shot_vy = _ballistic_velocity(
                self.x, origin_y, player.center_x, player.rect.centery, 250, 405,
            )
            self.projectiles.append(InkBlob(self.x, origin_y, shot_vx, shot_vy))

    def _boss(self, dt, distance, player, ctx):
        phase = 1 if self.hp > 10 else 2 if self.hp > 5 else 3
        if phase > self.last_phase:
            self.last_phase = phase
            ctx.level.toast = "the graphite cracks — a new pattern"
            ctx.level.toast_time = 2.2
            ctx.particles.paper_puff(self.x, self.y - 34, 12)
        if self.state == "recover":
            self.vx *= max(0, 1 - dt * 8)
            if self.state_time <= 0:
                self.state, self.state_time = "idle", .22
        elif self.state == "idle":
            if abs(distance) > 112:
                self.vx += self.facing * (920 + phase * 90) * dt
            if self.state_time <= 0 and abs(distance) > 125:
                self.state_time = .14
            elif self.state_time <= 0:
                self.state, self.state_time = "telegraph", max(.34, .58 - phase * .06)
        elif self.state == "telegraph" and self.state_time <= 0:
            if phase == 1:
                self.state, self.state_time = "slam", .62
                self.vy = -390
                self.vx = self.facing * 190
            else:
                self.state, self.state_time = "recover", .84 if phase == 2 else .66
                count = 2 if phase == 2 else 3
                for i in range(count):
                    origin_y = self.y - 45
                    spread = (i - (count - 1) / 2) * 54
                    shot_vx, shot_vy = _ballistic_velocity(
                        self.x, origin_y, player.center_x + spread,
                        player.rect.centery - abs(spread) * .08, 250, 430,
                    )
                    self.projectiles.append(InkBlob(
                        self.x, origin_y, shot_vx, shot_vy, 3, 9,
                    ))
        elif self.state == "slam" and self.y >= self.ground_y and self.vy == 0:
            self.state, self.state_time = "recover", .96

    def draw(self, surface, camera, renderer):
        if self.dead:
            return
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        color = (148, 45, 48) if self.hit_flash > 0 else INK
        if self.state == "telegraph":
            pygame.draw.circle(surface, (154, 75, 67), (x, y - self.radius), self.radius + 8, 2)
            cue = {"crawler": "->", "hopper": "^", "spitter": "o", "boss": "!!"}.get(self.kind, "!")
            renderer.doodle_text(surface, cue, (x - 8, y - self.radius * 2 - 26),
                                 (145, 57, 55), renderer.font)
        if self.kind == "crawler":
            # Six hard wax discs; the pressure rings remain visible instead of
            # being smoothed into a generic body sprite.
            sizes = (11, 14, 13, 16, 18)
            centers = []
            wax = (
                ((185, 139, 50), (122, 91, 38)),
                ((154, 65, 57), (99, 49, 45)),
                ((72, 118, 139), (48, 79, 94)),
                ((86, 124, 82), (52, 82, 52)),
                ((122, 77, 123), (76, 50, 78)),
            )
            for index, radius in enumerate(sizes):
                cx = x - 34 + index * 17
                cy = y - radius + (index % 2) * 3
                centers.append((cx, cy))
                wax_disc(surface, (cx, cy), radius, self.seed + index * 31, wax[index])
                pygame.draw.line(surface, color, (cx - 4, y - 3),
                                 (cx - 7 + self.facing * 3, y + 7), 2)
            head = centers[-1] if self.facing > 0 else centers[0]
            eye = (head[0] + self.facing * 6, head[1] - 4)
            pygame.draw.circle(surface, PAPER, eye, 4)
            pygame.draw.circle(surface, color, (eye[0] + self.facing, eye[1]), 2)
            # Two lines and an open jaw communicate the coming horizontal bite.
            pygame.draw.line(surface, color, (head[0] + self.facing * 4, head[1] - 13),
                             (head[0] + self.facing * 11, head[1] - 21), 2)
            pygame.draw.line(surface, color, (head[0] + self.facing * 8, head[1] + 4),
                             (head[0] + self.facing * 17, head[1] + 9), 2)
        elif self.kind == "hopper":
            # A compass was opened too far and given a spring. No torso, no
            # humanoid template: its tools are its anatomy.
            top = (x, y - 47)
            left_joint, right_joint = (x - 20, y - 27), (x + 20, y - 27)
            left_tip, right_tip = (x - 31, y), (x + 31, y)
            pygame.draw.line(surface, color, top, left_joint, 4)
            pygame.draw.line(surface, color, top, right_joint, 4)
            pygame.draw.line(surface, color, left_joint, left_tip, 3)
            pygame.draw.line(surface, color, right_joint, right_tip, 3)
            pivot(surface, top, 7, self.seed, color, PAPER)
            pivot(surface, left_joint, 5, self.seed + 1, color, PAPER)
            pivot(surface, right_joint, 5, self.seed + 2, color, PAPER)
            spring = [(x + (-8 if i % 2 else 8), y - 37 + i * 6)
                      for i in range(6)]
            pygame.draw.lines(surface, (72, 87, 99), False, spring, 3)
            pygame.draw.circle(surface, color,
                               (x + self.facing * 4, y - 47), 2)
        elif self.kind == "spitter":
            # A transparent bottle squats on four wire legs. The moving ink
            # level makes the projectile source legible before it fires.
            bottle = pygame.Rect(x - 20, y - 39, 40, 35)
            pygame.draw.rect(surface, PAPER, bottle, border_radius=6)
            ink_level = y - 19 + round(math.sin(self.time * 3) * 2)
            pygame.draw.rect(surface, (62, 49, 76),
                             (bottle.x + 3, ink_level, bottle.w - 6,
                              bottle.bottom - ink_level - 2), border_radius=3)
            pygame.draw.rect(surface, color, bottle, 3, border_radius=6)
            pygame.draw.line(surface, INK_LIGHT,
                             (bottle.x + 6, y - 33), (bottle.x + 6, y - 13), 1)
            pygame.draw.rect(surface, color, (x - 11, y - 46, 22, 7), 2)
            nozzle_x = x + self.facing * 34
            neck = x + self.facing * 17
            pygame.draw.line(surface, color, (neck, y - 28),
                             (nozzle_x, y - 24), 5)
            pygame.draw.polygon(surface, PAPER,
                                [(nozzle_x, y - 30),
                                 (nozzle_x + self.facing * 10, y - 24),
                                 (nozzle_x, y - 18)])
            pygame.draw.polygon(surface, color,
                                [(nozzle_x, y - 30),
                                 (nozzle_x + self.facing * 10, y - 24),
                                 (nozzle_x, y - 18)], 2)
            for foot_x, dx in ((x - 14, -8), (x - 6, -3), (x + 6, 3), (x + 14, 8)):
                pygame.draw.line(surface, color, (foot_x, y - 5),
                                 (foot_x + dx, y + 5), 2)
        else:
            # The finale's Scribble Giant should dominate the notebook without
            # becoming a health sponge.  Its broad, unstable silhouette is
            # visual and collision scale; the same short recovery windows and
            # sixteen scratch-marks still govern the actual fight.
            sway = round(math.sin(self.time * 3.1) * 7)
            renderer.scribble(surface, (x, y - 73), 82, self.seed, 9, color)
            jitter_line(surface, color, (x - 48, y - 74), (x - 116, y - 34 + sway),
                        5, self.seed + 61, 4, 3.2)
            jitter_line(surface, color, (x + 47, y - 72), (x + 118, y - 42 - sway),
                        5, self.seed + 62, 4, 3.2)
            jitter_line(surface, color, (x - 29, y - 24), (x - 61, y + 2),
                        5, self.seed + 63, 3, 2.4)
            jitter_line(surface, color, (x + 28, y - 24), (x + 61, y + 2),
                        5, self.seed + 64, 3, 2.4)
            pygame.draw.circle(surface, (239, 233, 215), (x - 25, y - 88), 13)
            pygame.draw.circle(surface, (239, 233, 215), (x + 27, y - 88), 13)
            pygame.draw.circle(surface, color, (x - 22 + self.facing * 3, y - 87), 4)
            pygame.draw.circle(surface, color, (x + 30 + self.facing * 3, y - 87), 4)
            jitter_line(surface, color, (x - 26, y - 53), (x + 29, y - 48),
                        3, self.seed + 65, 2, 1.8)
            # Boss HP is scratched directly above it, not a generic UI bar.
            for i in range(self.max_hp):
                c = color if i < self.hp else (177, 169, 151)
                pygame.draw.line(surface, c, (x - 76 + i * 10, y - 171),
                                 (x - 72 + i * 10, y - 162), 2)
            if self.state != "recover":
                # Broken arcs read as compacted graphite rather than a digital
                # force field. Their absence is the counter-attack cue.
                shield = pygame.Rect(x - 92, y - 158, 184, 164)
                pygame.draw.arc(surface, INK_LIGHT, shield, .15, 2.45, 2)
                pygame.draw.arc(surface, INK_LIGHT, shield, 3.15, 5.75, 2)
        for blob in self.projectiles:
            blob.draw(surface, camera)


class CombatArena:
    is_combat_arena = True
    mandatory = True
    active = True

    def __init__(self, world, start_x, end_x, arena_id, enemy_specs, layer=0, boss=False):
        self.world = world
        self.start_x = start_x
        self.end_x = end_x
        self.arena_id = arena_id
        self.enemy_specs = list(enemy_specs)
        self.layer = layer
        self.boss = boss
        self.wave_ids = sorted({int(spec.get("wave", 0)) for spec in self.enemy_specs})
        self.encounter_active = False
        self.completed = False
        self.wave = -1
        self.wave_wait = 0.0
        self.encounter_time = 0.0
        self.enemies: list[object] = []
        self._pressure_time = 0.0
        self._last_attack_start = -1.0
        self._pressure_queue = []
        self._pressure_requests = {}
        self._pressure_player = None
        self.boss_kind = None
        self.boss_cue_started = False
        self.boss_intro_time = 0.0
        self.boss_rule = "READ THE RED MARK — MOVE, THEN PUNISH"
        self.entrance_gate = world.add(start_x - 80, start_x - 55, 255, 335,
                                       f"{arena_id}_entrance", 710 + int(start_x), layer)
        self.exit_gate = world.add(end_x - 22, end_x, 255, 335,
                                   f"{arena_id}_exit", 720 + int(end_x), layer)
        self.entrance_gate.enabled = False
        self.exit_gate.enabled = True
        self.entrance_gate.appearance = "arena_border"
        self.exit_gate.appearance = "arena_border"

    @property
    def gate(self):
        return self.exit_gate

    def update(self, dt, ctx, interact=False):
        if self.completed or ctx.player.health <= 0:
            return
        if not self.encounter_active:
            if ctx.player.center_x < self.start_x:
                return
            if (getattr(ctx.director, "blocks_combat", False) or
                    any(not getattr(stage, "entry_ready", True)
                        for stage in getattr(self, "artist_stages", ()))):
                return
            self._restore_fight_ink(ctx)
            self.encounter_active = True
            self.encounter_time = 0
            self.entrance_gate.enabled = True
            self.wave = 0
            if self.wave_ids:
                self._spawn_wave(ctx, self.wave_ids[0])
            if self.arena_id == "first_crossout":
                ctx.level.toast = "F / J ATTACK    SHIFT / K DASH"
                ctx.level.toast_time = 4.0
            elif self.boss:
                ctx.level.toast = "the gate shuts — a named drawing waits below"
                ctx.level.toast_time = 2.6
            else:
                ctx.level.toast = "arena sealed — clear every red mark"
                ctx.level.toast_time = 2.1
            ctx.sounds.play("arena_lock")
            combat_audio = getattr(ctx.sounds, "set_combat", None)
            if callable(combat_audio) and not self.boss_cue_started:
                # Boss arenas may open with a short regular-enemy guard wave.
                # Keep ordinary combat music until the actual boss drawing
                # appears instead of spending the boss cue on its doormen.
                combat_audio(True, False)
            ctx.camera.kick(4, .18)
            if getattr(ctx, "game", None) is not None:
                ctx.game.behavior.record("arena_enter", arena=self.arena_id,
                                         page=ctx.level.chapter_index)

        self.encounter_time += dt
        self.boss_intro_time = max(0.0, self.boss_intro_time - dt)

        # The entrance gate closes behind the activation line (start -80..-55).
        # Keeping enemy centres *ahead* of start used to leave an unreachable
        # strip where a player pressed against that gate could wait forever.
        # Let bodies approach the gate's inside face while still keeping them
        # on the playable side of both paper strokes.
        enemy_bounds = (self.start_x - 45, self.end_x - 35)
        self._coordinate_pressure(ctx, dt)
        for enemy in self.enemies:
            enemy.update(dt, ctx, enemy_bounds)
        self._frame_active_fight(ctx)
        self._update_audio_pressure(ctx)
        self.enemies = [e for e in self.enemies if not e.dead]
        if self.enemies or ctx.player.health <= 0:
            return
        if any(not getattr(stage, "wave_ready", True)
               for stage in getattr(self, "artist_stages", ())):
            return
        self.wave_wait += dt
        if self.wave + 1 < len(self.wave_ids) and self.wave_wait > .9:
            self.wave += 1
            self.wave_wait = 0
            self._spawn_wave(ctx, self.wave_ids[self.wave])
            ctx.sounds.play("doodle")
        elif self.wave + 1 >= len(self.wave_ids) and self.wave_wait > .8:
            self.completed = True
            self.encounter_active = False
            self.entrance_gate.enabled = False
            self.exit_gate.enabled = False
            ctx.camera.script_target = None
            ctx.level.flags.add(self.arena_id)
            ctx.sounds.play("arena_clear")
            ctx.level.toast = "crossed out — fresh ink at the next fight"
            ctx.level.toast_time = 2.5
            ctx.camera.kick(5, .22)
            combat_audio = getattr(ctx.sounds, "set_combat", None)
            if callable(combat_audio):
                combat_audio(False, self.boss)
            if getattr(ctx, "game", None) is not None:
                ctx.game.behavior.record("arena_clear", arena=self.arena_id,
                                         seconds=self.encounter_time,
                                         page=ctx.level.chapter_index)
                if self.boss:
                    boss_kind = self.boss_kind or next(
                        (str(spec.get("kind", "boss")) for spec in self.enemy_specs
                         if "boss" in str(spec.get("kind", ""))),
                        "boss",
                    )
                    ctx.game.behavior.record("boss_clear", kind=boss_kind,
                                             seconds=self.encounter_time)

    @staticmethod
    def _restore_fight_ink(ctx):
        if ctx.player.begin_fight():
            ctx.particles.paper_puff(ctx.player.center_x, ctx.player.y + 18, 13)
            ctx.sounds.play("heart")

    def _spawn_wave(self, ctx, wave):
        specs = [s for s in self.enemy_specs if int(s.get("wave", 0)) == wave]
        counter = 0
        spawned_boss = False
        arena_seed = sum((index + 1) * ord(char) for index, char in enumerate(self.arena_id))
        for spec in specs:
            count = int(spec.get("count", 1))
            for i in range(count):
                if "x" in spec:
                    base_x = float(spec["x"])
                elif "offset" in spec:
                    # Offsets make encounter definitions portable when an
                    # arena is moved to another stretch of the notebook.
                    base_x = self.start_x + float(spec["offset"])
                else:
                    base_x = self.start_x + 250 + counter * 130
                x = base_x + i * float(spec.get("spacing", 95))
                kind = str(spec.get("kind", "crawler"))
                normalized_kind = kind.strip().lower().replace("-", "_").replace(" ", "_")
                ground_y = float(spec.get("ground_y", spec.get("y", 590)))
                seed = (arena_seed + wave * 101 + counter * 17 + i * 7) & 0xffff
                enemy = None

                # Canonical advanced names take the fast path.  Non-legacy
                # names are also offered to the factory so its friendly
                # aliases ("wasp", "brute", etc.) work.  A malformed or
                # unavailable advanced spec falls back to the original
                # DoodleEnemy contract without changing legacy behavior.
                use_factory = (
                    create_advanced_enemy is not None
                    and (normalized_kind in ADVANCED_ENEMY_TYPES
                         or normalized_kind not in LEGACY_ENEMY_TYPES)
                )
                if use_factory:
                    try:
                        enemy = create_advanced_enemy(kind, x, ground_y, seed)
                    except (KeyError, TypeError, ValueError):
                        enemy = None
                if enemy is None:
                    enemy = DoodleEnemy(
                        kind, x, ground_y, seed=seed,
                        boss=self.boss or normalized_kind == "boss",
                    )
                self.enemies.append(enemy)
                if getattr(enemy, "is_boss", False):
                    self.boss_kind = getattr(enemy, "kind", normalized_kind)
                    spawned_boss = True
                enemy.encounter_role = {
                    "crawler": "horizontal",
                    "crumpled_one": "horizontal",
                    "hopper": "vertical",
                    "paper_wasp": "vertical",
                    "spitter": "ranged",
                    "doodle_turret": "space_control",
                    "ruler_guard": "frontline",
                    "eraser_brute": "terrain_control",
                    "ink_clone": "reaction",
                    "ink_samurai": "frontline",
                    "goblin_scribble": "vertical",
                    "origami_drone": "ranged",
                    "ink_outlaw": "ranged",
                    "tumbleweed_thing": "horizontal",
                    "star_scout": "ranged",
                    "moon_bot": "space_control",
                    "lantern_yokai": "ranged",
                    "gutter_lantern": "vertical",
                    "rake_cactus": "space_control",
                    "ember_hound": "terrain_control",
                    "cactus_gunner": "space_control",
                    "comet_hound": "horizontal",
                }.get(normalized_kind, "boss" if getattr(enemy, "is_boss", False) else "pressure")
                counter += 1
        if spawned_boss and not self.boss_cue_started:
            combat_audio = getattr(ctx.sounds, "set_combat", None)
            if callable(combat_audio):
                combat_audio(True, True)
            self.boss_cue_started = True
            self.boss_intro_time = 2.8
            self._restore_fight_ink(ctx)
            ctx.sounds.play("boss_reveal")
            ctx.level.toast = "a named drawing — three fresh heart-marks"
            ctx.level.toast_time = 2.35
            ctx.camera.kick(6, .22)

    def _frame_active_fight(self, ctx):
        """Follow the duel inside wide arenas instead of exposing blind corners."""
        live = [enemy for enemy in self.enemies if not getattr(enemy, "dead", False)]
        if not live:
            ctx.camera.script_target = (self.start_x + self.end_x) * .5
            return
        player_x = ctx.player.center_x
        bosses = [enemy for enemy in live if getattr(enemy, "is_boss", False)]
        target = (bosses[0] if bosses else
                  min(live, key=lambda enemy: abs(enemy.x - player_x)))
        focus = (player_x + float(target.x)) * .5
        # Keep both gate strokes readable when the room fits. In larger rooms,
        # allow travel but retain a generous screen margin around combatants.
        margin = min(WIDTH * .37, max(150.0, (self.end_x - self.start_x) * .5))
        low = self.start_x + margin
        high = self.end_x - margin
        if low > high:
            focus = (self.start_x + self.end_x) * .5
        else:
            focus = max(low, min(high, focus))
        ctx.camera.script_target = focus

    @staticmethod
    def _attack_committed(enemy):
        state = getattr(enemy, "state", "")
        return (state in ATTACK_WARNINGS or state in ATTACK_COMMITMENTS
                or state in getattr(enemy, "contact_states", ()))

    @staticmethod
    def _pressure_role(enemy):
        if getattr(enemy, "is_boss", False) or getattr(enemy, "kind", "") == "boss":
            return "boss"
        return ENCOUNTER_ROLES.get(getattr(enemy, "kind", ""), "close")

    def _nearby_hazard(self, enemy):
        player = self._pressure_player
        if player is None:
            return False
        nearby = player.rect.inflate(340, 230)
        for shot in getattr(enemy, "projectiles", ()):
            if getattr(shot, "life", 0) <= 0:
                continue
            # Include an approaching shot, but release pressure after it has
            # passed the player. Old bullets across the room are not a lock.
            horizon = min(.32, shot.life)
            future = shot.rect.move(round(getattr(shot, "vx", 0) * horizon),
                                    round(getattr(shot, "vy", 0) * horizon
                                          + .5 * getattr(shot, "gravity", 0) * horizon ** 2))
            if shot.rect.union(future).colliderect(nearby):
                return True
        for edit in getattr(enemy, "_temporary_erases", ()):
            if edit.get("time", 0) <= 0:
                continue
            for left, right in edit.get("after", ()):
                if (left, right) in edit.get("before", ()):
                    continue
                floor = edit["platform"]
                if (right >= nearby.left and left <= nearby.right
                        and abs(floor.y_at(player.center_x) - player.rect.bottom) < 115):
                    return True
        return False

    def _pressure_load(self):
        # A volley is one source, regardless of bullet count. Its role remains
        # occupied in recovery while its projectiles or erased floor are near.
        return [self._pressure_role(enemy) for enemy in self.enemies
                if not getattr(enemy, "dead", False)
                and (self._attack_committed(enemy) or self._nearby_hazard(enemy))]

    def _role_can_enter(self, enemy, load):
        role = self._pressure_role(enemy)
        if len(load) >= 2 or "boss" in load or role in load:
            return False
        # A fan and an area denial attack both close escape lanes. Pair either
        # with a body to dodge/punish, never with another screen-filling source.
        return not (role in {"ranged", "area"} and any(
            active in {"ranged", "area"} for active in load))

    def _admit_attack(self, enemy, next_state):
        # Boss scripts and transitions within an already announced attack are
        # autonomous. Only the first warning asks for admission. MoonBot's
        # charge is its visible ranged windup despite the shared state name.
        if (self._pressure_role(enemy) == "boss"
                or self._attack_committed(enemy)
                or (next_state not in ATTACK_WARNINGS
                    and not (enemy.kind == "moon_bot" and next_state == "charge"))):
            return True
        key = id(enemy)
        self._pressure_requests[key] = self._pressure_time
        if enemy not in self._pressure_queue:
            self._pressure_queue.append(enemy)
        if self._pressure_time - self._last_attack_start < .24:
            return False
        load = self._pressure_load()
        # Requests keep their place when another role is admitted. Each source
        # goes to the back after starting; the list update order cannot let it
        # repeatedly jump ahead of a waiting peer.
        eligible = next((waiting for waiting in self._pressure_queue
                         if self._role_can_enter(waiting, load)), None)
        if eligible is not enemy:
            return False
        self._pressure_queue.remove(enemy)
        self._pressure_requests.pop(key, None)
        self._last_attack_start = self._pressure_time
        return True

    def _coordinate_pressure(self, ctx=None, dt=0.0):
        """Space new warnings without freezing pursuit or announced attacks."""
        self._pressure_time += dt
        if ctx is not None:
            self._pressure_player = ctx.player
        live_ids = {id(enemy) for enemy in self.enemies if not getattr(enemy, "dead", False)}
        self._pressure_queue = [enemy for enemy in self._pressure_queue
                                if id(enemy) in live_ids
                                and not self._attack_committed(enemy)
                                and getattr(enemy, "hit_stun", 0) <= 0
                                and self._pressure_time - self._pressure_requests.get(id(enemy), -1) < .15]
        self._pressure_requests = {id(enemy): self._pressure_requests[id(enemy)]
                                   for enemy in self._pressure_queue}
        for enemy in self.enemies:
            enemy.attack_admission = self._admit_attack

    def _update_audio_pressure(self, ctx):
        """Let the score watch the fight instead of acting like a room switch."""
        setter = getattr(ctx.sounds, "set_intensity", None)
        if not callable(setter):
            return
        live = [enemy for enemy in self.enemies if not getattr(enemy, "dead", False)]
        danger_states = {
            "telegraph", "lunge", "drop", "charge_telegraph", "charge",
            "dive_telegraph", "dive", "slam_telegraph", "slam",
            "stomp_warn", "stomp", "sweep_warn", "sweep", "aim",
            "snap_telegraph", "boss_telegraph", "pattern_telegraph",
            "draw_cut", "pounce", "roll", "ram", "comet_dash",
            "sheath", "snicker", "quickdraw", "rustle", "lock", "scan",
            "flare", "prickle", "tail_warn", "charge",
            "counter_cut", "red_stamp", "proof_volley", "margin_burst",
            "agent_aim", "agent_burst", "cut_warn", "shear", "drop_warn",
            "sweep_telegraph", "bounty_draw", "rail_whistle", "staple_columns_warn",
            "moon_release_warn", "meteor_warn", "return_whistle", "return_telegraph", "cross_warn", "bounty_volley", "rail_rush",
            "staple_columns", "moon_release", "meteor_fall",
        }
        danger = sum(getattr(enemy, "state", "") in danger_states for enemy in live)
        health_ratio = ctx.player.health / max(1, ctx.player.max_health)
        pressure = .24 + min(.24, len(live) * .08) + min(.28, danger * .13)
        pressure += (1.0 - health_ratio) * .14
        if not live:
            pressure = .12
        setter(min(1.0, pressure), self.boss)

    def draw(self, surface, camera, renderer):
        if self.encounter_active:
            left = camera.screen_x(self.start_x)
            right = camera.screen_x(self.end_x)
            label = getattr(self, "display_name", self.arena_id.replace('_', ' '))
            renderer.doodle_text(surface, label, (left + 30, 305),
                                 INK_LIGHT, renderer.font_small, -1)
            renderer.doodle_text(surface, f"wave {self.wave + 1}/{max(1, len(self.wave_ids))}",
                                 (right - 115, 305), INK_LIGHT, renderer.font_small, 1)
            jitter_line(surface, (111, 66, 65), (left + 20, 340), (right - 25, 340),
                        1, int(self.start_x), 1, .8)
            if self.boss_intro_time > 0:
                alpha = min(1.0, self.boss_intro_time / .35,
                            (2.8 - self.boss_intro_time) / .3)
                card = pygame.Surface((760, 116), pygame.SRCALPHA)
                card.fill((246, 241, 222, round(226 * max(0.0, alpha))))
                pygame.draw.rect(card, (111, 66, 65, round(245 * max(0.0, alpha))),
                                 card.get_rect(), 3)
                label = getattr(self, "display_name", self.arena_id.replace('_', ' '))
                renderer.doodle_text(card, label, (34, 22), INK,
                                     renderer.font, -1)
                renderer.doodle_text(card, self.boss_rule, (36, 72),
                                     (126, 58, 58), renderer.font_small, 0)
                surface.blit(card, ((WIDTH - card.get_width()) // 2, 76))
        from staging import draw_enemy_read
        for enemy in self.enemies:
            enemy.draw(surface, camera, renderer)
            draw_enemy_read(surface, camera, renderer, enemy)
