"""Fast contracts for Paper Story's action-combat vertical slice.

These tests deliberately avoid playing the full campaign.  They protect the
small APIs needed by the real game loop: progression starts with one weapon,
weapon state round-trips, dash timing is readable, every authored advanced
enemy can run/render, and counter-play windows cannot be bypassed.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import tempfile
import unittest
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from advanced_enemies import ENEMY_TYPES, create_enemy
from camera import Camera
from combat import CombatArena, DoodleEnemy
from game import Game
from input_state import InputFrame
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from settings import HEIGHT, WIDTH
from weapons import WEAPON_ORDER, WeaponSystem
from world import PaperWorld


EXPECTED_ADVANCED_ENEMIES = {
    "redaction_agent", "scissor_director",
    "ruler_guard",
    "paper_wasp",
    "eraser_brute",
    "crumpled_one",
    "ink_clone",
    "doodle_turret",
    "compass",
    "stapler",
    "failed_sketch",
    "artist_mistake",
    "baby_face_giant",
    "ink_samurai",
    "origami_drone",
    "goblin_scribble",
    "ink_outlaw",
    "tumbleweed_thing",
    "star_scout",
    "moon_bot",
    "lantern_yokai",
    "cactus_gunner",
    "comet_hound",
    "moon_compass",
    "wanted_sketch",
    "railroad_stapler",
    "orbital_mistake",
    "final_editor",
}


class _SilentSounds:
    def __init__(self):
        self.played = []

    def play(self, name):
        self.played.append(name)


class ActionCombatContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        cls.renderer = PaperRenderer()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def make_context(self, player=None, width=1000):
        player = player or Player(250, 542)
        world = PaperWorld(page=1, build_legacy=False)
        world.width = width
        world.add(0, width, 590, 18, "action_test_floor", 991)
        level = SimpleNamespace(world=world, toast="", toast_time=0.0,
                                chapter_index=2)
        return SimpleNamespace(
            player=player,
            world=world,
            level=level,
            particles=ParticleSystem(),
            sounds=_SilentSounds(),
            camera=Camera(WIDTH),
            game=SimpleNamespace(hit_stop=0.0),
        )

    def test_new_game_starts_with_only_the_pencil_blade(self):
        with tempfile.TemporaryDirectory() as directory:
            save_path = os.path.join(directory, "action-save.json")
            game = Game(self.screen, save_path)
            game.save.update_combat(WEAPON_ORDER, "rubber_band", game.weapons.ammo)
            game.reset(new_game=True)

            self.assertEqual(game.weapons.unlocked, {"pencil_blade"})
            self.assertEqual(game.weapons.current_id, "pencil_blade")
            self.assertEqual(game.save.data["weapons"], ["pencil_blade"])
            self.assertEqual(game.save.data["current_weapon"], "pencil_blade")

    def test_weapon_unlock_select_and_snapshot_restore(self):
        player = Player()
        weapons = WeaponSystem(player)
        self.assertEqual(weapons.unlocked, {"pencil_blade"})
        self.assertFalse(weapons.select("ink_pistol"))

        for weapon_id in WEAPON_ORDER[1:]:
            self.assertTrue(weapons.unlock(weapon_id))
        self.assertFalse(weapons.unlock("ink_pistol"), "unlock must be idempotent")
        self.assertTrue(weapons.select("marker"))
        weapons.weapons["ink_pistol"].ammo = 3
        weapons.weapons["ink_pistol"].reserve = 17
        snapshot = weapons.snapshot()

        restored = WeaponSystem(Player())
        self.assertTrue(restored.restore(snapshot))
        self.assertEqual(restored.unlocked, set(WEAPON_ORDER))
        self.assertEqual(restored.current_id, "marker_shotgun")
        self.assertEqual(restored.weapons["ink_pistol"].ammo, 3)
        self.assertEqual(restored.weapons["ink_pistol"].reserve, 17)

    def test_only_automatic_weapons_repeat_from_a_held_trigger(self):
        context = self.make_context()
        weapons = WeaponSystem(context.player)
        context.weapons = weapons

        self.assertTrue(weapons.handle_input(
            fire_pressed=True, fire_held=True, aim=(600, 550), ctx=context,
        ))
        for _ in range(30):
            weapons.handle_input(
                fire_pressed=False, fire_held=True, aim=(600, 550), ctx=context,
            )
            weapons.update(1 / 60, context, [])
        self.assertEqual(weapons.attack_serial, 1, "blade hold must not auto-combo")

        weapons.unlock("ink_pistol")
        self.assertTrue(weapons.select("ink_pistol"))
        for _ in range(30):
            weapons.handle_input(
                fire_pressed=False, fire_held=True, aim=(600, 550), ctx=context,
            )
            weapons.update(1 / 60, context, [])
        self.assertGreaterEqual(weapons.attack_serial, 3, "pistol hold should repeat")

    def test_weapon_recovery_delays_prevent_aggressive_fire_spam(self):
        weapons = WeaponSystem(Player())
        expected_minimums = {
            "pencil_blade": .34, "ink_pistol": .30,
            "marker_shotgun": 1.0, "eraser_cannon": 1.3,
            "rubber_band": .65, "excalibur": .80,
        }
        for weapon_id, minimum in expected_minimums.items():
            self.assertGreaterEqual(weapons.weapons[weapon_id].fire_delay, minimum)

    def test_hit_stop_buffers_a_tapped_jump(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, os.path.join(directory, "buffer-save.json"))
            game.reset(new_game=True)
            game.player.x = 220
            game.player.y = 542
            game.player.on_ground = True
            game.hit_stop = .01

            game.update(1 / 60, InputFrame(jump_pressed=True))
            self.assertEqual(game.player.vy, 0)
            game.update(1 / 60, InputFrame())

            self.assertLess(game.player.vy, 0, "jump tapped during hit-stop must replay")

    def test_advanced_hits_produce_scaled_hit_stop_and_directional_feedback(self):
        context = self.make_context()
        enemy = create_enemy("ruler_guard", 500, 590, 51)
        enemy.facing = 1

        self.assertTrue(enemy.hit_from_weapon(
            2, 240, 450, {"marker", "heavy", "attack:7"}, context,
        ))

        self.assertGreaterEqual(context.game.hit_stop, .05)
        self.assertIn("heavy_hit", context.sounds.played)
        self.assertTrue(any(p.kind == "slash" for p in context.particles.items))
        self.assertGreater(enemy.hit_stun, 0)

    def test_marker_volley_can_land_three_hits_without_fake_block_clangs(self):
        context = self.make_context(Player(330, 542))
        weapons = WeaponSystem(context.player)
        context.weapons = weapons
        enemy = create_enemy("doodle_turret", 475, 590, 52)
        weapons.unlock("marker_shotgun")
        weapons.select("marker_shotgun")

        self.assertTrue(weapons.handle_input(
            fire_pressed=True, aim=enemy.rect.center, ctx=context,
        ))
        for _ in range(24):
            weapons.update(1 / 60, context, [enemy])

        self.assertTrue(enemy.dead)
        self.assertEqual(enemy.hp, 0)
        self.assertNotIn("paper_step", context.sounds.played)

    def test_marker_volley_only_deals_one_damage_to_a_real_boss(self):
        context = self.make_context(Player(330, 542))
        weapons = WeaponSystem(context.player)
        context.weapons = weapons
        boss = create_enemy("final_editor", 500, 590, 521)
        boss.state = "proof_window"
        boss.window_hits = 0
        start_hp = boss.hp

        self.assertTrue(weapons.damage_enemy(
            boss, .62, 1, 145, .08, "marker", context, attack_id=77,
        ))
        boss.invulnerable = 0
        self.assertFalse(weapons.damage_enemy(
            boss, .62, 1, 145, .08, "marker", context, attack_id=77,
        ))
        self.assertEqual(boss.hp, start_hp - 1)

    def test_rubber_band_has_exactly_two_softening_ricochets(self):
        context = self.make_context()
        weapons = WeaponSystem(context.player)
        context.weapons = weapons
        weapons.unlock("rubber_band")
        weapons.select("rubber_band")
        self.assertTrue(weapons.handle_input(
            fire_pressed=True, aim=(700, 520), ctx=context,
        ))
        projectile = weapons.projectiles[-1]
        start_damage = projectile.damage
        self.assertEqual(projectile.bounces, 2)
        projectile._ricochet(projectile.rect, projectile.x, projectile.y,
                              context, weapons)
        self.assertEqual(projectile.bounces, 1)
        self.assertLess(projectile.damage, start_damage)

    def test_blade_mouse_aim_stays_readable_and_does_not_auto_lunge_at_air(self):
        context = self.make_context()
        weapons = WeaponSystem(context.player)
        context.weapons = weapons
        weapons._last_enemies = []
        weapons.handle_input(fire_pressed=True,
                             aim=(context.player.center_x, 50), ctx=context)
        self.assertGreater(abs(weapons.aim_direction.x), .7)
        self.assertLess(abs(weapons.aim_direction.y), .65)
        self.assertEqual(context.player.vx, 0)

    def test_real_weapon_attacks_advance_the_ink_clone_signal(self):
        context = self.make_context()
        weapons = WeaponSystem(context.player)
        context.weapons = weapons
        clone = create_enemy("ink_clone", 620, 590, 53)
        context.player.invulnerable = 999

        for _ in range(40):
            clone.update(1 / 60, context, (100, 900))
        self.assertEqual(clone.echo_attack_serial, 0)

        self.assertTrue(weapons.handle_input(
            fire_pressed=True, aim=(700, 550), ctx=context,
        ))
        self.assertEqual(weapons.attack_serial, 1)
        self.assertEqual(context.player.attack_serial, 1)
        for _ in range(40):
            clone.update(1 / 60, context, (100, 900))
        self.assertEqual(clone.echo_attack_serial, 1)

    def test_dash_grants_iframes_and_obeys_cooldown(self):
        player = Player(120, 500)
        context = self.make_context(player)

        self.assertTrue(player.start_dash(1, context.particles))
        self.assertTrue(player.dashing)
        self.assertFalse(player.hurt(player.center_x + 20))
        self.assertEqual(player.health, player.max_health)
        self.assertFalse(player.start_dash(-1, context.particles))

        # The dash itself ends quickly, while the longer cooldown remains.
        for _ in range(3):
            player.update(.07, 0, context.world, context.particles)
        self.assertFalse(player.dashing)
        self.assertFalse(player.dash_ready)
        self.assertTrue(player.hurt(player.center_x + 20))

        for _ in range(7):
            player.update(.07, 0, context.world, context.particles)
        self.assertTrue(player.dash_ready)
        self.assertTrue(player.start_dash(-1, context.particles))
        self.assertLess(player.vx, 0)

    def test_all_advanced_enemy_types_update_and_draw(self):
        self.assertEqual(set(ENEMY_TYPES), EXPECTED_ADVANCED_ENEMIES)
        surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

        for index, kind in enumerate(sorted(ENEMY_TYPES)):
            with self.subTest(kind=kind):
                context = self.make_context()
                context.player.invulnerable = 999
                enemy = create_enemy(kind, 500, 590, 100 + index)
                self.assertEqual(enemy.kind, kind)
                self.assertFalse(enemy.dead)
                enemy.update(1 / 60, context, (100, 900))
                enemy.draw(surface, context.camera, self.renderer)
                self.assertGreater(enemy.hp, 0)
                self.assertIsInstance(enemy.rect, pygame.Rect)

        self.assertGreater(surface.get_bounding_rect().width, 0)

    def test_final_editor_has_four_behavior_driven_scenarios(self):
        labels = {}
        scripts = {}
        for tendency in ("aggressive", "avoidant", "precise", "unreadable"):
            context = self.make_context()
            context.game.behavior = SimpleNamespace(
                broad_tendency=lambda value=tendency: value,
                record=lambda *args, **kwargs: None,
            )
            enemy = create_enemy("final_editor", 500, 590, 711)
            enemy.update(1 / 60, context, (100, 900))
            labels[tendency] = enemy.SCENARIO_LABELS[enemy.scenario]
            scripts[tendency] = enemy._scenario_patterns()
        self.assertEqual(len(set(labels.values())), 4)
        self.assertEqual(len(set(scripts.values())), 4)

    def test_every_enemy_can_threaten_a_stationary_player_at_both_arena_edges(self):
        """No entrance or exit corner may become a permanent AI safe pocket."""
        width = 1600
        legacy = ("crawler", "hopper", "spitter", "boss")
        kinds = tuple(sorted(ENEMY_TYPES)) + legacy
        # CombatArena's entrance stroke is -80..-55 relative to start; the
        # exit stroke begins at width-22. These positions model the real two
        # corners, not merely the enemy-centre bounds.
        for side, player_x in (("left", -55), ("right", width - 46)):
            for index, kind in enumerate(kinds):
                with self.subTest(side=side, kind=kind):
                    player = Player(player_x, 542)
                    player.on_ground = True
                    context = self.make_context(player, width)
                    if kind in legacy:
                        enemy = DoodleEnemy(
                            kind, width / 2, 590, 800 + index,
                            boss=kind == "boss",
                        )
                    else:
                        enemy = create_enemy(kind, width / 2, 590, 800 + index)

                    arena = CombatArena(
                        context.world, 0, width,
                        f"corner_contract_{side}_{kind}", [],
                    )
                    arena.encounter_active = True
                    arena.wave = 0
                    arena.wave_ids = [0]
                    arena.enemies = [enemy]
                    arena.entrance_gate.enabled = True

                    for _ in range(60 * 8):
                        arena.update(1 / 60, context)
                        if player.health < player.max_health:
                            break

                    self.assertLess(
                        player.health, player.max_health,
                        f"{kind} cannot threaten the stationary {side} edge",
                    )

    def test_directional_armor_and_recovery_vulnerabilities(self):
        context = self.make_context()

        guard = create_enemy("ruler_guard", 500, 590, 31)
        guard.facing = 1
        self.assertFalse(guard.hit_from_weapon(1, 100, 550, {"pencil"}, context))
        self.assertEqual(guard.hp, guard.max_hp)
        self.assertTrue(guard.hit_from_weapon(1, 100, 450, {"pencil"}, context))
        self.assertEqual(guard.hp, guard.max_hp - 1)

        brute = create_enemy("eraser_brute", 500, 590, 32)
        self.assertFalse(brute.hit_from_weapon(1, 100, 450, {"pencil"}, context))
        brute.state = "recover"
        self.assertTrue(brute.hit_from_weapon(1, 100, 450, {"pencil"}, context))

        crumpled = create_enemy("crumpled_one", 500, 590, 33)
        crumpled.state = "charge"
        self.assertFalse(crumpled.hit_from_weapon(1, 100, 450, {"marker"}, context))
        crumpled.state = "stunned"
        self.assertTrue(crumpled.hit_from_weapon(1, 100, 450, {"marker"}, context))

    def test_eraser_weapon_breaks_generic_armor(self):
        context = self.make_context()
        weapons = WeaponSystem(context.player)
        enemy = SimpleNamespace(
            rect=pygame.Rect(480, 530, 40, 60),
            x=500.0,
            hp=4,
            dead=False,
            active=True,
            armor=2,
            armored=True,
            vx=0.0,
            hit_flash=0.0,
        )

        self.assertFalse(weapons.damage_enemy(
            enemy, 1, 1, 100, .1, "ink", context,
        ))
        self.assertEqual(enemy.hp, 4)
        self.assertEqual(enemy.armor, 2)

        self.assertTrue(weapons.damage_enemy(
            enemy, 2, 1, 100, .7, "eraser", context,
        ))
        self.assertEqual(enemy.hp, 2)
        self.assertEqual(enemy.armor, 0)
        self.assertFalse(enemy.armored)

    def test_miniboss_and_major_boss_only_take_windowed_damage(self):
        context = self.make_context()
        context.player.health = 1

        compass = create_enemy("compass", 500, 590, 41)
        self.assertFalse(compass.hit_from_weapon(1, 80, 450, {"pencil"}, context))
        compass.state = "stuck"
        for expected_hits in (1, 2):
            compass.invulnerable = 0
            self.assertTrue(compass.hit_from_weapon(1, 80, 450, {"pencil"}, context))
            self.assertEqual(compass.window_hits, expected_hits)
        compass.invulnerable = 0
        self.assertFalse(compass.hit_from_weapon(1, 80, 450, {"pencil"}, context))

        boss = create_enemy("artist_mistake", 500, 590, 42)
        self.assertFalse(boss.hit_from_weapon(1, 100, 450, {"eraser"}, context))
        boss.state = "unravel"
        boss.hp = 11
        boss.invulnerable = 0
        self.assertTrue(boss.hit_from_weapon(1, 100, 450, {"eraser"}, context))
        self.assertEqual(boss.phase, 2)
        self.assertEqual(boss.state, "phase_shift")
        self.assertEqual(context.player.health, 1, "a boss phase change is the same fight")

        boss.invulnerable = 0
        self.assertFalse(boss.hit_from_weapon(1, 100, 450, {"eraser"}, context))
        boss.state = "unravel"
        boss.window_hits = 0
        boss.hp = 6
        boss.invulnerable = 0
        self.assertTrue(boss.hit_from_weapon(1, 100, 450, {"eraser"}, context))
        self.assertEqual(boss.phase, 3)

    def test_action_campaign_catalog_contract(self):
        if importlib.util.find_spec("action_content") is None:
            self.skipTest("action_content.py has not landed yet")

        action_content = importlib.import_module("action_content")
        self.assertTrue(callable(action_content.expand_action_chapter))
        encounter_ids = action_content.ACTION_ENCOUNTER_IDS
        pickup_catalog = action_content.WEAPON_PICKUPS

        encounter_values = list(encounter_ids.keys()) if isinstance(encounter_ids, dict) else list(encounter_ids)
        self.assertGreaterEqual(len(set(encounter_values)), 10)
        encounter_text = " ".join(str(value) for value in encounter_values).lower()
        for required in ("bamboo_static", "midnight_train", "orbital_debris", "zero_garden"):
            self.assertIn(required, encounter_text)

        pickup_values = list(pickup_catalog.items()) if isinstance(pickup_catalog, dict) else list(pickup_catalog)
        self.assertGreaterEqual(len(pickup_values), 4)
        pickup_text = repr(pickup_values).lower()
        for required in WEAPON_ORDER[1:]:
            self.assertIn(required, pickup_text)


if __name__ == "__main__":
    unittest.main()
