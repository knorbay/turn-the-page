"""An active first lesson, kept separate from campaign combat and saves."""
from __future__ import annotations

import math
import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT


def _saved_number(saved, key, maximum=math.inf, *, integer=False):
    """A damaged lesson counter must never select a negative stage or NaN."""
    value = saved.get(key, 0)
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return 0
    if not math.isfinite(number):
        return 0
    number = max(0, min(maximum, number))
    return int(number) if integer else number


class TrainingLesson:
    active = True
    mandatory = True
    layer = 0
    MIN_SECONDS = 75.0
    DURATIONS = (12.0, 12.0, 18.0, 18.0, 15.0)
    TITLES = ("01 / FIND YOUR FEET", "02 / FOLLOW THE INK", "03 / THE RETURNING FOLD",
              "04 / LEAVE THE RED LINE", "05 / IDEAS THAT STAY")
    TIPS = ("A / D or Left / Right: move.",
            "Space / W / Up: jump. Release for a short jump. Pick up the tool.",
            "F / J or left click: break four targets.",
            "Shift / K or right click: dash out of three red warnings.",
            "E: ask the Artist for stairs, then read the rune seal.")

    def __init__(self, runtime, save, checkpoint_id):
        self.runtime, self.save = runtime, save
        first = next(e for e in runtime.entities.items if getattr(e, "is_combat_arena", False))
        self.seal_x = first.start_x - 94
        self.gate = runtime.world.add(first.start_x - 30, first.start_x - 14, 270, 320,
                                      "training_seal", 22060)
        self.gate.appearance = "arena_border"
        self.seal_ground = 365
        from major_update import PracticeDrawing
        self.targets = [e for e in runtime.entities.items if isinstance(e, PracticeDrawing)]
        for x in (2050, 2500, 2950):
            target = PracticeDrawing(x, 590)
            self.targets.append(target)
            runtime.entities.add(target)
        self.target_gate = runtime.world.add(3200, 3215, 270, 320, "training_target_gate", 25001)
        self.dodge_gate = runtime.world.add(4400, 4415, 270, 320, "training_dodge_gate", 25002)
        self.warning_x = None
        self.warning_time = 0.0
        self.warning_cooldown = .6
        self.dash_since_warning = False
        self.stairs = []
        for i, (x, y) in enumerate(((4690, 515), (4870, 440), (5050, 365), (5240, 365))):
            stair = runtime.world.add(x, x+220, y, 12, f"training_artist_stair_{i}", 25020+i)
            stair.begin_drawing()
            stair.appearance = "handwriting"
            self.stairs.append(stair)
        stair = runtime.world.add(5430, self.seal_x+70, 365, 12, "training_rune_deck", 25030)
        stair.begin_drawing()
        self.stairs.append(stair)
        self.lever_x = 4620
        self.bridge_requested = False
        self.bridge_time = 0.0
        self.hand = None
        saved = save.data.get("tutorial", {}) if save else {}
        if not isinstance(saved, dict):
            saved = {}
        if saved.get("course_revision") != 2 and saved.get("completed") is not True:
            saved = {}
        self.elapsed = _saved_number(saved, "seconds", self.MIN_SECONDS)
        self.stage = _saved_number(saved, "stage", 4, integer=True)
        self.stage_seconds = _saved_number(saved, "stage_seconds")
        self.distance = _saved_number(saved, "distance")
        self.jumps = _saved_number(saved, "jumps", integer=True)
        self.dashes = _saved_number(saved, "dashes", integer=True)
        self.read_seal = saved.get("read_seal") is True
        self.practice_done = saved.get("practice_done") is True
        self.tool_collected = saved.get("tool_collected") is True
        self.dodges = _saved_number(saved, "dodges", integer=True)
        self.bridge_requested = saved.get("bridge_requested") is True
        self.bridge_time = 1.0 if self.bridge_requested else 0.0
        targets = saved.get("targets", ())
        for i in targets if isinstance(targets, (tuple, list)) else ():
            if type(i) is int and 0 <= i < len(self.targets):
                self.targets[i].completed = True
                self.targets[i].enemies.clear()
        self.completed = saved.get("completed") is True or checkpoint_id not in ("start", "alive")
        self.last_x = None
        self.last_airborne = False
        self.last_dash = False
        self.write_clock = 0.0
        self.gate.enabled = not self.completed
        self.target_gate.enabled = not self.completed and self.stage < 3
        self.dodge_gate.enabled = not self.completed and self.stage < 4
        if self.completed or self.bridge_requested:
            for stair in self.stairs:
                stair.complete_drawing()
        # A checkpoint inside the lesson may never bypass its physical seal.
        for cp in runtime.checkpoints:
            if cp.checkpoint_id == "before_" + first.arena_id:
                cp.requires = (*cp.requires, "training_complete")

    def _persist(self, write=False):
        if not self.save:
            return
        self.save.data["tutorial"] = dict(seconds=self.elapsed, stage=self.stage,
            stage_seconds=self.stage_seconds, distance=self.distance, jumps=self.jumps,
            dashes=self.dashes, read_seal=self.read_seal, practice_done=self.practice_done,
            tool_collected=self.tool_collected, completed=self.completed,
            course_revision=2, dodges=self.dodges, bridge_requested=self.bridge_requested,
            targets=[i for i, target in enumerate(self.targets) if target.completed])
        if write:
            self.save.write()

    def observe(self, frame, player):
        if self.completed or player.locked or player.health <= 0:
            self.last_x = player.x
            return
        if self.last_x is not None:
            self.distance += min(30, abs(player.x - self.last_x))
        self.last_x = player.x
        airborne = not player.on_ground and player.vy < -50
        if airborne and not self.last_airborne:
            self.jumps += 1
        self.last_airborne = airborne
        dashing = player.dash_timer > 0
        if dashing and self.warning_x is not None:
            self.dash_since_warning = True
        if dashing and not self.last_dash:
            self.dashes += 1
        self.last_dash = dashing

    def _objectives(self, ctx):
        tool = bool(ctx.weapons and "folded_shuriken" in ctx.weapons.unlocked)
        self.tool_collected = self.tool_collected or tool
        self.practice_done = all(target.completed for target in self.targets)
        return (self.distance >= 260, self.jumps >= 3 and self.tool_collected,
                self.practice_done, self.dashes >= 3 and self.dodges >= 3,
                self.bridge_requested and self.read_seal)

    def _course_update(self, dt, ctx, interact):
        from action_content import claim_artist_canvas, release_artist_canvas
        from scripted_events import ArtistTool
        self.hand = None
        player = ctx.player
        if self.stage == 3 and 3250 < player.center_x < 4360:
            if self.warning_x is None:
                self.warning_cooldown -= dt
                if self.warning_cooldown <= 0:
                    self.warning_x = player.center_x
                    self.warning_time = 1.2
                    self.dash_since_warning = False
                    ctx.sounds.play("pencil")
            else:
                self.warning_time -= dt
                if self.warning_time <= 0:
                    column = pygame.Rect(self.warning_x-70, 320, 140, 270)
                    if not column.colliderect(player.rect) and self.dash_since_warning:
                        self.dodges += 1
                        ctx.level.toast = "Good dodge."
                    else:
                        ctx.level.toast = "Dash after the red warning appears."
                    ctx.level.toast_time = 2
                    self.warning_x = None
                    self.warning_cooldown = 1.0
        else:
            self.warning_x = None
        if self.stage == 4 and abs(player.center_x-self.lever_x) < 85 and not self.bridge_requested:
            ctx.level.interaction_hint = "E / draw the stairs"
            if interact:
                self.bridge_requested = True
                self.bridge_time = 0
        if self.bridge_requested and self.bridge_time < 1:
            if claim_artist_canvas(ctx, self):
                self.bridge_time = min(1, self.bridge_time+dt/.9)
                for stair in self.stairs:
                    stair.draw_progress = self.bridge_time
                self.hand = ArtistTool("pencil", self.stairs[0].visible_x2, self.stairs[0].y, True)
                ctx.director.tool = self.hand
                if self.bridge_time >= 1:
                    release_artist_canvas(ctx, self)

    def update(self, dt, ctx, interact=False):
        if self.completed:
            ctx.level.flags.add("training_complete")
            self.gate.enabled = False
            self.target_gate.enabled = self.dodge_gate.enabled = False
            return
        if ctx.player.locked or ctx.player.health <= 0:
            return
        self.elapsed = min(self.MIN_SECONDS, self.elapsed + dt)
        self.stage_seconds += dt
        self._course_update(dt, ctx, interact)
        near = (abs(ctx.player.center_x - self.seal_x) < 90 and
                abs(ctx.player.rect.bottom-self.seal_ground) < 28)
        if near and not self.read_seal:
            ctx.level.interaction_hint = "E / read the rune seal"
            if interact:
                self.read_seal = True
                ctx.level.toast = "Sketch runes grant permanent techniques. Find them on optional routes."
                ctx.level.toast_time = 4
        objectives = self._objectives(ctx)
        if self.stage_seconds >= self.DURATIONS[self.stage] and objectives[self.stage]:
            if self.stage < 4:
                self.stage += 1
                self.stage_seconds = 0
                self.target_gate.enabled = self.stage < 3
                self.dodge_gate.enabled = self.stage < 4
                ctx.sounds.play("pencil")
            elif self.elapsed >= self.MIN_SECONDS and all(objectives):
                self.completed = True
                self.gate.enabled = False
                ctx.level.flags.add("training_complete")
                ctx.level.toast = "FIRST LESSON COMPLETE / the combat page is open"
                ctx.level.toast_time = 3
                ctx.sounds.play("paper_break")
                self._persist(write=True)
        self.write_clock += dt
        self._persist(write=self.write_clock >= 5)
        if self.write_clock >= 5:
            self.write_clock = 0

    def draw(self, surface, camera, renderer):
        if self.completed:
            return
        x = camera.screen_x(self.seal_x)
        y = round(self.seal_ground-35 + camera.offset_y)
        if -70 < x < surface.get_width() + 70:
            pygame.draw.circle(surface, (139, 57, 50), (x, y), 22, 2)
            pygame.draw.lines(surface, INK, False, [(x-8,y-4),(x,y+5),(x+12,y-10)], 2)
            renderer.doodle_text(surface, "E / LESSON SEAL", (x-84,y-51), INK_LIGHT,
                                  renderer.font_small)
        for x0, text in ((1650, "FOUR TARGETS"),
                         (3330, "THREE RED WARNINGS"),
                         (4550, "THE ARTIST'S STAIRS")):
            renderer.doodle_text(surface, text, (camera.screen_x(x0), 300+camera.offset_y),
                                  (139,57,50), renderer.font_small)
        if self.warning_x is not None:
            sx = camera.screen_x(self.warning_x)
            rect = pygame.Rect(sx-70, 330+camera.offset_y, 140, 260)
            pygame.draw.rect(surface, (163, 68, 55), rect, 2)
            pygame.draw.line(surface, (163,68,55), rect.bottomleft, rect.bottomright, 5)
            renderer.doodle_text(surface, "DASH →", (sx-48, 354+camera.offset_y),
                                  (163,68,55), renderer.font_small)
        sx, sy = camera.screen_x(self.lever_x), round(540+camera.offset_y)
        pygame.draw.line(surface, INK, (sx, sy+25), (sx+16, sy-18), 4)
        renderer.doodle_text(surface, "E / ARTIST", (sx-45, sy-51), INK_LIGHT, renderer.font_small)

    def draw_overlay(self, surface, camera, renderer):
        if self.completed:
            return
        from sketches import wrap_text
        rect = pygame.Rect(24, 102, 425, 162)
        pygame.draw.rect(surface, (247, 241, 219), rect)
        renderer.rough_rect(surface, INK_LIGHT, rect, 1, 22160)
        renderer.doodle_text(surface, self.TITLES[self.stage], (39, 114), (139,57,50),
                              renderer.font_small)
        lines = wrap_text(self.TIPS[self.stage], renderer.font_small, 391)
        for i, line in enumerate(lines[:3]):
            renderer.doodle_text(surface, line, (39, 140+i*21), INK, renderer.font_small)
        statuses = (f"Moved: {round(self.distance)} / 260", f"Jumps: {min(3,self.jumps)} / 3",
                    f"Targets: {sum(t.completed for t in self.targets)} / 4",
                    f"Dodges: {min(3,self.dodges)} / 3",
                    "Seal read" if self.read_seal else "Read the seal with E")
        renderer.doodle_text(surface, statuses[self.stage], (39, 217), INK_LIGHT,
                              renderer.font_small)
        label = f"LESSON {self.stage+1} / 5  ·  {math.floor(self.elapsed):02d} / 75 s"
        renderer.doodle_text(surface, label, (39, 241), INK_LIGHT, renderer.font_small)
        pygame.draw.line(surface, (169,154,126), (280,251), (431,251), 2)
        pygame.draw.line(surface, (139,57,50), (280,251), (280+round(151*self.elapsed/75),251), 3)


def attach_training(runtime, save, checkpoint_id):
    if runtime.index == 0:
        lesson = TrainingLesson(runtime, save, checkpoint_id)
        runtime.entities.add(lesson)
        runtime.training = lesson
    return runtime
