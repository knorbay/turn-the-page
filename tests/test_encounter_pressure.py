"""New warnings share space; committed attacks and pursuit keep advancing."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import unittest
from types import SimpleNamespace
from advanced_enemies import (RedactionAgent, RulerGuard, PaperWasp,
                              EraserBrute, MoonCompassBoss, PaperProjectile, InkClone)
from combat import CombatArena, DoodleEnemy
from player import Player
from world import PaperWorld


class EncounterPressureContracts(unittest.TestCase):
    def setUp(self):
        self.world = PaperWorld(page=1, build_legacy=False)
        self.floor = self.world.add(0, 1500, 590, 18, "pressure_floor", 18)
        self.player = Player(390, 542)
        self.ctx = SimpleNamespace(player=self.player)
        self.arena = CombatArena(self.world, 100, 1400, "pressure", [])

    def prepare(self, *enemies):
        self.arena.enemies = list(enemies)
        for enemy in enemies:
            enemy.state = "idle"
            enemy.state_time = 0
        self.arena._coordinate_pressure(self.ctx, .016)

    def advance(self, seconds=.25):
        # Real frames keep actively requesting peers in the queue.
        for _ in range(round(seconds / .01)):
            self.arena._coordinate_pressure(self.ctx, .01)

    def test_compatible_attacks_start_apart_and_third_source_waits(self):
        gun, guard, wasp = RedactionAgent(680), RulerGuard(500), PaperWasp(750)
        self.prepare(gun, guard, wasp)
        self.assertTrue(gun._set_state("agent_aim", .95))
        self.assertFalse(guard._set_state("brace", .52))
        self.advance()
        self.assertTrue(guard._set_state("brace", .52))
        self.advance()
        self.assertFalse(wasp._set_state("dive_telegraph", .65))
        self.assertEqual(wasp.state, "idle")
        # An already announced attack is never paused by the scheduler.
        self.assertTrue(gun._set_state("agent_burst", .55))
        self.assertTrue(guard._set_state("thrust", .32))

    def test_waiting_peer_precedes_the_previous_attacker(self):
        first, second = RedactionAgent(650), RedactionAgent(800)
        self.prepare(first, second)
        self.assertTrue(first._set_state("agent_aim", .95))
        for _ in range(40):
            self.arena._coordinate_pressure(self.ctx, .016)
            self.assertFalse(second._set_state("agent_aim", .95))
        first._set_state("idle", 0)
        self.assertFalse(first._set_state("agent_aim", .95))
        self.assertTrue(second._set_state("agent_aim", .95))

    def test_nearby_volley_counts_once_and_releases_after_passing(self):
        gun, guard, area = RedactionAgent(650), RulerGuard(500), EraserBrute(900)
        self.prepare(gun, guard, area)
        gun.state = "reload"
        gun.projectiles = [PaperProjectile(700, 560, -500, 0) for _ in range(3)]
        self.assertEqual(self.arena._pressure_load(), ["ranged"])
        self.assertFalse(area._set_state("slam_telegraph", .8))
        self.assertTrue(guard._set_state("brace", .52))
        guard._set_state("idle", 0)
        for shot in gun.projectiles:
            shot.x = 60
        self.advance()
        self.assertEqual(self.arena._pressure_load(), [])
        self.assertTrue(area._set_state("slam_telegraph", .8))

    def test_erased_floor_keeps_area_pressure_until_it_is_restored(self):
        area, gun = EraserBrute(650), RedactionAgent(850)
        self.prepare(area, gun)
        area.state = "recover"
        area._temporary_erases = [{"time": 1, "platform": self.floor,
                                   "before": [], "after": [(330, 460)]}]
        self.assertFalse(gun._set_state("agent_aim", .95))
        area._temporary_erases[0]["time"] = 0
        self.assertTrue(gun._set_state("agent_aim", .95))

    def test_stale_dead_and_stunned_requests_do_not_block_the_queue(self):
        gun, waiting, guard = RedactionAgent(700), RedactionAgent(800), RulerGuard(500)
        self.prepare(gun, waiting, guard)
        gun._set_state("agent_aim", .95)
        waiting._set_state("agent_aim", .95)
        waiting.dead = True
        self.advance()
        self.assertNotIn(waiting, self.arena._pressure_queue)
        self.assertTrue(guard._set_state("brace", .52))
        guard._set_state("idle", 0)
        guard._set_state("brace", .52)
        guard.hit_stun = .3
        self.arena._coordinate_pressure(self.ctx, .016)
        self.assertNotIn(guard, self.arena._pressure_queue)
        guard.hit_stun = 0
        guard._set_state("brace", .52)
        self.advance()
        self.assertNotIn(guard, self.arena._pressure_queue)

    def test_legacy_doodles_share_admission_and_boss_scripts_bypass_it(self):
        gun, crawler, boss = RedactionAgent(700), DoodleEnemy("crawler", 450), MoonCompassBoss(900)
        self.prepare(gun, crawler, boss)
        gun._set_state("agent_aim", .95)
        crawler._start_telegraph(.38)
        self.assertEqual(crawler.state, "idle")
        self.advance()
        crawler._start_telegraph(.38)
        self.assertEqual(crawler.state, "telegraph")
        self.assertTrue(boss._set_state("sweep_telegraph", .94))

    def test_clone_retries_its_close_attack_after_a_delayed_warning(self):
        gun, clone = RedactionAgent(700), InkClone(430)
        self.prepare(gun, clone)
        clone.pressure_timer = 0
        gun._set_state("agent_aim", .95)
        clone._think(.016, self.ctx, (100, 1400))
        self.assertEqual(clone.state, "copy")
        self.assertEqual(clone.pressure_timer, 0)
        self.advance()
        clone._think(.016, self.ctx, (100, 1400))
        self.assertEqual(clone.state, "echo_telegraph")
