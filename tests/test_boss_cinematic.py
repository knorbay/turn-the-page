"""Real encounters share a protected, localized drawing and camera return."""
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import pygame
from advanced_enemies import PaperProjectile, _health_scratches
from combat import CombatArena
from game import Game
from input_state import InputFrame
from localization import CATALOGS, SUPPORTED_LANGUAGES, set_language, translate
from major_campaign import SecretPocket
from optional_encounters import OptionalGuardianPocket
from page_arsenal import PAGE_ENTRY_TOOLS
from particles import ParticleSystem
from player import Player
from scene_music import BOSS_PROFILES


def spawn_encounter(game, kind):
    """Use the authored room's spawn contract after completing prior rooms."""
    page = BOSS_PROFILES[kind]["page"]
    game.boss_cinematic.cancel()
    game.level.load_chapter(page, "start", game.player, game.camera)
    game._attach_runtime()
    game.state = "playing"
    game.transition_active = False
    game.player.release_all_locks()
    game.player.draw_amount = 1
    game.player.on_ground = True
    game.player.health = game.player.max_health
    game.player.invulnerable = 0
    game.player.vx = game.player.vy = 0
    game.particles = ParticleSystem()
    game.weapons.unlock(PAGE_ENTRY_TOOLS[page])
    game.weapons.select(PAGE_ENTRY_TOOLS[page])
    game.weapons.tool_hint_time = 0
    game.level.page_title_time = game.level.toast_time = 0
    game.level.director.tool.visible = False
    game.level.director.canvas_owner = None
    # A player reaches these rooms after the first lesson has opened combat.
    lesson = getattr(game.level.runtime, "training", None)
    if lesson is not None:
        lesson.completed = True
        lesson.gate.enabled = lesson.target_gate.enabled = lesson.dodge_gate.enabled = False
    for platform in game.level.world.platforms:
        platform.complete_drawing()
    for entity in game.level.entities.items:
        if isinstance(entity, CombatArena):
            entity.completed = True
            entity.entrance_gate.enabled = entity.exit_gate.enabled = False
    if kind == "cloud_kite":
        room = next(e for e in game.level.entities.items if isinstance(e, SecretPocket) and e.kind == "cloud")
    elif kind in ("brass_tumbleweed", "orbit_crab", "carbon_hound", "draft_moth"):
        room = next(e for e in game.level.entities.items if isinstance(e, OptionalGuardianPocket) and e.kind == kind)
    else:
        room = next(e for e in game.level.entities.items if isinstance(e, CombatArena)
                    and any(spec["kind"] == kind for spec in e.enemy_specs))
    ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
    if isinstance(room, CombatArena):
        room.completed = False
        room.encounter_active = True
        room.wave = next(int(spec.get("wave", 0)) for spec in room.enemy_specs if spec["kind"] == kind)
        game.player.x = room.start_x+50
        game.player.y = 590-Player.HEIGHT
        room._spawn_wave(ctx, room.wave)
    else:
        room.entrance_open = room.entered = True
        room.entrance_progress = 1
        for platform in room.steps:
            platform.enabled = True
            platform.complete_drawing()
        game.player.x = room.bounds[0]+35
        game.player.y = room.ground-Player.HEIGHT
        started = room._begin_duel(ctx) if kind == "cloud_kite" else room.begin(ctx)
        if not started:
            raise AssertionError("Authored pocket could not begin: "+kind)
    boss = next(e for e in room.enemies if getattr(e, "kind", "") == kind)
    if getattr(boss, "notebook_spawn_pending", False):
        raise AssertionError("Boss placement pending: "+kind)
    game.camera.x = max(0, boss.x-560)
    game.camera.vertical_offset = min(0.0, game.player.rect.centery-400)
    game.camera.offset_y = round(-game.camera.vertical_offset)
    game._update_combat_music()
    return room, boss


class BossDrawingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.quit()
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        cls.display = pygame.display.set_mode((1120, 700))

    @classmethod
    def tearDownClass(cls):
        set_language("en")
        pygame.quit()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.game = Game(self.display, Path(self.folder.name)/"save.json")

    def tearDown(self):
        self.game.boss_cinematic.cancel()
        pygame.mixer.stop()

    def test_all_twelve_authored_bosses_are_detected_once_after_their_actual_spawn(self):
        for kind in BOSS_PROFILES:
            with self.subTest(kind=kind):
                room, boss = spawn_encounter(self.game, kind)
                self.assertTrue(self.game.sounds.boss_active)
                self.assertEqual(self.game.sounds.boss_kind, kind)
                cinema = self.game.boss_cinematic
                self.assertTrue(cinema.maybe_begin())
                self.assertIs(cinema.owner, room)
                self.assertIs(cinema.boss, boss)
                self.assertEqual(boss.notebook_reveal, 0)
                self.assertTrue(boss.cinematic_seen)
                self.assertTrue(boss.cinematic_active)
                self.assertFalse(cinema.maybe_begin())
                self.game.update(cinema.DURATION+.01, InputFrame())
                self.assertFalse(cinema.active)
                self.assertFalse(cinema.maybe_begin())
                self.assertEqual(boss.notebook_reveal, 1)
                self.assertFalse(getattr(room, "cinematic_active", False))
                self.assertFalse(boss.cinematic_active)
                self.assertFalse(self.game.player.locked)
                self.assertEqual(self.game.camera.zoom, 1)
                self.assertIsNone(self.game.camera.script_target)

    def test_game_update_freezes_player_enemy_health_timers_shots_and_control(self):
        game = self.game
        room, boss = spawn_encounter(game, "wanted_sketch")
        game.player.vx, game.player.vy = 73, -31
        self.assertTrue(game.boss_cinematic.maybe_begin())
        boss.projectiles.append(PaperProjectile(boss.x, boss.y-20, -120, 10, "ink", life=2))
        game.weapons.projectiles.append(SimpleNamespace(x=game.player.x+70, y=500, life=2, active=True))
        boss_before = (boss.x, boss.y, boss.hp, boss.state, boss.state_time, boss.time,
                       boss.projectiles[0].x, boss.projectiles[0].y, boss.projectiles[0].life)
        player_before = (game.player.x, game.player.y, game.player.health, game.player.dash_cooldown)
        weapon_before = (game.weapons.current_id, game.weapons.current.ammo,
                         game.weapons.current.reload_timer, game.weapons.projectiles[0].life)
        room_before = (room.encounter_time, room.wave_wait, room.wave)
        game.pending_input = InputFrame(jump_pressed=True, attack_pressed=True, dash_pressed=True,
                                        reload_pressed=True, interact=True, weapon_cycle=1)
        game._buffered_actions = InputFrame(jump_pressed=True, attack_pressed=True)
        frame = InputFrame(right=True, jump_pressed=True, jump_held=True, attack_pressed=True,
                           attack_held=True, dash_pressed=True, reload_pressed=True,
                           interact=True, weapon_slot=4, weapon_cycle=1)
        with patch.object(game.player, "update", side_effect=AssertionError("player ran during drawing")), \
             patch.object(game.level, "update", side_effect=AssertionError("world ran during drawing")), \
             patch.object(game.weapons, "handle_input", side_effect=AssertionError("attack leaked during drawing")):
            game.update(1.5, frame)
            self.assertTrue(game.boss_cinematic.active)
            self.assertAlmostEqual(game.camera.zoom, 1.7)
            self.assertGreater(boss.notebook_reveal, 0)
            self.assertLess(boss.notebook_reveal, 1)
            game.update(1.71, frame)
        self.assertEqual(boss_before, (boss.x, boss.y, boss.hp, boss.state, boss.state_time, boss.time,
                         boss.projectiles[0].x, boss.projectiles[0].y, boss.projectiles[0].life))
        self.assertEqual(player_before, (game.player.x, game.player.y, game.player.health, game.player.dash_cooldown))
        self.assertEqual(weapon_before, (game.weapons.current_id, game.weapons.current.ammo,
                         game.weapons.current.reload_timer, game.weapons.projectiles[0].life))
        self.assertEqual(room_before, (room.encounter_time, room.wave_wait, room.wave))
        self.assertEqual((game.player.vx, game.player.vy), (73, -31))
        self.assertEqual(game.pending_input, InputFrame())
        self.assertEqual(game._buffered_actions, InputFrame())
        self.assertEqual(game.camera.zoom, 1)

    def test_pending_spawn_and_dead_player_do_not_begin_a_drawing(self):
        room, boss = spawn_encounter(self.game, "moon_compass")
        boss.notebook_spawn_pending = True
        self.assertFalse(self.game.boss_cinematic.maybe_begin())
        boss.notebook_spawn_pending = False
        self.game.player.health = 0
        self.assertFalse(self.game.boss_cinematic.maybe_begin())
        self.game.player.health = self.game.player.max_health
        self.game.level.respawn_timer = .8
        self.assertFalse(self.game.boss_cinematic.maybe_begin())

    def test_keys_pressed_during_drawing_do_not_fire_on_the_first_live_frame(self):
        game = self.game
        spawn_encounter(game, "brass_tumbleweed")
        game.boss_cinematic.maybe_begin()
        for key in (pygame.K_SPACE, pygame.K_f, pygame.K_LSHIFT,
                    pygame.K_r, pygame.K_q, pygame.K_4, pygame.K_e):
            game._key_down(key)
        game.update(3.21, InputFrame())
        self.assertEqual(game.pending_input, InputFrame())
        with patch.object(game.player, "queue_jump") as jump, \
             patch.object(game.player, "start_dash") as dash, \
             patch.object(game.weapons, "handle_input", return_value=False) as attack:
            game.update(1/60, InputFrame())
        jump.assert_not_called()
        dash.assert_not_called()
        arguments = attack.call_args.args
        self.assertEqual(arguments[:4], (None, 0, False, False))
        self.assertFalse(arguments[-1])

    def test_health_marks_wait_for_drawing_to_end_before_they_appear(self):
        game = self.game
        _, boss = spawn_encounter(game, "final_editor")
        game.boss_cinematic.maybe_begin()
        game.update(1.3, InputFrame())
        target = pygame.Surface((1120, 700))
        target.fill((247, 241, 219))
        before = pygame.image.tobytes(target, "RGB")
        _health_scratches(target, game.camera, boss, 248)
        self.assertEqual(pygame.image.tobytes(target, "RGB"), before)
        game.boss_cinematic.cancel()
        self.assertFalse(boss.cinematic_active)
        _health_scratches(target, game.camera, boss, 248)
        self.assertNotEqual(pygame.image.tobytes(target, "RGB"), before)

    def test_drawing_keeps_the_real_boss_but_hides_unrelated_lesson_overlay(self):
        game = self.game
        room, _ = spawn_encounter(game, "moon_compass")
        lesson = game.level.runtime.training
        # A restored save may still contain an earlier lesson's overlay.
        lesson.completed = False
        game.boss_cinematic.maybe_begin()
        game.update(1.3, InputFrame())
        with patch.object(room, "draw", wraps=room.draw) as owner_draw, \
             patch.object(lesson, "draw_overlay", wraps=lesson.draw_overlay) as lesson_overlay:
            game.draw()
        owner_draw.assert_called_once()
        lesson_overlay.assert_not_called()

    def test_pause_holds_drawing_and_resumes_without_replaying_the_entry(self):
        game = self.game
        _, boss = spawn_encounter(game, "orbit_crab")
        game.boss_cinematic.maybe_begin()
        game.update(.8, InputFrame())
        elapsed = game.boss_cinematic.elapsed
        game._key_down(pygame.K_ESCAPE)
        self.assertEqual(game.state, "pause")
        game.update(3, InputFrame(attack_pressed=True))
        self.assertEqual(game.boss_cinematic.elapsed, elapsed)
        self.assertTrue(game.boss_cinematic.active)
        game._key_down(pygame.K_ESCAPE)
        game.update(.5, InputFrame())
        self.assertGreater(game.boss_cinematic.elapsed, elapsed)
        self.assertIs(game.boss_cinematic.boss, boss)

    def test_title_cancels_owned_canvas_camera_and_input_but_preserves_other_locks(self):
        game = self.game
        room, _ = spawn_encounter(game, "carbon_hound")
        game.player.acquire_lock("other_script")
        game.boss_cinematic.maybe_begin()
        game.update(1, InputFrame())
        game.pending_input.attack_pressed = True
        self.assertIs(game.level.director.canvas_owner, room)
        game._return_to_title()
        self.assertEqual(game.state, "title")
        self.assertFalse(game.boss_cinematic.active)
        self.assertEqual(game.camera.zoom, 1)
        self.assertIsNone(game.camera.script_target)
        self.assertEqual(game.pending_input, InputFrame())
        self.assertNotIn("boss_cinematic", game.player.control_locks)
        self.assertIn("other_script", game.player.control_locks)
        self.assertIsNone(game.level.director.canvas_owner)

    def test_pause_retry_cleans_drawing_before_the_first_restarted_frame(self):
        game = self.game
        room, _ = spawn_encounter(game, "cloud_kite")
        game.boss_cinematic.maybe_begin()
        game.update(1.2, InputFrame())
        game._key_down(pygame.K_ESCAPE)
        game._activate_pause("RESTART PAGE")
        self.assertEqual(game.state, "playing")
        self.assertFalse(game.boss_cinematic.active)
        self.assertFalse(getattr(room, "cinematic_active", False))
        self.assertFalse(game.player.locked)
        self.assertEqual(game.camera.zoom, 1)
        self.assertIsNone(game.camera.script_target)
        self.assertEqual(game.pending_input, InputFrame())
        game.draw()

    def test_end_death_world_swap_and_room_abort_release_their_owned_cinematic_state(self):
        for exit_kind in ("death", "room_abort", "boss_death", "world_swap"):
            with self.subTest(exit=exit_kind):
                game = self.game
                room, boss = spawn_encounter(game, "draft_moth")
                game.boss_cinematic.maybe_begin()
                game.update(.6, InputFrame())
                if exit_kind == "death":game.player.health = 0
                elif exit_kind == "room_abort":room.encounter_active = False
                elif exit_kind == "boss_death":boss.dead = True
                else:game.level.load_chapter(4, "start", game.player, game.camera)
                game.boss_cinematic.update(.01)
                self.assertFalse(game.boss_cinematic.active)
                self.assertFalse(getattr(room, "cinematic_active", False))
                self.assertFalse(boss.cinematic_active)
                self.assertNotIn("boss_cinematic", game.player.control_locks)
                self.assertEqual(game.camera.zoom, 1)
                self.assertIsNone(game.camera.script_target)

    def test_drawing_status_is_localized_in_all_four_catalogs(self):
        for language in SUPPORTED_LANGUAGES:
            with self.subTest(language=language):
                set_language(language)
                if language != "en":
                    self.assertIn("THE ARTIST IS DRAWING", CATALOGS[language])
                    self.assertNotEqual(translate("THE ARTIST IS DRAWING"), "THE ARTIST IS DRAWING")
                else:
                    self.assertEqual(translate("THE ARTIST IS DRAWING"), "THE ARTIST IS DRAWING")


if __name__ == "__main__":
    unittest.main()
