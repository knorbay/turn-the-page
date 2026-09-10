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


def brand_font(size):
    candidates=(
        Path("/System/Library/Fonts/Avenir Next Condensed.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate),size)
    return ImageFont.load_default()


def brand_art(size):
    width,height=size
    paper=(246,239,213);ink=(38,38,43);red=(153,48,45)
    # The cover is a real deterministic frame from the game: the signature
    # Baby Face reversal with the actual player, Excalibur, arena, notes, and
    # ruled-paper renderer. Branding should introduce the scene, not replace it.
    scene=Image.open(ROOT/"store"/"screenshots"/"baby-face-signature.png").convert("RGB")
    canvas=crop_fit(scene,size)
    draw=ImageDraw.Draw(canvas)

    left=round(width*.045);top=round(height*.045)
    right=round(width*(.62 if width/height<1.5 else .54))
    bottom=round(height*.235)
    # Offset rectangles echo the game's hand-drawn panels and leave the boss
    # silhouette fully visible.
    draw.rectangle((left+3,top+4,right+3,bottom+4),fill=(42,40,40))
    draw.rectangle((left,top,right,bottom),fill=paper,outline=ink,width=2)
    title=brand_font(round(height*.080))
    subtitle=brand_font(round(height*.034))
    draw.text((left+round(width*.018),top+round(height*.018)),
              "TURN THE PAGE",font=title,fill=ink)
    line_y=top+round(height*.118)
    draw.line((left+round(width*.018),line_y,right-round(width*.02),line_y-2),
              fill=red,width=max(3,round(height*.008)))
    draw.text((left+round(width*.02),top+round(height*.142)),
              "something is still drawing",font=subtitle,fill=ink)
    return canvas


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

    brand_art((960,540)).save(store/"hero.png",quality=95)
    brand_art((630,500)).save(store/"cover.png",quality=95)
    print(store)


if __name__=="__main__":main()
