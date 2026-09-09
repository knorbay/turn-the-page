from __future__ import annotations

from dataclasses import dataclass
import math
import random
import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT


class Entity:
    active = True

    def update(self, dt, ctx, interact=False):
        pass

    def draw(self, surface, camera, renderer):
        pass


@dataclass
class LostSketch(Entity):
    x: float
    y: float
    secret_id: str
    caption: str
    discovered: bool = False
    pulse: float = 0
    near: bool = False
    acquired_time: float = 0

    def update(self, dt, ctx, interact=False):
        from sketches import collection_message, sketch_for
        self.pulse += dt
        self.acquired_time = max(0, self.acquired_time-dt)
        self.near = abs(ctx.player.center_x - self.x) < 62 and abs(ctx.player.rect.bottom - self.y) < 95
        sketch = sketch_for(self.secret_id)
        if self.near and not self.discovered:
            ctx.level.interaction_hint = (f"E  learn {sketch.technique.lower()}" if sketch else
                                          "E  examine lost sketch")
        if self.near and interact and not self.discovered:
            self.discovered = True
            self.acquired_time = 2.4
            ctx.level.discover_secret(self.secret_id, self.caption)
            if sketch:
                ctx.level.toast = collection_message(self.secret_id)
                ctx.level.toast_time = 6
            ctx.sounds.play("pencil")
            ctx.particles.paper_puff(self.x, self.y, 12)

    def draw(self, surface, camera, renderer):
        from sketches import draw_sketch_icon, sketch_for, wrap_text
        if self.discovered and self.acquired_time <= 0:
            return
        x = camera.screen_x(self.x)
        if x < -360 or x > surface.get_width()+360:
            return
        y = round(self.y + camera.offset_y - 2 + math.sin(self.pulse * 2.2)*2)
        sketch = sketch_for(self.secret_id)
        accent = (151, 68, 62)
        if not self.discovered:
            page = [(x-26,y-37),(x+19,y-39),(x+29,y-30),(x+27,y+13),(x-27,y+11)]
            pygame.draw.polygon(surface, (246, 238, 211), page)
            pygame.draw.lines(surface, INK_LIGHT, True, page, 1)
            pygame.draw.lines(surface, accent, False, [(x+19,y-39),(x+18,y-28),(x+29,y-30)],1)
            draw_sketch_icon(surface, sketch.icon if sketch else "figure", (x,y-12),34)
            pygame.draw.line(surface,accent,(x-9,y+18),(x+9,y+18),2)
            if not self.near:
                return
        elif self.acquired_time > 1.6:
            radius = round(18+(2.4-self.acquired_time)*40)
            pygame.draw.circle(surface, accent, (x,y-14), radius, 1)
            pygame.draw.lines(surface,accent,False,[(x-9,y-15),(x-2,y-8),(x+13,y-24)],3)
        if not sketch:
            return
        # Explain the reward before collection, where the player can decide
        # whether the optional route is useful to their play style.
        width = 342
        card = pygame.Rect(max(12,min(surface.get_width()-width-12,x-width//2)),max(90,y-151),width,94)
        pygame.draw.rect(surface,(245,239,219),card,border_radius=3)
        renderer.rough_rect(surface,INK_LIGHT,card,1,5200+len(self.secret_id))
        label = ("LEARNED / " if self.discovered else "TECHNIQUE / ")+sketch.technique
        surface.blit(renderer.font_small.render(label,True,accent),(card.x+12,card.y+9))
        for index,line in enumerate(wrap_text(sketch.benefit,renderer.font_small,width-24)):
            surface.blit(renderer.font_small.render(line,True,INK),(card.x+12,card.y+34+index*19))
        prompt = "Clipped into BACK PAGES" if self.discovered else "E  keep this drawing"
        surface.blit(renderer.font_small.render(prompt,True,INK_LIGHT),(card.x+12,card.y+70))


@dataclass
class PressureSwitch(Entity):
    x: float
    y: float
    flag: str
    require_creature: bool = False
    pressed: bool = False
    width: int = 64

    def update(self, dt, ctx, interact=False):
        plate = pygame.Rect(round(self.x - self.width / 2), round(self.y - 8), self.width, 12)
        player_on = plate.colliderect(ctx.player.rect.inflate(-6, 8))
        creature_on = any(getattr(e, "is_doodle", False) and e.rect.colliderect(plate.inflate(4, 12))
                          for e in ctx.level.entities.items)
        pressed = creature_on if self.require_creature else (player_on or creature_on)
        if pressed and not self.pressed:
            self.pressed = True
            ctx.level.flags.add(self.flag)
            ctx.camera.kick(3, .16)
            ctx.sounds.play("paper_step")

    def draw(self, surface, camera, renderer):
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        drop = 4 if self.pressed else 0
        pygame.draw.polygon(surface, (65, 63, 60), [(x - 32, y - 7 + drop), (x + 32, y - 7 + drop),
                                                    (x + 25, y + 1), (x - 25, y + 1)])
        pygame.draw.line(surface, (122, 115, 101), (x - 23, y + 2), (x + 23, y + 2), 2)


class DoodleCreature(Entity):
    is_doodle = True

    def __init__(self, x, y, name="scribble", companion=True, color=INK):
        self.x = float(x)
        self.y = float(y)
        self.vx = self.vy = 0.0
        self.name = name
        self.companion = companion
        self.color = color
        self.time = 0.0
        self.facing = 1
        self.on_ground = False
        self.active = True
        self.holding = False

    @property
    def rect(self):
        return pygame.Rect(round(self.x - 15), round(self.y - 28), 30, 28)

    def update(self, dt, ctx, interact=False):
        self.time += dt
        distance = ctx.player.center_x - self.x
        near_player = abs(distance) < 72 and abs(ctx.player.rect.bottom - self.y) < 80
        if near_player:
            ctx.level.interaction_hint = "E  ask the blot to " + ("follow" if self.holding else "stay")
        if near_player and interact:
            self.holding = not self.holding
            ctx.sounds.play("doodle")
        if self.holding:
            desired = 0
        elif self.companion:
            desired = 120 * (1 if distance > 80 else -1 if distance < -45 else 0)
        else:
            desired = -90 * (1 if abs(distance) < 140 else 0)
        self.vx += (desired - self.vx) * min(1, dt * 5)
        if abs(self.vx) > 3:
            self.facing = 1 if self.vx > 0 else -1
        # Catch up without teleporting on camera: the doodle hops in a paper puff.
        if self.companion and abs(distance) > 620:
            self.x = ctx.player.x - ctx.player.facing * 180
            self.y = ctx.player.y + ctx.player.HEIGHT
            self.vy = -180
            ctx.particles.paper_puff(self.x, self.y, 8)
        self.x += self.vx * dt
        self.vy = min(700, self.vy + 1450 * dt)
        previous_bottom = self.y
        self.y += self.vy * dt
        self.on_ground = False
        for platform in ctx.world.collision_rects():
            if self.rect.colliderect(platform) and self.vy >= 0 and previous_bottom <= platform.top + 5:
                self.y = platform.top
                self.vy = 0
                self.on_ground = True
        # Friendly creatures bounce over small breaks.
        if self.on_ground and abs(desired) > 0 and self._no_floor_ahead(ctx.world):
            self.vy = -410
        if self.y > 820 and self.companion:
            self.x = ctx.player.x - 100
            self.y = ctx.player.y
            self.vy = 0

    def _no_floor_ahead(self, world):
        ahead = pygame.Rect(round(self.x + self.facing * 28), round(self.y + 2), 8, 38)
        return not any(ahead.colliderect(p) for p in world.collision_rects())

    def draw(self, surface, camera, renderer):
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        bounce = math.sin(self.time * 9) * 2 if abs(self.vx) > 10 else math.sin(self.time * 3)
        rng = random.Random(round(self.time * 7) % 3 + 71)
        points = []
        for i in range(13):
            a = math.tau * i / 13
            radius = 13 + rng.uniform(-4, 4)
            points.append((x + math.cos(a) * radius, y - 13 + math.sin(a) * (10 + bounce)))
        pygame.draw.lines(surface, self.color, True, points, 2)
        pygame.draw.circle(surface, self.color, (x - 4, round(y - 15)), 1)
        pygame.draw.circle(surface, self.color, (x + 5, round(y - 15)), 1)
        mouth = pygame.Rect(x - 5, round(y - 13), 11, 7)
        pygame.draw.arc(surface, self.color, mouth, 0, math.pi, 1)
        pygame.draw.line(surface, self.color, (x - 7, y - 2), (x - 12 - self.facing * 2, y + 3), 2)
        pygame.draw.line(surface, self.color, (x + 7, y - 2), (x + 12 - self.facing * 2, y + 3), 2)


@dataclass
class TearPortal(Entity):
    rect: pygame.Rect
    target_x: float
    target_y: float
    target_layer: int
    label: str = "enter tear"
    one_way: bool = False
    used: bool = False

    def update(self, dt, ctx, interact=False):
        near = self.rect.inflate(45, 35).colliderect(ctx.player.rect)
        if near:
            ctx.level.interaction_hint = f"E  {self.label}"
        if near and interact and not (self.one_way and self.used):
            self.used = True
            ctx.sounds.play("tear")
            ctx.particles.paper_puff(ctx.player.center_x, ctx.player.rect.bottom, 16)
            ctx.world.active_layer = self.target_layer
            ctx.player.x = self.target_x
            ctx.player.y = self.target_y
            ctx.player.vx = ctx.player.vy = 0
            ctx.camera.x = max(0, self.target_x - 360)

    def draw(self, surface, camera, renderer):
        x = camera.screen_x(self.rect.x)
        y = round(self.rect.y + camera.offset_y)
        points = [(x, y + 16), (x + 13, y + 3), (x + 31, y + 13), (x + 49, y),
                  (x + 66, y + 17), (x + self.rect.w, y + 7),
                  (x + self.rect.w - 8, y + self.rect.h), (x + 8, y + self.rect.h - 5)]
        pygame.draw.polygon(surface, (54, 52, 51), points)
        pygame.draw.lines(surface, (120, 114, 102), True, points, 2)
        for px, py in points[:6]:
            pygame.draw.line(surface, (196, 189, 169), (px, py), (px + 8, py - 8), 1)


@dataclass
class FallingDoodle(Entity):
    x: float
    y: float
    width: int
    height: int
    trigger_flag: str
    result_flag: str
    vy: float = 0
    fallen: bool = False

    @property
    def rect(self):
        return pygame.Rect(round(self.x), round(self.y), self.width, self.height)

    def update(self, dt, ctx, interact=False):
        if self.trigger_flag in ctx.level.flags and not self.fallen:
            self.vy = min(800, self.vy + 1200 * dt)
            self.y += self.vy * dt
            for platform in ctx.world.collision_rects():
                if self.rect.colliderect(platform) and self.vy > 0:
                    self.y = platform.top - self.height
                    self.vy = 0
                    self.fallen = True
                    ctx.level.flags.add(self.result_flag)
                    ctx.camera.kick(7, .3)
                    ctx.sounds.play("paper_step")

    def draw(self, surface, camera, renderer):
        x = camera.screen_x(self.x)
        y = round(self.y + camera.offset_y)
        jitter_line(surface, INK, (x, y), (x + self.width, y + self.height), 4, 301, 2, 2)
        jitter_line(surface, INK, (x + self.width, y), (x, y + self.height), 4, 302, 2, 2)
        renderer.doodle_text(surface, "?", (x + self.width // 2 - 5, y + self.height // 2 - 15), font=renderer.font)


class EntitySystem:
    def __init__(self, items=None):
        self.items: list[Entity] = list(items or [])

    def add(self, entity):
        self.items.append(entity)
        return entity

    def update(self, dt, ctx, interact=False):
        for item in self.items:
            if getattr(item, "active", True):
                item.update(dt, ctx, interact)

    def draw(self, surface, camera, renderer):
        for item in self.items:
            if getattr(item, "active", True):
                item.draw(surface, camera, renderer)
