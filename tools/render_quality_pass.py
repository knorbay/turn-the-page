"""Render the quality pass from real Game.update/draw states, without a save."""
from pathlib import Path
import os
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from game import Game
from input_state import InputFrame
from page_arsenal import PAGE_ENTRY_TOOLS
from page_flow import FLOW_SECTIONS
from settings import WIDTH, HEIGHT

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "quality-pass-review"


def frame(game, name):
    game.draw()
    pygame.image.save(game.screen, OUT / (name + ".png"))


def opening(game):
    game.reset()
    captured = set()
    jumps = 0
    for tick in range(680):
        player = game.player
        thresholds = (720, 980, 1215)
        jump = jumps < 3 and player.on_ground and player.x >= thresholds[jumps]
        if jump:
            jumps += 1
        game.update(1/60, InputFrame(right=player.x < 1530,
                                   jump_pressed=jump, jump_held=True))
        gift = next(e for e in game.level.entities.items
                    if getattr(e,"weapon_id",None)=="folded_shuriken")
        stroke = game.level.world.platform_named("first_step")
        samples = {
            "opening-figure": .25 < player.draw_amount < .60,
            "opening-live-platform": .28 < stroke.draw_progress < .70,
            "opening-drawn-fold": .28 < gift.draw_progress < .70,
            "opening-tool-collected": gift.collected,
        }
        for name, ready in samples.items():
            if ready and name not in captured:
                frame(game, name)
                captured.add(name)
        if player.x >= 1530 and not player.locked:
            break
    if len(captured) != 4 or game.weapons.current_id != "folded_shuriken":
        raise RuntimeError((captured, game.player.x, game.weapons.current_id))


def first_sketch(game):
    game.reset()
    for _ in range(230):
        game.update(1/60, InputFrame(right=game.player.x < 434))
    discovery = next(e for e in game.level.entities.items
                     if getattr(getattr(e,"sketch",None),"secret_id",None)=="old_first_figure")
    seen = False
    for _ in range(90):
        game.update(1/60, InputFrame(interact=True))
        if .35 < discovery.reveal < .65 and not seen:
            frame(game, "sketch-artist-erasure")
            seen = True
    if "old_first_figure" not in game.save.data["secrets"]:
        raise RuntimeError("First Lost Sketch was not physically discovered/kept")
    frame(game, "sketch-first-explanation")


def routes(game):
    for page, sections in FLOW_SECTIONS.items():
        for name, span, landings, _style in sections:
            game.level.load_chapter(page,"start",game.player,game.camera)
            game._attach_runtime()
            game.weapons.lend_drawn_tool(PAGE_ENTRY_TOOLS[page])
            a,b,y = landings[0]
            game.player.x = (a+b)/2-12
            game.player.y = y-game.player.HEIGHT
            game.player.on_ground = True
            game.player.draw_amount = 1
            game.player.page_style = ("ronin","cowboy","astronaut","ink_agent","bad_drawing")[page]
            game.camera.x = game.camera.target_x = span[0]-360
            game.camera.offset_x = game.camera.offset_y = 0
            game.level.page_title_time = 0
            game.level.toast_time = 0
            game.weapon_reveal_time = 0
            frame(game,"route-"+name)


def resolutions(game):
    for size in ((960,600),(1280,800),(1366,768),(1600,900)):
        game._set_display_mode(size, fullscreen=False)
        game.draw()
        game._present()
        pygame.image.save(game.display, OUT / f"resolution-{size[0]}x{size[1]}.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.mixer.pre_init(22050,-16,1,512)
    pygame.init()
    try:
        screen = pygame.display.set_mode((WIDTH,HEIGHT))
        with tempfile.TemporaryDirectory(prefix="turn-the-page-quality-") as directory:
            game = Game(screen,Path(directory)/"review.json")
            opening(game)
            first_sketch(game)
            routes(game)
            resolutions(game)
    finally:
        pygame.quit()
    print(OUT)


if __name__ == "__main__":
    main()
