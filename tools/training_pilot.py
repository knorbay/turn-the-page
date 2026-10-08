"""Input-only QA pilot for the visible lesson, without changing game state."""
from input_state import InputFrame


def lesson_input(game):
    lesson = game.level.runtime.training
    player = game.player
    jump = dash = interact = attack = False
    aim = None
    if "folded_shuriken" not in game.weapons.unlocked:
        gift = next(e for e in game.level.entities.items
                    if getattr(e, "weapon_id", None) == "folded_shuriken")
        destination = gift.x
        interact = abs(player.center_x-gift.x) < 50
        jump = player.on_ground and any(a < player.x < b for a, b in ((715,760),(970,1010),(1205,1250)))
    elif not lesson.practice_done:
        target = next((t for t in lesson.targets if not t.completed), lesson.targets[-1])
        destination = target.x-105
        if target is lesson.targets[0] and "third_step_drawn" not in game.level.flags:
            destination = 1200
        attack = target.reveal >= 1
        aim = target.target.rect.center
        jump = player.on_ground and (lesson.jumps < 3 or
               any(a < player.x < b for a, b in ((1160,1280),)))
    elif lesson.stage < 3:
        destination = 3120
        jump = player.on_ground and lesson.jumps < 3
    elif lesson.stage == 3:
        destination = 3700
        if lesson.warning_x is not None:
            destination = lesson.warning_x+(270 if player.center_x < 3810 else -270)
            dash = lesson.warning_time < .9 and player.dash_ready
    elif not lesson.bridge_requested:
        destination = lesson.lever_x
        interact = abs(player.center_x-destination) < 70
    else:
        landing = next((p for p in lesson.stairs
                        if player.rect.bottom > p.y+3 or player.center_x < p.x1+50), None)
        if landing is None:
            destination = lesson.seal_x
            interact = abs(player.center_x-destination) < 65
        else:
            destination = landing.x1+105
            jump = player.on_ground and player.rect.bottom > landing.y+3
    delta = destination-player.center_x
    return InputFrame(left=delta < -14, right=delta > 14, jump_pressed=jump,
        jump_held=True, dash_pressed=dash, interact=interact, attack_pressed=attack,
        aim_x=aim[0] if aim else None, aim_y=aim[1] if aim else None)
