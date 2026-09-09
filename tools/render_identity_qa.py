"""Render deterministic contact sheets for the Turn the Page rebuild pass."""
from __future__ import annotations

import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from camera import Camera
from combat import CombatArena
from game import Game
from identity_content import BabyFaceSignatureBeat
from paper_renderer import PaperRenderer
from player import Player
from scripted_events import ArtistDirector, ArtistTool
from settings import HEIGHT, INK, INK_LIGHT, WIDTH


def _save(surface, name):
    target = ROOT / "work" / "visual_qa" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, target)
    print(target)


def _game(save_name="qa-save.json"):
    display = pygame.display.get_surface() or pygame.display.set_mode((WIDTH, HEIGHT))
    path = ROOT / "work" / "visual_qa" / save_name
    if path.exists():
        path.unlink()
    game = Game(display, path)
    game.state = "playing"
    return game


def _scene(page, checkpoint, arena_id, x, wave=0):
    game = _game(f"qa-{page}.json")
    game.level.load_chapter(page, checkpoint, game.player, game.camera)
    game._apply_page_identity()
    for platform in game.level.world.platforms:
        if "artist_cover" not in platform.name:
            platform.draw_progress = 1
    arena = next(entity for entity in game.level.entities.items
                 if isinstance(entity, CombatArena) and entity.arena_id == arena_id)
    context = game.level.context(game.player, game.camera, game.particles, game.sounds)
    arena.encounter_active = True
    arena.wave = wave
    arena._spawn_wave(context, wave)
    for enemy in arena.enemies:
        enemy.state_time = .45
    game.player.x, game.player.y = x, 542
    game.player.draw_amount = 1
    game.camera.x = max(0, x - WIDTH * .38)
    game.camera.offset_x = game.camera.offset_y = 0
    surface = pygame.Surface((WIDTH, HEIGHT))
    game._draw_scene(surface)
    return game, surface, arena


def render_page_contact_sheet():
    panels = []
    page0 = _scene(0, "bridge", "practice_crossouts", 4880)[1]
    panels.append((page0, "INK OF THE RONIN — samurai / drone / goblin"))
    page1 = _scene(1, "margin_exit", "marker_margin_trial", 8680)[1]
    panels.append((page1, "DUST & BAD DECISIONS — cowboy collage"))
    game2, page2, arena = _scene(2, "after_eraser_calibration",
                                 "baby_face_interlude", 15980, 0)
    boss = next(enemy for enemy in arena.enemies if enemy.kind == "baby_face_giant")
    boss.moustache_progress = 1
    boss.empowered = True
    beat = next(entity for entity in game2.level.entities.items
                if isinstance(entity, BabyFaceSignatureBeat))
    beat.state = "sword_pull"
    beat.sword_progress = .86
    beat.pull_progress = .22
    game2._draw_scene(page2)
    panels.append((page2, "A VERY WRONG FUTURE — baby / moustache / sword"))

    sheet = pygame.Surface((1280, 900))
    sheet.fill((32, 31, 30))
    font = pygame.font.Font(None, 28)
    for index, (panel, label) in enumerate(panels):
        scaled = pygame.transform.smoothscale(panel, (600, 375))
        px = 25 + (index % 2) * 630
        py = 25 + (index // 2) * 425
        sheet.blit(scaled, (px, py))
        sheet.blit(font.render(label, True, (238, 232, 212)), (px, py + 382))
    # Third panel gets a wider crop beside a compact style legend.
    legend_x, legend_y = 655, 455
    legend = [
        "Three worlds; one handmade ink language:",
        "• washi / bamboo / torii / brush road",
        "• ledger desert / cactus / railroad",
        "• orbit chart / constellation / moon deck",
        "• ronin / cowboy / astronaut silhouette",
        "• prototype annexes pruned from runtime",
    ]
    for line_index, line in enumerate(legend):
        color = (238, 232, 212) if line_index == 0 else (184, 178, 164)
        sheet.blit(font.render(line, True, color),
                   (legend_x, legend_y + line_index * 42))
    _save(sheet, "turn_the_page_rebuild_contact_sheet.png")


def render_redraw_sequence():
    renderer = PaperRenderer()
    sheet = pygame.Surface((1280, 500))
    sheet.fill((36, 35, 33))
    font = pygame.font.Font(None, 25)
    stages = ((.06, "HEAD ARC"), (.28, "SPINE"), (.50, "ARMS"),
              (.72, "FIRST LEG"), (1.0, "CONTROL"))
    for index, (amount, label) in enumerate(stages):
        panel = pygame.Surface((230, 410))
        renderer.background(panel, 0)
        player = Player(91, 265)
        player.draw_amount = amount
        player.redraw_variant = "long_arm" if index == 4 else "clean"
        camera = Camera(230)
        player.draw(panel, camera)
        director = ArtistDirector()
        tip_x, tip_y = player.redraw_tip()
        director.tool = ArtistTool("pencil", tip_x, tip_y, True, -.64, 1.1)
        director.draw(panel, camera, renderer)
        x = 20 + index * 250
        sheet.blit(panel, (x, 24))
        sheet.blit(font.render(f"{index + 1}. {label}", True, (236, 231, 211)),
                   (x + 8, 449))
    _save(sheet, "turn_the_page_redraw_sequence.png")


def render_signature_full():
    game, surface, arena = _scene(2, "after_eraser_calibration",
                                  "baby_face_interlude", 15980, 0)
    boss = next(enemy for enemy in arena.enemies if enemy.kind == "baby_face_giant")
    boss.moustache_progress = 1
    boss.empowered = True
    boss.state = "idle"
    beat = next(entity for entity in game.level.entities.items
                if isinstance(entity, BabyFaceSignatureBeat))
    beat.state = "sword_pull"
    beat.sword_progress = 1
    beat.pull_progress = .28
    game.level.director.write(boss.x - 170, boss.ground_y - 345,
                              "It's more fair now.", 1)
    game._draw_scene(surface)
    _save(surface, "turn_the_page_baby_face_signature.png")


if __name__ == "__main__":
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    pygame.display.set_mode((WIDTH, HEIGHT))
    render_page_contact_sheet()
    render_redraw_sequence()
    render_signature_full()
    pygame.quit()
