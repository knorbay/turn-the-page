import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import json,tempfile,unittest
from pathlib import Path
import pygame
from chapters import build_chapter
from combat import CombatArena
from player import Player
from particles import ParticleSystem
from world import PaperWorld
from behavior import BehaviorLedger
from game import Game
from save_system import SaveSystem
from campaign import FinalPageEdit
from settings import WIDTH,HEIGHT

class FivePageBetaContracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  pygame.init();cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))
 @classmethod
 def tearDownClass(cls):pygame.quit()

 def test_thin_platform_passes_from_below_and_catches_fast_fall(self):
  world=PaperWorld(0,False)
  world.add(0,500,590,16,'floor')
  platform=world.add(100,350,505,10,'landing')
  player=Player(190,542);player.on_ground=True
  player.queue_jump();particles=ParticleSystem()
  for _ in range(110):player.update(1/120,0,world,particles)
  self.assertTrue(player.on_ground)
  self.assertEqual(player.rect.bottom,505)
  player.y=200;player.vy=950
  player._move_y(.4,world)
  self.assertEqual(player.rect.bottom,505)
  platform.erase(100,350)
  player.update(.02,0,world,particles)
  self.assertFalse(player.on_ground)

 def test_artist_arena_landings_are_physical_on_every_page(self):
  for page in range(5):
   runtime=build_chapter(page)
   covers=[p for p in runtime.world.platforms if 'artist_cover' in p.name]
   self.assertTrue(covers)
   for p in covers:
    p.draw_progress=1
    self.assertTrue(p.collidable)
    self.assertTrue(p.one_way)
    self.assertTrue(p.collision_rects())

 def test_all_new_checkpoints_have_support_and_cannot_skip_the_next_room(self):
  for page in (3,4):
   with tempfile.TemporaryDirectory() as directory:
    game=Game(self.screen,Path(directory)/'save.json')
    runtime=build_chapter(page)
    for cp in runtime.checkpoints:
     game.level.load_chapter(page,cp.checkpoint_id,game.player,game.camera)
     game._apply_page_identity()
     for _ in range(20):game.player.update(1/120,0,game.level.world,game.particles)
     self.assertTrue(game.player.on_ground,(page,cp.checkpoint_id))
     if cp.checkpoint_id.startswith('before_'):
      name=cp.checkpoint_id.removeprefix('before_')
      arena=next(a for a in game.level.entities.items if isinstance(a,CombatArena) and a.arena_id==name)
      self.assertFalse(arena.completed)
      self.assertTrue(arena.exit_gate.enabled)

 def test_new_page_catch_lines_have_a_real_return_jump(self):
  for page in (3,4):
   runtime=build_chapter(page)
   for arena in [a for a in runtime.entities.items if isinstance(a,CombatArena)]:
    player=Player(arena.start_x+70,690-48);player.on_ground=True
    player.queue_jump()
    for _ in range(120):player.update(1/120,0,runtime.world,ParticleSystem())
    # Ground at 590 is within a full jump from the visible lower margin.
    self.assertEqual(player.rect.bottom,590,(page,arena.arena_id))
    self.assertGreaterEqual(arena.exit_gate.thickness,435)

 def test_behavior_uses_actual_retreat_and_four_final_layouts_are_distinct(self):
  from types import SimpleNamespace
  b=BehaviorLedger();p=Player(100,542);p.vx=-200
  for _ in range(300):b.observe_combat(.1,p,[SimpleNamespace(x=500,dead=False)])
  self.assertEqual(b.broad_tendency(),'avoidant')
  b.data['combat_motion']['retreat_seconds']=0
  b.data['combat_motion']['close_seconds']=25
  b.data['counts']['attacks']=100
  self.assertEqual(b.broad_tendency(),'aggressive')
  b.data['counts']['enemies_defeated']=25
  b.data['boss_clear_seconds']['moon_compass']=35
  self.assertEqual(b.broad_tendency(),'precise')
  geometries=[]
  for scenario in ('aggressive','avoidant','precise','unreadable'):
   with tempfile.TemporaryDirectory() as d:
    game=Game(self.screen,Path(d)/'save.json')
    game.level.load_chapter(4,'before_final_margin_revision',game.player,game.camera)
    arena=next(a for a in game.level.entities.items if isinstance(a,CombatArena) and a.arena_id=='final_margin_revision')
    ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
    arena.encounter_active=True;arena._spawn_wave(ctx,0)
    arena.enemies[0].scenario=scenario
    edit=next(e for e in game.level.entities.items if isinstance(e,FinalPageEdit))
    for _ in range(30):edit.update(.1,ctx)
    geometries.append(tuple((p.x1,p.y) for p in edit.platforms))
    self.assertTrue(all(p.draw_progress==1 and p.collision_rects() for p in edit.platforms))
  self.assertEqual(len(set(geometries)),4)

 def test_old_completed_three_page_save_continues_into_agent(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/'save.json'
   path.write_text(json.dumps({'version':5,'chapter':2,'checkpoint':'after_final_margin_revision','completed':True,'achievements':['first_crossout'],'behavior':{'final_scenario':'precise'}}))
   save=SaveSystem(path)
   self.assertEqual(save.data['chapter'],3)
   self.assertFalse(save.data['completed'])
   self.assertIn('first_crossout',save.data['achievements'])
   self.assertEqual(save.data['behavior']['final_scenario'],'')

 def test_perfect_dash_returns_one_projectile_and_late_dash_does_not(self):
  from advanced_enemies import PaperProjectile
  with tempfile.TemporaryDirectory() as d:
   game=Game(self.screen,Path(d)/'save.json')
   game.player.x,game.player.y=500,542
   ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
   game.player.start_dash(1)
   shot=PaperProjectile(525,565,-300,0,grace=0,terrain_collision=False)
   shot.update(.001,ctx)
   self.assertEqual(shot.life,0)
   self.assertEqual(len(game.weapons.projectiles),1)
   self.assertGreater(game.weapons.projectiles[0].vx,0)
   self.assertEqual(game.behavior.count('perfect_return'),1)
   another=PaperProjectile(525,565,-300,0,grace=0,terrain_collision=False)
   another.update(.001,ctx)
   self.assertGreater(another.life,0)
   self.assertEqual(len(game.weapons.projectiles),1)
   game.player.return_used=False;game.player.dash_timer=.05
   another.update(.001,ctx)
   self.assertEqual(len(game.weapons.projectiles),1)
   from advanced_enemies import InkOutlaw
   target = InkOutlaw(650,590)
   for _ in range(60):game.weapons.update(1/120,ctx,[target])
   self.assertLess(target.hp,target.max_hp)

 def test_scissor_wall_recovery_keeps_low_shear_and_heavy_hits_pause_agent_burst(self):
  from campaign_enemies import ScissorDirector,RedactionAgent
  with tempfile.TemporaryDirectory() as d:
   game=Game(self.screen,Path(d)/'save.json')
   game.player.x,game.player.y=918,475
   ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
   boss=ScissorDirector(931,590);boss.facing=1;boss._set_state('shear',1)
   boss.update(.016,ctx,(0,1000))
   self.assertEqual(boss.state,'open_hinge')
   self.assertEqual(game.player.health,game.player.max_health)
   agent=RedactionAgent(500,590);agent._set_state('agent_burst',.55)
   agent.aim_target=(900,550)
   agent.hit_from_weapon(1,100,400,{'heavy'},ctx)
   for _ in range(6):agent.update(.016,ctx,(0,1000))
   self.assertEqual(len(agent.projectiles),0)
   for _ in range(10):agent.update(.016,ctx,(0,1000))
   self.assertGreater(len(agent.projectiles),0)

 def test_three_agents_cannot_start_three_simultaneous_bursts(self):
  from campaign_enemies import RedactionAgent
  with tempfile.TemporaryDirectory() as d:
   game=Game(self.screen,Path(d)/'save.json')
   game.player.x,game.player.y=400,542
   ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
   arena=CombatArena(ctx.world,200,1500,'pressure_contract',[])
   arena.encounter_active=True;arena.wave_ids=[0];arena.wave=0
   arena.enemies=[RedactionAgent(650+i*100) for i in range(3)]
   for enemy in arena.enemies:enemy.state_time=0
   arena.update(.016,ctx)
   self.assertEqual(sum(e.state=='agent_aim' for e in arena.enemies),2)
   self.assertEqual(sum(e.state=='idle' for e in arena.enemies),1)
