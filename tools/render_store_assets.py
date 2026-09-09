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
    paper=(246,239,213);ink=(38,38,43);red=(153,48,45);rule=(176,207,217)
    canvas=Image.new("RGB",size,paper)
    draw=ImageDraw.Draw(canvas)
    for y in range(54,height,54):
        draw.line((0,y,width,y),fill=rule,width=2)
    draw.line((round(width*.075),0,round(width*.075),height),fill=(202,117,112),width=3)

    emblem=Image.open(ROOT/"packaging"/"brand-emblem.png").convert("RGBA")
    box=emblem.getchannel("A").getbbox()
    emblem=emblem.crop(box)
    # Leave a clean gutter between the emblem's external pencil and the wordmark.
    # The same proportions must remain readable in both the wide hero and the
    # nearly-square itch cover.
    mark=round(min(width*.46,height*.76))
    emblem.thumbnail((mark,mark),Image.Resampling.LANCZOS)
    canvas.paste(emblem,(round(width*.015),(height-emblem.height)//2),emblem)

    left=round(width*.51)
    small=brand_font(round(height*.095));large=brand_font(round(height*.20))
    draw.text((left,round(height*.19)),"TURN THE",font=small,fill=ink,stroke_width=1)
    draw.text((left-4,round(height*.28)),"PAGE",font=large,fill=ink,stroke_width=1)
    line_y=round(height*.51)
    draw.line((left,line_y,width-round(width*.04),line_y-10),fill=red,width=8)
    draw.line((left+10,line_y+12,width-round(width*.10),line_y+4),fill=ink,width=3)
    tagline=brand_font(round(height*.044))
    draw.text((left,round(height*.57)),"THE ARTIST DRAWS.",font=tagline,fill=ink)
    draw.text((left,round(height*.625)),"YOU FIGHT BACK.",font=tagline,fill=red)
    stamp_font=brand_font(round(height*.045))
    stamp=(left,round(height*.74),width-round(width*.05),round(height*.84))
    draw.rounded_rectangle(stamp,radius=6,fill=paper,outline=red,width=3)
    label="PUBLIC BETA 0.9"
    bounds=draw.textbbox((0,0),label,font=stamp_font)
    tx=stamp[0]+(stamp[2]-stamp[0]-(bounds[2]-bounds[0]))//2
    ty=stamp[1]+(stamp[3]-stamp[1]-(bounds[3]-bounds[1]))//2-2
    draw.text((tx,ty),label,font=stamp_font,fill=red)
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
