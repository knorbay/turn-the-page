"""Review the actual gameplay render and time-based enemy poses."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from game import Game
from camera import Camera
from advanced_enemies import InkSamurai, InkOutlaw, MoonBot, CometHound
from staging import ROUTES, draw_enemy_read
from settings import WIDTH, HEIGHT

pygame.init()
display=pygame.display.set_mode((WIDTH,HEIGHT))
out=ROOT/'work'/'polish_qa';out.mkdir(parents=True,exist_ok=True)
game=Game(display,out/'qa-save.json');game.state='playing'
canvas=pygame.Surface((WIDTH,HEIGHT*3))
for page,start,title,secret,caption,style in ROUTES:
    game.level.load_chapter(page, None, game.player, game.camera)
    game._apply_page_identity()
    for p in game.level.world.platforms:
        if 'artist_cover' not in p.name: p.draw_progress=1
    game.camera.x=start-70
    game.camera.offset_x=game.camera.offset_y=0
    game.player.x=start+440;game.player.y=345-48
    game.player.draw_amount=1
    game.time=1.2
    frame=pygame.Surface((WIDTH,HEIGHT));game._draw_scene(frame)
    pygame.image.save(frame,out/f'world-{page+1}.png')
    canvas.blit(frame,(0,page*HEIGHT))
pygame.image.save(canvas,out/'three-routes.png')
actors=[InkSamurai(140,310),InkOutlaw(420,310),MoonBot(700,310),CometHound(980,310)]
cycles=[(('sheath',.68),('draw_cut',.32),('recover',.82)),
        (('quickdraw',.82),('recover',.95)),
        (('ram_warn',.52),('ram',.42),('cool',.85)),
        (('tail_warn',.68),('comet_dash',1.18),('cool',.84))]
frames=[];camera=Camera(WIDTH)
for frame_index in range(90):
    t=frame_index/30
    panel=pygame.Surface((WIDTH,420));panel.fill((243,237,216))
    font=pygame.font.Font(None,25)
    for i,(actor,cycle) in enumerate(zip(actors,cycles)):
        local=t%sum(d for _,d in cycle)
        for state,duration in cycle:
            if local < duration:break
            local-=duration
        actor._set_state(state,duration);actor.state_time=duration-local;actor.time=t
        actor.facing=1;actor.vx=590 if state=='comet_dash' else 0
        actor.aim_target=(actor.x+100,280)
        actor.draw(panel,camera,game.renderer)
        draw_enemy_read(panel,camera,game.renderer,actor)
        title=actor.kind.replace('_',' ').upper()
        panel.blit(font.render(title,True,(49,48,47)),(i*280+45,36))
        panel.blit(font.render(state.upper(),True,(100,90,80)),(i*280+65,359))
        pygame.draw.line(panel,(115,105,85),(i*280+20,313),(i*280+260,313),1)
    frames.append(Image.frombytes('RGB',panel.get_size(),pygame.image.tobytes(panel,'RGB')))
frames[0].save(out/'combat-motion.gif',save_all=True,append_images=frames[1:],duration=33,loop=0)
pygame.quit()
print(out)
