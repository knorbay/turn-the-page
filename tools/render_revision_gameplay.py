"""Walk the hidden cloud entrance and climb using real game-loop input."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from game import Game
from input_state import InputFrame
from localization import set_language
from major_campaign import SecretPocket
from settings import WIDTH, HEIGHT


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "revision-gameplay"
    out.mkdir(parents=True, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    snapshots = []
    with tempfile.TemporaryDirectory() as folder:
        game = Game(screen, Path(folder) / "save.json")
        game.reset()
        set_language("tr")
        # A shipping checkpoint after the previous arena starts the review.
        # Every secret interaction, movement and jump after this uses InputFrame.
        game.level.load_chapter(0, "after_practice_crossouts", game.player, game.camera)
        game._attach_runtime()
        game.save.checkpoint(0, "after_practice_crossouts")
        pocket = next(entity for entity in game.level.entities.items
            if isinstance(entity, SecretPocket) and entity.kind == "cloud")

        def tick(frame=InputFrame()):
            game.update(1 / 60, frame)
            if game.level.respawn_timer > 0 or game.player.health <= 0:
                raise AssertionError(("unexpected death", game.player.x, game.player.y))

        def capture(name):
            game.draw()
            pygame.image.save(game.screen, out / (name + ".png"))
            snapshots.append({"capture": name, "time": round(game.session_seconds, 3),
                "player": [round(game.player.center_x, 2), round(game.player.y, 2)],
                "screen_player": [game.camera.screen_x(game.player.center_x),
                    round(game.player.y + game.camera.offset_y)],
                "camera_x": round(game.camera.x, 2), "camera_offset_y": game.camera.offset_y,
                "camera_script_target": game.camera.script_target,
                "entrance_open": pocket.entrance_open,
                "entrance_progress": round(pocket.entrance_progress, 3),
                "guardian_active": pocket.encounter_active,
                "guardian": [{"kind": enemy.kind, "hp": enemy.hp, "state": enemy.state}
                    for enemy in pocket.enemies], "health": game.player.health,
                "weapon": game.weapons.current_id})

        def walk_to(target, limit=180):
            for _ in range(limit):
                distance = target - game.player.center_x
                if abs(distance) <= 9 and abs(game.player.vx) < 12:
                    return
                tick(InputFrame(left=distance < -9, right=distance > 9))
            raise AssertionError(("walk did not reach target", target, game.player.x))

        for _ in range(260):
            tick()
        walk_to(pocket.base + 60)
        for _ in range(20):
            tick()
        assert not pocket.entrance_open
        assert all(not platform.enabled and not platform.collision_rects()
            for platform in pocket.steps)
        assert not pocket.encounter_active
        capture("01-main-road-hidden")

        tick(InputFrame(interact=True))
        assert pocket.entrance_open
        for _ in range(100):
            tick()
            if pocket.entrance_progress >= 1:
                break
        assert pocket.entrance_progress == 1
        assert all(platform.collision_rects() for platform in pocket.steps)
        capture("02-corner-opened")

        for index, landing in enumerate(pocket.steps):
            target = ((landing.x1 + landing.x2) / 2 if index < 4
                      else pocket.bounds[0] + 65)
            tick(InputFrame(jump_pressed=True, jump_held=True,
                left=target < game.player.center_x, right=target > game.player.center_x))
            reached = False
            for _ in range(240):
                distance = target - game.player.center_x
                tick(InputFrame(left=distance < -9, right=distance > 9, jump_held=True))
                if game.player.on_ground and abs(game.player.rect.bottom - landing.y) <= 2:
                    reached = True
                    break
            if not reached:
                raise AssertionError(("landing unreachable", landing.name,
                    game.player.x, game.player.y, game.player.vx, game.player.vy))
            if index in (1, 3, 4):
                capture(f"0{index + 2}-climb-{index + 1}")

        walk_to(pocket.bounds[0] + 65)
        for _ in range(30):
            tick()
        assert game.camera.offset_y > 130
        assert 340 < game.player.y + game.camera.offset_y < 430
        assert game.camera.script_target is None
        capture("07-cloud-deck-follow")
        tick(InputFrame(interact=True))
        assert pocket.encounter_active
        for _ in range(140):
            tick()
            if pocket.reveal >= 1 and pocket.enemies[0].state == "gust_warn":
                break
        assert pocket.reveal == 1
        assert pocket.enemies[0].kind == "cloud_kite"
        capture("08-distinct-guardian-warning")
        metrics = {"checkpoint": "after_practice_crossouts", "input_driven": True,
            "secrets_granted": list(game.save.data["secrets"]),
            "deaths": game.behavior.snapshot().get("deaths", 0), "snapshots": snapshots}
        (out / "gameplay-contracts.json").write_text(json.dumps(metrics,
            ensure_ascii=False, indent=2), encoding="utf8")
    pygame.quit()
    print(out)


if __name__ == "__main__":
    main()
