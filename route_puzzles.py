"""Small, physical notebook puzzles for the curated route.

The puzzle owns its geometry.  A completed checkpoint may set ``completed``
directly, just as Level does for combat gates; this restores the drawn ledge
and the open passage without replaying the interactions.
"""

from __future__ import annotations

import math

import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT, RED_RULE


def _record_puzzle_solved(ctx, puzzle_id):
    """Write a solved route beat only for an actual in-game interaction."""
    game = getattr(ctx, "game", None)
    if game is not None:
        game.behavior.record("puzzle_solved", puzzle_id=puzzle_id,
                             page=getattr(ctx.level, "chapter_index", -1))
        game.persist_behavior(write=True)


class DraftBridgePuzzle:
    """Trace below, connect above, then cross out the blocking margin.

    The middle mark is out of reach from the floor.  Tracing the first mark
    causes the Artist to finish a real, landable line; the player must jump
    onto it to continue.  The tall red stroke stays solid until the last
    mark has visibly erased it.  No timing or guessed combination is needed.
    """

    active = True
    mandatory = True
    layer = 0

    def __init__(self, world, start_x: float, page_index: int = 0,
                 puzzle_id: str = "first_page_draft"):
        self.start_x = float(start_x)
        self.page_index = int(page_index)
        self.puzzle_id = puzzle_id
        self.phase = 0
        self.timer = 0.0
        self.erase_progress = 0.0
        self._completed = False
        self.near_index = -1
        self.ledge = world.add(self.start_x + 225, self.start_x + 455, 495, 11,
                               f"{puzzle_id}_upper_line", 9311 + self.page_index)
        self.ledge.appearance = "handwriting"
        self.ledge.draw_progress = 0.0
        # A top well above jump height and a bottom joined to the floor make
        # this a real route gate, including during a dash.
        self.gate = world.add(self.start_x + 650, self.start_x + 676, 92, 498,
                              f"{puzzle_id}_red_margin", 9317 + self.page_index)
        self.gate.appearance = "arena_border"
        self.marks = (
            (self.start_x + 105, 590),
            (self.start_x + 350, 495),
            (self.start_x + 545, 590),
        )

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        self._completed = bool(value)
        if self._completed:
            self.phase = 3
            self.ledge.draw_progress = 1.0
            self.erase_progress = 1.0
            self.gate.enabled = False

    def _near(self, player, index):
        x, bottom_y = self.marks[index]
        return (abs(player.center_x - x) <= 57 and
                abs(player.rect.bottom - bottom_y) <= 54)

    def update(self, dt, ctx, interact=False):
        if self.completed:
            return
        self.timer += max(0.0, dt)
        if self.phase == 1:
            self.ledge.draw_progress = min(1.0, self.timer / .68)
        elif self.phase > 1:
            self.ledge.draw_progress = 1.0
        if self.phase == 3:
            self.erase_progress = min(1.0, self.timer / .52)
            if self.erase_progress >= 1.0:
                self.completed = True
                ctx.level.flags.add(self.puzzle_id)
                _record_puzzle_solved(ctx, self.puzzle_id)
                ctx.level.toast = "THE ARTIST: Better. That line can go."
                ctx.level.toast_time = 2.5
                ctx.sounds.play("paper_break")
                ctx.particles.paper_puff(self.gate.x1, 450, 10)
            return

        self.near_index = next((i for i in range(3) if self._near(ctx.player, i)), -1)
        line_ready = self.phase != 1 or self.ledge.draw_progress >= .95
        if self.near_index == self.phase and not line_ready:
            ctx.level.interaction_hint = "WAIT / the Artist is finishing this line"
        elif self.near_index == self.phase:
            hint = ("E  trace the first graphite mark",
                    "E  connect the upper mark",
                    "E  cross out the red margin")[self.phase]
            ctx.level.interaction_hint = hint
        elif self.near_index >= 0:
            ctx.level.interaction_hint = ("FIRST / lower pencil mark" if self.phase == 0 else
                                          "NEXT / upper pencil mark" if self.phase == 1 else
                                          "LAST / cross out the margin")

        if not interact or self.near_index != self.phase or not line_ready:
            return
        self.phase += 1
        self.timer = 0.0
        ctx.sounds.play("pencil" if self.phase < 3 else "erase")
        ctx.camera.kick(2.0, .12)
        mark_x, mark_y = self.marks[self.phase - 1]
        ctx.particles.paper_puff(mark_x, mark_y - 31, 6)
        ctx.level.toast = (
            "THE ARTIST: A step belongs above this line." if self.phase == 1 else
            "THE ARTIST: Yes. Find the last crossed-out mark." if self.phase == 2 else
            "THE ARTIST: Erasing the margin now."
        )
        ctx.level.toast_time = 2.1

    def draw(self, surface, camera, renderer):
        left = camera.screen_x(self.start_x)
        if left > surface.get_width() + 80 or left + 720 < -80:
            return
        oy = camera.offset_y
        graphite = (75, 73, 71)
        blue = (75, 105, 128)
        faded = (158, 153, 143)
        labels = ("1 / TRACE", "2 / CONNECT ABOVE", "3 / CROSS OUT")
        for i, ((mx, foot_y), label) in enumerate(zip(self.marks, labels)):
            sx = camera.screen_x(mx)
            sy = round(foot_y + oy - 63)
            is_done = self.completed or self.phase > i
            is_current = not self.completed and self.phase == i
            color = blue if is_done else graphite if is_current else faded
            # Three distinct hand-drawn glyphs; their numbers and arrows are
            # still legible without relying on colour.
            if i == 0:
                pygame.draw.arc(surface, color, (sx - 16, sy - 9, 34, 29),
                                .15, math.tau * .91, 2)
                jitter_line(surface, color, (sx - 7, sy + 2), (sx + 12, sy - 5),
                            2, 9350, 2, 1.3)
            elif i == 1:
                jitter_line(surface, color, (sx - 17, sy + 5), (sx + 17, sy - 8),
                            2, 9360, 2, 1.5)
                pygame.draw.circle(surface, color, (sx - 17, sy + 5), 3, 1)
                pygame.draw.circle(surface, color, (sx + 17, sy - 8), 3, 1)
            else:
                jitter_line(surface, color, (sx - 16, sy - 9), (sx + 16, sy + 10),
                            2, 9370, 2, 1.7)
                jitter_line(surface, color, (sx + 15, sy - 10), (sx - 14, sy + 10),
                            2, 9371, 2, 1.7)
            if is_current:
                pygame.draw.circle(surface, color, (sx, sy), 25 + round(2 * math.sin(self.timer * 4)), 1)
            renderer.doodle_text(surface, label, (sx - 73, sy - 45), color,
                                 renderer.font_small, -1 if i != 1 else 1)
            if i == 1:
                jitter_line(surface, color, (sx, sy + 17), (sx, sy + 34),
                            1, 9380, 1, .7)
            else:
                jitter_line(surface, color, (sx, sy + 17), (sx, round(foot_y + oy - 14)),
                            1, 9390 + i, 1, .7)

        # A construction preview describes the jump before it becomes solid.
        y = round(self.ledge.y + oy)
        a, b = camera.screen_x(self.ledge.x1), camera.screen_x(self.ledge.x2)
        if self.phase == 0:
            for x in range(a, b, 22):
                pygame.draw.line(surface, faded, (x, y), (min(x + 9, b), y), 1)
        elif 0 < self.ledge.draw_progress < 1:
            tip = camera.screen_x(self.ledge.visible_x2)
            pygame.draw.polygon(surface, (181, 137, 74),
                                [(tip, y), (tip + 17, y - 16), (tip + 21, y - 8)])
            pygame.draw.line(surface, INK, (tip, y), (tip + 7, y - 6), 2)

        gate_x = camera.screen_x(self.gate.x1)
        if not self.completed:
            renderer.doodle_text(surface, "MARGIN / CLOSED", (gate_x - 86, 307 + oy),
                                 RED_RULE, renderer.font_small, -2)
        if self.phase == 3 and not self.completed:
            # Eraser travels down the stroke while collision remains closed;
            # the last frame disables the gate together with the art.
            top = 100 + oy
            bottom = top + round(480 * self.erase_progress)
            pygame.draw.line(surface, (239, 230, 207), (gate_x + 13, top),
                             (gate_x + 13, bottom), 13)
            pygame.draw.ellipse(surface, (202, 179, 170),
                                (gate_x - 6, bottom - 11, 36, 23), 2)
        elif self.completed:
            jitter_line(surface, INK_LIGHT, (gate_x - 9, 318 + oy),
                        (gate_x + 40, 311 + oy), 1, 9401, 2, 1.2)
            renderer.doodle_text(surface, "REVISED", (gate_x - 19, 272 + oy),
                                 blue, renderer.font_small, -2)


class PerforatedPosterPuzzle:
    """Page II: tear a wanted poster by dashing through its raised seam.

    A floor dash hits solid paper.  A long, one-way torn-paper shelf leads to
    the dashed weak strip ninety pixels above the floor.  A dash at that
    height tears the poster and its collision at once.  The shelf remains
    available after a checkpoint redraw, including when an adjacent vignette
    replaces the old canyon steps.
    """

    active = True
    mandatory = True
    layer = 0

    def __init__(self, world, seam_x: float = 10670, page_index: int = 1,
                 puzzle_id: str = "wanted_perforation"):
        self.start_x = float(seam_x)
        self.page_index = int(page_index)
        self.puzzle_id = puzzle_id
        self._completed = False
        self.timer = 0.0
        self.failed_dash_flash = 0.0
        self.ledge = world.add(seam_x - 300, seam_x - 16, 500, 11,
                               f"{puzzle_id}_approach", 9500 + page_index)
        self.ledge.appearance = "torn_edge"
        self.gate = world.add(seam_x, seam_x + 27, 92, 498,
                              f"{puzzle_id}_poster", 9510 + page_index)
        self.gate.appearance = "arena_border"

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        self._completed = bool(value)
        if self._completed:
            self.gate.enabled = False

    def update(self, dt, ctx, interact=False):
        del interact
        if self.completed:
            return
        self.timer += max(0.0, dt)
        self.failed_dash_flash = max(0.0, self.failed_dash_flash - dt)
        player = ctx.player
        near = self.gate.x1 - 215 <= player.center_x <= self.gate.x2 + 85
        at_seam = 450 <= player.rect.bottom <= 535
        striking = (self.gate.x1 - 33 <= player.rect.right <= self.gate.x2 + 12
                    and player.rect.left < self.gate.x1 and player.dashing
                    and player.dash_direction > 0)
        if near:
            ctx.level.interaction_hint = (
                "DASH RIGHT / through the dashed seam" if at_seam else
                "JUMP ABOVE / the poster tears at the dashed seam"
            )
        if not striking:
            return
        if not at_seam:
            self.failed_dash_flash = .4
            return
        self.completed = True
        ctx.level.flags.add(self.puzzle_id)
        _record_puzzle_solved(ctx, self.puzzle_id)
        ctx.level.toast = "THE ARTIST: A good tear. I should have left that edge rough."
        ctx.level.toast_time = 3.1
        ctx.sounds.play("paper_break")
        ctx.camera.kick(5.0, .22)
        ctx.particles.paper_puff(self.gate.x1, 480, 18)

    def draw(self, surface, camera, renderer):
        sx = camera.screen_x(self.gate.x1)
        if sx < -125 or sx > surface.get_width() + 125:
            return
        oy = camera.offset_y
        paper = (232, 217, 187)
        edge = (117, 91, 74)
        faint = (150, 119, 97)
        top = round(267 + oy)
        if not self.completed:
            shelf_x = camera.screen_x(self.ledge.x1)
            renderer.doodle_text(surface, "JUMP / THEN DASH  >>",
                                 (shelf_x + 17, 456 + oy), edge,
                                 renderer.font_small, -2)
            # The silhouette is a pinned western wanted sheet, not an arena
            # bar.  Imperfect repeated strokes match the ruled notebook.
            pygame.draw.polygon(surface, paper,
                                [(sx - 47, top + 5), (sx - 16, top + 3),
                                 (sx + 40, top - 4), (sx + 45, top + 31),
                                 (sx + 43, top + 104), (sx + 50, top + 195),
                                 (sx + 19, top + 199), (sx - 43, top + 201),
                                 (sx - 40, top + 139), (sx - 48, top + 87)])
            jitter_line(surface, edge, (sx - 47, top + 5), (sx + 40, top - 4),
                        2, 9511, 2, 1.9)
            jitter_line(surface, edge, (sx - 43, top + 201), (sx + 50, top + 195),
                        2, 9512, 2, 1.9)
            jitter_line(surface, faint, (sx - 47, top + 5), (sx - 43, top + 201),
                        1, 9513, 2, 2.0)
            jitter_line(surface, faint, (sx + 40, top - 4), (sx + 50, top + 195),
                        1, 9514, 2, 2.0)
            for i in range(6):
                hatch_x = sx - 31 + i * 12
                pygame.draw.line(surface, (191, 173, 143),
                                 (hatch_x, top + 174), (hatch_x + 7, top + 187), 1)
            pygame.draw.circle(surface, edge, (sx - 39, top + 11), 3, 1)
            pygame.draw.circle(surface, edge, (sx + 35, top + 4), 3, 1)
            renderer.doodle_text(surface, "WANTED", (sx - 40, top + 20),
                                 RED_RULE, renderer.font_small, -3)
            # The bad likeness is deliberately page-local, unlike the foes.
            pygame.draw.ellipse(surface, edge, (sx - 19, top + 64, 35, 46), 2)
            jitter_line(surface, edge, (sx - 29, top + 71), (sx + 25, top + 72),
                        3, 9520, 2, 1.2)
            pygame.draw.line(surface, edge, (sx - 9, top + 86), (sx - 5, top + 86), 2)
            pygame.draw.line(surface, edge, (sx + 5, top + 86), (sx + 9, top + 86), 2)
            pygame.draw.arc(surface, edge, (sx - 7, top + 94, 15, 9), 0, math.pi, 1)
            renderer.doodle_text(surface, "TEAR ALONG  - - -", (sx - 73, 423 + oy),
                                 edge, renderer.font_small, -2)
            seam_color = RED_RULE if self.failed_dash_flash <= 0 else (215, 74, 60)
            for x in range(sx - 88, sx + 83, 19):
                pygame.draw.line(surface, seam_color,
                                 (x, round(501 + oy)), (x + 10, round(499 + oy)), 2)
            renderer.doodle_text(surface, "SHIFT / K  RIGHT", (sx - 77, 530 + oy),
                                 RED_RULE, renderer.font_small, 1)
            for arrow_x in (sx - 94, sx - 66):
                jitter_line(surface, edge, (arrow_x, 479 + oy),
                            (arrow_x + 20, 479 + oy), 1, 9530 + arrow_x, 1, .7)
                pygame.draw.polygon(surface, edge,
                                    [(arrow_x + 21, 479 + oy),
                                     (arrow_x + 15, 475 + oy),
                                     (arrow_x + 15, 483 + oy)])
        else:
            for i in range(4):
                x = sx + (i % 2) * 12 - 17
                y = 412 + i * 30 + oy
                jitter_line(surface, faint, (x, y), (x + (9 if i % 2 else -9), y + 18),
                            1, 9560 + i, 1, 1.6)
            renderer.doodle_text(surface, "TORN", (sx - 35, 381 + oy),
                                 faint, renderer.font_small, -5)


class SatelliteRelayPuzzle:
    """Page III: carry a fading star along the raised satellite route.

    The charging point stays on safe ground.  The receiver is on the second
    existing satellite ledge, so merely running past it cannot open the
    airlock.  Charge expiry resets only the star, never the player's route.
    """

    active = True
    mandatory = True
    layer = 0
    charge_duration = 15.0

    def __init__(self, world, start_x: float = 9100, page_index: int = 2,
                 puzzle_id: str = "satellite_relay"):
        self.start_x = float(start_x)
        self.page_index = int(page_index)
        self.puzzle_id = puzzle_id
        self.source = (self.start_x + 80, 590)
        self.receiver = (self.start_x + 630, 465)
        self.gate = world.add(self.start_x + 1010, self.start_x + 1038,
                              92, 498, f"{puzzle_id}_airlock", 9620 + page_index)
        self.gate.appearance = "arena_border"
        self._completed = False
        self.phase = "idle"
        self.charge = 0.0
        self.timer = 0.0
        self.expired_flash = 0.0
        self.carrier_position = None

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        self._completed = bool(value)
        if self._completed:
            self.phase = "delivered"
            self.charge = 0.0
            self.carrier_position = None
            self.gate.enabled = False

    @staticmethod
    def _at_pad(player, position, radius=57):
        x, foot_y = position
        return (player.on_ground and abs(player.center_x - x) <= radius
                and abs(player.rect.bottom - foot_y) <= 36)

    def update(self, dt, ctx, interact=False):
        if self.completed:
            return
        dt = max(0.0, dt)
        self.timer += dt
        self.expired_flash = max(0.0, self.expired_flash - dt)
        player = ctx.player
        at_source = self._at_pad(player, self.source)
        at_receiver = self._at_pad(player, self.receiver)
        if self.phase == "carrying":
            self.charge = max(0.0, self.charge - dt)
            self.carrier_position = (player.center_x, player.rect.centery)
            if self.charge <= 0:
                self.phase = "idle"
                self.carrier_position = None
                self.expired_flash = .7
                ctx.level.toast = "THE ARTIST: The star faded. I can charge it again."
                ctx.level.toast_time = 2.4
        if at_source:
            ctx.level.interaction_hint = ("E  charge the loose star / 15 seconds"
                                          if self.phase == "idle" else
                                          "STAR CHARGED / climb the satellite steps")
        elif at_receiver:
            ctx.level.interaction_hint = ("E  connect the star to the dish"
                                          if self.phase == "carrying" else
                                          "NO SIGNAL / take the star from the lower pad")
        elif (self.gate.x1 - 130 <= player.center_x <= self.gate.x2 + 40
              and self.phase == "idle"):
            ctx.level.interaction_hint = "AIRLOCK CLOSED / return to the star pad"
        if not interact:
            return
        if self.phase == "idle" and at_source:
            self.phase = "carrying"
            self.charge = self.charge_duration
            self.carrier_position = (player.center_x, player.rect.centery)
            ctx.sounds.play("pencil")
            ctx.particles.pencil_speck(*self.source)
            ctx.level.toast = "THE ARTIST: Carry this spark to the dish before it fades."
            ctx.level.toast_time = 3.1
        elif self.phase == "carrying" and at_receiver:
            self.completed = True
            ctx.level.flags.add(self.puzzle_id)
            _record_puzzle_solved(ctx, self.puzzle_id)
            ctx.sounds.play("paper_break")
            ctx.camera.kick(4.5, .2)
            ctx.particles.paper_puff(self.gate.x1, 455, 13)
            ctx.level.toast = "THE ARTIST: Connected. That airlock was a bad drawing."
            ctx.level.toast_time = 3.1

    def draw(self, surface, camera, renderer):
        left = camera.screen_x(self.start_x)
        if left > surface.get_width() + 100 or left + 1100 < -100:
            return
        oy = camera.offset_y
        blue = (72, 105, 135)
        pale = (143, 155, 158)
        sx = camera.screen_x(self.source[0])
        rx = camera.screen_x(self.receiver[0])
        gx = camera.screen_x(self.gate.x1)
        sy = round(self.source[1] - 61 + oy)
        ry = round(self.receiver[1] - 83 + oy)
        color = blue if self.phase == "carrying" or self.completed else pale
        # A dashed orbit path makes the raised, two-step solution visible at
        # a glance without painting a false solid platform into the page.
        path = [(sx, sy - 22), (camera.screen_x(self.start_x + 255), 450 + oy),
                (camera.screen_x(self.start_x + 400), 411 + oy), (rx, ry)]
        for a, b in zip(path, path[1:]):
            for part in range(7):
                t0, t1 = part / 7, min(1, (part + .52) / 7)
                pygame.draw.line(surface, color,
                                 (round(a[0] + (b[0] - a[0]) * t0),
                                  round(a[1] + (b[1] - a[1]) * t0)),
                                 (round(a[0] + (b[0] - a[0]) * t1),
                                  round(a[1] + (b[1] - a[1]) * t1)), 1)
        pygame.draw.circle(surface, blue, (sx, sy), 23, 1)
        for i in range(8):
            angle = math.tau * i / 8 + .2
            endpoint = (sx + round(math.cos(angle) * 14),
                        sy + round(math.sin(angle) * 14))
            pygame.draw.line(surface, color, (sx, sy), endpoint, 1)
        if self.phase == "idle":
            renderer.doodle_text(surface, "E / CHARGE", (sx - 52, sy - 53),
                                 blue, renderer.font_small, -1)
        else:
            pygame.draw.circle(surface, pale, (sx, sy), 7, 1)
        # Receiver is a dish, physically above the second satellite ledge.
        pygame.draw.arc(surface, blue, (rx - 36, ry - 8, 72, 34),
                        .10, math.pi - .10, 3)
        jitter_line(surface, blue, (rx, ry + 8), (rx, ry + 40), 2, 9670, 2, 1.2)
        pygame.draw.circle(surface, blue, (rx, ry + 40), 4, 1)
        renderer.doodle_text(surface, "E / CONNECT", (rx - 66, ry - 58),
                             blue, renderer.font_small, 1)
        if self.phase == "carrying":
            p = self.charge / self.charge_duration
            px = camera.screen_x(self.start_x + 445)
            pygame.draw.rect(surface, pale, (px - 72, 307 + oy, 144, 7), 1)
            pygame.draw.line(surface, blue, (px - 68, 310 + oy),
                             (px - 68 + round(136 * p), 310 + oy), 3)
            renderer.doodle_text(surface, "STAR  /  %.0fs" % self.charge,
                                 (px - 63, 269 + oy), blue, renderer.font_small, -2)
            if self.carrier_position is not None:
                star_x = camera.screen_x(self.carrier_position[0]) - 21
                star_y = round(self.carrier_position[1] - 24 + oy)
                pygame.draw.circle(surface, blue, (star_x, star_y), 12, 1)
                for i in range(6):
                    angle = math.tau * i / 6 + self.timer * 1.8
                    outer = (star_x + round(math.cos(angle) * 16),
                             star_y + round(math.sin(angle) * 16))
                    inner = (star_x + round(math.cos(angle) * 7),
                             star_y + round(math.sin(angle) * 7))
                    pygame.draw.line(surface, blue, inner, outer, 2)
        if not self.completed:
            renderer.doodle_text(surface, "AIRLOCK / NO SIGNAL",
                                 (gx - 91, 325 + oy), RED_RULE, renderer.font_small, -2)
        else:
            renderer.doodle_text(surface, "CONNECTION HELD",
                                 (gx - 75, 325 + oy), blue, renderer.font_small, -2)
