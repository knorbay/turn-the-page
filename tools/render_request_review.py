"""Capture automatic Artist drawings in the actual game, with temporary saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from game import Game
from notebook_agency import NotebookAgency
from page_arsenal import PAGE_ENTRY_TOOLS
from localization import set_language
from settings import WIDTH,HEIGHT

def load(g,page):
    g.reset();g.level.load_chapter(page,'start',g.player,g.camera);g._attach_runtime()
    g.player.release_all_locks();g.player.draw_amount=1;g.player.y=542;g.player.on_ground=True
    lesson=getattr(g.level.runtime,'training',None)
    if lesson:lesson.completed=True;lesson.gate.enabled=False
    g.save.checkpoint(page,'start');g.state='playing';g.time=3
    g.level.page_title_time=g.level.toast_time=g.weapon_reveal_time=0
    g.level.director.tool.visible=False;g.level.director.messages.clear()
    a=next(e for e in g.level.entities.items if isinstance(e,NotebookAgency))
    ctx=g.level.context(g.player,g.camera,g.particles,g.sounds);a._restore(ctx)
    w=PAGE_ENTRY_TOOLS[page];g.weapons.unlock(w);g.weapons.select(w)
    return a,ctx

def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work/automatic-artist-review';out.mkdir(parents=True,exist_ok=True)
    pygame.init();screen=pygame.display.set_mode((WIDTH,HEIGHT));metadata=[];panels=[]
    with tempfile.TemporaryDirectory() as folder:
        g=Game(screen,Path(folder)/'save.json')
        for page in range(5):
            a,ctx=load(g,page);set_language('tr');a.first.completed=True
            g.player.x=a.first.end_x+30;g.camera.x=g.player.center_x-WIDTH/2
            held=g.weapons.current_id;ammo=g.weapons.current.ammo
            a.update(.01,ctx);assert a.operation=='support_tool';a.update(.9,ctx)
            g.draw();pygame.image.save(g.screen,out/f'page-{page+1}-automatic-drawing.png');panels.append(g.screen.copy())
            for _ in range(30):a.update(1/60,ctx)
            g.draw();pygame.image.save(g.screen,out/f'page-{page+1}-gift-keeps-weapon.png')
            assert g.weapons.current_id==held and g.weapons.current.ammo==ammo
            metadata.append({'page':page+1,'gift':a.selected_weapon,'held':held,'ammo_preserved':ammo,'requested':False})
        a,ctx=load(g,0);r=a.first;r.encounter_active=True;r.encounter_time=3
        g.player.x=r.start_x+150;g.camera.x=g.player.center_x-WIDTH/2
        r._spawn_wave(ctx,0)
        for enemy in r.enemies:enemy.notebook_reveal=1;enemy.notebook_spawn_pending=False
        g.player.health=1;a.update(.01,ctx);a.update(.65,ctx)
        g.draw();pygame.image.save(g.screen,out/'automatic-heart-redraw.png')
        sheet=pygame.Surface((WIDTH,HEIGHT*5))
        for i,panel in enumerate(panels):sheet.blit(panel,(0,i*HEIGHT))
        pygame.image.save(sheet,out/'five-page-automatic-tools.png')
    (out/'automatic-contracts.json').write_text(json.dumps(metadata,indent=2),encoding='utf8');pygame.quit();print(out)

if __name__=='__main__':main()
