"""Playable empty-hands, temporary tools and material-aware boss damage."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import pygame

from advanced_enemies import (MoonCompassBoss, WantedSketchBoss, RailroadStaplerBoss,
                              OrbitalMistakeBoss, FinalEditorBoss, ScissorDirector)
from boss_effectiveness import BOSS_WEAPON_EFFECTIVENESS, WEAPON_FAMILIES, effectiveness_for
from camera import Camera
from combat import CombatArena, DoodleEnemy
from page_arsenal import PAGE_ENTRY_TOOLS, draw_weapon, loadout_for
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from weapons import WeaponSystem, _live_enemies
from world import PaperWorld


class QualityWeaponTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def context(self, page=0):
        player = Player(100, 542)
        system = WeaponSystem(player)
        system.configure_page(page)
        world = PaperWorld(page=page+1, build_legacy=False)
        ctx = SimpleNamespace(player=player, weapons=system, world=world,
                              particles=ParticleSystem(), camera=Camera(1120),
                              sounds=SimpleNamespace(play=lambda _: None),
                              level=SimpleNamespace(toast="", toast_time=0),
                              game=SimpleNamespace(hit_stop=0))
        return system, ctx

    def test_empty_hands_can_move_aim_switch_reload_and_draw_without_attacking(self):
        system, ctx = self.context()
        self.assertEqual(system.available_ids, ())
        self.assertEqual(system.current_id, "unarmed")
        self.assertEqual(ctx.player.current_weapon, "unarmed")
        self.assertFalse(system.handle_input(fire_pressed=True, fire_held=True,
                                             aim=(600, 500), reload_pressed=True, ctx=ctx))
        self.assertFalse(system.cycle())
        system.update(1/60, ctx, [])
        self.assertEqual(system.attack_serial, 0)
        self.assertFalse(system.projectiles)
        self.assertIsNone(system.melee)
        surface = pygame.Surface((1120, 700), pygame.SRCALPHA)
        draw_weapon(surface, "unarmed", 0, (200, 200))
        self.assertEqual(pygame.mask.from_surface(surface).count(), 0)
        ctx.player.draw(surface, ctx.camera)
        system.draw_world(surface, ctx.camera, PaperRenderer())
        system.draw_hud(surface, PaperRenderer())

    def test_empty_loadout_is_deliberate_and_never_reveals_hidden_owned_tools(self):
        system, ctx = self.context()
        system.unlock("ink_pistol")
        system.select("ink_pistol")
        system.set_page_loadout(())
        self.assertEqual(system.available_ids, ())
        self.assertEqual(system.current_id, "unarmed")
        self.assertFalse(system.select("ink_pistol"))
        system.set_page_loadout(None)
        self.assertEqual(system.current_id, "ink_pistol")
        self.assertEqual(system.unlocked, {"ink_pistol"})

    def test_completed_drawings_can_replace_loadout_without_resetting_a_magazine(self):
        system, ctx = self.context(1)
        system.constrain_page_inventory(loadout_for(1), reset=True)
        self.assertFalse(system.unlocked)
        self.assertTrue(system.lend_drawn_tool("ink_pistol"))
        system.current.ammo = 2
        self.assertTrue(system.lend_drawn_tool("margin_maul", replace=True))
        self.assertEqual(system.unlocked, {"margin_maul"})
        self.assertEqual(system.current_id, "margin_maul")
        self.assertTrue(system.lend_drawn_tool("ink_pistol", replace=True))
        self.assertEqual(system.current.ammo, 2)
        self.assertEqual(system.erase_page_tools(), ["ink_pistol"])
        self.assertEqual(system.current_id, "unarmed")
        self.assertFalse(system.unlocked)

    def test_checkpoint_preserves_empty_inventory_and_old_saved_tool_ids(self):
        system, ctx = self.context(1)
        system.set_page_loadout(())
        restored, other = self.context(1)
        restored.unlock("pencil_blade")
        restored.restore(system.snapshot())
        self.assertEqual(restored.current_id, "unarmed")
        self.assertEqual(restored.unlocked, set())
        self.assertEqual(restored.active_loadout, set())
        restored.set_page_loadout(None)
        restored.restore({"version": 1, "unlocked": ["pencil_blade", "ink_pistol"],
                          "current_id": "ink_pistol", "ammo": {"ink_pistol": 2}})
        self.assertEqual(restored.current_id, "ink_pistol")
        self.assertEqual(restored.current.ammo, 2)
        restored.configure_page(1)
        self.assertEqual(restored.current.ammo, 2)

    def test_page_reload_cannot_reuse_a_buffered_attack_or_an_old_boss_caption(self):
        system, ctx = self.context(1)
        system.lend_drawn_tool("ink_pistol")
        system.current.ammo = 2
        boss = MoonCompassBoss(500)
        boss._set_state("stuck", 2)
        system.damage_enemy(boss, 1, 1, 0, 0, "ink", ctx, weapon_id="ink_pistol")
        system._last_enemies = [boss]
        system.fire_buffer = .12
        system.combo_window = .8
        self.assertTrue(system.boss_feedback)
        system.reset_scene()
        system.update(1/60, ctx, [])
        self.assertFalse(system.handle_input(ctx=ctx))
        self.assertFalse(system.boss_feedback)
        self.assertFalse(system._last_enemies)
        self.assertEqual(system.current_id, "ink_pistol")
        self.assertEqual(system.current.ammo, 2)

    def test_capsule_contact_on_tall_boss_edge_damages_the_exposed_body(self):
        system, ctx = self.context(4)
        ctx.world.add(0, 1120, 590, 15, "capsule_floor")
        ctx.player.x = 360
        boss = FinalEditorBoss(460)
        boss._set_state("proof_window", 5)
        system.lend_drawn_tool("chalk_bomb")
        health = boss.hp
        self.assertTrue(system.handle_input(fire_pressed=True, aim=boss.rect.center, ctx=ctx))
        for _ in range(90):
            system.update(1/60, ctx, [boss])
        self.assertGreater(health-boss.hp, 0)
        self.assertEqual(boss.last_weapon_effectiveness, "normal")

    def test_page_entry_tools_are_drawn_folds_ranged_tools_and_heavy_pencil(self):
        self.assertEqual([PAGE_ENTRY_TOOLS[page] for page in range(5)],
                         ["folded_shuriken", "ink_pistol", "rubber_band", "ink_pistol", "margin_maul"])
        for page in range(5):
            self.assertIn(PAGE_ENTRY_TOOLS[page], loadout_for(page))
            system, ctx = self.context(page)
            system.constrain_page_inventory(loadout_for(page), reset=True)
            self.assertEqual(system.current_id, "unarmed")

    def test_actual_boss_damage_varies_and_never_closes_a_window_by_weapon_type(self):
        system, ctx = self.context()
        for weapon_id, expected in (("folded_shuriken", 1.40), ("ink_pistol", .70), ("pencil_blade", 1)):
            boss = MoonCompassBoss(500)
            boss._set_state("stuck", 2)
            hp = boss.hp
            self.assertTrue(system.damage_enemy(boss, 9, 1, 30, 0, "ink", ctx, weapon_id=weapon_id))
            self.assertAlmostEqual(hp-boss.hp, expected)
            self.assertEqual(boss.window_hits, 1)
            self.assertEqual(boss.last_weapon_effectiveness,
                             "strong" if expected > 1 else "weak" if expected < 1 else "normal")
            boss.invulnerable = 0
            self.assertTrue(system.damage_enemy(boss, 9, 1, 30, 0, "ink", ctx, weapon_id=weapon_id))
            boss.invulnerable = 0
            self.assertFalse(system.damage_enemy(boss, 9, 1, 30, 0, "ink", ctx, weapon_id=weapon_id))
        self.assertTrue(any(mark.kind == "boss_strong" for mark in system.impacts))
        self.assertTrue(any(mark.kind == "boss_weak" for mark in system.impacts))
        self.assertEqual({item["label"] for item in system.boss_feedback}, {"deep mark", "faint mark"})

    def test_projectile_retains_its_drawn_tool_after_switching(self):
        system, ctx = self.context()
        system.lend_drawn_tool("folded_shuriken")
        self.assertTrue(system.handle_input(fire_pressed=True, aim={"direction": (1, 0)}, ctx=ctx))
        shot = system.projectiles[0]
        system.lend_drawn_tool("ink_pistol")
        self.assertEqual(shot.weapon_id, "folded_shuriken")
        boss = MoonCompassBoss(500)
        boss._set_state("stuck", 2)
        hp = boss.hp
        self.assertTrue(system.damage_enemy(boss, shot.damage, 1, shot.knockback, shot.stagger,
                                           shot.kind, ctx, weapon_id=shot.weapon_id))
        self.assertAlmostEqual(hp-boss.hp, 1.40)

    def test_all_six_current_bosses_scale_accepted_strong_and_weak_weapon_hits(self):
        system, ctx = self.context()
        cases = ((MoonCompassBoss, "stuck", "folded_shuriken", "ink_pistol"),
                 (WantedSketchBoss, "unravel", "ink_pistol", "marker_shotgun"),
                 (RailroadStaplerBoss, "reload", "margin_maul", "ink_pistol"),
                 (OrbitalMistakeBoss, "unravel", "eraser_cannon", "pencil_blade"),
                 (FinalEditorBoss, "proof_window", "margin_maul", "rubber_band"),
                 (ScissorDirector, "open_hinge", "ink_pistol", "margin_maul"))
        for constructor, opening, strong_tool, weak_tool in cases:
            for tool in (strong_tool, weak_tool):
                with self.subTest(boss=constructor.__name__, tool=tool):
                    boss = constructor(600)
                    boss._set_state(opening, 2)
                    if hasattr(boss, "orbiters"):
                        boss.orbiters = []
                    hp = boss.hp
                    expected = effectiveness_for(boss, tool).multiplier
                    self.assertTrue(system.damage_enemy(boss, 1, 1, 0, 0, "ink", ctx,
                                                       source_x=100, weapon_id=tool))
                    self.assertAlmostEqual(hp-boss.hp, expected)

    def test_closed_boss_windows_never_emit_a_misleading_weak_or_strong_annotation(self):
        system, ctx = self.context()
        for tool in ("folded_shuriken", "ink_pistol"):
            boss = MoonCompassBoss(500)
            boss._set_state("idle", 1)
            self.assertFalse(system.damage_enemy(boss, 1, 1, 0, 0, "ink", ctx, weapon_id=tool))
            self.assertFalse(system.boss_feedback)
            self.assertFalse(any(mark.kind.startswith("boss_") for mark in system.impacts))
            self.assertFalse(hasattr(boss, "last_weapon_effectiveness"))

    def test_artist_enemy_birth_is_clamped_inside_gates_and_clear_of_existing_actors(self):
        system, ctx = self.context()
        ctx.player.x = 338
        arena = CombatArena(ctx.world, 100, 800, "safe_birth", [
            {"kind": "ruler_guard", "offset": 250, "count": 3, "spacing": 0},
            {"kind": "moon_compass", "x": 2000},
        ])
        arena._spawn_wave(ctx, 0)
        self.assertEqual(len(arena.enemies), 4)
        for index, enemy in enumerate(arena.enemies):
            self.assertFalse(enemy.notebook_spawn_pending)
            self.assertEqual(enemy.notebook_reveal, 0)
            self.assertGreaterEqual(enemy.rect.left, arena.entrance_gate.x2)
            self.assertLessEqual(enemy.rect.right, arena.exit_gate.x1)
            self.assertFalse(enemy.rect.colliderect(ctx.player.rect))
            self.assertFalse(any(enemy.rect.colliderect(other.rect)
                                 for other in arena.enemies[:index]))

    def test_enemy_completion_waits_for_player_to_clear_the_finished_footprint(self):
        system, ctx = self.context()
        arena = CombatArena(ctx.world, 100, 800, "safe_completion", [
            {"kind": "ruler_guard", "offset": 250},
        ])
        arena.encounter_active = True
        arena._spawn_wave(ctx, 0)
        enemy = arena.enemies[0]
        enemy.notebook_reveal = .99
        ctx.player.x = enemy.x-ctx.player.rect.width/2
        arena.update(.02, ctx)
        self.assertEqual(enemy.notebook_reveal, 1)
        self.assertTrue(enemy.notebook_activation_blocked)
        self.assertEqual(enemy.time, 0)
        self.assertEqual(_live_enemies(arena.enemies), [])
        self.assertFalse(system.damage_enemy(enemy, 1, 1, 0, 0, "ink", ctx))
        ctx.player.x = 100
        arena.update(.02, ctx)
        self.assertFalse(enemy.notebook_activation_blocked)
        self.assertGreater(enemy.time, 0)
        self.assertEqual(_live_enemies(arena.enemies), [enemy])

    def test_legacy_boss_uses_same_table_and_erasing_bodies_reject_hits(self):
        system, ctx = self.context()
        boss = DoodleEnemy("boss", 500, boss=True)
        boss.state = "recover"
        hp = boss.hp
        system.damage_enemy(boss, 1, 1, 0, 0, "ink", ctx, weapon_id="ink_pistol")
        self.assertAlmostEqual(hp-boss.hp, .75)
        boss.artist_erasing = True
        self.assertFalse(system.damage_enemy(boss, 1, 1, 0, 0, "eraser", ctx))
        self.assertFalse(boss.hit_from_weapon(1, 0, 100, {"eraser"}, ctx))

    def test_each_relationship_is_positive_and_every_named_boss_has_clear_contrasts(self):
        for kind, family_table in BOSS_WEAPON_EFFECTIVENESS.items():
            self.assertTrue(any(value > 1 for value in family_table.values()), kind)
            self.assertTrue(any(value < 1 for value in family_table.values()), kind)
            for weapon_id in WEAPON_FAMILIES:
                self.assertGreater(effectiveness_for(kind, weapon_id).multiplier, 0)
        self.assertEqual(effectiveness_for("unknown_boss", "ink_pistol").multiplier, 1)

    def test_hud_shows_only_current_tool_and_hides_switch_hint_after_short_interval(self):
        system, ctx = self.context(1)
        system.lend_drawn_tool("ink_pistol")
        system.unlock("margin_maul")
        surface = pygame.Surface((1120, 700))
        renderer = SimpleNamespace(font_small=pygame.font.Font(None, 18),
                                   doodle_text=lambda *args: None)
        with patch.object(system, "draw_icon") as icon:
            system.draw_hud(surface, renderer)
            self.assertEqual([call.args[1] for call in icon.call_args_list], ["ink_pistol"])
        for _ in range(150):
            system.update(1/60, ctx, [])
        self.assertEqual(system.tool_hint_time, 0)


if __name__ == "__main__":
    unittest.main()
