"""Render the shipped boss animation cycles and the actual pencil combo.

The actor montage is a controlled animation review, not a playthrough.
Bosses use their real update/draw methods on their real page geometry.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import math
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from game import Game
from combat import CombatArena
from weapons import MeleeSwing
from settings import WIDTH,HEIGHT


def pil(surface):
    return Image.frombytes("RGB",surface.get_size(),pygame.image.tobytes(surface,"RGB"))


def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    out=ROOT/"work"/"identity_pass_review"
    out.mkdir(parents=True,exist_ok=True)
    font=pygame.font.Font(None,25)
    configs=((0,"moon_gate_duel","PERGEL / geometrik kesiş"),
             (1,"marker_margin_trial","ARANAN / yaşayan afiş"),
             (1,"midnight_train","ZIMBA TRENİ / ray hücumu"),
             (2,"zero_garden","YÖRÜNGE / uydular ve meteor"))
    games=[]
    with tempfile.TemporaryDirectory() as temp:
        for i,(page,room,title) in enumerate(configs):
            g=Game(screen,Path(temp)/f"review-{i}.json")
            g.level.load_chapter(page,"start",g.player,g.camera)
            g._apply_page_identity()
            a=next(a for a in g.level.entities.items if isinstance(a,CombatArena) and a.arena_id==room)
            for p in g.level.world.platforms:
                if p.thickness<=40:p.draw_progress=1
            ctx=g.level.context(g.player,g.camera,g.particles,g.sounds)
            a.encounter_active=True
            wave=max(s["wave"] for s in a.enemy_specs)
            a.wave=wave;a._spawn_wave(ctx,wave);a.boss_intro_time=0
            g.player.release_all_locks();g.player.x=a.start_x+360;g.player.y=542
            g.player.draw_amount=1;g.player.invulnerable=999
            g.camera.x=a.start_x+max(0,(a.end_x-a.start_x-WIDTH)/2)
            g.camera.offset_x=g.camera.offset_y=0
            g.level.page_title_time=g.level.toast_time=0
            games.append((g,a,ctx,title))
        frames=[]
        for frame in range(210):
            montage=pygame.Surface((1120,746));montage.fill((39,39,38))
            for i,(g,a,ctx,title) in enumerate(games):
                g.time=frame/30
                for enemy in a.enemies:
                    enemy.update(1/30,ctx,(a.start_x-45,a.end_x-35))
                g.particles.update(1/30)
                g.camera.offset_x=g.camera.offset_y=0
                g._draw_scene(g.screen)
                tile=pygame.transform.smoothscale(g.screen,(552,345))
                x=(i%2)*560+4;y=(i//2)*373+24
                montage.blit(tile,(x,y))
                montage.blit(font.render(title,True,(235,230,211)),(x,y-23))
                if frame==40:
                    pygame.image.save(g.screen,out/f"boss-{i+1}.png")
            if frame==40:pygame.image.save(montage,out/"Bosslar-ve-Ders-Notlari.png")
            if frame%2==0:
                frames.append(pil(pygame.transform.smoothscale(montage,(896,597))))
        frames[0].save(out/"Boss-Davranislari.gif",save_all=True,
                        append_images=frames[1:],duration=67,loop=0)
        # Three different combat strokes, with actual pose and ribbon code.
        g=games[0][0]
        g.player.x=160;g.player.y=218;g.player.on_ground=True
        g.player.invulnerable=0;g.player.page_style="ronin"
        g.player.current_weapon="pencil_blade"
        g.camera.x=0;g.camera.offset_x=g.camera.offset_y=0
        combo=[]
        for frame in range(72):
            t=frame/30
            panel=pygame.Surface((840,315));panel.fill((242,235,211))
            for i,duration in enumerate((.25,.28,.46)):
                g.player.x=100+i*280
                swing=MeleeSwing(i+1,pygame.Vector2(1,0),duration,.045,
                    .16 if i<2 else .25,1, (61,67,91)[i],100,.1)
                local=t%.8
                swing.elapsed=min(duration,local)
                g.weapons.melee=swing if local<duration else None
                g.player.combat_swing=swing.pencil_pose() if local<duration else None
                g.player.anim_time=t;g.player.vx=0
                if g.weapons.melee:g.weapons._draw_melee(panel,g.camera)
                g.player.draw(panel,g.camera)
                pygame.draw.line(panel,(112,99,76),(20+i*280,267),(260+i*280,267),1)
                panel.blit(font.render(("01 / KESİŞ","02 / TERS KESİŞ","03 / BİTİRİCİ")[i],
                                       True,(58,58,57)),(30+i*280,30))
            combo.append(pil(panel))
        combo[0].save(out/"Katana-Hareketleri.gif",save_all=True,
                       append_images=combo[1:],duration=33,loop=0)
        notes=pygame.Surface((1020,825));notes.fill((242,235,211))
        for page in range(5):
            for i in range(2):
                notes.blit(g.renderer.notebook_notes.sheets[page][i],(i*510,page*165))
        pygame.image.save(notes,out/"ders-notlari.png")
    pygame.quit()
    print(out)


if __name__=="__main__":main()
