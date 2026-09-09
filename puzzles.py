from __future__ import annotations

import math
import pygame

from paper_renderer import jitter_line
from settings import INK, INK_LIGHT


def _make_gate(world, x, name, layer=0):
    gate = world.add(x, x + 22, 260, 330, name, 600 + int(x), layer)
    return gate


class InkCircuitPuzzle:
    """Small Lights-Out-style circuit drawn directly on the notebook page."""

    def __init__(self, world, x, gate_x, puzzle_id, target=(True, True, True), layer=0):
        self.x = x
        self.y = 500
        self.puzzle_id = puzzle_id
        self.target = list(target)
        self.state = [False, False, False]
        self.gate = _make_gate(world, gate_x, f"{puzzle_id}_gate", layer)
        self.completed = False
        self.mandatory = True
        self.active = True
        self.layer = layer
        self.cooldown = 0.0

    def update(self, dt, ctx, interact=False):
        self.cooldown = max(0, self.cooldown - dt)
        if self.completed:
            return
        nearest = min(range(3), key=lambda i: abs(ctx.player.center_x - (self.x + i * 95)))
        distance = abs(ctx.player.center_x - (self.x + nearest * 95))
        if distance < 52 and abs(ctx.player.rect.bottom - self.y) < 110:
            ctx.level.interaction_hint = "E  redraw circuit node"
            if interact and self.cooldown <= 0:
                self.cooldown = .2
                self.state[nearest] = not self.state[nearest]
                if nearest > 0:
                    self.state[nearest - 1] = not self.state[nearest - 1]
                ctx.sounds.play("pencil")
                ctx.particles.pencil_speck(self.x + nearest * 95, self.y - 20)
        if self.state == self.target:
            self.completed = True
            self.gate.enabled = False
            ctx.level.flags.add(self.puzzle_id)
            ctx.level.toast = "the ink circuit hums open"
            ctx.level.toast_time = 2.5
            ctx.camera.kick(3, .18)

    def draw(self, surface, camera, renderer):
        y = round(self.y + camera.offset_y)
        points = []
        for i in range(3):
            x = camera.screen_x(self.x + i * 95)
            points.append((x, y - 20))
            pygame.draw.circle(surface, INK if self.state[i] else INK_LIGHT, (x, y - 20), 14, 3 if self.state[i] else 2)
            if self.state[i]:
                pygame.draw.circle(surface, (74, 72, 67), (x, y - 20), 6)
            renderer.doodle_text(surface, str(i + 1), (x - 5, y + 7), INK_LIGHT, renderer.font_small)
        for i in range(2):
            pygame.draw.line(surface, INK if self.state[i] and self.state[i + 1] else INK_LIGHT,
                             points[i], points[i + 1], 2)
        renderer.doodle_text(surface, "make the current agree", (points[0][0] - 45, y - 78),
                             INK_LIGHT, renderer.font_small, -1)


class GlyphLockPuzzle:
    """Three hand-drawn dials; nearby E cycles each symbol to match the clue."""

    GLYPHS = ("O", "X", "^")

    def __init__(self, world, x, gate_x, puzzle_id, target=(0, 2, 1), layer=0):
        self.x = x
        self.y = 490
        self.puzzle_id = puzzle_id
        self.target = tuple(target)
        self.values = [0, 0, 0]
        self.gate = _make_gate(world, gate_x, f"{puzzle_id}_gate", layer)
        self.completed = False
        self.mandatory = True
        self.active = True
        self.layer = layer
        self.cooldown = 0

    def update(self, dt, ctx, interact=False):
        self.cooldown = max(0, self.cooldown - dt)
        if self.completed:
            return
        nearest = min(range(3), key=lambda i: abs(ctx.player.center_x - (self.x + i * 86)))
        if abs(ctx.player.center_x - (self.x + nearest * 86)) < 48:
            ctx.level.interaction_hint = "E  turn the paper dial"
            if interact and self.cooldown <= 0:
                self.cooldown = .2
                self.values[nearest] = (self.values[nearest] + 1) % len(self.GLYPHS)
                ctx.sounds.play("paper_step")
        if tuple(self.values) == self.target:
            self.completed = True
            self.gate.enabled = False
            ctx.level.flags.add(self.puzzle_id)
            ctx.level.toast = "the old symbols remember"
            ctx.level.toast_time = 2.5

    def draw(self, surface, camera, renderer):
        y = round(self.y + camera.offset_y)
        clue = "  ".join(self.GLYPHS[i] for i in self.target)
        renderer.doodle_text(surface, f"clue: {clue}", (camera.screen_x(self.x - 20), y - 92),
                             INK_LIGHT, renderer.font_small, 1)
        for i, value in enumerate(self.values):
            x = camera.screen_x(self.x + i * 86)
            pygame.draw.circle(surface, INK_LIGHT, (x, y - 23), 28, 2)
            text = renderer.font.render(self.GLYPHS[value], True, INK)
            surface.blit(text, text.get_rect(center=(x, y - 23)))
            pygame.draw.line(surface, INK_LIGHT, (x, y + 8), (x, y + 20), 1)
