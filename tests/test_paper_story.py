import json
import os
import tempfile
import unittest
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from game import Game
from input_state import InputFrame
from combat import CombatArena, DoodleEnemy
from identity_content import REQUIRED_SLICE_ENCOUNTERS
from paper_puzzles import CarbonTransferPuzzle, CreaseWeavePuzzle
from puzzles import GlyphLockPuzzle, InkCircuitPuzzle
from save_system import SaveSystem
from settings import HEIGHT, WIDTH


ROUTE_JUMPS = {
    0: [(700, 760), (950, 1015), (1180, 1260), (3400, 3490), (3670, 3760),
        (3970, 4060), (4260, 4370)],
    1: [(800, 900), (1140, 1245), (1550, 1660), (3440, 3570), (4420, 4550),
        (4630, 4700), (4810, 4870), (5020, 5120), (5290, 5410)],
    2: [(1740, 1820), (1940, 2000), (2110, 2180), (2780, 2900), (4450, 4540),
        (5260, 5290), (5660, 5770)],
    3: [(2280, 2370), (2580, 2720), (2960, 3110), (4780, 4880), (5450, 5560)],
    4: [(930, 1040), (2070, 2190), (2490, 2620), (2950, 3060), (3390, 3510),
        (3870, 3960), (4360, 4440), (4770, 4880), (5400, 5530)],
}


class PaperStoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        cls.screen = pygame.display.set_mode((WIDTH, HEIGHT))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save_path = os.path.join(self.temp.name, "save.json")
        self.game = Game(self.screen, self.save_path)

    def tearDown(self):
        self.temp.cleanup()

    def step(self, frames, input_frame=None, draw=False):
        for _ in range(frames):
            self.game.update(1 / 60, input_frame or InputFrame())
            if draw:
                self.game.draw()

    def test_prologue_draws_player_in_order_and_unlocks(self):
        self.game.reset(True)
        self.assertEqual(self.game.player.draw_amount, 0)
        self.step(45)
        self.assertGreater(self.game.player.draw_amount, 0)
        self.assertLess(self.game.player.draw_amount, 1)
        self.step(220)
        self.assertEqual(self.game.player.draw_amount, 1)
        self.assertFalse(self.game.player.locked)
        self.assertIn("player_drawn", self.game.level.flags)

    def test_editable_geometry_and_material_layers(self):
        self.game.state = "playing"
        self.game.level.load_chapter(2, "start", self.game.player, self.game.camera)
        bridge = self.game.level.world.platform_named("correction_bridge")
        before = sum(r.width for r in bridge.collision_rects())
        bridge.erase(3200, 3400)
        after = sum(r.width for r in bridge.collision_rects())
        self.assertGreater(before, after)
        self.assertFalse(any(r.collidepoint(3300, 536) for r in bridge.collision_rects()))

        # Layer portals remain a mechanics-catalogue contract. The shipping
        # fourth page is now the single-layer Agent chapter.
        from chapters import _under_ink
        catalog = _under_ink()
        self.game.level.runtime = catalog
        self.game.level.chapter_index = 3
        self.game.player.x, self.game.player.y = 1100, 520
        self.step(1, InputFrame(interact=True))
        self.assertEqual(self.game.level.world.active_layer, 1)
        self.assertEqual(self.game.player.x, 1780)

    def test_obsolete_catalog_puzzles_and_their_gates_are_pruned(self):
        puzzle_types = (GlyphLockPuzzle, InkCircuitPuzzle,
                        CreaseWeavePuzzle, CarbonTransferPuzzle)
        for page in range(3):
            self.game.level.load_chapter(page, "start", self.game.player, self.game.camera)
            self.assertFalse(any(isinstance(entity, puzzle_types)
                                 for entity in self.game.level.entities.items))
        names = {platform.name for platform in self.game.level.world.platforms}
        self.assertFalse(any("glyph_lock" in name or "carbon_copy" in name
                             or "shared_crease" in name for name in names))

    def test_long_traversal_has_a_continuous_primary_route(self):
        route_names = {0: "route_bamboo_road", 1: "route_dust_road",
                       2: "route_orbit_deck"}
        for page, route_name in route_names.items():
            self.game.level.load_chapter(page, "start", self.game.player, self.game.camera)
            route = self.game.level.world.platform_named(route_name)
            self.assertIsNotNone(route)
            self.assertEqual(route.y, 590)
            self.assertGreater(route.x2, self.game.level.runtime.end_x)

    def test_one_attack_swing_only_hits_an_enemy_once(self):
        self.game.state = "playing"
        self.game.level.load_chapter(1, "margin_exit", self.game.player, self.game.camera)
        player = self.game.player
        player.x, player.y, player.facing = 7900, 542, 1
        enemy = DoodleEnemy("crawler", player.rect.right + 28, 590, 17)
        enemy.state, enemy.state_time = "idle", 2
        context = self.game.level.context(player, self.game.camera, self.game.particles, self.game.sounds)
        self.assertTrue(player.attack())
        for _ in range(14):
            player.update(1 / 60, 0, self.game.level.world, self.game.particles)
            enemy.update(1 / 60, context, (7800, 8200))
        self.assertEqual(enemy.hp, enemy.max_hp - 1)

    def test_arena_gates_checkpoint_and_mandatory_boss_block(self):
        self.game.state = "playing"
        self.game.level.load_chapter(1, "margin_exit", self.game.player, self.game.camera)
        arena = next(entity for entity in self.game.level.entities.items
                     if isinstance(entity, CombatArena) and entity.arena_id == "marker_margin_trial")
        self.game.player.x, self.game.player.y = arena.start_x + 5, 542
        # Direct arrival still waits for the physical room drawing; the gate
        # only closes once ordinary Artist staging has relinquished the page.
        for _ in range(180):
            self.step(1)
            if arena.encounter_active:
                break
        self.assertTrue(arena.encounter_active)
        self.assertTrue(arena.entrance_gate.enabled)
        self.assertTrue(arena.exit_gate.enabled)

        # Clear each authored wave without bypassing the arena state machine.
        for _ in range(600):
            for enemy in arena.enemies:
                enemy.dead = True
            self.step(1)
            if arena.completed:
                break
        self.assertTrue(arena.completed)
        self.assertFalse(arena.entrance_gate.enabled)
        self.assertFalse(arena.exit_gate.enabled)

        self.game.level.load_chapter(1, "after_marker_margin_trial", self.game.player, self.game.camera)
        restored = next(entity for entity in self.game.level.entities.items
                        if isinstance(entity, CombatArena) and entity.arena_id == "marker_margin_trial")
        self.assertTrue(restored.completed)
        self.assertFalse(restored.exit_gate.enabled)

        self.game.level.load_chapter(2, "circuit", self.game.player, self.game.camera)
        signature = next(entity for entity in self.game.level.entities.items
                         if isinstance(entity, CombatArena)
                         and entity.arena_id == "eraser_calibration")
        self.assertTrue(signature.mandatory)
        self.game.player.x = self.game.level.runtime.end_x + 10
        self.game.player.y = 542
        self.game.player.on_ground = True
        self.step(1)
        self.assertFalse(self.game.level.chapter_complete)

    def test_boss_requires_recovery_windows_and_reaches_three_phases(self):
        self.game.state = "playing"
        self.game.level.load_chapter(4, "finale_circuit", self.game.player, self.game.camera)
        player = self.game.player
        boss = DoodleEnemy("boss", 11680, 590, 71, boss=True)
        boss.state, boss.state_time = "idle", .01
        context = self.game.level.context(player, self.game.camera,
                                          self.game.particles, self.game.sounds)
        player.invulnerable = 999
        seen_states = set()
        seen_phases = set()
        elapsed = 0.0
        for _ in range(60 * 40):
            player.x, player.y, player.facing = boss.x - 56, 542, 1
            player.attack()
            player.update(1 / 60, 0, self.game.level.world, self.game.particles)
            boss.update(1 / 60, context, (11300, 12200))
            elapsed += 1 / 60
            seen_states.add(boss.state)
            seen_phases.add(1 if boss.hp > 10 else 2 if boss.hp > 5 else 3)
            if boss.dead:
                break
        self.assertTrue(boss.dead, (boss.hp, boss.state, elapsed))
        self.assertTrue({"telegraph", "slam", "recover"}.issubset(seen_states), seen_states)
        self.assertEqual(seen_phases, {1, 2, 3})
        self.assertGreater(elapsed, 8.0)
        self.assertLess(elapsed, 40.0)

    def test_every_checkpoint_respawns_inside_its_chapter(self):
        self.game.state = "playing"
        for chapter in range(5):
            self.game.level.load_chapter(chapter, "start", self.game.player, self.game.camera)
            ids = [cp.checkpoint_id for cp in self.game.level.runtime.checkpoints]
            for checkpoint_id in ids:
                self.game.level.load_chapter(chapter, checkpoint_id, self.game.player, self.game.camera)
                self.game.level.begin_respawn(self.game.player)
                self.step(60)
                self.assertGreaterEqual(self.game.player.x, -30)
                self.assertLessEqual(self.game.player.x, self.game.level.world.width)
                self.assertEqual(self.game.level.world.active_layer,
                                 self.game.level.checkpoint_spec(checkpoint_id).layer)

    def test_save_roundtrip_continue_and_corruption_fallback(self):
        save = SaveSystem(self.save_path)
        save.checkpoint(3, "surface", 123.5)
        save.discover("under_character")
        loaded = SaveSystem(self.save_path)
        self.assertEqual(loaded.data["chapter"], 3)
        self.assertEqual(loaded.data["checkpoint"], "surface")
        self.assertIn("under_character", loaded.data["secrets"])
        with open(self.save_path, "w", encoding="utf8") as handle:
            handle.write("{broken")
        repaired = SaveSystem(self.save_path)
        self.assertEqual(repaired.data["chapter"], 0)

    def test_new_game_to_ending_canonical_route(self):
        game = self.game
        game.reset(True)
        falls = 0
        fall_log = []
        visited = [0]
        cleared = set()
        solved_paper = set()

        def circuit_move(state, target):
            queue = deque([(tuple(state), [])])
            seen = {tuple(state)}
            while queue:
                current, path = queue.popleft()
                if current == tuple(target):
                    return path[0] if path else None
                for index in range(3):
                    changed = list(current)
                    changed[index] = not changed[index]
                    if index:
                        changed[index - 1] = not changed[index - 1]
                    changed = tuple(changed)
                    if changed not in seen:
                        seen.add(changed)
                        queue.append((changed, path + [index]))

        def crease_move(state, target):
            queue = deque([(tuple(state), [])])
            seen = {tuple(state)}
            while queue:
                current, path = queue.popleft()
                if current == tuple(target):
                    return path[0] if path else None
                for index in range(4):
                    changed = list(current)
                    changed[index] ^= 1
                    if index:
                        changed[index - 1] ^= 1
                    changed = tuple(changed)
                    if changed not in seen:
                        seen.add(changed)
                        queue.append((changed, path + [index]))

        # The pilot reads visible threat roles and recovery animations; it
        # never grants a weapon, edits health, or skips an encounter.
        for frame_index in range(60 * 3600):
            if game.state == "ending":
                break
            chapter = game.level.chapter_index
            if chapter not in visited:
                visited.append(chapter)
            player = game.player
            left = right = interact = attack = jump = dash = False
            weapon_slot = None
            aim_point = None
            arena = next((entity for entity in game.level.entities.items
                          if isinstance(entity, CombatArena) and entity.encounter_active and not entity.completed), None)
            if arena:
                if arena.enemies:
                    ranged_kinds = {"doodle_turret","redaction_agent","ink_outlaw",
                                    "cactus_gunner","rake_cactus","gutter_lantern",
                                    "paper_wasp","origami_drone","star_scout"}
                    def target_priority(enemy):
                        distance = abs(enemy.x-player.center_x)
                        # A firing line is the first problem to solve while a
                        # visibly armoured brute is waiting for a baited slam.
                        if len(arena.enemies)>1 and enemy.kind in ("eraser_brute","crumpled_one") and not enemy.vulnerable:
                            distance+=900
                        if enemy.kind in ranged_kinds:
                            distance-=220
                        return distance
                    target = min(arena.enemies,key=target_priority)
                    aim_point = (target.rect.centerx,target.rect.centery-12)
                    distance = target.x - player.center_x
                    kind = target.kind
                    preferred = {
                        "paper_wasp": "ink_pistol", "doodle_turret": "ink_pistol",
                        "spitter": "ink_pistol", "ruler_guard": "pencil_blade",
                        "eraser_brute": "eraser_cannon", "crumpled_one": "marker_shotgun",
                        "compass": "marker_shotgun", "stapler": "eraser_cannon",
                        "failed_sketch": "marker_shotgun", "artist_mistake": "marker_shotgun",
                        "boss": "marker_shotgun",
                        "ink_samurai": "pencil_blade", "goblin_scribble": "pencil_blade",
                        "origami_drone": "ink_pistol", "ink_outlaw": "ink_pistol",
                        "tumbleweed_thing": "marker_shotgun", "star_scout": "rubber_band",
                        "moon_bot": "rubber_band", "lantern_yokai": "pencil_blade",
                        "cactus_gunner": "ink_pistol", "comet_hound": "rubber_band",
                        "gutter_lantern": "ink_pistol", "rake_cactus": "ink_pistol",
                        "ember_hound": "rubber_band",
                        "moon_compass": "pencil_blade", "wanted_sketch": "ink_pistol",
                        "railroad_stapler": "marker_shotgun",
                        "orbital_mistake": "eraser_cannon",
                        "final_editor": "eraser_cannon", "redaction_agent": "ink_pistol",
                        "scissor_director": "marker_shotgun",
                    }.get(kind, "pencil_blade")
                    # Finish the last scratch with the fast blade instead of
                    # standing over an erased floor for a full cannon reload.
                    # This also exercises mid-fight weapon switching.
                    if kind == "eraser_brute" and target.hp <= 1:
                        preferred = "marker_shotgun"
                    available = game.weapons.available_ids
                    if kind == "lantern_yokai" and "rubber_band" in available:
                        preferred="rubber_band"
                    if preferred not in available:
                        preferred = next((weapon for weapon in ("ink_pistol","rubber_band","marker_shotgun","pencil_blade")
                                          if weapon in available),"pencil_blade")
                    if kind == "baby_face_giant" and "excalibur" in available:
                        preferred = "excalibur"
                    weapon_slot = list(game.weapons.weapons).index(preferred)
                    desired_range = (
                        205 if kind in ("artist_mistake", "orbital_mistake",
                                        "boss", "baby_face_giant", "final_editor")
                        else 135 if kind in ("paper_wasp", "doodle_turret", "spitter",
                                             "origami_drone", "ink_outlaw", "star_scout",
                                             "moon_bot", "lantern_yokai", "cactus_gunner",
                                             "gutter_lantern", "rake_cactus")
                        else 96 if kind in ("compass", "stapler", "failed_sketch",
                                            "moon_compass", "wanted_sketch",
                                            "railroad_stapler")
                        else 45
                    )
                    if not getattr(target,"is_boss",False):
                        desired_range={"ink_pistol":220,"rubber_band":205,
                                       "marker_shotgun":155,"eraser_cannon":190}.get(preferred,45)
                    if kind == "wanted_sketch":
                        desired_range=220
                    if kind == "eraser_brute" and target.state == "idle":
                        desired_range=88  # Step into its advertised slam trigger, then leave.
                    if preferred in ("pencil_blade", "excalibur"):
                        desired_range = 62 if preferred == "excalibur" else 45
                    if abs(distance) > desired_range + 22:
                        left, right = distance < 0, distance > 0
                    elif abs(distance) < desired_range - 22:
                        left, right = distance > 0, distance < 0
                    attack = True
                    if kind in ("eraser_brute","crumpled_one","scissor_director"):
                        # Read the exposed soft side instead of emptying the
                        # slow cannon into armour and reloading its opening.
                        attack = target.vulnerable
                    danger_states = {
                        "telegraph", "brace", "aim", "dive_telegraph", "slam_telegraph",
                        "charge_telegraph", "sweep_telegraph", "snap_telegraph",
                        "boss_telegraph", "pattern_telegraph",
                        "stomp_warn", "sweep_warn",
                        "sheath", "snicker", "quickdraw", "rustle", "lock", "scan", "charge",
                        "flare", "prickle", "tail_warn", "ram_warn", "agent_aim", "cut_warn", "drop_warn",
                        "bounty_draw", "rail_whistle", "return_whistle", "return_telegraph", "cross_warn", "staple_columns_warn",
                        "moon_release_warn", "meteor_warn",
                    }
                    ranged_windups = {"aim","scan","flare","quickdraw","lock","agent_aim","bounty_draw"}
                    threats = [enemy for enemy in arena.enemies if enemy.state in danger_states
                               and enemy.state not in ranged_windups
                               and not (enemy.kind=="moon_bot" and enemy.state=="charge")]
                    threat = min(threats, key=lambda enemy: abs(enemy.x - player.center_x),
                                 default=None)
                    # Commit the dodge near the end of a readable telegraph.
                    # Dashing on its first frame spent the entire i-frame before
                    # long boss windups actually became dangerous.
                    dash = (threat is not None and player.dash_ready and
                            abs(threat.x-player.center_x) < 350 and
                            getattr(threat, "state_time", 1) <= .14)
                    if threat is not None and abs(threat.x-player.center_x) < 350:
                        # Dodge away from the committed edit instead of using
                        # the dash as a gap-closer into a telegraph.
                        threat_distance = threat.x - player.center_x
                        left, right = threat_distance > 0, threat_distance < 0
                    committed_states = {
                        "crossout", "charge", "thrust", "dive", "slam",
                        "erase_slam", "sweep", "snap",
                        "stomp",
                        "draw_cut", "pounce", "roll", "ram", "comet_dash",
                        "counter_cut", "red_stamp", "shear", "drop",
                        "rail_rush", "meteor_fall",
                    }
                    committed = min(
                        (enemy for enemy in arena.enemies
                         if enemy.state in committed_states
                         and not (enemy.kind=="moon_bot" and enemy.state=="charge")),
                        key=lambda enemy: abs(enemy.x - player.center_x),
                        default=None,
                    )
                    if committed is not None:
                        committed_distance = committed.x - player.center_x
                        if abs(committed_distance) < 185 and player.dash_ready:
                            # At a closed arena stroke, the valid answer to a
                            # long charge is through the attacker, not farther
                            # into the wall.
                            dash = True
                            left, right = committed_distance < 0, committed_distance > 0
                    meteor = next((e for e in arena.enemies if e.state in
                                   ("meteor_warn", "meteor_fall")),None)
                    if meteor is not None and abs(player.center_x-meteor.meteor_x)<150:
                        # Follow the visible frozen X, not the airborne body.
                        left = player.center_x < meteor.meteor_x
                        right = not left
                    eraser_hole = next(
                        (enemy for enemy in arena.enemies
                         if bool(getattr(enemy, "_temporary_erases", ()))),
                        None,
                    )
                    if eraser_hole is not None:
                        effect = eraser_hole._temporary_erases[0]
                        added = [interval for interval in effect["after"]
                                 if interval not in effect["before"]]
                        if added:
                            hole_center = sum(added[-1]) / 2
                            hole_distance = hole_center - player.center_x
                            if abs(hole_distance) < 180:
                                left, right = hole_distance > 0, hole_distance < 0
                # React to the projectile's visible flight, not the first
                # windup frame. Dash invulnerability must cover arrival.
                incoming = []
                for enemy in arena.enemies:
                    for shot in getattr(enemy,"projectiles",()):
                        if getattr(shot,"life",0)<=0:continue
                        horizon=.16
                        start=(shot.x,shot.y)
                        end=(shot.x+shot.vx*horizon,
                             shot.y+shot.vy*horizon+.5*getattr(shot,"gravity",0)*horizon*horizon)
                        danger=player.rect.inflate(getattr(shot,"radius",6)*2+8,12)
                        if danger.clipline(start,end):
                            incoming.append(shot)
                if incoming and player.dash_ready:
                    shot=min(incoming,key=lambda s:abs(s.x-player.center_x))
                    dash=True
                    left,right=shot.vx>0,shot.vx<0
                jump = player.on_ground and (
                    not arena.enemies or bool(incoming) or
                    (preferred in ("pencil_blade","excalibur") and
                     target.rect.bottom<player.rect.bottom-40) or
                    any(e.state in ("shear", "rail_rush") and abs(e.x-player.center_x)<300 for e in arena.enemies) or
                    any(e.state == "cut_warn" and e.state_time < .22 and
                        abs(e.x-player.center_x)<180 for e in arena.enemies) or
                    any(e.state in ("rail_whistle", "return_whistle") and e.state_time < .22 for e in arena.enemies) or
                    any(enemy.state in ("telegraph", "slam_telegraph", "sweep_telegraph", "return_telegraph")
                        or (enemy.kind == "eraser_brute" and
                            (enemy.state in ("slam", "recover")
                             or bool(getattr(enemy, "_temporary_erases", ()))))
                        or (enemy.kind == "artist_mistake" and
                            (enemy.state in ("erase_slam", "unravel", "phase_shift")
                             or bool(getattr(enemy, "_temporary_erases", ()))))
                        for enemy in arena.enemies)
                )
            else:
                puzzle = next((entity for entity in game.level.entities.items
                               if isinstance(entity, (GlyphLockPuzzle, InkCircuitPuzzle,
                                                      CreaseWeavePuzzle, CarbonTransferPuzzle)) and
                               not entity.completed and player.x > entity.x - 100 and
                               player.x < entity.gate.x1 + 10), None)
                if puzzle:
                    if isinstance(puzzle, GlyphLockPuzzle):
                        index = next((i for i in range(3) if puzzle.values[i] != puzzle.target[i]), None)
                        target_x = puzzle.x + index * 86 - 12 if index is not None else player.x
                    elif isinstance(puzzle, InkCircuitPuzzle):
                        index = circuit_move(puzzle.state, puzzle.target)
                        target_x = puzzle.x + index * 95 - 12 if index is not None else player.x
                    elif isinstance(puzzle, CreaseWeavePuzzle):
                        index = crease_move(puzzle.states, puzzle.target)
                        target_x = puzzle.stations[index][0] - 12 if index is not None else player.x
                    elif puzzle.phase == "reveal":
                        index = next((i for i, rubbed in enumerate(puzzle.rubbed) if not rubbed), None)
                        target_x = puzzle.stations[index][0] - 12 if index is not None else player.x
                    elif puzzle.phase == "turn":
                        index = 0
                        target_x = puzzle.turn_position[0] - 12
                    else:
                        index = puzzle.solution[len(puzzle.transfer_order)]
                        target_x = puzzle.stations[index][0] - 12
                    if index is not None:
                        distance = target_x - player.x
                        left, right, interact = distance < -12, distance > 12, abs(distance) <= 12
                        if isinstance(puzzle, CreaseWeavePuzzle):
                            jump = player.on_ground and abs(distance) > 24
                else:
                    wait = ((chapter == 2 and 5600 < player.x < 5740 and
                             "blot_on_switch" not in game.level.flags))
                    right = not wait
                    interact = chapter == 3 and (
                        (1050 < player.x < 1220 and game.level.world.active_layer == 0) or
                        (3880 < player.x < 4100 and game.level.world.active_layer == 1)
                    )
                    zones = list(ROUTE_JUMPS[chapter])
                    zones.extend((platform.x1 - 150, platform.x1 - 25)
                                 for platform in game.level.world.platforms
                                 if platform.name.startswith("room_"))
                    zones.extend((flap.x1 - 150, flap.x1 - 25)
                                 for entity in game.level.entities.items
                                 if isinstance(entity, CreaseWeavePuzzle)
                                 for flap in entity.flaps)
                    zones.extend((zone.rect.x - 48, zone.rect.x - 5)
                                 for zone in game.level.world.zones if zone.kind == "ink_hazard")
                    jump = player.on_ground and (
                        any(a < player.x < b for a, b in zones)
                        or (right and abs(player.vx) < 8)
                    )
            before = game.level.respawn_timer
            game.update(1 / 60, InputFrame(left=left, right=right, jump_pressed=jump,
                                           jump_held=jump, interact=interact,
                                           # The deterministic driver taps as
                                           # soon as a weapon is ready.  Live
                                           # hold-to-repeat remains a property
                                           # of automatic weapons only.
                                           attack_pressed=attack,
                                           attack_held=attack,
                                           dash_pressed=dash, weapon_slot=weapon_slot,
                                           aim_x=aim_point[0] if aim_point else None,
                                           aim_y=aim_point[1] if aim_point else None))
            if before == 0 and game.level.respawn_timer > 0:
                falls += 1
                fall_log.append((chapter, round(player.x), round(player.y),
                                 game.level.current_checkpoint, player.health,
                                 [(enemy.kind, enemy.hp, enemy.state)
                                  for enemy in arena.enemies] if arena else [],
                                 [(platform.name, list(platform.erased))
                                  for platform in game.level.world.platforms
                                  if platform.erased]))
            for entity in game.level.entities.items:
                if isinstance(entity, CombatArena) and entity.completed:
                    cleared.add(entity.arena_id)
                if isinstance(entity, (CreaseWeavePuzzle, CarbonTransferPuzzle)) and entity.completed:
                    solved_paper.add(entity.puzzle_id)
        self.assertEqual(game.state, "ending",
                         (game.level.chapter_index, round(game.player.x), round(game.player.y),
                          round(game.player.vx), round(game.player.vy), game.level.current_checkpoint,
                          round(game.session_seconds, 2),
                          sorted(game.player.control_locks), round(game.hit_stop, 3),
                          (getattr(arena, "arena_id", None), getattr(arena, "wave", None),
                           round(getattr(arena, "wave_wait", 0), 2),
                           [(enemy.kind, enemy.hp, enemy.state,
                             round(getattr(enemy, "state_time", 0), 2))
                            for enemy in getattr(arena, "enemies", ())]) if arena else None,
                          sorted(game.level.flags), sorted(cleared), falls, fall_log,
                          [(type(entity).__name__, getattr(entity, "puzzle_id", ""),
                            getattr(entity, "states", getattr(entity, "phase", None)))
                           for entity in game.level.entities.items
                           if getattr(entity, "mandatory", False) and
                           not getattr(entity, "completed", False)]))
        self.assertEqual(visited, [0, 1, 2, 3, 4])
        # The Baby interlude deliberately contributes two authored deaths.
        self.assertLessEqual(falls, 20, fall_log)
        required = {arena_id for ids in REQUIRED_SLICE_ENCOUNTERS.values() for arena_id in ids}
        self.assertEqual(cleared, required)
        self.assertEqual(solved_paper, set())
        self.assertTrue(game.save.data["completed"])
        if os.environ.get("PAPER_STORY_ROUTE_METRICS"):
            print(f"canonical_simulation_seconds={game.session_seconds:.2f} falls={falls}")


if __name__ == "__main__":
    unittest.main()
