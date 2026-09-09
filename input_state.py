from dataclasses import dataclass


@dataclass
class InputFrame:
    left: bool = False
    right: bool = False
    jump_pressed: bool = False
    jump_held: bool = False
    jump_released: bool = False
    interact: bool = False
    attack_pressed: bool = False
    attack_held: bool = False
    dash_pressed: bool = False
    reload_pressed: bool = False
    weapon_slot: int | None = None
    weapon_cycle: int = 0
    aim_x: float | None = None
    aim_y: float | None = None
    pause: bool = False

    @property
    def axis(self):
        return int(self.right) - int(self.left)
