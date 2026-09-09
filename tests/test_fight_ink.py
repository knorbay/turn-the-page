"""Three-heart encounter rules, death ordering and persistent loadouts."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import tempfile
import unittest
from pathlib import Path
import pygame
from combat import CombatArena
from game import Game
from player import Player
from health_hud import draw_health
from sketches import SKETCHES, derive_modifiers
from settings import WIDTH, HEIGHT


class FightInkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.game = Game(self.screen, Path(self.temp.name)/"save.json")
        self.game.level.director.events.clear()
        self.player = self.game.player
        self.player.x, self.player.y = 420, 542
        self.player.release_all_locks()
        self.ctx = self.game.level.context(self.player, self.game.camera,
                                           self.game.particles, self.game.sounds)

    def tearDown(self):
        self.temp.cleanup()

    def arena(self, specs):
        return CombatArena(self.ctx.world, 400, 1600, "ink_contract", specs)

    def advance_clear(self, arena, until_wave=None):
        for enemy in arena.enemies:
            enemy.dead = True
        for _ in range(80):
            arena.update(1/60, self.ctx)
            if arena.completed or (until_wave is not None and arena.wave == until_wave):
                return
        self.fail("cleared wave did not advance")

    def test_three_marks_refill_at_arena_entry_but_not_clear_or_guard_wave(self):
        self.assertEqual((self.player.health,self.player.max_health),(3,3))
        self.player.health = 1
        arena = self.arena([{"kind":"crawler","wave":0,"x":1350},
                            {"kind":"hopper","wave":1,"x":1350}])
        arena.update(.001,self.ctx)
        self.assertEqual(self.player.health,3)
        self.player.health = 1
        self.advance_clear(arena,1)
        self.assertEqual(self.player.health,1)
        self.advance_clear(arena)
        self.assertEqual(self.player.health,1)
        next_arena = self.arena([{"kind":"crawler","x":1350}])
        next_arena.update(.001,self.ctx)
        self.assertEqual(self.player.health,3)

    def test_named_boss_entry_refills_once_after_its_guard_wave(self):
        arena = self.arena([{"kind":"crawler","wave":0,"x":1350},
                            {"kind":"moon_compass","wave":1,"x":1350}])
        arena.update(.001,self.ctx)
        self.player.health=1
        self.advance_clear(arena,1)
        self.assertTrue(arena.boss_cue_started)
        self.assertEqual(self.player.health,3)
        self.player.health=2
        arena.update(.001,self.ctx)
        self.assertEqual(self.player.health,2)

    def test_lethal_hit_cannot_go_negative_or_be_rescued_by_a_trigger(self):
        self.player.health=1
        self.assertTrue(self.player.hurt(700))
        self.assertEqual(self.player.health,0)
        self.player.invulnerable=0
        self.assertFalse(self.player.hurt(700))
        self.assertFalse(self.player.begin_fight())
        arena = self.arena([{"kind":"crawler","x":1350}])
        arena.update(.001,self.ctx)
        self.assertFalse(arena.encounter_active)
        self.game.level.update(.016,self.player,self.game.camera,
                               self.game.particles,self.game.sounds)
        self.assertGreater(self.game.level.respawn_timer,0)
        for _ in range(110):
            self.game.level.update(.016,self.player,self.game.camera,
                                   self.game.particles,self.game.sounds)
        self.assertEqual(self.player.health,3)
        self.assertNotIn("respawn",self.player.control_locks)

    def test_retry_restores_page_magazines_selected_tool_and_old_sketches(self):
        g=self.game
        g.save.data.update(chapter=1,checkpoint="after_marker_margin_trial",
                           weapons=["pencil_blade","ink_pistol","marker_shotgun"],
                           current_weapon="marker_shotgun",
                           weapon_ammo={"ink_pistol":8,"marker_shotgun":1},
                           secrets=[s.secret_id for s in SKETCHES])
        g.save.write()
        g.continue_game()
        self.assertEqual(g.weapons.current_id,"marker_shotgun")
        self.assertEqual(g.weapons.current.label,"DOUBLE BARREL")
        self.assertEqual(g.weapons.current.ammo,1)
        self.assertEqual(g.weapons.weapons["ink_pistol"].ammo,6)
        for key,value in derive_modifiers(g.save.data["secrets"]).items():
            self.assertEqual(getattr(g.player,key),value)
        g.level.load_chapter(1,"after_marker_margin_trial",g.player,g.camera)
        for key,value in derive_modifiers(g.save.data["secrets"]).items():
            self.assertEqual(getattr(g.player,key),value)
        self.assertEqual(g.player.health,3)

    def test_collection_applies_immediately_and_health_is_visible_outside_fights(self):
        self.game.level.discover_secret("last_homework","unused caption")
        self.assertEqual(self.player.sketch_dash_recovery,.10)
        self.assertIn("REVISION RHYTHM",self.game.level.toast)
        surface=pygame.Surface((WIDTH,HEIGHT))
        surface.fill((0,0,0))
        full=draw_health(surface,self.game.renderer,self.player,0)
        full_pixels=pygame.image.tobytes(surface.subsurface(full),"RGB")
        self.player.health=1
        draw_health(surface,self.game.renderer,self.player,0)
        self.assertNotEqual(full_pixels,pygame.image.tobytes(surface.subsurface(full),"RGB"))
        self.assertFalse(any(getattr(a,"encounter_active",False)
                             for a in self.game.level.entities.items))
