"""Procedural action-combat weapons for Paper Story.

The module deliberately owns no game-loop policy.  A game creates one
``WeaponSystem(player)``, forwards input to :meth:`handle_input`, updates it
with the currently live enemies, then asks it to draw world and HUD effects.

``aim`` is a world-space point.  Enemies are intentionally duck-typed: the
system understands the current ``DoodleEnemy`` fields (``rect``, ``hp``,
``dead``, ``vx`` and ``state``), but will prefer a future ``take_damage`` or
``damage`` method when one exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

import pygame

from paper_renderer import jitter_line
from page_arsenal import profile_for, draw_weapon_icon
from settings import INK, INK_LIGHT, PAPER


WEAPON_ORDER = (
    "pencil_blade",
    "ink_pistol",
    "marker_shotgun",
    "eraser_cannon",
    "rubber_band",
    "excalibur",
)

WEAPON_ALIASES = {
    "pencil": "pencil_blade",
    "blade": "pencil_blade",
    "pistol": "ink_pistol",
    "ink": "ink_pistol",
    "shotgun": "marker_shotgun",
    "marker": "marker_shotgun",
    "eraser": "eraser_cannon",
    "cannon": "eraser_cannon",
    "band": "rubber_band",
    "rubber": "rubber_band",
    "hero_sword": "excalibur",
    "king_arthur": "excalibur",
}

WEAPON_NAMES = {
    "pencil_blade": "PENCIL BLADE",
    "ink_pistol": "INK PISTOL",
    "marker_shotgun": "MARKER SHOTGUN",
    "eraser_cannon": "ERASER CANNON",
    "rubber_band": "RUBBER BAND",
    "excalibur": "THE VERY DRAMATIC SWORD",
}


def _clamp(value, low, high):
    return max(low, min(high, value))


def _enemy_rect(enemy):
    rect = getattr(enemy, "rect", None)
    rect = rect() if callable(rect) else rect
    return rect if isinstance(rect, pygame.Rect) else None


def _live_enemies(items) -> list[object]:
    """Flatten enemies, arenas, entity systems, and ordinary iterables."""
    if items is None:
        return []
    if hasattr(items, "items") and not isinstance(items, (list, tuple, set, dict)):
        items = items.items
    try:
        roots = list(items)
    except TypeError:
        roots = [items]
    result, seen = [], set()
    pending = list(roots)
    while pending:
        item = pending.pop(0)
        nested = getattr(item, "enemies", None)
        if nested is not None and _enemy_rect(item) is None:
            pending.extend(list(nested))
            continue
        identity = id(item)
        if identity in seen or _enemy_rect(item) is None:
            continue
        seen.add(identity)
        if not getattr(item, "dead", False) and getattr(item, "active", True):
            result.append(item)
            pending.extend(getattr(item, "combat_targets", ()))
    return result


def _call(ctx, owner, method, *args):
    target = getattr(ctx, owner, None)
    function = getattr(target, method, None)
    if callable(function):
        return function(*args)
    return None


@dataclass
class ImpactMark:
    x: float
    y: float
    kind: str
    life: float = .28
    max_life: float = .28
    size: float = 13.0
    seed: int = 1
    layer: object = field(default=None, repr=False)

    def update(self, dt):
        self.life -= dt

    def draw(self, surface, camera):
        fade = _clamp(self.life / max(.001, self.max_life), 0, 1)
        screen_x, screen_y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        target = surface
        if self.layer is None:
            self.layer = pygame.Surface((96,96),pygame.SRCALPHA)
        surface = self.layer
        surface.fill((0,0,0,0))
        x, y = 48,48
        alpha = round(245*fade**.75)
        color = (*INK_LIGHT,alpha)
        radius = max(2, round(self.size * (.65 + .35 * fade)))
        rng = random.Random(self.seed)
        if self.kind.endswith("_muzzle"):
            # A short paper-white flash with graphite edges; the heavy marker
            # blossoms wider while the pistol gives one sharp, dry tick.
            count=7 if self.kind.startswith("marker") else 5
            points=[]
            for i in range(count*2):
                a=i*math.tau/(count*2)
                r=radius if i%2==0 else radius*.32
                points.append((x+math.cos(a)*r,y+math.sin(a)*r))
            pygame.draw.polygon(surface,(247,238,200,alpha),points)
            pygame.draw.lines(surface,(65,55,62,alpha),True,points,1)
        elif self.kind == "eraser":
            for _ in range(5):
                ox, oy = rng.randint(-radius, radius), rng.randint(-radius // 2, radius // 2)
                pygame.draw.rect(surface, (177,153,140,alpha), (x + ox, y + oy, 4, 2), border_radius=1)
        elif self.kind == "marker":
            pygame.draw.circle(surface, (48,48,57,alpha), (x, y), radius, 2)
            pygame.draw.circle(surface, (86,82,91,alpha), (x - 2, y - 2), max(1, radius // 3), 1)
        elif self.kind == "ion_wave":
            pygame.draw.arc(surface, (74, 136, 158, alpha),
                            (x-radius, y-radius, radius*2, radius*2), -.75, .75, 3)
            pygame.draw.line(surface, (215, 232, 230, alpha),
                             (x-radius, y), (x+radius, y), 1)
        elif self.kind.startswith("bowie"):
            for index in range(3 if self.kind.endswith("finisher") else 1):
                ox = index * 5 - 5
                pygame.draw.line(surface, (143, 88, 55, alpha),
                                 (x-radius+ox, y+radius), (x+radius+ox, y-radius), 2)
        elif self.kind.startswith("field"):
            pygame.draw.line(surface, (68, 96, 82, alpha),
                             (x-radius, y+3), (x+radius, y-3), 2)
            if self.kind.endswith("finisher"):
                pygame.draw.line(surface, (68, 96, 82, alpha),
                                 (x-radius//2, y-radius), (x+radius//2, y+radius), 2)
        elif self.kind.startswith("redraw"):
            pygame.draw.line(surface, (64, 61, 60, alpha),
                             (x-radius, y+radius//2), (x+radius, y-radius//2), 2)
            pygame.draw.line(surface, (165, 60, 63, alpha),
                             (x-radius+4, y+radius//2+4), (x+radius+4, y-radius//2+4), 2)
        elif self.kind.startswith("katana"):
            angle = -.9 if self.kind.endswith("rise") else -.35
            end = (x + math.cos(angle) * radius, y + math.sin(angle) * radius)
            start = (x - math.cos(angle) * radius, y - math.sin(angle) * radius)
            pygame.draw.line(surface, (151, 61, 58, alpha), start, end,
                             3 if self.kind.endswith("rise") else 2)
        elif self.kind in ("pencil", "pencil_finisher"):
            for i in range(3):
                ox=rng.randrange(-7,8);oy=rng.randrange(-5,6)
                pygame.draw.line(surface,(151,61,58,alpha) if self.kind.endswith("finisher") else color,
                    (x-radius+ox,y+radius//2+oy),(x+radius+ox,y-radius//2+oy),2 if i==0 else 1)
        else:
            for index in range(5):
                angle = math.tau * index / 5 + rng.uniform(-.16, .16)
                end = (x + math.cos(angle) * radius, y + math.sin(angle) * radius)
                pygame.draw.line(surface, color, (x, y), end, 1)
        target.blit(surface,(screen_x-48,screen_y-48))


@dataclass
class MeleeSwing:
    combo: int
    direction: pygame.Vector2
    duration: float
    active_from: float
    active_to: float
    damage: float
    reach: float
    knockback: float
    stagger: float
    style: str = "pencil"
    damage_kind: str = "pencil"
    echo_from: float = 0.0
    echo_to: float = 0.0
    echo_damage: float = 0.0
    elapsed: float = 0.0
    hit_ids: set[int] = field(default_factory=set)
    echo_hit_ids: set[int] = field(default_factory=set)

    @property
    def active(self):
        return self.primary_active or self.echo_active

    @property
    def primary_active(self):
        return self.active_from <= self.elapsed <= self.active_to

    @property
    def echo_active(self):
        return self.echo_damage > 0 and self.echo_from <= self.elapsed <= self.echo_to

    @property
    def current_hit_ids(self):
        return self.echo_hit_ids if self.echo_active and not self.primary_active else self.hit_ids

    @property
    def current_damage(self):
        return self.damage * self.echo_damage if self.echo_active and not self.primary_active else self.damage

    @property
    def finished(self):
        return self.elapsed >= self.duration

    def hit_rect(self, player):
        origin = pygame.Vector2(player.center_x, player.rect.centery)
        center = origin + self.direction * (self.reach * .53)
        if self.style == "bowie":
            height = 50 if self.combo == 3 else 42
        elif self.style == "field_knife":
            height = 58 if self.combo == 3 else 40
        elif self.style == "katana" and self.combo == 3:
            height = 104
            center.y -= 18
        elif self.style == "ion_blade":
            height = 86 if self.combo == 3 else 62
        else:
            height = 74 if self.combo == 3 else 54
        width = round(self.reach * max(.55, abs(self.direction.x)))
        width = max(38 if self.style in ("bowie", "field_knife") else 48, width)
        return pygame.Rect(round(center.x - width / 2), round(center.y - height / 2), width, height)

    def pencil_pose(self):
        """Three authored strokes; animation shares the real active interval."""
        facing = 1 if self.direction.x >= 0 else -1
        base = math.atan2(self.direction.y, self.direction.x)
        strokes = {
            "katana": {1: (-.38, .28), 2: (.34, -.24), 3: (.88, -1.08)},
            "bowie": {1: (-.58, .24), 2: (.44, -.22), 3: (-.82, .48)},
            "ion_blade": {1: (-1.22, .86), 2: (1.12, -.96), 3: (-1.58, 1.18)},
            "field_knife": {1: (-.18, .06), 2: (.16, -.05), 3: (-.34, .18)},
        }.get(self.style, {1: (-1.05, .65), 2: (.80, -.78), 3: (-1.45, .92)})
        start, finish = strokes[self.combo]
        if self.elapsed < self.active_from:
            t = _clamp(self.elapsed / self.active_from, 0, 1)
            offset = start * (.66 + .34*t)
            power = -.12*t
        elif self.elapsed <= self.active_to:
            t = (self.elapsed-self.active_from) / (self.active_to-self.active_from)
            t = 1-(1-t)**2
            offset = start+(finish-start)*t
            power = math.sin(t*math.pi)
        else:
            t = _clamp((self.elapsed-self.active_to)/(self.duration-self.active_to),0,1)
            offset = finish*(1-.20*t)
            power = (1-t)*.20
        return base + offset*facing, self.reach*(.80+.20*max(0,power)), power


@dataclass
class PaperProjectile:
    kind: str
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    radius: int
    life: float
    knockback: float
    stagger: float = 0.0
    gravity: float = 0.0
    bounces: int = 0
    pierce: int = 0
    erase_radius: int = 0
    seed: int = 1
    attack_id: int = 0
    active: bool = True
    age: float = 0.0
    hit_ids: set[int] = field(default_factory=set)
    trail: list[tuple[float, float]] = field(default_factory=list)
    visual: str = ""
    ricochet_loss: float = .84

    @property
    def rect(self):
        return pygame.Rect(round(self.x - self.radius), round(self.y - self.radius),
                           self.radius * 2, self.radius * 2)

    def update(self, dt, ctx, enemies, solids, system):
        if not self.active:
            return
        self.age += dt
        self.life -= dt
        if self.life <= 0:
            self.active = False
            return
        speed = max(1, math.hypot(self.vx, self.vy))
        steps = max(1, min(12, math.ceil(speed * dt / max(3, self.radius * .65))))
        step_dt = dt / steps
        for _ in range(steps):
            if not self.active:
                break
            old_x, old_y = self.x, self.y
            self.vy += self.gravity * step_dt
            self.x += self.vx * step_dt
            self.y += self.vy * step_dt
            if not self.trail or math.hypot(self.x - self.trail[-1][0], self.y - self.trail[-1][1]) > 7:
                self.trail.append((self.x, self.y))
                del self.trail[:-8]

            if self.erase_radius:
                self._erase_hostile_projectiles(enemies, ctx, system)

            collision = next((solid for solid in solids if self.rect.colliderect(solid)), None)
            if collision is not None:
                if self.kind == "rubber_band" and self.bounces > 0:
                    self._ricochet(collision, old_x, old_y, ctx, system)
                else:
                    self.active = False
                    system.impact(self.x, self.y, self.kind)
                continue

            for enemy in enemies:
                identity = id(enemy)
                rect = _enemy_rect(enemy)
                if identity in self.hit_ids or rect is None or not self.rect.colliderect(rect):
                    continue
                self.hit_ids.add(identity)
                direction = 1 if self.vx >= 0 else -1
                system.damage_enemy(enemy, self.damage, direction, self.knockback,
                                    self.stagger, self.kind, ctx, self.attack_id)
                system.impact(self.x, self.y, self.kind, self.radius + 6)
                if self.kind == "rubber_band" and self.bounces > 0:
                    self.vx *= -1
                    if self.visual != "pulse":
                        self.vy += (self.y - rect.centery) * 4
                    self.bounces -= 1
                    self.damage *= .96 if self.visual == "pulse" else .88
                    _call(ctx, "sounds", "play", "paper_step")
                elif self.pierce > 0:
                    self.pierce -= 1
                    self.damage *= .72
                else:
                    self.active = False
                break

    def _ricochet(self, solid, old_x, old_y, ctx, system):
        old = pygame.Rect(round(old_x - self.radius), round(old_y - self.radius),
                          self.radius * 2, self.radius * 2)
        if old.right <= solid.left + 2 or old.left >= solid.right - 2:
            self.vx *= -1
            self.x = old_x
        elif old.bottom <= solid.top + 2 or old.top >= solid.bottom - 2:
            self.vy *= -1
            self.y = old_y
        else:
            # Choose the shallowest penetration for rough/overlapping ink strokes.
            px = min(abs(self.rect.right - solid.left), abs(solid.right - self.rect.left))
            py = min(abs(self.rect.bottom - solid.top), abs(solid.bottom - self.rect.top))
            if px < py:
                self.vx *= -1
                self.x = old_x
            else:
                self.vy *= -1
                self.y = old_y
        self.bounces -= 1
        self.damage *= self.ricochet_loss
        system.impact(self.x, self.y, "pulse" if self.visual == "pulse" else "band", 9)
        _call(ctx, "sounds", "play", "rubber")

    def _erase_hostile_projectiles(self, enemies, ctx, system):
        erase_rect = self.rect.inflate(self.erase_radius * 2, self.erase_radius * 2)
        for enemy in enemies:
            hostile = getattr(enemy, "projectiles", None)
            if not isinstance(hostile, list):
                continue
            for shot in hostile:
                rect = getattr(shot, "rect", None)
                rect = rect() if callable(rect) else rect
                alive = getattr(shot, "life", 1) > 0 and getattr(shot, "active", True)
                if alive and isinstance(rect, pygame.Rect) and erase_rect.colliderect(rect):
                    if hasattr(shot, "life"):
                        shot.life = 0
                    if hasattr(shot, "active"):
                        shot.active = False
                    system.impact(rect.centerx, rect.centery, "eraser", 8)
                    _call(ctx, "particles", "eraser_dust", rect.centerx, rect.centery, 4)

    def draw(self, surface, camera):
        if not self.active:
            return
        points = [(camera.screen_x(x), round(y + camera.offset_y)) for x, y in self.trail]
        if len(points) > 1:
            color = ((69, 123, 148) if self.visual in ("pulse", "null", "ion_wave") else
                     (101, 97, 91) if self.kind != "marker" else (66, 61, 72))
            pygame.draw.lines(surface, color, False, points,
                              3 if self.visual == "ion_wave" else 2 if self.visual == "pulse" else 1)
        x, y = camera.screen_x(self.x), round(self.y + camera.offset_y)
        if self.visual == "ion_wave":
            direction = pygame.Vector2(self.vx, self.vy)
            if direction.length_squared() > 0:
                direction = direction.normalize()
            normal = pygame.Vector2(-direction.y, direction.x)
            back = pygame.Vector2(x, y) - direction * 13
            front = pygame.Vector2(x, y) + direction * 7
            pygame.draw.lines(surface, (64, 111, 139), False,
                              [back + normal*12, front, back - normal*12], 3)
            pygame.draw.lines(surface, (222, 236, 232), False,
                              [back + normal*7, front-direction*2, back-normal*7], 1)
        elif self.visual == "pulse":
            pygame.draw.circle(surface, (64, 109, 139), (x,y), self.radius, 2)
            pygame.draw.circle(surface, (215, 230, 226), (x,y), max(1,self.radius-3))
            pygame.draw.line(surface, (83, 126, 148), (x-self.radius-3,y), (x+self.radius+3,y), 1)
            pygame.draw.line(surface, (83, 126, 148), (x,y-self.radius-3), (x,y+self.radius+3), 1)
        elif self.visual == "null":
            pygame.draw.circle(surface, (66, 115, 139), (x,y), self.radius+2, 2)
            pygame.draw.circle(surface, (224, 233, 219), (x,y), self.radius-2)
            pygame.draw.line(surface, (137, 157, 157), (x-self.radius+4,y), (x+self.radius-4,y), 2)
        elif self.visual == "suppressed":
            direction = pygame.Vector2(self.vx,self.vy).normalize()
            pygame.draw.line(surface, (45,56,50), (x,y),
                             (x-direction.x*9,y-direction.y*9), 2)
        elif self.kind == "ink":
            pygame.draw.circle(surface, (28, 29, 37), (x, y), self.radius)
            pygame.draw.circle(surface, (91, 88, 96), (x - 2, y - 2), max(1, self.radius // 3))
        elif self.kind == "marker":
            pygame.draw.ellipse(surface, (48, 44, 55),
                                (x - self.radius - 2, y - self.radius // 2, self.radius * 2 + 4, self.radius), 0)
        elif self.kind == "eraser":
            angle = math.degrees(math.atan2(-self.vy, self.vx))
            block = pygame.Surface((36, 20), pygame.SRCALPHA)
            pygame.draw.rect(block, (210, 166, 151), (1, 1, 34, 18), border_radius=3)
            pygame.draw.line(block, (112, 103, 99), (18, 2), (18, 18), 1)
            block = pygame.transform.rotate(block, angle)
            surface.blit(block, block.get_rect(center=(x, y)))
        else:
            pygame.draw.ellipse(surface, (170, 104, 82),
                                (x - self.radius, y - max(3, self.radius // 2), self.radius * 2, max(6, self.radius)), 3)
            pygame.draw.line(surface, INK_LIGHT, (x - self.radius, y), (x + self.radius, y), 1)


class BaseWeapon:
    weapon_id = "base"
    label = "BASE"
    mag_size = -1
    reload_time = 0.0
    fire_delay = .3
    automatic = False

    def __init__(self):
        self.ammo = self.mag_size
        self.reserve = -1  # infinite reserve avoids campaign soft-locks
        self.cooldown = 0.0
        self.reload_timer = 0.0

    @property
    def reloading(self):
        return self.reload_timer > 0

    def update(self, dt):
        self.cooldown = max(0, self.cooldown - dt)
        if self.reload_timer > 0:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.reload_timer = 0
                self.ammo = self.mag_size

    def start_reload(self):
        if self.mag_size > 0 and self.ammo < self.mag_size and not self.reloading:
            player = getattr(getattr(self,"system",None), "player", None)
            bonus = (getattr(player,"sketch_pistol_reload",1.0) if self.weapon_id == "ink_pistol" else
                     getattr(player,"sketch_eraser_reload",1.0) if self.weapon_id == "eraser_cannon" else 1.0)
            self.reload_duration = self.reload_time * bonus
            self.reload_timer = self.reload_duration
            return True
        return False

    def trigger(self, system, pressed, held, ctx):
        wants_fire = pressed or (self.automatic and held)
        if not wants_fire or self.cooldown > 0 or self.reloading:
            return False
        if self.mag_size > 0 and self.ammo <= 0:
            self.start_reload()
            _call(ctx, "sounds", "play", "reload")
            return False
        fired = self.fire(system, ctx)
        if fired:
            self.cooldown = max(self.cooldown, self.fire_delay)
            if self.mag_size > 0:
                self.ammo -= 1
                if self.ammo <= 0:
                    self.start_reload()
        return fired

    def fire(self, system, ctx):
        raise NotImplementedError


class PencilBlade(BaseWeapon):
    weapon_id = "pencil_blade"
    label = "PENCIL BLADE"
    fire_delay = .34

    def fire(self, system, ctx):
        profile = system.profile()
        style = profile.silhouette
        combo = system.combo_index + 1 if system.combo_window > 0 else 1
        if combo > 3:
            combo = 1
        system.combo_index = combo

        # Each page's starter uses a different combat grammar.  The save id is
        # intentionally stable, but these are authored attacks rather than one
        # combo with renamed stats.
        if style == "katana":
            durations = {1: .25, 2: .28, 3: .46}
            damage = {1: 1.15, 2: .95, 3: 2.45}
            reach = {1: 61, 2: 67, 3: 91}
            active_to = {1: .16, 2: .16, 3: .25}
            knockback = {1: 230, 2: 90, 3: 255}
            stagger = {1: .16, 2: .08, 3: .72}
            damage_kind = {1: "katana_draw", 2: "katana_return", 3: "katana_rise"}[combo]
            combo_window = .67
        elif style == "bowie":
            durations = {1: .18, 2: .19, 3: .29}
            damage = {1: .72, 2: .78, 3: 1.30}
            reach = {1: 58, 2: 55, 3: 64}
            active_to = {1: .105, 2: .11, 3: .17}
            knockback = {1: 65, 2: 45, 3: 185}
            stagger = {1: .07, 2: .07, 3: .42}
            damage_kind = "bowie_finisher" if combo == 3 else "bowie_cut"
            combo_window = .48
        elif style == "ion_blade":
            durations = {1: .24, 2: .25, 3: .40}
            damage = {1: .82, 2: .90, 3: 1.55}
            reach = {1: 66, 2: 72, 3: 86}
            active_to = {1: .14, 2: .15, 3: .23}
            knockback = {1: 105, 2: 115, 3: 245}
            stagger = {1: .08, 2: .10, 3: .48}
            damage_kind = "ion_edge_finisher" if combo == 3 else "ion_edge"
            combo_window = .58
        elif style == "field_knife":
            durations = {1: .15, 2: .16, 3: .25}
            damage = {1: .62, 2: .68, 3: 1.35}
            reach = {1: 54, 2: 56, 3: 63}
            active_to = {1: .085, 2: .09, 3: .14}
            knockback = {1: 40, 2: 45, 3: 155}
            stagger = {1: .04, 2: .04, 3: .30}
            damage_kind = "field_finisher" if combo == 3 else "field_knife"
            combo_window = .39
        else:
            durations = {1: .25, 2: .28, 3: .46}
            damage = {1: 1.0, 2: 1.15, 3: 2.8}
            reach = {1: 61, 2: 67, 3: 91}
            active_to = {1: .16, 2: .16, 3: .25}
            knockback = {1: 175, 2: 175, 3: 410}
            stagger = {1: .12, 2: .12, 3: .70}
            damage_kind = "redraw_finisher" if style == "redraw_pencil" and combo == 3 else (
                "redraw" if style == "redraw_pencil" else
                "pencil_finisher" if combo == 3 else "pencil"
            )
            combo_window = .62

        system.combo_window = combo_window if combo < 3 else .18
        duration = durations[combo] * profile.tempo
        reach = reach[combo]*profile.reach_scale + (getattr(system.player,"sketch_finisher_reach",0) if combo == 3 else 0)
        active_from = (.025 if style in ("bowie", "field_knife") else .045) * profile.tempo
        strike_to = active_to[combo] * profile.tempo
        echo_from = echo_to = echo_damage = 0.0
        if style == "redraw_pencil":
            echo_from = strike_to + .055
            echo_to = echo_from + (.075 if combo < 3 else .105)
            echo_damage = {1: .55, 2: .60, 3: .70}[combo]
            duration = max(duration, echo_to + .055)
        system.melee = MeleeSwing(combo, system.aim_direction, duration,
                                  active_from, strike_to,
                                  damage[combo]*profile.damage, reach,
                                  knockback[combo], stagger[combo], style=style,
                                  damage_kind=damage_kind, echo_from=echo_from,
                                  echo_to=echo_to, echo_damage=echo_damage)

        target_range = {"katana": 190, "bowie": 112, "ion_blade": 170,
                        "field_knife": 102, "redraw_pencil": 155}.get(style, 165)
        step = {
            "katana": {1: 165, 2: -105, 3: 74},
            "bowie": {1: 92, 2: 70, 3: 48},
            "ion_blade": {1: 38, 2: 32, 3: 18},
            "field_knife": {1: 78, 2: 68, 3: 54},
            "redraw_pencil": {1: 40, 2: 46, 3: 62},
        }.get(style, {1: 48, 2: 62, 3: 96})[combo]
        target_ahead = system.melee_target_ahead(target_range)
        if (abs(system.aim_direction.x) > .25 and not system.player.dashing
                and abs(system.player.vx) < 230 and target_ahead):
            system.player.vx = _clamp(
                system.player.vx + system.aim_direction.x * step, -390, 390,
            )

        # Ion Edge's third input covers a corridor instead of only enlarging
        # the melee box.  Its finite pierce count makes lining enemies up matter.
        if style == "ion_blade" and combo == 3:
            origin = system.muzzle(34)
            direction = system.aim_direction
            system.projectiles.append(PaperProjectile(
                "ion_wave", origin.x, origin.y, direction.x * 780, direction.y * 780,
                1.25, 15, .48, 125, .18, pierce=3,
                seed=system.next_seed(), visual="ion_wave",
            ))
            system.impact(origin.x, origin.y, "ion_wave", 18)

        recovery = ({"bowie": .67, "field_knife": .58, "ion_blade": .76,
                     "redraw_pencil": .96}.get(style, .78)
                    if combo < 3 else
                    {"bowie": .78, "field_knife": .72, "ion_blade": .88,
                     "redraw_pencil": .98}.get(style, .94))
        self.cooldown = duration * recovery
        cut_sound = {
            "katana": "katana_cut",
            "bowie": "bowie_cut",
            "ion_blade": "ion_slice",
            "field_knife": "field_knife",
        }.get(style, "blade")
        _call(ctx, "sounds", "play", cut_sound)
        kick = ({"bowie": .8, "field_knife": .45, "ion_blade": 1.0,
                 "redraw_pencil": .7}.get(style, 1.2) if combo < 3 else
                {"bowie": 2.6, "field_knife": 1.8, "ion_blade": 3.8,
                 "redraw_pencil": 3.0}.get(style, 3.2))
        _call(ctx, "camera", "kick", kick, .07 if combo < 3 else .15)
        return True


class InkPistol(BaseWeapon):
    weapon_id = "ink_pistol"
    label = "INK PISTOL"
    mag_size = 9
    reload_time = 1.22
    fire_delay = .30
    automatic = True

    def fire(self, system, ctx):
        direction = system.aim_direction
        origin = system.muzzle(19)
        profile = system.profile()
        speed = profile.speed * getattr(system.player,"sketch_pistol_velocity",1.0)
        system.projectiles.append(PaperProjectile("ink", origin.x, origin.y,
                                                  direction.x * speed, direction.y * speed,
                                                  profile.damage, 3 if system.page_index == 3 else 5,
                                                  profile.lifetime, profile.knockback, .05,
                                                  gravity=profile.gravity,
                                                  pierce=getattr(system.player,"sketch_pistol_pierce",0),
                                                  seed=system.next_seed(),
                                                  visual="suppressed" if system.page_index == 3 else ""))
        system.muzzle_flash("ink", origin, 3 if system.page_index == 3 else 9 if system.page_index == 1 else 7)
        system.player.vx -= direction.x * profile.recoil
        _call(ctx, "sounds", "play", "staple" if system.page_index == 3 else "pistol")
        _call(ctx, "camera", "kick", .35 if system.page_index == 3 else 1.2 if system.page_index == 1 else .8, .055)
        return True


class MarkerShotgun(BaseWeapon):
    weapon_id = "marker_shotgun"
    label = "MARKER SHOTGUN"
    mag_size = 4
    reload_time = 1.72
    fire_delay = 1.04

    def fire(self, system, ctx):
        # Keep ids until their whole volley expires, including future faster
        # page variants. A second barrel must not re-enable the first's hits.
        living_ids = {shot.attack_id for shot in system.projectiles if shot.active}
        system._boss_marker_volleys = {key for key in system._boss_marker_volleys if key[0] in living_ids}
        base = math.atan2(system.aim_direction.y, system.aim_direction.x)
        origin = system.muzzle(22)
        volley_id = system.next_seed()
        profile = system.profile()
        spread = profile.spread * getattr(system.player,"sketch_shotgun_spread",1.0)
        for index in range(profile.pellets):
            angle = base + math.radians(-spread/2 + index * (spread / max(1,profile.pellets-1)))
            speed = profile.speed - abs(index - (profile.pellets-1)/2) * 14
            system.projectiles.append(PaperProjectile(
                "marker", origin.x, origin.y, math.cos(angle) * speed, math.sin(angle) * speed,
                profile.damage, 6, profile.lifetime,
                profile.knockback*getattr(system.player,"sketch_shotgun_knockback",1.0),
                .08, gravity=profile.gravity, seed=system.next_seed(),
                attack_id=volley_id))
        system.muzzle_flash("marker", origin, 20 if system.page_index == 1 else 13 if system.page_index == 3 else 17)
        # Physical marker recoil makes its role readable without a stat screen.
        system.player.vx -= system.aim_direction.x * profile.recoil
        _call(ctx, "sounds", "play", "shotgun")
        _call(ctx, "camera", "kick", 4.2, .16)
        return True


class EraserCannon(BaseWeapon):
    weapon_id = "eraser_cannon"
    label = "ERASER CANNON"
    mag_size = 2
    reload_time = 2.35
    fire_delay = 1.38

    def fire(self, system, ctx):
        direction = system.aim_direction
        origin = system.muzzle(25)
        profile = system.profile()
        system.projectiles.append(PaperProjectile(
            "eraser", origin.x, origin.y, direction.x * profile.speed, direction.y * profile.speed,
            profile.damage, 13, profile.lifetime, profile.knockback, .9, gravity=profile.gravity,
            pierce=profile.pierce, erase_radius=profile.erase_radius,
            seed=system.next_seed(), visual="null" if system.page_index == 2 else ""))
        system.player.vx -= direction.x * profile.recoil
        system.muzzle_flash("eraser", origin, 20)
        _call(ctx, "particles", "eraser_dust", origin.x, origin.y, 8)
        _call(ctx, "sounds", "play", "cannon")
        _call(ctx, "camera", "kick", 6, .22)
        return True


class RubberBand(BaseWeapon):
    weapon_id = "rubber_band"
    label = "RUBBER BAND"
    fire_delay = .78
    automatic = True

    def fire(self, system, ctx):
        direction = system.aim_direction
        origin = system.muzzle(18)
        profile = system.profile()
        system.projectiles.append(PaperProjectile(
            "rubber_band", origin.x, origin.y, direction.x * profile.speed, direction.y * profile.speed,
            profile.damage, 9, profile.lifetime*getattr(system.player,"sketch_rubber_lifetime",1.0), profile.knockback, .1,
            gravity=profile.gravity,
            bounces=profile.bounces+getattr(system.player,"sketch_rubber_bounces",0), seed=system.next_seed(),
            visual="pulse" if system.page_index == 2 else "",
            ricochet_loss=.94 if system.page_index == 2 else .84))
        system.muzzle_flash("band", origin, 9)
        _call(ctx, "sounds", "play", "rubber")
        return True


class Excalibur(BaseWeapon):
    """Signature-page power reversal, intentionally not a campaign staple."""

    weapon_id = "excalibur"
    label = "THE VERY DRAMATIC SWORD"
    fire_delay = .84

    def fire(self, system, ctx):
        system.combo_index = 3
        system.combo_window = .18
        system.melee = MeleeSwing(3, system.aim_direction, .52,
                                  .06, .35, 4.0, 158, 620, 1.0,
                                  style="excalibur", damage_kind="excalibur")
        if not system.player.dashing:
            system.player.vx = _clamp(
                system.player.vx + system.aim_direction.x * 190, -460, 460,
            )
        _call(ctx, "sounds", "play", "hero_sword")
        _call(ctx, "camera", "kick", 7.5, .24)
        return True


class WeaponSystem:
    """Page-aware arsenal with procedural projectiles, combo state, and saves.

    Typical integration::

        weapons.handle_input(slot, wheel, pressed, held, world_mouse, ctx)
        weapons.update(dt, ctx, active_arena.enemies)
        weapons.draw_world(surface, camera, renderer)
        weapons.draw_hud(surface, renderer)

    ``weapon_select`` accepts an id, alias, legacy number key, or zero-based index.
    ``switch`` accepts ``-1``/``1`` or ``"prev"``/``"next"``.
    """

    def __init__(self, player):
        self.player = player
        instances = (PencilBlade(), InkPistol(), MarkerShotgun(), EraserCannon(),
                     RubberBand(), Excalibur())
        self.weapons = {weapon.weapon_id: weapon for weapon in instances}
        for weapon in self.weapons.values():
            weapon.system = self
        self.page_index = None
        self.current_id = "pencil_blade"
        self.unlocked: set[str] = {"pencil_blade"}
        self.projectiles: list[PaperProjectile] = []
        self.impacts: list[ImpactMark] = []
        self.melee: MeleeSwing | None = None
        self.combo_index = 0
        self.combo_window = 0.0
        self.aim_target: pygame.Vector2 | None = None
        self.aim_direction = pygame.Vector2(getattr(player, "facing", 1) or 1, 0)
        self._seed = 1907
        self._last_enemies: list[object] = []
        self.attack_serial = 0
        self.fire_buffer = 0.0
        self.active_loadout: set[str] | None = None
        self._boss_marker_volleys: set[tuple[int, int]] = set()
        self._bowie_marks: dict[int, tuple[int, float]] = {}

    @property
    def ammo(self):
        return {weapon_id: weapon.ammo for weapon_id, weapon in self.weapons.items()}

    @property
    def reserve(self):
        return {weapon_id: weapon.reserve for weapon_id, weapon in self.weapons.items()}

    @property
    def current(self):
        return self.weapons[self.current_id]

    def profile(self, weapon_id=None):
        return profile_for(self.page_index, weapon_id or self.current_id)

    def label_for(self, weapon_id=None):
        return self.profile(weapon_id).label

    def draw_icon(self, surface, weapon_id, center, size=42):
        draw_weapon_icon(surface, weapon_id, self.page_index, center, size)

    @property
    def available_ids(self):
        return tuple(weapon_id for weapon_id in WEAPON_ORDER
                     if weapon_id in self.unlocked
                     and (self.active_loadout is None or weapon_id in self.active_loadout))

    def configure_page(self, page_index):
        """Apply handling before importing a checkpoint's magazine counts.

        This method never unlocks a drawing. Ownership and allowed tools are
        separately managed by the page's physical pickups/loadout policy.
        """
        changed = self.page_index != page_index
        self.page_index = page_index
        self.player.arsenal_page = page_index
        if changed:
            self._bowie_marks.clear()
        for weapon_id, weapon in self.weapons.items():
            if weapon_id == "excalibur":
                continue
            profile = self.profile(weapon_id)
            weapon.label = profile.label
            weapon.mag_size = profile.mag_size
            weapon.reload_time = profile.reload_time
            weapon.fire_delay = profile.fire_delay
            if changed:
                weapon.ammo = weapon.mag_size
                weapon.cooldown = 0
                weapon.reload_timer = 0
            elif weapon.mag_size > 0:
                weapon.ammo = min(weapon.ammo,weapon.mag_size)
        return {weapon_id:self.label_for(weapon_id) for weapon_id in self.available_ids}

    def next_seed(self):
        self._seed = (1103515245 * self._seed + 12345) & 0x7fffffff
        return self._seed

    @staticmethod
    def aim_targets(enemies):
        # Keyboard assistance sees the same shootable copies as mouse fire;
        # it cannot reveal the real Wanted poster for free.
        return _live_enemies(enemies)

    def unlock(self, weapon_id):
        resolved = self._resolve_id(weapon_id)
        if resolved is None:
            return False
        was_new = resolved not in self.unlocked
        self.unlocked.add(resolved)
        return was_new

    def set_page_loadout(self, weapon_ids):
        """Restrict selection for one page without forgetting found tools."""
        resolved = {self._resolve_id(item) for item in weapon_ids}
        resolved.discard(None)
        self.active_loadout = resolved or None
        if self.active_loadout is not None and self.current_id not in self.active_loadout:
            fallback = next((weapon_id for weapon_id in WEAPON_ORDER
                             if weapon_id in self.unlocked and weapon_id in self.active_loadout),
                            None)
            if fallback is not None:
                self.current_id = fallback
        return set(self.active_loadout or ())

    def constrain_page_inventory(self, weapon_ids, reset=False):
        """Make ownership page-local while retaining same-page checkpoints."""
        allowed = {self._resolve_id(item) for item in weapon_ids}
        allowed.discard(None)
        allowed.add("pencil_blade")
        if reset:
            self.unlocked = {"pencil_blade"}
        else:
            self.unlocked.intersection_update(allowed)
            self.unlocked.add("pencil_blade")
        if self.current_id not in self.unlocked:
            self.current_id = "pencil_blade"
        self.set_page_loadout(allowed)
        return set(self.unlocked)

    def erase_page_tools(self):
        """Physically concluded pages keep no combat inventory."""
        erased = [weapon_id for weapon_id in WEAPON_ORDER
                  if weapon_id in self.unlocked and weapon_id != "pencil_blade"]
        self.unlocked = {"pencil_blade"}
        self.current_id = "pencil_blade"
        self.projectiles.clear()
        self.impacts.clear()
        self.melee = None
        self.combo_index = 0
        self.combo_window = 0
        self.fire_buffer = 0
        self._boss_marker_volleys.clear()
        self._bowie_marks.clear()
        for weapon in self.weapons.values():
            weapon.cooldown = 0
            weapon.reload_timer = 0
            weapon.ammo = weapon.mag_size
        self.player.set_weapon_pose("pencil_blade", 0, 0)
        self.player.combat_swing = None
        return erased

    def select(self, weapon_id):
        resolved = self._resolve_id(weapon_id)
        if (resolved not in self.unlocked
                or (self.active_loadout is not None and resolved not in self.active_loadout)
                or resolved == self.current_id):
            return False
        self.current_id = resolved
        self.melee = None
        self.player.combat_swing = None
        self.combo_index = 0
        self.combo_window = 0
        self.fire_buffer = 0
        self._bowie_marks.clear()
        return True

    def cycle(self, direction=1):
        available = [weapon_id for weapon_id in WEAPON_ORDER
                     if weapon_id in self.unlocked
                     and (self.active_loadout is None or weapon_id in self.active_loadout)]
        if not available:
            return False
        index = available.index(self.current_id) if self.current_id in available else 0
        return self.select(available[(index + (1 if direction >= 0 else -1)) % len(available)])

    def reload(self, weapon_id=None):
        resolved = self._resolve_id(weapon_id) if weapon_id is not None else self.current_id
        weapon = self.weapons.get(resolved)
        return weapon.start_reload() if weapon else False

    def handle_input(self, weapon_select=None, switch=0, fire_pressed=False, fire_held=False,
                     aim=None, ctx=None, reload_pressed=False):
        if weapon_select is not None:
            self.select(weapon_select)
        if switch:
            direction = -1 if switch in (-1, "prev", "previous", "left") else 1
            self.cycle(direction)
        self._set_aim(aim)
        if reload_pressed:
            if self.reload():
                _call(ctx, "sounds", "play", "reload")
        if getattr(self.player, "locked", False) or getattr(self.player,"health",1) <= 0:
            return False
        if fire_pressed:
            self.fire_buffer = .12
        queued_press = self.fire_buffer > 0
        if queued_press or fire_held:
            if abs(self.aim_direction.x) > .15:
                self.player.facing = 1 if self.aim_direction.x > 0 else -1
        fired = self.current.trigger(self, queued_press, bool(fire_held), ctx)
        if fired:
            self.fire_buffer = 0
            self.attack_serial += 1
            # Compatibility for the current Ink Clone sampling contract.  The
            # legacy attack timer stays untouched, so this cannot create a
            # second melee hit path.
            self.player.attack_serial = self.attack_serial
        return fired

    def update(self, dt, ctx, enemies):
        dt = max(0.0, min(.05, float(dt)))
        for weapon in self.weapons.values():
            weapon.update(dt)
        self.fire_buffer = max(0, self.fire_buffer - dt)
        self.combo_window = max(0, self.combo_window - dt)
        self._bowie_marks = {
            identity: (count, remaining-dt)
            for identity, (count, remaining) in self._bowie_marks.items()
            if remaining > dt
        }
        if self.combo_window <= 0 and self.melee is None:
            self.combo_index = 0
        live = _live_enemies(enemies)
        self._last_enemies = live
        if self.melee is not None:
            self.melee.elapsed += dt
            if self.melee.active:
                hitbox = self.melee.hit_rect(self.player)
                for enemy in live:
                    identity = id(enemy)
                    rect = _enemy_rect(enemy)
                    hit_ids = self.melee.current_hit_ids
                    if identity in hit_ids or rect is None or not hitbox.colliderect(rect):
                        continue
                    hit_ids.add(identity)
                    direction = 1 if self.melee.direction.x >= 0 else -1
                    swing = self.melee
                    echoing = swing.echo_active and not swing.primary_active
                    damage = swing.current_damage
                    knockback = swing.knockback * (.58 if echoing else 1.0)
                    stagger = swing.stagger * (.55 if echoing else 1.0)
                    kind = ("redraw_echo_finisher" if echoing and swing.combo == 3 else
                            "redraw_echo" if echoing else swing.damage_kind)

                    # Bowie cuts only cash out when all three strokes stay on
                    # one target.  Whiffing or changing targets loses the bonus.
                    bowie_marks = self._bowie_marks.get(identity, (0, 0))[0]
                    if swing.style == "bowie" and swing.combo == 3:
                        damage += min(2, bowie_marks) * .72

                    # The field knife is deliberately weak at opening a fight,
                    # then becomes lethal once a non-boss is visibly wounded.
                    hp_before = float(getattr(enemy, "hp", 1))
                    max_hp = float(getattr(enemy, "max_hp", max(1, hp_before)))
                    wounded = max_hp > 0 and hp_before / max_hp <= .55
                    if swing.style == "field_knife" and swing.combo == 3 and wounded:
                        damage = (max(damage, hp_before) if not getattr(enemy, "is_boss", False)
                                  and getattr(enemy, "kind", "") != "boss" else damage * 1.45)

                    applied = self.damage_enemy(enemy, damage, direction, knockback,
                                                stagger, kind, ctx)
                    if applied and swing.style == "bowie":
                        if swing.combo < 3:
                            self._bowie_marks[identity] = (min(2, bowie_marks + 1), .86)
                        else:
                            self._bowie_marks.pop(identity, None)
                    if applied and swing.style == "katana" and swing.combo == 3 \
                            and not getattr(enemy, "is_boss", False) \
                            and getattr(enemy, "kind", "") != "boss" and hasattr(enemy, "vy"):
                        enemy.vy = min(float(enemy.vy), -395.0)
                    if applied and swing.style == "field_knife" and swing.combo == 3 \
                            and getattr(enemy, "hp", 1) <= 0:
                        # A clean execution lets the knife immediately move on.
                        self.weapons["pencil_blade"].cooldown = min(
                            self.weapons["pencil_blade"].cooldown, .055,
                        )
                    self.impact(rect.centerx, rect.centery, kind,
                                20 if swing.combo == 3 else 12)
            if self.melee.finished:
                self.melee = None
        self.player.combat_swing = (self.melee.pencil_pose()
            if self.melee is not None and self.current_id == "pencil_blade" else None)

        world = getattr(ctx, "world", None)
        if world is None and getattr(ctx, "level", None) is not None:
            world = getattr(ctx.level, "world", None)
        solids = list(world.collision_rects()) if world is not None else []
        for projectile in self.projectiles:
            projectile.update(dt, ctx, live, solids, self)
        self.projectiles = [projectile for projectile in self.projectiles if projectile.active]
        for mark in self.impacts:
            mark.update(dt)
        self.impacts = [mark for mark in self.impacts if mark.life > 0]

    def damage_enemy(self, enemy, damage, direction, knockback, stagger, damage_kind, ctx,
                     attack_id=0):
        if getattr(enemy, "dead", False):
            return False
        boss_target = bool(getattr(enemy, "is_boss", False)
                           or getattr(enemy, "kind", "") == "boss")
        volley_key = (int(attack_id), id(enemy))
        if damage_kind == "marker" and attack_id and boss_target \
                and volley_key in self._boss_marker_volleys:
            return False
        weapon_hit = getattr(enemy, "hit_from_weapon", None)
        if callable(weapon_hit):
            # Stateful enemies own their armor and counter-play windows.  In
            # particular, an eraser shot must not forcibly rename a Crumpled
            # One's state before it can decide whether the wall-crash window
            # is open.
            tags = {damage_kind}
            if damage_kind == "eraser":
                tags.update(("eraser", "heavy"))
            elif damage_kind == "marker" or damage_kind.endswith("finisher") \
                    or damage_kind == "katana_rise":
                tags.add("heavy")
            if damage_kind in ("rubber_band", "ion_wave"):
                tags.add("pierce")
            if damage_kind.endswith("finisher") or damage_kind == "katana_rise":
                tags.add("finisher")
            if damage_kind.startswith(("katana_", "bowie_", "ion_edge", "field_", "redraw")):
                tags.add("melee")
            if damage_kind == "excalibur":
                tags.update(("heavy", "finisher", "heroic"))
            if attack_id:
                tags.add(f"attack:{int(attack_id)}")
            applied = weapon_hit(damage, knockback, self.player.center_x, tags, ctx) is not False
            if applied and damage_kind == "marker" and attack_id and boss_target:
                self._boss_marker_volleys.add(volley_key)
            return applied
        armor = getattr(enemy, "armor", 0)
        armored = bool(getattr(enemy, "armored", False) or armor > 0)
        # Existing dense-scribble bosses expose their armor through combat state.
        if getattr(enemy, "kind", "") == "boss" and getattr(enemy, "state", "") != "recover":
            armored = True
        if armored and damage_kind != "eraser":
            self.impact(_enemy_rect(enemy).centerx, _enemy_rect(enemy).centery, "blocked", 10)
            _call(ctx, "particles", "pencil_speck", _enemy_rect(enemy).centerx, _enemy_rect(enemy).centery)
            _call(ctx, "sounds", "play", "paper_step")
            return False
        if damage_kind == "eraser":
            if isinstance(armor, (int, float)) and armor > 0:
                enemy.armor = max(0, armor - 2)
            if hasattr(enemy, "armored"):
                enemy.armored = False
            if hasattr(enemy, "state"):
                enemy.state = "recover"
                enemy.state_time = max(float(getattr(enemy, "state_time", 0)), max(.55, stagger))
            if hasattr(enemy, "stagger_cooldown"):
                enemy.stagger_cooldown = max(float(getattr(enemy, "stagger_cooldown", 0)), stagger)

        applied = False
        method = getattr(enemy, "take_damage", None) or getattr(enemy, "damage", None)
        if callable(method):
            for args in ((damage, direction, ctx), (damage, direction), (damage,)):
                try:
                    result = method(*args)
                    applied = result is not False
                    break
                except TypeError:
                    continue
        elif hasattr(enemy, "hp"):
            enemy.hp -= damage
            applied = True

        if not applied:
            return False
        if damage_kind == "marker" and attack_id and boss_target:
            self._boss_marker_volleys.add(volley_key)
        game = getattr(ctx, "game", None)
        behavior = getattr(game, "behavior", None)
        if behavior is not None:
            behavior.record("enemy_hit", kind=getattr(enemy, "kind", "unknown"),
                            weapon=self.current_id)
        if hasattr(enemy, "vx"):
            enemy.vx += direction * knockback
        if hasattr(enemy, "hit_flash"):
            enemy.hit_flash = max(float(getattr(enemy, "hit_flash", 0)), .15)
        enemy.last_weapon_hit = damage_kind
        hp = getattr(enemy, "hp", 1)
        heavy = (damage_kind in ("eraser", "marker", "pencil_finisher", "excalibur",
                                 "katana_rise") or damage_kind.endswith("finisher"))
        rect = _enemy_rect(enemy)
        if rect:
            _call(ctx, "particles", "combat_hit", rect.centerx, rect.centery,
                  direction, heavy)
        if hp <= 0:
            if hasattr(enemy, "dead"):
                enemy.dead = True
            if hasattr(enemy, "active"):
                enemy.active = False
            if rect:
                _call(ctx, "particles", "paper_puff", rect.centerx, rect.centery, 16)
                _call(ctx, "particles", "enemy_break", rect.centerx, rect.centery,
                      direction, 22 if heavy else 17)
            if behavior is not None:
                behavior.record("enemy_defeated",
                                kind=getattr(enemy, "kind", "unknown"),
                                weapon=self.current_id)
        else:
            if rect:
                if damage_kind == "eraser":
                    _call(ctx, "particles", "eraser_dust", rect.centerx, rect.centery, 6)
                else:
                    _call(ctx, "particles", "pencil_speck", rect.centerx, rect.centery)
        _call(ctx, "camera", "kick", 3.8 if heavy else 1.8,
              .14 if heavy else .08)
        _call(ctx, "sounds", "play", "erase" if damage_kind == "eraser" else
              "heavy_hit" if heavy else "hit")
        game = getattr(ctx, "game", None)
        if game is not None:
            request = getattr(game, "request_hit_stop", None)
            duration = .075 if hp <= 0 else .055 if heavy else .026
            if callable(request):
                request(duration)
            else:
                game.hit_stop = max(getattr(game, "hit_stop", 0), duration)
        return True

    def impact(self, x, y, kind, size=13):
        self.impacts.append(ImpactMark(float(x), float(y), kind, size=float(size), seed=self.next_seed()))

    def muzzle_flash(self, kind, origin, size):
        self.impacts.append(ImpactMark(origin.x,origin.y,kind+"_muzzle",
                           life=.095,max_life=.095,size=size,seed=self.next_seed()))

    def muzzle(self, distance):
        rect = self.player.rect
        origin = pygame.Vector2(self.player.center_x, rect.centery - 5)
        return origin + self.aim_direction * distance

    def _set_aim(self, aim):
        origin = pygame.Vector2(self.player.center_x, self.player.rect.centery - 5)
        if isinstance(aim, dict) and "direction" in aim:
            direction = pygame.Vector2(aim["direction"])
            self.aim_target = origin + direction * 100
        elif aim is not None:
            try:
                self.aim_target = pygame.Vector2(aim)
                direction = self.aim_target - origin
            except (TypeError, ValueError):
                direction = pygame.Vector2(getattr(self.player, "facing", 1) or 1, 0)
                self.aim_target = None
        else:
            direction = pygame.Vector2(getattr(self.player, "facing", 1) or 1, 0)
            self.aim_target = None
        if direction.length_squared() < .0001:
            direction.update(getattr(self.player, "facing", 1) or 1, 0)
        if self.current_id in ("pencil_blade", "excalibur"):
            # Keep a mostly vertical mouse position from collapsing the sword's
            # horizontal hitbox or shoving the player in a surprising direction.
            facing = (1 if direction.x > .08 else -1 if direction.x < -.08
                      else getattr(self.player, "facing", 1) or 1)
            direction.x = facing * max(.62, abs(direction.x))
            direction.y = _clamp(direction.y, -.48, .48)
        self.aim_direction = direction.normalize()

    def melee_target_ahead(self, max_distance=165):
        origin = pygame.Vector2(self.player.center_x, self.player.rect.centery)
        for enemy in self._last_enemies:
            rect = _enemy_rect(enemy)
            if rect is None:
                continue
            offset = pygame.Vector2(rect.center) - origin
            if offset.length() <= max_distance and offset.dot(self.aim_direction) > 0:
                return True
        return False

    def _resolve_id(self, weapon_id):
        if isinstance(weapon_id, int):
            if 1 <= weapon_id <= len(WEAPON_ORDER):
                return WEAPON_ORDER[weapon_id - 1]
            if 0 <= weapon_id < len(WEAPON_ORDER):
                return WEAPON_ORDER[weapon_id]
            return None
        key = str(weapon_id).strip().lower()
        return WEAPON_ALIASES.get(key, key if key in self.weapons else None)

    def snapshot(self):
        return {
            "version": 1,
            "current_id": self.current_id,
            "unlocked": [weapon_id for weapon_id in WEAPON_ORDER if weapon_id in self.unlocked],
            "ammo": self.ammo,
            "reserve": self.reserve,
        }

    def restore(self, data):
        if not isinstance(data, dict):
            return False
        unlocked = {self._resolve_id(item) for item in data.get("unlocked", [])}
        unlocked.discard(None)
        if unlocked:
            self.unlocked = unlocked
        for weapon_id, amount in data.get("ammo", {}).items():
            resolved = self._resolve_id(weapon_id)
            weapon = self.weapons.get(resolved)
            if weapon and weapon.mag_size > 0:
                try:
                    weapon.ammo = int(_clamp(int(amount), 0, weapon.mag_size))
                except (TypeError, ValueError):
                    pass
        for weapon_id, amount in data.get("reserve", {}).items():
            resolved = self._resolve_id(weapon_id)
            weapon = self.weapons.get(resolved)
            if weapon:
                try:
                    weapon.reserve = int(amount)
                except (TypeError, ValueError):
                    pass
        desired = self._resolve_id(data.get("current_id", self.current_id))
        fallback = next((weapon_id for weapon_id in WEAPON_ORDER if weapon_id in self.unlocked),
                        "pencil_blade")
        self.current_id = desired if desired in self.unlocked else fallback
        self.projectiles.clear()
        self.impacts.clear()
        self.melee = None
        self.player.combat_swing = None
        self.combo_index = 0
        self.combo_window = 0
        self.attack_serial = 0
        self.player.attack_serial = 0
        self.fire_buffer = 0
        self._boss_marker_volleys.clear()
        self._bowie_marks.clear()
        for weapon in self.weapons.values():
            weapon.cooldown = 0
            weapon.reload_timer = 0
        return True

    def draw_world(self, surface, camera, renderer):
        for projectile in self.projectiles:
            projectile.draw(surface, camera)
        for mark in self.impacts:
            mark.draw(surface, camera)
        if self.melee is not None:
            self._draw_melee(surface, camera)
        if self.aim_target is not None and self.current_id != "pencil_blade":
            x, y = camera.screen_x(self.aim_target.x), round(self.aim_target.y + camera.offset_y)
            color = (113, 88, 82) if self.current_id == "eraser_cannon" else INK_LIGHT
            pygame.draw.arc(surface, color, (x - 8, y - 8, 16, 16), .2, 1.35, 1)
            pygame.draw.arc(surface, color, (x - 8, y - 8, 16, 16), 3.35, 4.5, 1)

    def _draw_melee(self, surface, camera):
        swing = self.melee
        if self.current_id == "pencil_blade":
            self._draw_pencil_ribbon(surface, camera, swing)
            return
        progress = _clamp(swing.elapsed / swing.duration, 0, 1)
        origin = pygame.Vector2(camera.screen_x(self.player.center_x),
                                self.player.rect.centery - 5 + camera.offset_y)
        base = math.atan2(swing.direction.y, swing.direction.x)
        span = 1.25 if swing.combo < 3 else 1.85
        angle = base - span * .5 + span * progress
        reach = swing.reach * (.82 + .18 * math.sin(progress * math.pi))
        end = origin + pygame.Vector2(math.cos(angle), math.sin(angle)) * reach
        color = (48, 47, 48) if swing.combo < 3 else (137, 55, 53)
        jitter_line(surface, color, origin, end, 3 if swing.combo < 3 else 5,
                    self._seed + swing.combo, 2, 2.2)
        if swing.combo == 3:
            echo = origin + pygame.Vector2(math.cos(angle - .16), math.sin(angle - .16)) * (reach - 7)
            echo_color = (216, 183, 79) if self.current_id == "excalibur" else INK_LIGHT
            pygame.draw.line(surface, echo_color, origin, echo, 3 if self.current_id == "excalibur" else 2)

    def _draw_pencil_ribbon(self, surface, camera, swing):
        # The held blade is drawn with its hands by Player. Only the fast,
        # active slice leaves a curved graphite ribbon behind that blade.
        if swing.elapsed < swing.active_from:
            return
        angle, reach, power = swing.pencil_pose()
        fade = _clamp((swing.duration-swing.elapsed) /
                      max(.001,swing.duration-swing.active_to),0,1)
        origin = pygame.Vector2(camera.screen_x(self.player.center_x),
                                self.player.rect.centery-5+camera.offset_y)
        if not hasattr(self,"_slash_layer"):
            self._slash_layer = pygame.Surface((280,280),pygame.SRCALPHA)
        layer = self._slash_layer
        layer.fill((0,0,0,0))
        facing = 1 if swing.direction.x >= 0 else -1
        turn = (-1 if swing.combo == 2 else 1)*facing
        base_span = {
            "katana": (.72 if swing.combo < 3 else 1.34),
            "bowie": (.48 if swing.combo < 3 else .88),
            "ion_blade": (1.06 if swing.combo < 3 else 1.62),
            "field_knife": (.38 if swing.combo < 3 else .72),
            "redraw_pencil": (.86 if swing.combo < 3 else 1.42),
        }.get(swing.style, .92 if swing.combo < 3 else 1.48)
        span = base_span*fade
        outer=[];inner=[]
        stroke_width = {
            "katana": 3 if swing.combo < 3 else 8,
            "bowie": 7 if swing.combo < 3 else 10,
            "ion_blade": 8 if swing.combo < 3 else 15,
            "field_knife": 3 if swing.combo < 3 else 7,
            "redraw_pencil": 5 if swing.combo < 3 else 10,
        }.get(swing.style, 5 if swing.combo < 3 else 12)
        for i in range(15):
            t=i/14
            a=angle-turn*span*(1-t)
            radius=reach*(.83+.17*t)
            width=stroke_width*math.sin(t*math.pi)
            outer.append((140+math.cos(a)*radius,140+math.sin(a)*radius))
            inner.append((140+math.cos(a)*(radius-width),140+math.sin(a)*(radius-width)))
        color = {
            "katana": (151, 58, 57),
            "bowie": (133, 83, 52),
            "ion_blade": (63, 123, 151),
            "field_knife": (64, 91, 79),
            "redraw_pencil": ((165, 60, 63) if swing.echo_active else (62, 60, 59)),
        }.get(swing.style, self.profile().accent if swing.combo == 3 else (65,63,61))
        fill_alpha = 45 if swing.style in ("katana", "field_knife") else 105
        pygame.draw.polygon(layer,(*color,round(fill_alpha*fade)),outer+list(reversed(inner)))
        pygame.draw.lines(layer,(*color,round(225*fade)),False,outer,
                          1 if swing.style == "field_knife" else 2 if swing.combo<3 else 3)
        for offset in (7,13):
            echo=[(140+(p[0]-140)*(1-offset/reach),140+(p[1]-140)*(1-offset/reach)) for p in outer[3:11]]
            pygame.draw.lines(layer,(*color,round(70*fade)),False,echo,1)
        if swing.style == "ion_blade":
            # Clean light core and parallel edge make the energy slash legible
            # even before its third-hit projectile leaves the player.
            pygame.draw.lines(layer,(224,239,235,round(205*fade)),False,outer[3:13],2)
            pygame.draw.lines(layer,(91,150,171,round(105*fade)),False,inner[2:12],2)
        elif swing.style == "field_knife":
            # Short, separated speed ticks sell rapid stabbing motion.
            for index in (2,6,10):
                pygame.draw.line(layer,(*color,round(210*fade)),outer[index],inner[index],2)
        elif swing.style == "bowie" and swing.combo == 3:
            for index in range(3):
                offset = pygame.Vector2(-4+index*4, 3+index*2)
                pygame.draw.line(layer,(151,92,55,round(180*fade)),
                                 pygame.Vector2(outer[4+index])+offset,
                                 pygame.Vector2(outer[10+index])+offset,2)
        elif swing.style == "redraw_pencil":
            trace = [(x+5*facing,y+4) for x,y in outer[2:13]]
            trace_color = (166,59,62) if swing.echo_active else (124,105,99)
            pygame.draw.lines(layer,(*trace_color,round((235 if swing.echo_active else 85)*fade)),
                              False,trace,2)
        elif swing.style == "katana" and swing.combo == 2:
            pygame.draw.line(layer,(50,49,49,round(170*fade)),outer[2],outer[-2],1)
        surface.blit(layer,(round(origin.x)-140,round(origin.y)-140))

    def draw_hud(self, surface, renderer, pos=(26, 604), controller=False):
        x, y = pos
        available = self.available_ids
        panel = pygame.Rect(x, y, 338 + 46*max(0,len(available)-1), 82)
        veil = pygame.Surface(panel.size, pygame.SRCALPHA)
        veil.fill((*PAPER, 232))
        surface.blit(veil, panel.topleft)
        if hasattr(renderer, "rough_rect"):
            renderer.rough_rect(surface, INK_LIGHT, panel, 1, 913)
        profile = self.profile()
        renderer.doodle_text(surface, profile.label, (x + 14, y + 5), INK, renderer.font_small, -1)
        weapon = self.current
        role = "Finishing stroke" if self.current_id == "pencil_blade" and self.combo_index == 3 and self.melee else profile.role
        renderer.doodle_text(surface, role, (x + 14, y + 27), INK_LIGHT, renderer.font_small)
        for index, weapon_id in enumerate(available):
            bx = x + 32 + index * 46
            selected = weapon_id == self.current_id
            if selected:
                pygame.draw.rect(surface, (228, 218, 192), (bx-21,y+48,42,28), border_radius=3)
                pygame.draw.line(surface, profile.accent, (bx-18,y+77), (bx+18,y+77), 2)
            self.draw_icon(surface,weapon_id,(bx,y+62),size=35)
        if len(available) > 1:
            renderer.doodle_text(surface,"LB / D-PAD" if controller else "Q / wheel",
                                 (x+28+len(available)*46,y+55),INK_LIGHT,renderer.font_small)
        if weapon.mag_size > 0:
            ammo_x = panel.right - 105
            status = "RELOADING" if weapon.reloading else f"{weapon.ammo} / {weapon.mag_size}"
            renderer.doodle_text(surface,status,(ammo_x,y+5),profile.accent if weapon.reloading else INK,renderer.font_small)
            if weapon.reloading:
                duration = getattr(weapon,"reload_duration",weapon.reload_time)
                progress = _clamp(1-weapon.reload_timer/max(.001,duration),0,1)
                pygame.draw.line(surface,(182,172,151),(ammo_x,y+24),(panel.right-14,y+24),2)
                pygame.draw.line(surface,profile.accent,(ammo_x,y+24),(ammo_x+round(progress*91),y+24),3)
            else:
                for index in range(weapon.mag_size):
                    color = INK if index < weapon.ammo else (181,173,153)
                    pygame.draw.line(surface,color,(ammo_x+index*9,y+23),(ammo_x+index*9+3,y+23),2)


__all__ = [
    "WeaponSystem", "BaseWeapon", "PencilBlade", "InkPistol", "MarkerShotgun",
    "EraserCannon", "RubberBand", "Excalibur", "PaperProjectile", "MeleeSwing", "WEAPON_ORDER",
]
