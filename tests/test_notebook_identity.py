import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy');os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import tempfile,unittest
import pygame
from game import Game
from input_state import InputFrame
from notebook_agency import NotebookAgency
from advanced_enemies import InkSamurai,MoonCompassBoss,PaperProjectile
from settings import WIDTH,HEIGHT
from save_system import SaveSystem

class NotebookIdentityContracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  pygame.init();cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))
 @classmethod
 def tearDownClass(cls):pygame.quit()
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'save.json'
  self.g=Game(self.screen,self.path);self.g.reset()
  self.g.player.release_all_locks();self.g.player.draw_amount=1
  self.a=next(e for e in self.g.level.entities.items if isinstance(e,NotebookAgency))
  self.ctx=self.g.level.context(self.g.player,self.g.camera,self.g.particles,self.g.sounds)
  self.a._restore(self.ctx)
 def tearDown(self):self.tmp.cleanup()
 def advance(self,n=80):
  for _ in range(n):self.a.update(1/60,self.ctx)
 def test_observed_tool_is_drawn_after_a_fight_and_preserves_current_weapon(self):
  w=self.g.weapons;w.unlock('folded_shuriken');w.select('folded_shuriken')
  self.a.first.completed=True;self.g.player.x=self.a.first.end_x+30
  self.a.update(.01,self.ctx)
  self.assertEqual(self.a.operation,'support_tool')
  self.assertNotIn('pencil_blade',w.unlocked)
  self.advance()
  self.assertIn('pencil_blade',w.available_ids)
  self.assertEqual(w.current_id,'folded_shuriken')
  self.assertFalse(self.a.choose('road',self.ctx))
 def test_legacy_road_save_restores_actual_collision(self):
  self.g.save.data['notebook_choices']['0']='road'
  self.a._restore(self.ctx)
  self.assertTrue(all(p.collision_rects() for p in self.a.platforms))
  self.g.save.write()
  self.g.level.load_chapter(0,'alive',self.g.player,self.g.camera)
  a=next(e for e in self.g.level.entities.items if isinstance(e,NotebookAgency))
  a.update(.01,self.g.level.context(self.g.player,self.g.camera,self.g.particles,self.g.sounds))
  self.assertTrue(all(p.draw_progress==1 for p in a.platforms))
 def test_low_ink_observation_restores_a_heart_without_erasing_a_foe(self):
  arena=self.a.first;arena.encounter_active=True;arena.encounter_time=3
  enemy=InkSamurai(600);arena.enemies=[enemy];self.g.player.health=1
  self.a.update(.01,self.ctx)
  self.assertEqual(self.a.operation,'patch_player')
  self.assertFalse(enemy.dead)
  self.advance()
  self.assertFalse(enemy.dead)
  self.assertEqual(self.g.player.health,2)
  self.assertFalse(hasattr(self.a,'pets'))
  self.assertFalse(arena.completed)
  self.assertIn(arena.arena_id,self.a.used_patches)
 def test_boss_phase_draws_one_additive_landing(self):
  arena=self.a.first;arena.encounter_active=True
  boss=MoonCompassBoss(1800);boss.phase=2;arena.enemies=[boss]
  existing=[p for p in self.g.level.world.platforms if p.draw_progress==1]
  self.a.update(.01,self.ctx)
  self.assertEqual(self.a.operation,'boss_road')
  self.advance();count=len(self.a.platforms)
  self.advance()
  self.assertEqual(len(self.a.platforms),count)
  self.assertTrue(all(p.draw_progress==1 for p in existing))
  self.assertTrue(self.a.platforms[-1].collision_rects())
 def test_unfinished_enemy_cannot_hit_or_be_hit(self):
  arena=self.a.first
  arena._spawn_wave(self.ctx,0)
  enemy=arena.enemies[0];hp=enemy.hp
  self.assertEqual(enemy.notebook_reveal,0)
  self.assertFalse(self.g.weapons.damage_enemy(enemy,99,1,0,0,'pencil',self.ctx))
  self.assertEqual(enemy.hp,hp)
 def test_maul_windup_and_defensive_sweep_use_the_same_window(self):
  w=self.g.weapons;w.unlock('margin_maul');w.select('margin_maul')
  self.g.player.x,self.g.player.y=340,542
  enemy=InkSamurai(420)
  shot=PaperProjectile(410,565,0,0,life=2,gravity=0)
  enemy.projectiles=[shot]
  w.handle_input(fire_pressed=True,aim=(440,565),ctx=self.ctx)
  for _ in range(12):w.update(1/60,self.ctx,[enemy])
  self.assertGreater(shot.life,0);self.assertEqual(enemy.hp,enemy.max_hp)
  for _ in range(12):w.update(1/60,self.ctx,[enemy])
  self.assertEqual(shot.life,0);self.assertLess(enemy.hp,enemy.max_hp)
 def test_page_turn_endpoints_do_not_leave_old_ink(self):
  old=pygame.Surface((WIDTH,HEIGHT));new=old.copy();target=old.copy()
  old.fill((22,33,44));new.fill((200,190,180))
  self.g.renderer.page_turn(target,old,new,0)
  self.assertEqual(target.get_at((500,350)),old.get_at((500,350)))
  self.g.renderer.page_turn(target,old,new,1)
  self.assertEqual(target.get_at((500,350)),new.get_at((500,350)))
 def test_background_doodles_stay_glued_to_world_not_parallax(self):
  n=self.g.renderer.notebook
  self.assertIs(n.tile(0,1),n.tile(0,1))
  self.assertNotEqual(pygame.image.tobytes(n.tile(0,0),'RGBA'),pygame.image.tobytes(n.tile(0,1),'RGBA'))
 def test_scene_keeps_paper_and_actor_visible_across_repeated_draws(self):
  for _ in range(12):
   self.g._draw_scene(self.g.screen)
   paper=[self.g.screen.get_at((x,y)).r for x in range(100,WIDTH,100)
          for y in range(100,500,100)]
   self.assertGreater(sum(c>180 for c in paper),len(paper)*.8)
   feet=self.g.player.rect.bottom
   x=self.g.camera.screen_x(self.g.player.center_x)
   marks=[self.g.screen.get_at((px,py)).r for px in range(x-12,x+13)
          for py in range(feet-55,feet) if 0<=py<HEIGHT]
   self.assertTrue(any(c<100 for c in marks))

 def test_scratch_marks_are_bounded(self):
  p=self.g.particles
  for i in range(100):p.combat_hit(400,500,1,True)
  self.assertLessEqual(len(p.scars),48)
  p.update(20)
  self.assertEqual(p.scars,[])

if __name__=='__main__':unittest.main()
