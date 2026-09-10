"""Create itch/GitHub beta art from the real game renderer."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import shutil
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pygame
from game import Game
from settings import HEIGHT,WIDTH
from render_gameplay_pass import main as render_gameplay
from brand_art import render_key_art


def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    store=ROOT/"store";shots=store/"screenshots"
    shots.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="turn-the-page-store-") as directory:
        game=Game(screen,Path(directory)/"save.json")
        game.state="title";game.time=1.2;game.draw()
        pygame.image.save(game.screen,(store/"title.png").as_posix())
    pygame.quit()
    render_gameplay()
    review=ROOT/"work"/"gameplay_review"
    for page in range(1,6):
        shutil.copy2(review/f"page-{page}.png",shots/f"page-{page}.png")
    shutil.copy2(review/"back-pages.png",shots/"back-pages.png")

    render_key_art((960,540)).save(store/"hero.png",quality=95)
    render_key_art((630,500)).save(store/"cover.png",quality=95)
    print(store)


if __name__=="__main__":main()
