"""Longer, spatial puzzles built around the physical behaviour of paper.

The existing campaign uses short node and glyph locks.  The two reusable
systems here are intentionally more embodied:

``CreaseWeavePuzzle``
    Four linked folds reshape real ``InkPlatform`` ramps.  Folding one tab also
    pulls the crease immediately to its left, so the player must reason about
    the shared sheet rather than set four independent switches.

``CarbonTransferPuzzle``
    The player rubs several pressure impressions to reveal them, turns over a
    carbon sheet, then revisits the impressions in mirrored order.  Station
    positions may be placed on authored platforms, making the solution a
    traversal route instead of a panel UI.

Both classes satisfy the campaign entity API and expose ``puzzle_id`` and a
real ``InkPlatform`` ``gate``.  Level's generic checkpoint snapshot therefore
restores a puzzle when a checkpoint lies beyond its gate.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT, PAPER, RED_RULE


def _ink_gate(world, gate_x: float, puzzle_id: str, layer: int):
    """Make a tall, cross-hatched InkPlatform that genuinely blocks passage."""

    return world.add(
        gate_x,
        gate_x + 30,
        246,
        344,
        f"{puzzle_id}_paper_gate",
        1700 + round(gate_x) % 10000,
        layer,
    )


def _near_player(ctx, point, x_radius=54, y_radius=105):
    return (
        abs(ctx.player.center_x - point[0]) <= x_radius
        and abs(ctx.player.rect.bottom - point[1]) <= y_radius
    )


def _complete_feedback(ctx, puzzle_id, message):
    ctx.level.flags.add(puzzle_id)
    ctx.level.toast = message
    ctx.level.toast_time = 3.0
    ctx.sounds.play("fold")
    ctx.camera.kick(4, .22)


class CreaseWeavePuzzle:
    """Linked page folds that reshape physical platform strokes.

    Parameters
    ----------
    world:
        The chapter's ``PaperWorld``.
    x:
        Left edge of the four-crease apparatus.
    gate_x:
        World x-coordinate of the mandatory ink gate.
    puzzle_id:
        Stable completion flag used by checkpoints.
    target:
        Desired valley/mountain state.  The default ``(0, 0, 0, 1)`` means
        only the rightmost crease should remain raised.
    station_positions:
        Optional four ``(x, floor_y)`` tab positions.  Supplying positions on
        separate authored ledges turns the puzzle into a larger traversal
        route.  When omitted, tabs are spaced across the apparatus.

    Interaction rule
    ----------------
    Pressing a tab flips its own fold and, except for the binding-side tab,
    flips the crease directly to its left.  This models tension travelling
    through one shared sheet.  From the default flat state, the default target
    is solved by folding tabs 4, 3, 2, then 1 (right to left).
    """

    mandatory = True
    active = True
    is_paper_puzzle = True

    def __init__(
        self,
        world,
        x: float,
        gate_x: float,
        puzzle_id: str,
        target: Sequence[int | bool] = (0, 0, 0, 1),
        layer: int = 0,
        floor_y: float = 590,
        station_positions: Sequence[tuple[float, float]] | None = None,
    ):
        if len(target) != 4:
            raise ValueError("CreaseWeavePuzzle requires exactly four target folds")
        if any(value not in (0, 1, False, True) for value in target):
            raise ValueError("crease targets must contain only flat/raised states")

        self.world = world
        self.x = float(x)
        self.floor_y = float(floor_y)
        self.puzzle_id = str(puzzle_id)
        self.checkpoint_flag = self.puzzle_id
        self.layer = int(layer)
        self.target = tuple(int(value) for value in target)
        self.states = [0, 0, 0, 0]
        self.cooldown = 0.0
        self.pulse = 0.0
        self.last_tab = -1

        if station_positions is None:
            station_positions = [
                (self.x + 95 + index * 190, self.floor_y)
                for index in range(4)
            ]
        if len(station_positions) != 4:
            raise ValueError("station_positions must contain four (x, y) pairs")
        self.stations = [(float(px), float(py)) for px, py in station_positions]

        # These are not decorative indicators: changing their y/end_y changes
        # both rendering and collision through InkPlatform.collision_rects().
        self.flaps = []
        for index in range(4):
            x1 = self.x + 14 + index * 190
            flap = world.add(
                x1,
                x1 + 166,
                self.floor_y - 42,
                12,
                f"{self.puzzle_id}_crease_{index}",
                1800 + round(self.x) % 1000 + index * 19,
                self.layer,
            )
            self.flaps.append(flap)

        self.gate = _ink_gate(world, gate_x, self.puzzle_id, self.layer)
        self._completed = False
        self._apply_fold_geometry()

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        """Checkpoint snapshots may assign this directly; restore all geometry."""

        self._completed = bool(value)
        if not hasattr(self, "gate"):
            return
        if self._completed:
            self.states[:] = self.target
            self._apply_fold_geometry()
            self.gate.enabled = False

    @property
    def solution(self):
        """Return a shortest tab set for documentation, hints, and tests."""

        best = None
        for mask in range(1 << 4):
            state = [0, 0, 0, 0]
            presses = []
            for index in range(4):
                if not mask & (1 << index):
                    continue
                presses.append(index)
                state[index] ^= 1
                if index > 0:
                    state[index - 1] ^= 1
            if tuple(state) != self.target:
                continue
            if best is None or len(presses) < len(best):
                best = presses
        return tuple(best or ())

    def _apply_fold_geometry(self):
        for index, (flap, raised) in enumerate(zip(self.flaps, self.states)):
            if not raised:
                flap.y = self.floor_y - 42
                flap.end_y = self.floor_y - 42
            elif index % 2:
                # Alternating slopes make the creases read as a concertina,
                # and create useful high/low routes in authored platform rooms.
                flap.y = self.floor_y - 122
                flap.end_y = self.floor_y - 45
            else:
                flap.y = self.floor_y - 45
                flap.end_y = self.floor_y - 122
            flap.enabled = True

    def _restore_from_flag(self, ctx):
        if self.puzzle_id in ctx.level.flags and not self.completed:
            self.completed = True

    def update(self, dt, ctx, interact=False):
        self.pulse += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self._restore_from_flag(ctx)
        if self.completed:
            self.gate.enabled = False
            return

        nearest = min(
            range(4),
            key=lambda index: math.dist(
                (ctx.player.center_x, ctx.player.rect.bottom),
                self.stations[index],
            ),
        )
        if not _near_player(ctx, self.stations[nearest]):
            return

        state_name = "mountain" if self.states[nearest] else "valley"
        ctx.level.interaction_hint = (
            f"E  fold tab {nearest + 1} ({state_name})"
        )
        if not interact or self.cooldown > 0:
            return

        self.cooldown = .20
        self.last_tab = nearest
        self.states[nearest] ^= 1
        if nearest > 0:
            self.states[nearest - 1] ^= 1
        self._apply_fold_geometry()
        ctx.sounds.play("fold")
        ctx.camera.kick(2.4, .14)
        for index in (nearest, nearest - 1):
            if index >= 0:
                flap = self.flaps[index]
                ctx.particles.paper_puff(
                    (flap.x1 + flap.x2) * .5,
                    (flap.y + flap.y_at(flap.x2)) * .5,
                    5,
                )

        if tuple(self.states) == self.target:
            self.completed = True
            _complete_feedback(
                ctx,
                self.puzzle_id,
                "the shared crease folds the ink gate away",
            )

    def draw(self, surface, camera, renderer):
        # Pale triangular undersides make raised strokes unmistakably folds,
        # while the InkPlatforms underneath retain authoritative collision.
        for index, (flap, raised) in enumerate(zip(self.flaps, self.states)):
            if not raised:
                continue
            x1 = camera.screen_x(flap.x1)
            x2 = camera.screen_x(flap.x2)
            y1 = round(flap.y + camera.offset_y)
            y2 = round(flap.y_at(flap.x2) + camera.offset_y)
            baseline = round(self.floor_y - 40 + camera.offset_y)
            folded = pygame.Surface(
                (max(2, abs(x2 - x1) + 2), max(2, abs(baseline - min(y1, y2)) + 7)),
                pygame.SRCALPHA,
            )
            local_y1 = y1 - min(y1, y2)
            local_y2 = y2 - min(y1, y2)
            local_base = baseline - min(y1, y2)
            pygame.draw.polygon(
                folded,
                (220, 214, 194, 118),
                [(0, local_y1), (folded.get_width() - 1, local_y2),
                 (folded.get_width() - 1, local_base), (0, local_base)],
            )
            surface.blit(folded, (min(x1, x2), min(y1, y2)))

        target_marks = "  ".join("/" if value else "_" for value in self.target)
        renderer.doodle_text(
            surface,
            f"crease clue:  {target_marks}",
            (camera.screen_x(self.x + 20), round(self.floor_y - 226 + camera.offset_y)),
            INK_LIGHT,
            renderer.font_small,
            -1,
        )
        renderer.doodle_text(
            surface,
            "one fold tugs the crease on its left",
            (camera.screen_x(self.x + 65), round(self.floor_y - 194 + camera.offset_y)),
            INK_LIGHT,
            renderer.font_small,
            1,
        )

        for index, ((tab_x, tab_y), state) in enumerate(zip(self.stations, self.states)):
            sx = camera.screen_x(tab_x)
            sy = round(tab_y - 13 + camera.offset_y)
            lift = round(math.sin(self.pulse * 3 + index) * 2)
            color = INK if state else INK_LIGHT
            points = [(sx - 18, sy), (sx + 18, sy), (sx, sy - 17 - lift)]
            pygame.draw.polygon(surface, PAPER, points)
            jitter_line(surface, color, points[0], points[1], 2, 2100 + index, 2, 1)
            jitter_line(surface, color, points[1], points[2], 2, 2110 + index, 2, 1)
            jitter_line(surface, color, points[2], points[0], 2, 2120 + index, 2, 1)
            renderer.doodle_text(
                surface,
                str(index + 1),
                (sx - 5, sy - 43),
                color,
                renderer.font_small,
            )

        if self.completed:
            renderer.doodle_text(
                surface,
                "CREASE HOLDS",
                (camera.screen_x(self.x + 300),
                 round(self.floor_y - 152 + camera.offset_y)),
                INK_LIGHT,
                renderer.font_small,
                -2,
            )


class CarbonTransferPuzzle:
    """Reveal pressure marks, turn the carbon paper, then copy in reverse.

    The default layout has four stations.  Phase one asks the player to rub each
    plate in any order.  A separate turn-tab becomes available only once all
    impressions are visible.  Because a carbon copy is mirrored, phase two
    accepts the stations from right to left.  A wrong station smudges only the
    current transfer attempt; the discovered impressions remain readable.

    ``station_positions`` can place the plates on slopes, coffee islands, or
    upper ledges.  This is the intended integration path for a multi-room
    mandatory puzzle rather than putting all four controls beside one another.
    """

    mandatory = True
    active = True
    is_paper_puzzle = True

    DEFAULT_GLYPHS = ("O", "X", "^", "[]")

    def __init__(
        self,
        world,
        x: float,
        gate_x: float,
        puzzle_id: str,
        station_positions: Sequence[tuple[float, float]] | None = None,
        glyphs: Sequence[str] = DEFAULT_GLYPHS,
        layer: int = 0,
        floor_y: float = 590,
        turn_position: tuple[float, float] | None = None,
    ):
        if not 3 <= len(glyphs) <= 6:
            raise ValueError("CarbonTransferPuzzle supports three to six impressions")

        self.world = world
        self.x = float(x)
        self.floor_y = float(floor_y)
        self.puzzle_id = str(puzzle_id)
        self.checkpoint_flag = self.puzzle_id
        self.layer = int(layer)
        self.glyphs = tuple(str(glyph) for glyph in glyphs)
        count = len(self.glyphs)

        if station_positions is None:
            station_positions = [
                (self.x + index * 235, self.floor_y)
                for index in range(count)
            ]
        if len(station_positions) != count:
            raise ValueError("one station position is required for every glyph")
        self.stations = [(float(px), float(py)) for px, py in station_positions]
        rightmost = max(self.stations, key=lambda point: point[0])
        self.turn_position = (
            (rightmost[0] + 150, rightmost[1])
            if turn_position is None
            else (float(turn_position[0]), float(turn_position[1]))
        )

        self.rubbed = [False] * count
        self.transfer_order: list[int] = []
        self.phase = "reveal"
        self.cooldown = 0.0
        self.pulse = 0.0
        self.smudge_time = 0.0

        # The mirrored transfer becomes a physical ink shelf as the sequence is
        # copied.  It is optional traversal geometry, but its collision progress
        # truthfully follows the amount of transferred graphite.
        span_start = min(point[0] for point in self.stations) - 42
        span_end = max(point[0] for point in self.stations) + 88
        self.copy_line = world.add(
            span_start,
            span_end,
            self.floor_y - 118,
            11,
            f"{self.puzzle_id}_carbon_copy",
            2300 + round(self.x) % 1000,
            self.layer,
        )
        self.copy_line.draw_progress = 0.0
        self.gate = _ink_gate(world, gate_x, self.puzzle_id, self.layer)
        self._completed = False

    @property
    def completed(self):
        return self._completed

    @completed.setter
    def completed(self, value):
        """Restore the final physical state when Level loads a later checkpoint."""

        self._completed = bool(value)
        if not hasattr(self, "gate"):
            return
        if self._completed:
            self.rubbed[:] = [True] * len(self.rubbed)
            self.transfer_order[:] = list(reversed(range(len(self.rubbed))))
            self.phase = "complete"
            self.copy_line.draw_progress = 1.0
            self.gate.enabled = False

    @property
    def solution(self):
        """The mirrored station order, expressed as zero-based indices."""

        return tuple(reversed(range(len(self.stations))))

    def _restore_from_flag(self, ctx):
        if self.puzzle_id in ctx.level.flags and not self.completed:
            self.completed = True

    def _nearest_station(self, ctx):
        return min(
            range(len(self.stations)),
            key=lambda index: math.dist(
                (ctx.player.center_x, ctx.player.rect.bottom),
                self.stations[index],
            ),
        )

    def update(self, dt, ctx, interact=False):
        self.pulse += dt
        self.cooldown = max(0.0, self.cooldown - dt)
        self.smudge_time = max(0.0, self.smudge_time - dt)
        self._restore_from_flag(ctx)
        if self.completed:
            self.gate.enabled = False
            return

        if self.phase == "turn":
            if _near_player(ctx, self.turn_position, 62, 115):
                ctx.level.interaction_hint = "E  turn over the carbon sheet"
                if interact and self.cooldown <= 0:
                    self.cooldown = .25
                    self.phase = "transfer"
                    ctx.sounds.play("page")
                    ctx.particles.paper_puff(
                        self.turn_position[0], self.turn_position[1] - 10, 12
                    )
                    ctx.camera.kick(2.5, .16)
                    ctx.level.toast = "carbon reads backwards — copy right to left"
                    ctx.level.toast_time = 3.2
            return

        nearest = self._nearest_station(ctx)
        if not _near_player(ctx, self.stations[nearest], 58, 115):
            return

        if self.phase == "reveal":
            if self.rubbed[nearest]:
                ctx.level.interaction_hint = (
                    f"impression {nearest + 1} already revealed"
                )
                return
            ctx.level.interaction_hint = f"E  rub impression {nearest + 1}"
            if not interact or self.cooldown > 0:
                return
            self.cooldown = .20
            self.rubbed[nearest] = True
            x, y = self.stations[nearest]
            ctx.sounds.play("pencil")
            for offset in (-18, -6, 8, 19):
                ctx.particles.pencil_speck(x + offset, y - 48)
            if all(self.rubbed):
                self.phase = "turn"
                ctx.level.toast = "all pressure marks found — turn the black sheet"
                ctx.level.toast_time = 3.0
            return

        # Transfer phase: the physical carbon copy must be read as a mirror.
        expected = self.solution[len(self.transfer_order)]
        ctx.level.interaction_hint = (
            f"E  transfer impression {nearest + 1} (right to left)"
        )
        if not interact or self.cooldown > 0:
            return
        self.cooldown = .20
        x, y = self.stations[nearest]
        if nearest != expected:
            self.transfer_order.clear()
            self.copy_line.draw_progress = 0.0
            self.smudge_time = .8
            ctx.sounds.play("erase")
            ctx.particles.eraser_dust(x, y - 42, 11)
            ctx.camera.kick(2.5, .14)
            ctx.level.toast = "the carbon smudged — begin again from the right"
            ctx.level.toast_time = 2.8
            return

        self.transfer_order.append(nearest)
        self.copy_line.draw_progress = (
            len(self.transfer_order) / len(self.stations)
        )
        ctx.sounds.play("pencil")
        ctx.particles.pencil_speck(
            self.copy_line.visible_x2, self.copy_line.y
        )
        if len(self.transfer_order) == len(self.stations):
            self.completed = True
            _complete_feedback(
                ctx,
                self.puzzle_id,
                "the mirrored carbon line copies the gate away",
            )

    def draw(self, surface, camera, renderer):
        for index, ((station_x, station_y), glyph, rubbed) in enumerate(
            zip(self.stations, self.glyphs, self.rubbed)
        ):
            sx = camera.screen_x(station_x)
            sy = round(station_y - 79 + camera.offset_y)
            panel = pygame.Rect(sx - 38, sy, 76, 58)
            pygame.draw.rect(surface, (222, 216, 198), panel)
            jitter_line(surface, INK_LIGHT, panel.topleft, panel.topright,
                        2, 2400 + index * 11, 2, 1.6)
            jitter_line(surface, INK_LIGHT, panel.bottomleft, panel.bottomright,
                        2, 2401 + index * 11, 2, 1.6)
            if rubbed:
                # Dense parallel ticks evoke graphite rubbing rather than a
                # clean UI reveal.
                for line in range(7):
                    jitter_line(
                        surface,
                        (112, 108, 102),
                        (panel.x + 7, panel.y + 8 + line * 6),
                        (panel.right - 7, panel.y + 5 + line * 6),
                        1,
                        2500 + index * 31 + line,
                        1,
                        1.2,
                    )
                text = renderer.font.render(glyph, True, INK)
                surface.blit(text, text.get_rect(center=panel.center))
            else:
                renderer.doodle_text(
                    surface, "?", (panel.centerx - 6, panel.y + 14),
                    INK_LIGHT, renderer.font
                )
            renderer.doodle_text(
                surface,
                str(index + 1),
                (panel.x + 3, panel.bottom + 4),
                INK_LIGHT,
                renderer.font_small,
            )

            if self.phase == "transfer" and index in self.transfer_order:
                pygame.draw.circle(surface, RED_RULE, panel.center, 35, 2)

        turn_x = camera.screen_x(self.turn_position[0])
        turn_y = round(self.turn_position[1] - 88 + camera.offset_y)
        sheet = pygame.Rect(turn_x - 48, turn_y, 96, 65)
        pygame.draw.polygon(
            surface,
            (63, 62, 66),
            [sheet.topleft, sheet.topright,
             (sheet.right - 8, sheet.bottom), (sheet.left + 7, sheet.bottom)],
        )
        pygame.draw.line(
            surface, (178, 170, 151),
            (sheet.right - 23, sheet.top), (sheet.right - 4, sheet.top + 18), 2
        )
        renderer.doodle_text(
            surface,
            "TURN" if self.phase == "turn" else "CARBON",
            (sheet.x + 11, sheet.y + 20),
            (231, 226, 208),
            renderer.font_small,
            -1,
        )

        direction = "RUB EVERY MARK" if self.phase == "reveal" else "COPY  <---"
        if self.completed:
            direction = "MIRROR COPY HOLDS"
        renderer.doodle_text(
            surface,
            direction,
            (camera.screen_x(self.x), round(self.floor_y - 190 + camera.offset_y)),
            INK_LIGHT,
            renderer.font_small,
            -1,
        )
        if self.smudge_time > 0:
            alpha = self.smudge_time / .8
            center_x = camera.screen_x(
                sum(point[0] for point in self.stations) / len(self.stations)
            )
            center_y = round(self.floor_y - 135 + camera.offset_y)
            radius = round(24 + (1 - alpha) * 30)
            renderer.scribble(
                surface,
                (center_x, center_y),
                radius,
                2777,
                5,
                (79, 75, 73),
            )


__all__ = ["CreaseWeavePuzzle", "CarbonTransferPuzzle"]
