from __future__ import annotations

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
        self.script_target: float | None = None
        self.look_ahead = 0.0

    def kick(self, strength: float = 5.0, duration: float = 0.22) -> None:
        self.shake_strength = min(12.0, max(self.shake_strength, strength))
        self.shake_time = max(self.shake_time, max(0.0, duration))
        self.shake_duration = max(.001, self.shake_time)

    def update(self, dt: float, focus_x: float, world_width: float, velocity_x: float = 0,
               focus_y: float | None = None) -> None:
        desired_look = max(-135.0, min(135.0, velocity_x * .42))
        self.look_ahead += (desired_look - self.look_ahead) * min(1.0, dt * 3.2)
        framed_x = self.script_target if self.script_target is not None else focus_x + self.look_ahead
        anchor = .5 if self.script_target is not None else .38
        self.target_x = max(0.0, min(max(0, world_width - self.screen_width), framed_x - self.screen_width * anchor))
        self.x += (self.target_x - self.x) * min(1.0, dt * 5.0)
        if focus_y is not None:
            desired_y = max(-54.0, min(46.0, (focus_y - 420) * .16))
            self.vertical_offset += (desired_y - self.vertical_offset) * min(1, dt * 2.8)
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
