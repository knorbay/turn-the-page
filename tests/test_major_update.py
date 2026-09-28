"""Living Margins regression contracts, exercised through shipping systems."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import tempfile
from pathlib import Path
import unittest
import pygame
from game import Game
from input_state import InputFrame
from chapters import build_chapter
from advanced_enemies import AdvancedEnemy, FinalEditorBoss, FoldDuelist, MarginSniper, SplitLantern, InkClone
from major_update import PracticeDrawing
from weapons import PaperProjectile
from settings import WIDTH, HEIGHT

class LivingMarginsContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))
    @classmethod
    def tearDownClass(cls): pygame.quit()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.g=Game(self.screen,Path(self.temp.name)/'save.json')
        self.ctx=self.g.level.context(self.g.player,self.g.camera,self.g.particles,self.g.sounds)
        self.g.player.draw_amount=1
        self.g.player.x,self.g.player.y=340,542
    def tearDown(self): self.temp.cleanup()
    def test_fractional_damage_is_not_rounded_up(self):
        e=AdvancedEnemy(600)
        for _ in range(3):
            e.invulnerable=0
            self.assertTrue(e.hit_from_weapon(.5,0,300,{'ink'},self.ctx))
        self.assertAlmostEqual(e.hp,e.max_hp-1.5)
    def test_final_editor_counts_openings_even_for_heroic_sword(self):
        e=FinalEditorBoss(650)
        e._set_state('proof_window',2)
        for _ in range(2):
            e.invulnerable=0
            self.assertTrue(e.hit_from_weapon(999,0,300,{'heroic'},self.ctx))
        e.invulnerable=0
        self.assertFalse(e.hit_from_weapon(999,0,300,{'heroic'},self.ctx))
        self.assertEqual(e.hp,e.max_hp-2)
    def test_every_encounter_has_unique_supported_retry(self):
        for page in range(5):
            runtime=build_chapter(page)
            ids=[cp.checkpoint_id for cp in runtime.checkpoints]
            self.assertEqual(len(ids),len(set(ids)))
            for arena in runtime.entities.items:
                if not getattr(arena,'is_combat_arena',False):continue
                cp=next(cp for cp in runtime.checkpoints if cp.checkpoint_id=='before_'+arena.arena_id)
                self.assertLess(cp.x,arena.start_x)
                self.assertTrue(any(p.collidable and p.x1 <= cp.x+12 <= p.x2 and abs(p.y-590)<2
                                    for p in runtime.world.platforms))
    def test_opening_gives_control_before_three_seconds(self):
        self.g.reset()
        for _ in range(180):self.g.update(1/60,InputFrame())
        self.assertFalse(self.g.player.locked)
        self.assertEqual(self.g.player.draw_amount,1)
    def test_practice_target_uses_real_weapon_hits(self):
        target=next(e for e in self.g.level.entities.items if isinstance(e,PracticeDrawing))
        for _ in range(2):
            target.target.invulnerable=0
            self.assertTrue(self.g.weapons.damage_enemy(target.target,1,1,0,0,'pencil',self.ctx))
        target.update(.01,self.ctx)
        self.assertTrue(target.completed)
        self.assertEqual(self.g.behavior.count('practice_complete'),1)
        target.update(.01,self.ctx)
        self.assertEqual(self.g.behavior.count('practice_complete'),1)
    def test_artist_reply_is_optional_and_persistent_once(self):
        a=self.g.artist_companion
        a.page=0
        a.say('test','Can you hear me?','A small nod.')
        a.update(.01,self.g,InputFrame(interact=True))
        a.update(.01,self.g,InputFrame(interact=True))
        self.assertEqual(self.g.behavior.count('artist_reply'),1)
        self.assertEqual(a.text,'A small nod.')
        self.assertFalse(self.g.player.locked)
    def test_sniper_freezes_target_before_shot(self):
        e=MarginSniper(700);e.state_time=0
        e.update(.01,self.ctx,(100,1000))
        target=e.aim_target
        self.g.player.x=900
        for _ in range(60):e.update(.01,self.ctx,(100,1000))
        self.assertEqual(e.aim_target,target)
        self.assertEqual(e.state,'agent_aim')
    def test_duelist_has_second_warning_before_echo(self):
        e=FoldDuelist(600);e.facing=-1;e._set_state('draw_cut',0)
        e.update(.01,self.ctx,(100,1000))
        self.assertEqual(e.state,'echo_telegraph')
        self.assertGreater(e.state_time,.4)
        facing=e.facing;self.g.player.x=900
        for _ in range(50):e.update(.01,self.ctx,(100,1000))
        self.assertEqual(e.state,'echo_slash')
        self.assertEqual(e.facing,facing)
    def test_split_lantern_marks_two_exact_columns(self):
        e=SplitLantern(700);e.state_time=0
        e.update(.01,self.ctx,(100,1000))
        target=e.target_x
        self.g.player.x=900
        e._drop_column(self.ctx)
        self.assertEqual([p.x for p in e.projectiles],[target-92,target+92])
        self.assertGreater(abs(e.projectiles[1].x-e.projectiles[0].x),100)
    def test_only_launch_platform_is_ignored(self):
        player=self.g.player;player.x=350;player.y=452
        own=pygame.Rect(300,500,180,19);other=pygame.Rect(300,545,180,19)
        shot=PaperProjectile('ink',365,470,0,400,.85,3,2,0)
        for _ in range(16):shot.update(.01,self.ctx,[],[own,other],self.g.weapons)
        self.assertTrue(shot.active)
        self.assertEqual(shot.launch_support,tuple(own))
        player.x=800
        for _ in range(12):shot.update(.01,self.ctx,[],[own,other],self.g.weapons)
        self.assertFalse(shot.active)
    def test_clone_finishes_committed_cut_despite_fresh_attack_memory(self):
        e=InkClone(600)
        e.echo_attack_serial=1
        e.memory.append((0,0,1,2,False))
        e._set_state('echo_slash',.08)
        e.update(.05,self.ctx,(100,1000))
        self.assertEqual(e.state,'echo_slash')
        self.assertLess(e.state_time,.04)
        e.update(.05,self.ctx,(100,1000))
        self.assertNotEqual(e.state,'echo_telegraph')

    def test_drop_through_keeps_the_main_floor_solid(self):
        p=self.g.player
        self.g.level.world.add(300,500,500,10,'drop_test',987)
        p.x,p.y,p.on_ground=350,452,True
        self.assertTrue(p.drop_through(self.g.level.world))
        for _ in range(60):p.update(1/60,0,self.g.level.world,self.g.particles)
        self.assertEqual(p.rect.bottom,590)
        self.assertTrue(p.on_ground)
        self.assertFalse(p.drop_through(self.g.level.world))

    def test_achievement_pages_wrap_without_hiding_entries(self):
        self.g.state='achievements'
        self.g._turn_achievement_page(1)
        self.assertEqual(self.g.achievement_page,1)
        self.g.draw()
        self.g._key_down(pygame.K_RIGHT)
        self.assertEqual(self.g.achievement_page,0)
        self.g.draw()

if __name__=='__main__':unittest.main()
