"""Actual runtime frame review for the five-page beta."""
import os,sys,tempfile
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import pygame
from game import Game
from combat import CombatArena
from scripted_events import ArtistTool
from campaign import FinalPageEdit
from settings import WIDTH,HEIGHT
from achievements import ACHIEVEMENTS
pygame.init();display=pygame.display.set_mode((WIDTH,HEIGHT))
out=ROOT/'work'/'beta_review';out.mkdir(parents=True,exist_ok=True)
scenes=((0,'practice_crossouts',1),(1,'coffee_crossfire',1),(2,'orbital_debris',1),(3,'carbon_crossfire',0),(3,'scissor_office',1),(4,'final_margin_revision',0))
sheet=pygame.Surface((1120,1150));sheet.fill((34,34,33))
font=pygame.font.Font(None,25)
with tempfile.TemporaryDirectory() as d:
 for index,(page,room,wave) in enumerate(scenes):
  game=Game(display,Path(d)/f'{index}.json')
  runtime=game.level.load_chapter(page,'start',game.player,game.camera)
  game._apply_page_identity();game.state='playing'
  for p in game.level.world.platforms:
   if p.thickness<=40:p.draw_progress=1
  arena=next(a for a in game.level.entities.items if isinstance(a,CombatArena) and a.arena_id==room)
  ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
  arena.encounter_active=True;arena.wave=wave;arena._spawn_wave(ctx,wave)
  arena.boss_intro_time=0
  game.player.x=arena.start_x+110;game.player.y=542;game.player.draw_amount=1
  game.player.page_style=['ronin','cowboy','astronaut','ink_agent','bad_drawing'][page]
  game.camera.x=arena.start_x-30;game.camera.offset_x=game.camera.offset_y=0
  game.level.page_title_time=0;game.level.toast_time=0
  game.level.director.tool=ArtistTool('pencil',arena.start_x+470,505,True,-.85)
  for enemy in arena.enemies:
   if enemy.kind=='redaction_agent':enemy._set_state('agent_aim',.95);enemy.state_time=.4;enemy.aim_target=(game.player.center_x,game.player.rect.centery)
   if enemy.kind=='scissor_director':enemy._set_state('cut_warn',.9);enemy.state_time=.25
   if enemy.kind=='final_editor':
    enemy.scenario='precise';enemy._set_state('proof_window',2.45);enemy.state_time=1.8
    edit=next(e for e in game.level.entities.items if isinstance(e,FinalPageEdit))
    for _ in range(30):edit.update(.1,ctx)
  game._draw_scene(game.screen)
  pygame.image.save(game.screen,out/f'page-{page+1}-{room}.png')
  thumb=pygame.transform.smoothscale(game.screen,(540,337))
  x=10+(index%2)*560;y=10+(index//2)*380
  sheet.blit(thumb,(x,y));sheet.blit(font.render(f'PAGE {page+1} / '+arena.display_name if hasattr(arena,'display_name') else room,True,(230,226,207)),(x,y+344))
 for item in ACHIEVEMENTS:game.achievements.unlocked.add(item.achievement_id)
 game.state='achievements';game.draw();pygame.image.save(game.screen,out/'achievements.png')
pygame.image.save(sheet,out/'five-pages-review.png')
pygame.quit();print(out)
