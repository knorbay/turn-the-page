from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable
import pygame

from settings import INK, WIDTH


def combat_active(ctx):
    """Traversal edits wait for the room, including its wave breaks, to clear."""
    entities = getattr(getattr(ctx.level, "entities", None), "items", ())
    return any(getattr(entity, "is_combat_arena", False)
               and getattr(entity, "encounter_active", False)
               and not getattr(entity, "completed", False) for entity in entities)


def artist_canvas_free(ctx, owner=None, allow_in_combat=False):
    director = getattr(ctx, "director", None)
    available = getattr(director, "canvas_available", None)
    return ((allow_in_combat or not combat_active(ctx)) and
            (available(owner) if callable(available) else
             not getattr(director, "blocks_combat", False)))


@dataclass
class EventContext:
    player: object
    world: object
    camera: object
    particles: object
    sounds: object
    level: object
    director: object
    weapons: object | None = None
    game: object | None = None


@dataclass
class EventStep:
    duration: float
    update: Callable[[EventContext, float], None] | None = None
    start: Callable[[EventContext], None] | None = None
    finish: Callable[[EventContext], None] | None = None
    lock_player: bool = False
    camera_x: float | None = None
    label: str = ""


class EventSequence:
    """Reusable timeline driven by a trigger predicate and small authored steps."""

    def __init__(self, name: str, trigger: Callable[[EventContext], bool], steps: list[EventStep], once=True,
                 allow_in_combat=False):
        self.name = name
        self.trigger = trigger
        self.steps = steps
        self.once = once
        self.active = False
        self.done = False
        self.index = 0
        self.timer = 0.0
        self.started_step = False
        self.allow_in_combat = allow_in_combat

    def update(self, dt: float, ctx: EventContext):
        if self.done or not self.steps:
            ctx.player.release_lock(self.name)
            self._release_camera(ctx)
            return
        if not self.allow_in_combat and combat_active(ctx):
            # Also protects direct practice entries or a restored checkpoint:
            # an unfinished traversal scene must never freeze a live fight.
            ctx.player.release_lock(self.name)
            self._release_camera(ctx)
            return
        if not self.active:
            if not self.trigger(ctx):
                return
            self.active = True
            self.index = 0
            self.timer = 0
            self.started_step = False
        step = self.steps[self.index]
        if not self.started_step:
            self.started_step = True
            if step.start:
                step.start(ctx)
        if step.lock_player:
            ctx.player.acquire_lock(self.name)
        else:
            ctx.player.release_lock(self.name)
        if step.lock_player and step.camera_x is not None:
            target = getattr(ctx.camera, "set_script_target", None)
            if callable(target):
                target(step.camera_x, self.name)
            else:
                ctx.camera.script_target = step.camera_x
        else:
            self._release_camera(ctx)
        self.timer += dt
        progress = min(1.0, self.timer / max(.001, step.duration))
        if step.update:
            step.update(ctx, progress)
        if progress < 1:
            return
        if step.finish:
            step.finish(ctx)
        self.index += 1
        self.timer = 0
        self.started_step = False
        self._release_camera(ctx)
        if self.index >= len(self.steps):
            self.done = True
            self.active = False
            ctx.player.release_lock(self.name)
            ctx.level.flags.add(self.name)

    def _release_camera(self, ctx):
        release = getattr(ctx.camera, "release_script_target", None)
        if callable(release):
            release(self.name)
        elif self.active:
            ctx.camera.script_target = None


@dataclass
class ArtistTool:
    kind: str = "none"
    x: float = 0
    y: float = 0
    visible: bool = False
    angle: float = -.55
    intensity: float = 1.0


@dataclass
class WrittenMessage:
    x: float
    y: float
    text: str
    progress: float = 0
    angry: bool = False


class ArtistDirector:
    def __init__(self):
        self.events: list[EventSequence] = []
        self.tool = ArtistTool()
        self.messages: list[WrittenMessage] = []
        self.canvas_owner = None
        self.canvas_in_combat = False

    def add(self, event: EventSequence):
        self.events.append(event)
        return event

    def update(self, dt, ctx):
        self.tool.visible = False
        if self.canvas_owner is not None:
            return
        # One hand owns one stroke. Dormant scenes queue behind the current
        # timeline instead of overwriting its tip or advancing off-screen.
        current = next((event for event in self.events if event.active and not event.done), None)
        if current is not None:
            current.update(dt, ctx)
            return
        for event in self.events:
            event.update(dt, ctx)
            if event.active or self.tool.visible:
                break

    @property
    def blocks_combat(self):
        return ((self.canvas_owner is not None and not self.canvas_in_combat) or
                any(event.active and not event.done and not event.allow_in_combat
                    for event in self.events))

    def canvas_available(self, owner=None):
        if self.canvas_owner is not None:
            return owner is self.canvas_owner
        return not self.tool.visible and not any(
            event.active and not event.done for event in self.events)

    def claim_canvas(self, owner, allow_in_combat=False):
        if owner is None or not self.canvas_available(owner):
            return False
        self.canvas_owner = owner
        self.canvas_in_combat = allow_in_combat
        return True

    def release_canvas(self, owner):
        if self.canvas_owner is owner:
            self.canvas_owner = None
            self.canvas_in_combat = False

    def write(self, x, y, text, progress, angry=False):
        message = next((m for m in self.messages if m.text == text and m.x == x), None)
        if message is None:
            message = WrittenMessage(x, y, text, 0, angry)
            self.messages.append(message)
        message.progress = max(message.progress, progress)
        return message

    def draw(self, surface, camera, renderer):
        self.draw_messages(surface, camera, renderer)
        self.draw_tool(surface, camera)

    def draw_messages(self, surface, camera, renderer):
        for message in self.messages:
            shown = message.text[:max(0, round(len(message.text) * message.progress))]
            if not shown:
                continue
            x = camera.screen_x(message.x)
            color = (70, 35, 35) if message.angry else INK
            renderer.doodle_text(surface, shown, (x, round(message.y + camera.offset_y)), color,
                                 renderer.font if message.angry else renderer.font_small,
                                 -2 if message.angry else 1)

    def draw_tool(self, surface, camera):
        if not self.tool.visible:
            return
        if self.tool.kind == "pencil":
            self._draw_pencil(surface, camera)
        elif self.tool.kind == "eraser":
            self._draw_eraser(surface, camera)

    def _draw_pencil(self, surface, camera):
        x = camera.screen_x(self.tool.x)
        y = round(self.tool.y + camera.offset_y)
        angle = self.tool.angle
        length = 330
        ex, ey = x + math.cos(angle) * length, y + math.sin(angle) * length
        pygame.draw.line(surface, (207, 139, 43), (x + 15, y - 9), (ex, ey), 25)
        pygame.draw.line(surface, (241, 194, 77), (x + 18, y - 14), (ex, ey - 5), 6)
        pygame.draw.polygon(surface, (218, 183, 127), [(x, y), (x + 31, y - 22), (x + 35, y - 6)])
        pygame.draw.polygon(surface, (39, 38, 37), [(x, y), (x + 9, y - 7), (x + 12, y - 2)])
        # Thumb and curled fingers actually grip the pencil. The wrist leaves
        # the frame, keeping the Artist outside the notebook's scale.
        hx, hy = round(ex+20), round(ey)
        skin, edge = (218,177,151), (145,105,88)
        outline = [(hx-29,hy-27),(hx-8,hy-51),(hx+27,hy-55),
                   (hx+65,hy-27),(hx+117,hy-19),(hx+127,hy+42),
                   (hx+58,hy+47),(hx+27,hy+27),(hx-5,hy+23),
                   (hx-27,hy+7)]
        pygame.draw.polygon(surface,skin,outline)
        pygame.draw.lines(surface,edge,True,outline,2)
        for offset in (0,17,34):
            pygame.draw.arc(surface,edge,(hx-13+offset,hy-31,28,42),1.4,4.1,2)
        pygame.draw.ellipse(surface,(232,192,163),(hx-32,hy-7,55,23))
        pygame.draw.arc(surface,edge,(hx-32,hy-7,55,23),0,math.pi,2)
        pygame.draw.polygon(surface,(91,107,124),
            [(hx+85,hy-29),(hx+131,hy-24),(hx+142,hy+47),(hx+96,hy+53)])
        pygame.draw.line(surface,(53,62,77),(hx+91,hy-27),(hx+103,hy+50),3)

    def _draw_eraser(self, surface, camera):
        x = camera.screen_x(self.tool.x) - 48
        y = round(self.tool.y + camera.offset_y) - 54
        pygame.draw.polygon(surface, (218, 145, 145), [(x + 5, y + 12), (x + 87, y + 2),
                                                       (x + 101, y + 45), (x + 20, y + 59)])
        pygame.draw.polygon(surface, (240, 190, 180), [(x + 5, y + 12), (x + 21, y + 31),
                                                       (x + 20, y + 59), (x, y + 37)])


def draw_platform_event(name, trigger_x, platform, duration=2.0, lock=True, message=None):
    def start(ctx):
        platform.begin_drawing()
        ctx.sounds.play("pencil")

    def update(ctx, progress):
        platform.draw_progress = progress
        ctx.director.tool = ArtistTool("pencil", platform.visible_x2, platform.y, True)
        ctx.particles.pencil_speck(platform.visible_x2, platform.y)
        if message:
            ctx.director.write(platform.x1, platform.y - 90, message, progress)

    def finish(ctx):
        platform.complete_drawing()
        ctx.camera.kick(3, .18)

    return EventSequence(name, lambda ctx: ctx.player.x >= trigger_x, [
        EventStep(.35, lock_player=lock, label="artist hesitation"),
        EventStep(duration, update=update, start=start, finish=finish, lock_player=lock,
                  camera_x=(platform.x1 + platform.x2) * .5),
        EventStep(.25, lock_player=lock),
    ])


class EraserChase:
    """A fair run-forward set piece: collision disappears behind, not under, the player."""

    def __init__(self, name, platform, trigger_x, end_x, speed=235):
        self.name = name
        self.platform = platform
        self.trigger_x = trigger_x
        self.cursor = platform.x1
        self.end_x = end_x
        self.speed = speed
        self.active = False
        self.done = False
        self.warning = 0.0

    def update(self, dt, ctx):
        if self.done:
            return
        if combat_active(ctx):
            return
        if not self.active:
            if ctx.player.x < self.trigger_x:
                return
            self.active = True
            self.warning = .9
            ctx.sounds.play("erase")
        if self.warning > 0:
            self.warning -= dt
            ctx.director.tool = ArtistTool("eraser", self.cursor, self.platform.y, True)
            return
        safe_limit = max(self.cursor, ctx.player.x - 135)
        target = min(self.end_x, self.cursor + self.speed * dt, safe_limit)
        if target > self.cursor:
            self.platform.erase(self.cursor, target)
            self.cursor = target
            ctx.particles.eraser_dust(self.cursor, self.platform.y, 4)
        ctx.director.tool = ArtistTool("eraser", self.cursor, self.platform.y, True)
        if self.cursor >= self.end_x - 1:
            self.done = True
            ctx.level.flags.add(self.name)
            ctx.camera.kick(4, .2)


class FinaleDirector:
    """Position-driven combination of drawing, erasing and Artist handwriting."""

    def __init__(self, platforms):
        self.platforms = platforms
        self.done = False
        self.beats = set()

    def update(self, dt, ctx):
        if combat_active(ctx):
            return
        x = ctx.player.x
        for i, platform in enumerate(self.platforms):
            threshold = platform.x1 - 280
            if x > threshold and platform.draw_progress < 1:
                platform.draw_progress = min(1, platform.draw_progress + dt * 1.8)
                ctx.director.tool = ArtistTool("pencil", platform.visible_x2, platform.y, True)
                ctx.particles.pencil_speck(platform.visible_x2, platform.y)
        if x > 2450 and "no" not in self.beats:
            self.beats.add("no")
            ctx.director.write(2520, 270, "NO", 1, True)
            ctx.sounds.play("pencil")
        if x > 3600 and "hesitate" not in self.beats:
            self.beats.add("hesitate")
            ctx.director.write(3740, 260, "...", 1)
        if x > ctx.world.width - 300:
            self.done = True
            ctx.level.flags.add("finale_complete")
