"""Optional challenge boundaries and new weapon/boss counterplay."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import tempfile
import unittest
import pygame
from game import Game
from chapters import build_chapter
from entities import LostSketch
from page_experiences import SketchTrial
from advanced_enemies import AdvancedEnemy, RedactionDirector
from settings import WIDTH, HEIGHT

class CarbonRevisionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.g=Game(self.screen,Path(self.tmp.name)/'save.json');self.g.reset()
        self.g.player.release_all_locks();self.g.player.draw_amount=1
        self.ctx=self.g.level.context(self.g.player,self.g.camera,self.g.particles,self.g.sounds)
        self.trial=next(e for e in self.g.level.entities.items if isinstance(e,SketchTrial))
    def tearDown(self):self.tmp.cleanup()
    def near(self,t):
        self.g.player.x=t.sketch.x-self.g.player.WIDTH/2
        self.g.player.y=t.sketch.y-self.g.player.HEIGHT
    def test_all_twelve_scraps_require_optional_trials_but_earned_saves_stay_earned(self):
        count=0
        for page in range(5):
            runtime=build_chapter(page)
            scraps=[e for e in runtime.entities.items if isinstance(e,LostSketch)]
            count+=len(scraps)
            for sketch in scraps:
                trial=sketch.trial
                self.assertLess(abs(sum(trial.bounds)/2-sketch.x),350,
                                "the guard must stay near its scrap, not in the next encounter")
            self.assertTrue(all(isinstance(s.trial,SketchTrial) and not s.trial.mandatory for s in scraps))
            restored=build_chapter(page,[s.secret_id for s in scraps])
            self.assertTrue(all(e.completed for e in restored.entities.items if isinstance(e,SketchTrial)))
        self.assertEqual(count,12)
    def test_pressing_collect_starts_a_visible_fight_without_granting_reward(self):
        t=self.trial;self.near(t)
        t.sketch.update(.01,self.ctx,True)
        self.assertFalse(t.sketch.discovered)
        self.assertTrue(t.encounter_active)
        self.assertEqual(t.enemies[0].notebook_reveal,0)
        enemy=t.enemies[0];hp=enemy.hp
        self.g.weapons.damage_enemy(enemy,99,1,0,0,'ink',self.ctx)
        self.assertEqual(enemy.hp,hp)
        for _ in range(60):t.update(1/60,self.ctx)
        self.assertEqual(enemy.notebook_reveal,1)
        enemy.dead=True;t.update(.01,self.ctx)
        self.assertTrue(t.completed)
        self.assertFalse(t.sketch.discovered)
        t.sketch.update(.01,self.ctx,True)
        self.assertTrue(t.sketch.discovered)
        self.assertIn(t.sketch.secret_id,self.g.save.data['secrets'])
    def test_running_away_resets_trial_and_clears_threats(self):
        t=self.trial;self.near(t);self.assertTrue(t.begin(self.ctx))
        self.g.player.x=t.sketch.x+900;t.update(.01,self.ctx)
        self.assertFalse(t.encounter_active);self.assertFalse(t.completed)
        self.assertEqual(t.enemies,[])
        self.near(t);self.assertTrue(t.begin(self.ctx));self.assertEqual(t.wave,0)
    def test_trial_cannot_stack_over_a_mandatory_encounter(self):
        t=self.trial;self.near(t)
        arena=next(e for e in self.g.level.entities.items if getattr(e,'is_combat_arena',False))
        arena.encounter_active=True
        self.assertFalse(t.begin(self.ctx));self.assertEqual(t.enemies,[])
    def test_rifle_unlock_requires_both_archive_opponents_and_survives_save(self):
        self.g.level.load_chapter(3,'start',self.g.player,self.g.camera)
        self.g.player.release_all_locks()
        self.ctx=self.g.level.context(self.g.player,self.g.camera,self.g.particles,self.g.sounds)
        t=next(e for e in self.g.level.entities.items if isinstance(e,SketchTrial))
        self.near(t);self.assertTrue(t.begin(self.ctx))
        self.assertNotIn('carbon_lance',self.g.weapons.unlocked)
        first=t.enemies[0].kind;t.enemies[0].dead=True;t.update(.01,self.ctx)
        self.assertNotEqual(first,t.enemies[0].kind)
        self.assertNotIn('carbon_lance',self.g.weapons.unlocked)
        t.enemies[0].dead=True;t.update(.01,self.ctx)
        self.assertIn('carbon_lance',self.g.weapons.unlocked)
        self.assertIn('carbon_lance',self.g.save.data['weapons'])
    def equip(self,weapon):
        w=self.g.weapons;w.active_loadout=None;w.configure_page(3);w.unlock(weapon);w.select(weapon)
        self.g.player.x,self.g.player.y=300,450
        w.handle_input(fire_pressed=True,aim={'direction':(1,0)},ctx=self.ctx)
        return w
    def test_rifle_has_a_real_one_round_reload_and_recoil(self):
        w=self.equip('carbon_lance')
        self.assertTrue(w.current.reloading);self.assertEqual(w.current.ammo,0)
        self.assertEqual(w.projectiles[0].pierce,3);self.assertLess(self.g.player.vx,-100)
        for _ in range(60):w.update(1/60,self.ctx,[])
        self.assertFalse(w.handle_input(fire_pressed=True,ctx=self.ctx))
        for _ in range(50):w.update(1/60,self.ctx,[])
        self.assertTrue(w.handle_input(fire_pressed=True,ctx=self.ctx))
    def test_returning_fold_can_hit_twice_but_cannot_be_spammed(self):
        w=self.equip('folded_shuriken');shot=w.projectiles[0]
        # Put a durable target in the outward AND return line, off terrain.
        enemy=AdvancedEnemy(445,500);enemy.hp=enemy.max_hp=20
        for _ in range(25):
            enemy.invulnerable=0;shot.update(1/60,self.ctx,[enemy],[],w)
        outward=enemy.hp;self.assertLess(outward,20)
        w.current.cooldown=0
        self.assertFalse(w.handle_input(fire_pressed=True,ctx=self.ctx))
        for _ in range(45):
            enemy.invulnerable=0;shot.update(1/60,self.ctx,[enemy],[],w)
        self.assertLess(enemy.hp,outward)
        self.assertFalse(shot.active)
    def test_director_preview_does_not_fire_early_and_opening_removes_lingering_shots(self):
        boss=RedactionDirector(600);boss.phase=3;boss.facing=-1
        boss._set_state('carbon_warn',.76)
        for _ in range(35):boss.update(1/60,self.ctx,(100,1000))
        self.assertEqual(boss.projectiles,[])
        for _ in range(12):boss.update(1/60,self.ctx,(100,1000))
        self.assertEqual(len(boss.projectiles),3)
        self.assertFalse(boss.vulnerable)
        for _ in range(50):boss.update(1/60,self.ctx,(100,1000))
        self.assertTrue(boss.vulnerable);self.assertEqual(boss.projectiles,[])

if __name__=='__main__':unittest.main()
