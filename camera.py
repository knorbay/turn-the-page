from __future__ import annotations

import math
import random


class Camera:
    def __init__(self, screen_width: int):
        self.x = 0.0
        self.target_x = 0.0
        self.screen_width = screen_width
        self.shake_time = 0.0
        self.shake_strength = 0.0
        self.shake_duration = .22
        self.offset_x = 0
        self.offset_y = 0
        self.vertical_offset = 0.0
        self._script_target: float | None = None
        self._script_owner: str | None = None
        self.look_ahead = 0.0
        self.zoom = 1.0

    @property
    def script_target(self) -> float | None:
        return self._script_target

    @script_target.setter
    def script_target(self, target: float | None) -> None:
        self._script_target = target
        self._script_owner = None

    def set_script_target(self, target: float, owner: str) -> None:
        self._script_target = float(target)
        self._script_owner = owner

    def release_script_target(self, owner: str | None = None) -> None:
        if owner is None or owner == self._script_owner:
            self.script_target = None

    def kick(self, strength: float = 5.0, duration: float = 0.22) -> None:
        self.shake_strength = min(12.0, max(self.shake_strength, strength))
        self.shake_time = max(self.shake_time, max(0.0, duration))
        self.shake_duration = max(.001, self.shake_time)

    def update(self, dt: float, focus_x: float, world_width: float, velocity_x: float = 0,
               focus_y: float | None = None, player_locked: bool = False) -> None:
        # A drawing may frame a locked scene. The moment the controller is
        # available again, movement owns the camera, including inside arenas.
        if not player_locked:
            self.release_script_target()
        dt = max(0.0, dt)
        desired_look = max(-85.0, min(85.0, velocity_x * .22))
        self.look_ahead += (desired_look - self.look_ahead) * (1 - math.exp(-dt * 6.5))
        framed_x = self.script_target if self.script_target is not None else focus_x + self.look_ahead
        self.target_x = max(0.0, min(max(0, world_width - self.screen_width),
                                   framed_x - self.screen_width * .5))
        self.x += (self.target_x - self.x) * (1 - math.exp(-dt * 8.0))
        if focus_y is not None:
            # Keep ordinary floor movement steady, then follow a high jump or
            # climb. An upper route can leave the page's original viewport;
            # the old 54-pixel cap prevented the camera from following it.
            desired_y = min(0.0, focus_y - 400.0) + max(0.0, focus_y - 540.0)
            self.vertical_offset += (desired_y - self.vertical_offset) * (1 - math.exp(-dt * 5.8))
        if self.shake_time > 0:
            self.shake_time -= dt
            fade = min(1.0, max(0.0, self.shake_time / self.shake_duration)) ** 2
            strength = self.shake_strength * fade
            self.offset_x = round(random.uniform(-strength, strength))
            self.offset_y = round(random.uniform(-strength, strength) - self.vertical_offset)
        else:
            self.offset_x = 0
            self.offset_y = round(-self.vertical_offset)
            self.shake_strength = 0.0

    def screen_x(self, world_x: float) -> int:
        return round(world_x - self.x + self.offset_x)
