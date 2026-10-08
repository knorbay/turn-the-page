"""Capture both scenic versions with the same live player, room and creatures."""
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
from localization import set_language
from scenic_backgrounds import ScenicBackgrounds, PAGE_SCENES
from settings import WIDTH, HEIGHT


def prepare_room(game, page, boss=False):
    game.level.load_chapter(page, "start", game.player, game.camera)
    game._attach_runtime()
    game.player.release_all_locks()
    game.player.draw_amount = 1
    lesson = getattr(game.level.runtime, "training", None)
    if lesson:
        lesson.completed = True
        lesson.gate.enabled = False
    rooms = [e for e in game.level.entities.items if getattr(e, "is_combat_arena", False)]
    room = next(e for e in rooms if bool(e.boss) == boss)
    game.player.x = room.start_x + 145
    game.player.y = 542
    game.player.on_ground = True
    game.player.health = 3
    ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
    room.encounter_active = True
    room.wave = 0
    room.entrance_gate.enabled = True
    room._spawn_wave(ctx, room.wave_ids[0])
    for enemy in room.enemies:
        enemy.notebook_reveal = 1
        enemy.notebook_spawn_pending = False
        enemy.state = "idle"
    if boss and room.enemies:
        focus = room.enemies[0].x - 545
        game.player.x = focus + 185
    else:
        focus = room.start_x - 150
    game.camera.x = max(0, focus)
    game.camera.offset_x = game.camera.offset_y = 0
    game.level.page_title_time = game.level.toast_time = game.weapon_reveal_time = 0
    game.level.director.tool.visible = False
    game.level.director.messages.clear()
    game.time = 3.4
    game.state = "playing"
    return room


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "background-review"
    out.mkdir(parents=True, exist_ok=True)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    metadata = []
    with tempfile.TemporaryDirectory() as folder:
        game = Game(screen, Path(folder) / "save.json")
        set_language("tr")
        original = game.renderer.scenery
        font = game.renderer.font
        comparisons = []
        for page in range(5):
            room = prepare_room(game, page)
            panels = []
            for mode in ("before", "after"):
                game.renderer.scenery = None if mode == "before" else original
                game.draw()
                path = out / f"page-{page + 1}-{mode}.png"
                pygame.image.save(game.screen, path)
                panels.append(game.screen.copy())
            pair = pygame.Surface((WIDTH * 2, HEIGHT + 44))
            pair.fill((242, 235, 211))
            for index, (panel, title) in enumerate(zip(panels, ("Önce / Sayfa", "Sonra / Sayfa"))):
                pair.blit(font.render(f"{title} {page + 1}", True, (70, 68, 58)), (index * WIDTH + 20, 8))
                pair.blit(panel, (index * WIDTH, 44))
            pygame.image.save(pair, out / f"page-{page + 1}-comparison.png")
            comparisons.append(pygame.transform.scale(pair, (1120, 372)))
            metadata.append({"page": page + 1, "scene": PAGE_SCENES[page],
                             "room": room.arena_id, "camera_x": game.camera.x})
            boss = prepare_room(game, page, True)
            game.renderer.scenery = original
            game.draw()
            pygame.image.save(game.screen, out / f"page-{page + 1}-boss.png")
        sheet = pygame.Surface((1120, 372 * 5))
        for i, comparison in enumerate(comparisons):
            sheet.blit(comparison, (0, i * 372))
        pygame.image.save(sheet, out / "five-page-background-comparison.png")
        prepare_room(game, 0)
        game.camera.offset_y = 330
        game.player.y = 210
        game.draw()
        pygame.image.save(game.screen, out / "cloud-climb.png")
    (out / "review.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    pygame.quit()
    print(out)


if __name__ == "__main__":
    main()
