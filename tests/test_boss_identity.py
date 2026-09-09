"""Playable rules behind the four redesigned boss silhouettes and finale."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import math
import tempfile
import unittest
from pathlib import Path
import pygame
from game import Game
from advanced_enemies import (MoonCompassBoss,WantedSketchBoss,RailroadStaplerBoss,
                              OrbitalMistakeBoss,FinalEditorBoss,PaperProjectile)
from weapons import _live_enemies
from settings import WIDTH,HEIGHT


class BossIdentityContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.game=Game(self.screen,Path(self.temp.name)/"save.json")
        self.game.player.x,self.game.player.y=340,542
        self.ctx=self.game.level.context(self.game.player,self.game.camera,
                                         self.game.particles,self.game.sounds)

    def tearDown(self):
        self.temp.cleanup()

    def test_compass_needle_and_danger_line_stop_at_paper(self):
        boss=MoonCompassBoss(550)
        for i in range(101):
            _,tip=boss._blade_points(math.pi*i/100)
            self.assertLessEqual(tip[1],590.00001)
        self.assertAlmostEqual(boss._blade_points(math.pi/2)[1][1],590)
        boss._set_state("stuck",2.15)
        for _ in range(3):
            boss.invulnerable=0
            boss.hit_from_weapon(9,0,400,{"heavy"},self.ctx)
        self.assertEqual(boss.hp,4,"one pinning accepts two hits, regardless of damage")

    def test_wanted_false_posters_take_real_shots_without_counting_kills(self):
        boss=WantedSketchBoss(600)
        boss._shuffle(self.ctx,(100,1100))
        targets=_live_enemies([boss])
        self.assertEqual(len(targets),3)
        copy=boss.combat_targets[0]
        before=self.game.behavior.count("enemies_defeated")
        self.game.weapons.damage_enemy(copy,1,1,100,.1,"ink",self.ctx)
        self.assertTrue(copy.dead)
        self.assertEqual(self.game.behavior.count("enemies_defeated"),before)
        frozen=boss.shot_target
        self.game.player.x=1000
        boss.update(.01,self.ctx,(100,1100))
        self.assertEqual(boss.shot_target,frozen)
        self.game.weapons.damage_enemy(boss,1,1,0,0,"ink",self.ctx)
        self.assertEqual(boss.state,"poster_escape")
        self.assertEqual(boss.combat_targets,[])

    def test_train_rear_is_a_positional_weakness_and_low_cut_stays_low(self):
        boss=RailroadStaplerBoss(600)
        boss.facing=1;boss._set_state("rail_rush",3)
        self.assertFalse(boss.hit_from_weapon(1,0,800,{"ink"},self.ctx))
        self.assertTrue(boss.hit_from_weapon(1,0,400,{"ink"},self.ctx))
        self.assertEqual(boss.hp,5)
        cut=boss.attack_rect_for_state("rail_rush")
        self.assertEqual(cut.bottom,590)
        self.assertEqual(cut.height,43)
        # A jump over the cowcatcher remains safe as the train brakes.
        boss.x=1017;boss._set_state("rail_rush",1)
        self.game.player.x,self.game.player.y=1000,490
        health=self.game.player.health
        boss.update(.016,self.ctx,(100,1100))
        self.assertEqual(boss.state,"staple_columns_warn")
        self.assertEqual(self.game.player.health,health)

    def test_orbital_armour_leaves_with_real_moons_and_core_lowers(self):
        self.game.player.x,self.game.player.y=1050,100
        boss=OrbitalMistakeBoss(600)
        boss._set_state("moon_release",1.2)
        boss.shot_target=(352,566)
        self.assertFalse(boss.hit_from_weapon(1,0,350,{"eraser"},self.ctx))
        for _ in range(50):boss.update(1/60,self.ctx,(100,1100))
        self.assertEqual(boss.orbiters,[])
        self.assertTrue(boss.vulnerable)
        self.assertEqual(len(boss.projectiles),3)
        for _ in range(80):boss.update(1/60,self.ctx,(100,1100))
        self.assertGreater(boss.y,575,"the core can be reached by the blade")

    def test_final_warning_locks_target_and_weapon_then_opening_clears_damage(self):
        self.game.weapons.active_loadout=None
        for scenario in ("aggressive","avoidant","precise","unreadable"):
            boss=FinalEditorBoss(600)
            boss.scenario=scenario
            self.game.weapons.unlock("eraser_cannon")
            self.game.weapons.select("eraser_cannon")
            boss._start_pattern(self.ctx)
            target=boss.proof_target
            lanes=list(boss.margin_lanes)
            self.game.player.x+=190
            self.game.player.y-=100
            self.game.weapons.select("pencil_blade")
            boss.update(.01,self.ctx,(100,1100))
            self.assertEqual(boss.proof_target,target)
            self.assertEqual(boss.margin_lanes,lanes)
            self.assertEqual(boss.mirror_weapon,"eraser_cannon")
            p=self.game.player
            boss.projectiles=[PaperProjectile(p.center_x,p.rect.centery,0,0,
                                               grace=0,terrain_collision=False)]
            boss._finish_pattern(self.ctx)
            health=p.health
            for _ in range(30):boss.update(1/60,self.ctx,(100,1100))
            self.assertEqual(p.health,health,scenario)
            self.assertTrue(boss.vulnerable)
            self.assertEqual(boss.projectiles,[])
            self.game.player.x,self.game.player.y=340,542
