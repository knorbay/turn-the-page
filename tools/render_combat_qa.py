"""Render deterministic combat frames for local visual QA.

The script uses SDL's dummy drivers, so it exercises the real game renderer
without opening a window. Output is intentionally kept under ``work/`` and is
not part of the release archive.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from advanced_enemies import create_enemy
from camera import Camera
from combat import DoodleEnemy
from game import Game
from paper_renderer import PaperRenderer
from settings import INK_LIGHT
from settings import HEIGHT, WIDTH
from weapons import WEAPON_ORDER, WeaponSystem


OUT = ROOT / "work" / "visual_qa"


def build_scene(chapter: int, arena_id: str, weapon_id: str):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    temporary = tempfile.TemporaryDirectory()
    game = Game(screen, Path(temporary.name) / "qa-save.json")
    game.level.load_chapter(chapter, "start", game.player, game.camera)
    game.weapons = WeaponSystem(game.player)
    for unlock_id in WEAPON_ORDER:
        game.weapons.unlock(unlock_id)
    game.weapons.select(weapon_id)
    game._attach_runtime()
    game.state = "playing"

    arena = next(
        entity for entity in game.level.entities.items
        if getattr(entity, "arena_id", None) == arena_id
    )
    game.level.world.active_layer = arena.layer
    game.player.x = arena.start_x + min(300, (arena.end_x - arena.start_x) * .24)
    game.player.y = 542 if arena.layer == 0 else 562
    game.player.on_ground = True
    game.player.invulnerable = 999
    game.player.facing = 1
    game.camera.x = game.camera.target_x = max(
        0, (arena.start_x + arena.end_x) / 2 - WIDTH / 2
    )
    context = game.level.context(game.player, game.camera, game.particles, game.sounds)
    arena.update(1 / 60, context)
    game.level.page_title_time = 0
    game.level.toast_time = 0
    game.level.interaction_hint = ""
    game.time = 8.0
    return temporary, screen, game, arena, context


def render_marker_impact() -> None:
    temporary, screen, game, arena, context = build_scene(
        1, "marker_margin_trial", "marker_shotgun"
    )
    try:
        target = arena.enemies[0]
        target_rect = target.rect() if callable(getattr(target, "rect", None)) else target.rect
        game.player.x = target_rect.left - 128
        game.player.y = target_rect.bottom - game.player.HEIGHT
        game.player.facing = 1
        game.weapons.handle_input(
            fire_pressed=True,
            aim=(target_rect.centerx, target_rect.centery),
            ctx=context,
        )
        for _ in range(48):
            game.weapons.update(1 / 120, context, arena.enemies)
            game.particles.update(1 / 120)
            if game.hit_stop > 0:
                break
        game.draw()
        pygame.image.save(screen, OUT / "combat_milestone_marker_impact.png")
    finally:
        temporary.cleanup()


def render_boss_scene() -> None:
    temporary, screen, game, arena, _context = build_scene(
        2, "artist_mistake", "eraser_cannon"
    )
    try:
        game.player.set_weapon_pose("eraser_cannon", -.1, .7)
        game.draw()
        pygame.image.save(screen, OUT / "combat_milestone_boss.png")
    finally:
        temporary.cleanup()


def render_boss_lineup() -> None:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    renderer = PaperRenderer()
    camera = Camera(WIDTH)
    renderer.background(screen, 1)
    pygame.draw.line(screen, (82, 78, 73), (82, 590), (WIDTH, 590), 3)
    entries = [
        ("COMPASS", create_enemy("compass", 125, 590, 11), "stuck"),
        ("STAPLER", create_enemy("stapler", 305, 590, 12), "reload"),
        ("FAILED SKETCH", create_enemy("failed_sketch", 500, 590, 13), "unravel"),
        ("ARTIST'S MISTAKE", create_enemy("artist_mistake", 710, 590, 14), "intro"),
        ("SCRIBBLE GIANT", DoodleEnemy("boss", 915, 590, 15, boss=True), "recover"),
    ]
    for label, enemy, state in entries:
        enemy.state = state
        if getattr(enemy, "kind", "") == "artist_mistake":
            enemy.phase = 2
        enemy.draw(screen, camera, renderer)
        renderer.doodle_text(
            screen, label,
            (camera.screen_x(enemy.x) - len(label) * 5, 625),
            INK_LIGHT, renderer.font_small, -1,
        )
    pygame.image.save(screen, OUT / "boss_silhouette_lineup.png")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    try:
        render_marker_impact()
        render_boss_scene()
        render_boss_lineup()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
