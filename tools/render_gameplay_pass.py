"""Controlled runtime frames for visual review of the gameplay systems.

These are scene inspections, not a recorded human playthrough. All geometry,
actors, weapon poses and UI are drawn by the shipping game.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from game import Game
from combat import CombatArena
from action_content import WeaponPickup
from sketches import SKETCHES
from settings import WIDTH,HEIGHT


def pil(surface):
    return Image.frombytes("RGB",surface.get_size(),pygame.image.tobytes(surface,"RGB"))


def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    out=ROOT/"work"/"gameplay_review"
    out.mkdir(parents=True,exist_ok=True)
    scenes=((0,"practice_crossouts","pencil_blade"),
            (1,"marker_margin_trial","marker_shotgun"),
            (2,"orbital_debris","rubber_band"),
            (3,"redacted_rooftops","ink_pistol"),
            (4,"erased_answers","eraser_cannon"))
    frames=[]
    with tempfile.TemporaryDirectory() as temp:
        for page,room,tool in scenes:
            g=Game(screen,Path(temp)/f"scene-{page}.json")
            g.level.load_chapter(page,"start",g.player,g.camera)
            a=next(a for a in g.level.entities.items
                   if isinstance(a,CombatArena) and a.arena_id==room)
            cp=max((cp for cp in g.level.runtime.checkpoints if cp.x<a.start_x),
                   key=lambda cp:cp.x)
            g.level.load_chapter(page,cp.checkpoint_id,g.player,g.camera)
            g._apply_page_identity()
            a=next(a for a in g.level.entities.items
                   if isinstance(a,CombatArena) and a.arena_id==room)
            for gift in g.level.entities.items:
                if isinstance(gift,WeaponPickup) and gift.x<a.start_x:
                    g.weapons.unlock(gift.weapon_id)
            g.weapons.select(tool)
            g.player.x,g.player.y=a.start_x+210,542
            g.player.draw_amount=1
            g.player.release_all_locks()
            g.player.page_style=("ronin","cowboy","astronaut","ink_agent","bad_drawing")[page]
            g.camera.x=a.start_x-100
            g.camera.offset_x=g.camera.offset_y=0
            ctx=g.level.context(g.player,g.camera,g.particles,g.sounds)
            a.encounter_active=True;a.wave=0
            a._spawn_wave(ctx,a.wave_ids[0])
            a.entrance_gate.enabled=True
            for stage in getattr(a,"artist_stages",()):
                cover=getattr(stage,"cover",None)
                if cover is not None:cover.draw_progress=1
            g.weapons.handle_input(fire_pressed=True,aim=(g.player.center_x+300,551),ctx=ctx)
            for _ in range(5):
                g.weapons.update(1/60,ctx,g.level.entities)
            g.player.set_weapon_pose(tool,0,.7)
            g.level.page_title_time=g.level.toast_time=0
            g.state="playing";g.time=4.4
            g.draw()
            frame=pil(g.screen)
            frame.save(out/f"page-{page+1}.png")
            frames.append(frame)
            if page==1:
                g.player.health=1;g.player.hurt_flash=.3
                g.draw()
                pil(g.screen).save(out/"one-heart.png")
                g.player.begin_fight();g.draw()
                pil(g.screen).save(out/"next-fight.png")
                g.save.data["secrets"]=[s.secret_id for s in SKETCHES]
                g._apply_page_identity()
                g.state="back_pages";g.draw()
                back=pil(g.screen);back.save(out/"back-pages.png")
        frames.append(back)
        montage=Image.new("RGB",(1120,1050),(242,237,215))
        for i,frame in enumerate(frames):
            montage.paste(frame.resize((560,350),Image.Resampling.LANCZOS),
                          ((i%2)*560,(i//2)*350))
        montage.save(out/"gameplay-overview.png")
    pygame.quit()
    print(out)


if __name__=="__main__":main()
