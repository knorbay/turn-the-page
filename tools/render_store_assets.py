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
from PIL import Image,ImageDraw,ImageFont
from game import Game
from settings import HEIGHT,WIDTH
from render_gameplay_pass import main as render_gameplay


def crop_fit(image,size):
    scale=max(size[0]/image.width,size[1]/image.height)
    resized=image.resize((round(image.width*scale),round(image.height*scale)),Image.Resampling.LANCZOS)
    left=(resized.width-size[0])//2;top=(resized.height-size[1])//2
    return resized.crop((left,top,left+size[0],top+size[1]))


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

    title=Image.open(store/"title.png").convert("RGB")
    title=crop_fit(title,(960,540))
    title.save(store/"hero.png",quality=94)
    cover=crop_fit(title,(630,500))
    # Keep the game-rendered paper, then add a small beta stamp in the same red ink.
    draw=ImageDraw.Draw(cover)
    font=ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf",28)
    stamp=(444,438,608,482)
    draw.rounded_rectangle(stamp,radius=5,fill=(244,236,210),outline=(146,61,59),width=3)
    draw.text((464,445),"BETA 0.9",font=font,fill=(146,61,59))
    cover.save(store/"cover.png",quality=94)
    print(store)


if __name__=="__main__":main()
