"""Reproduce release UI and gameplay captures with disposable QA saves."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from game import Game
from localization import set_language
from notebook_notes import NotebookAnnotations
from sketches import SKETCHES
from settings import WIDTH,HEIGHT

out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work'/'release-review'
out.mkdir(parents=True,exist_ok=True)
pygame.init();screen=pygame.display.set_mode((WIDTH,HEIGHT))
with tempfile.TemporaryDirectory() as tmp:
 game=Game(screen,Path(tmp)/'save.json')
 for language in ('tr','en'):
  set_language(language);game.save.data['settings']['language']=language
  game.renderer.notebook.tiles.clear();game.renderer.notebook_notes=NotebookAnnotations()
  game.save.data['secrets']=[s.secret_id for s in SKETCHES]
  for state in ('title','settings','pause','controls','achievements','back_pages'):
   game.state=state;game.previous_state='title';game.sketch_page=0
   game.draw();pygame.image.save(game.screen,out/f'{language}-{state}.png')
  game.sketch_page=1;game.draw();pygame.image.save(game.screen,out/f'{language}-runes.png')
 set_language("tr");game.save.data["settings"]["language"]="tr"
 game.renderer.notebook.tiles.clear();game.renderer.notebook_notes=NotebookAnnotations()
 game.save.data["secrets"]=[]
 for page in (0,1,3):
  game.level.load_chapter(page,'start',game.player,game.camera);game._attach_runtime()
  pocket=next(e for e in game.level.entities.items if getattr(e,'is_secret_pocket',False))
  game.player.x=pocket.bounds[0]+35;game.player.y=pocket.ground-48
  game.player.draw_amount=1;game.player.release_all_locks()
  game.camera.x=pocket.base+170;game.camera.offset_y=0;game.camera.offset_x=0
  game.level.page_title_time=game.level.toast_time=game.weapon_reveal_time=0
  lesson=getattr(game.level.runtime,'training',None)
  if lesson:lesson.completed=True;lesson.gate.enabled=False
  if page==0:
   ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
   game.player.x=pocket.base+60-12;game.player.y=542
   pocket.update(.01,ctx,True)
   for _ in range(50):pocket.update(1/60,ctx)
   game.player.x=pocket.bounds[0]+35;game.player.y=pocket.ground-48
   game.weapons.unlock('folded_shuriken');game.weapons.select('folded_shuriken')
   pocket.update(.01,game.level.context(game.player,game.camera,game.particles,game.sounds),True)
   for _ in range(60):pocket.update(1/60,game.level.context(game.player,game.camera,game.particles,game.sounds))
   pocket.letter_time=0
  game.state='playing';game.draw()
  pygame.image.save(game.screen,out/f'secret-{pocket.kind}.png')
pygame.quit()
print(out)
