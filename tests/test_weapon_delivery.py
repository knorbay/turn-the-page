"""Real chapter gates expose new combat verbs without replacing held ammo."""
import math
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from camera import Camera
from adaptive_artist import AdaptiveArtist, CLOSE_TOOLS
from game import Game
from notebook_agency import NotebookAgency
from page_arsenal import PAGE_ENTRY_TOOLS, draw_weapon, loadout_for, profile_for
from paper_renderer import PaperRenderer
from particles import ParticleSystem
from player import Player
from save_system import SaveSystem
from weapon_delivery import CHAPTER_DELIVERIES, next_delivery
from weapons import WEAPON_ORDER, WeaponSystem
from world import PaperWorld


class ChapterWeaponVariety(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.screen = pygame.display.set_mode((1120,700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setup_weapon(self, page, weapon):
        player = Player(100,542)
        system = WeaponSystem(player)
        system.configure_page(page)
        system.lend_drawn_tool(weapon)
        world = PaperWorld(page=page+1,build_legacy=False)
        world.width = 1200
        ctx = SimpleNamespace(player=player,weapons=system,world=world,
                              particles=ParticleSystem(),camera=Camera(1120),
                              sounds=SimpleNamespace(play=lambda _:None),
                              game=SimpleNamespace(hit_stop=0))
        return system,ctx

    @staticmethod
    def wait_for_letter_spacing(agency, ctx):
        # A completed gift leaves time to read its note. Earned later drawings
        # stay pending and may begin when the final quiet frame arrives.
        delay = max(agency.letter_time, agency.gift_cooldown)
        for _ in range(math.ceil(delay*60)):
            agency.update(1/60, ctx)

    @staticmethod
    def target(x,y,hp=5):
        return SimpleNamespace(rect=pygame.Rect(x,y,25,40),hp=hp,max_hp=hp,
                               dead=False,active=True,vx=0)

    def test_new_ids_append_to_legacy_slots_and_both_round_trip_ammo(self):
        self.assertEqual(WEAPON_ORDER[:10],("pencil_blade","ink_pistol","marker_shotgun",
                         "eraser_cannon","rubber_band","excalibur","margin_maul",
                         "carbon_lance","folded_shuriken","chalk_bomb"))
        system,ctx = self.setup_weapon(2,"orbit_saw")
        system.unlock("fold_crossbow")
        system.current.ammo = 1
        system.weapons["fold_crossbow"].ammo = 0
        restored = WeaponSystem(Player())
        restored.configure_page(2)
        restored.restore(system.snapshot())
        self.assertEqual(restored.current_id,"orbit_saw")
        self.assertEqual(restored.current.ammo,1)
        self.assertEqual(restored.weapons["fold_crossbow"].ammo,0)
        self.assertEqual(restored.unlocked,{"orbit_saw","fold_crossbow"})

    def test_artist_complements_the_new_ranged_tools_with_a_close_drawing(self):
        policy = AdaptiveArtist()
        for page, tool in ((0, "fold_crossbow"), (1, "fold_crossbow"),
                           (2, "orbit_saw"), (3, "fold_crossbow"), (4, "orbit_saw")):
            with self.subTest(page=page, tool=tool):
                system, _ = self.setup_weapon(page, tool)
                self.assertEqual(policy.gift_for(page, system), CLOSE_TOOLS[page])
                system.unlock(CLOSE_TOOLS[page])
                self.assertIsNone(policy.gift_for(page, system), "do not redraw an owned complement")

    def test_crossbow_splits_at_contact_and_first_target_does_not_take_three_extra_hits(self):
        system,ctx = self.setup_weapon(0,"fold_crossbow")
        self.assertTrue(system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx))
        bolt = system.projectiles[0]
        first = self.target(bolt.x+90,bolt.y-20)
        behind = self.target(bolt.x+170,bolt.y-20)
        for _ in range(17):system.update(1/60,ctx,[first,behind])
        self.assertAlmostEqual(first.hp,4.05,places=2)
        self.assertLess(behind.hp,5,"a split shard must damage a body behind the first")
        shards = [shot for shot in system.projectiles if shot.visual == "fold_shard"]
        self.assertTrue(shards)
        self.assertTrue(all(shot.weapon_id == "fold_crossbow" for shot in shards))
        self.assertTrue(all(id(first) in shot.hit_ids for shot in shards))
        self.assertTrue(all(shot.attack_id == bolt.attack_id for shot in shards))

    def test_crossbow_wall_contact_unfolds_outside_cover_without_shooting_through_it(self):
        system,ctx = self.setup_weapon(0,"fold_crossbow")
        ctx.world.add(230,250,450,180,"crossbow_wall",1)
        victim = self.target(260,530)
        system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        for _ in range(25):system.update(1/60,ctx,[victim])
        self.assertEqual(victim.hp,5)
        shards = [shot for shot in system.projectiles if shot.visual == "fold_shard"]
        self.assertTrue(shards)
        self.assertTrue(all(shot.vx < 0 for shot in shards))

    def test_crossbow_requires_a_tap_and_one_round_reload(self):
        system,ctx = self.setup_weapon(0,"fold_crossbow")
        system.handle_input(fire_pressed=True,fire_held=True,ctx=ctx)
        self.assertEqual(system.current.ammo,0)
        self.assertTrue(system.current.reloading)
        for _ in range(80):
            system.update(1/60,ctx,[])
            system.handle_input(fire_held=True,ctx=ctx)
        self.assertEqual(system.attack_serial,1)
        self.assertEqual(system.current.ammo,1)

    def test_orbit_ring_stops_and_delivers_two_separated_committed_cuts(self):
        system,ctx = self.setup_weapon(2,"orbit_saw")
        system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        ring = system.projectiles[0]
        for _ in range(19):system.update(1/60,ctx,[])
        position = (ring.x,ring.y)
        target = self.target(ring.x-12,ring.y-20)
        far = self.target(ring.x+95,ring.y-20)
        for _ in range(10):system.update(1/60,ctx,[target,far])
        self.assertAlmostEqual(target.hp,4.28)
        self.assertEqual(len(ring.pulse_ids),1)
        for _ in range(22):system.update(1/60,ctx,[target,far])
        self.assertAlmostEqual(target.hp,3.56)
        self.assertEqual(len(ring.pulse_ids),2)
        self.assertEqual(far.hp,5)
        self.assertEqual((ring.x,ring.y),position)
        for _ in range(25):system.update(1/60,ctx,[target,far])
        self.assertFalse(system.projectiles)
        self.assertAlmostEqual(target.hp,3.56,msg="a ring has only two cuts")

    def test_orbit_ring_cannot_stack_and_does_not_spend_ammo_for_rejected_throw(self):
        system,ctx = self.setup_weapon(2,"orbit_saw")
        system.handle_input(fire_pressed=True,ctx=ctx)
        for _ in range(42):system.update(1/60,ctx,[])
        before = system.current.ammo
        self.assertFalse(system.handle_input(fire_pressed=True,ctx=ctx))
        self.assertEqual(system.current.ammo,before)
        self.assertEqual(len(system.projectiles),1)

    def test_both_new_shapes_are_bounded_distinct_and_use_drawn_muzzle(self):
        images = []
        for page,weapon in ((0,"fold_crossbow"),(2,"orbit_saw")):
            system,ctx = self.setup_weapon(page,weapon)
            surface = pygame.Surface((140,100),pygame.SRCALPHA)
            draw_weapon(surface,weapon,page,(45,50),scale=1)
            bounds = surface.get_bounding_rect()
            self.assertGreater(bounds.width,35)
            self.assertLess(bounds.width,80)
            self.assertLess(bounds.height,60)
            images.append(pygame.image.tobytes(surface,"RGBA"))
            for angle in (0,math.pi,-1.1):
                system.current.ammo=system.current.mag_size
                system.current.cooldown=system.current.reload_timer=0
                system.projectiles.clear()
                ctx.player.facing=1 if math.cos(angle)>0 else -1
                ctx.player.aim_angle=angle
                expected=ctx.player.weapon_attachment().muzzle
                system.handle_input(fire_pressed=True,
                    aim={"direction":(math.cos(angle),math.sin(angle))},ctx=ctx)
                shot=system.projectiles[0]
                self.assertAlmostEqual(shot.x,expected.x)
                self.assertAlmostEqual(shot.y,expected.y)
        self.assertNotEqual(*images)

    def test_every_chapter_earns_two_additional_drawings_at_real_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            for page in range(5):
                with self.subTest(page=page):
                    game=Game(self.screen,Path(directory)/f"gate-{page}.json")
                    game.reset()
                    game.level.load_chapter(page,"start",game.player,game.camera)
                    game._attach_runtime()
                    game.save.checkpoint(page,"start")
                    game.player.release_all_locks()
                    agency=next(e for e in game.level.entities.items if isinstance(e,NotebookAgency))
                    ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
                    agency._restore(ctx)
                    game.weapons.lend_drawn_tool(PAGE_ENTRY_TOOLS[page])
                    held=game.weapons.current_id
                    game.weapons.current.ammo=max(-1,game.weapons.current.ammo-1)
                    ammo=game.weapons.current.ammo
                    rooms=sorted((r for r in agency.arenas if r.mandatory
                                  and r.arena_id!="baby_face_interlude"),key=lambda r:r.start_x)
                    # The original adaptive close/range gift still appears first.
                    rooms[0].completed=True
                    game.player.x=rooms[0].end_x+30
                    agency.update(.01,ctx)
                    self.assertEqual(agency.operation,"support_tool")
                    for _ in range(75):agency.update(1/60,ctx)
                    for delivery in CHAPTER_DELIVERIES[page]:
                        self.wait_for_letter_spacing(agency, ctx)
                        self.assertIn(delivery.weapon_id,loadout_for(page))
                        self.assertNotIn(delivery.weapon_id,game.weapons.unlocked)
                        rooms[delivery.after_clear-1].completed=True
                        # A physical pickup near the gate owns its drawing.
                        # The earned extra tool stays available farther along
                        # the same quiet stretch, before the following room.
                        game.player.x=rooms[delivery.after_clear-1].end_x+800
                        agency.update(.01,ctx)
                        self.assertEqual(agency.selected_weapon,delivery.weapon_id)
                        self.assertEqual(agency.operation,"support_tool")
                        self.assertNotIn(delivery.weapon_id,game.weapons.unlocked)
                        for _ in range(75):agency.update(1/60,ctx)
                        self.assertIn(delivery.weapon_id,game.weapons.available_ids)
                        self.assertEqual(game.weapons.current_id,held)
                        self.assertEqual(game.weapons.current.ammo,ammo)
                    saved=SaveSystem(game.save.path)
                    self.assertTrue(all(delivery.weapon_id in saved.data["artist_adaptation"]["gifts"][str(page)]
                                        for delivery in CHAPTER_DELIVERIES[page]))
                    game.continue_game()
                    restored=next(e for e in game.level.entities.items if isinstance(e,NotebookAgency))
                    restored.update(0,game.level.context(game.player,game.camera,game.particles,game.sounds))
                    self.assertEqual(game.weapons.current_id,held)
                    self.assertEqual(game.weapons.current.ammo,ammo)
                    self.assertTrue(all(delivery.weapon_id in game.weapons.available_ids
                                        for delivery in CHAPTER_DELIVERIES[page]))

    def test_legacy_late_checkpoint_catches_up_all_earned_tools_without_refilling_held_ammo(self):
        with tempfile.TemporaryDirectory() as directory:
            for page in range(5):
                with self.subTest(page=page):
                    game = Game(self.screen, Path(directory)/f"legacy-late-{page}.json")
                    game.reset()
                    game.level.load_chapter(page, "start", game.player, game.camera)
                    game._attach_runtime()
                    agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
                    rooms = sorted((r for r in agency.arenas if r.mandatory
                                   and r.arena_id != "baby_face_interlude"), key=lambda r: r.start_x)
                    checkpoint = "after_"+rooms[2].arena_id
                    starter = PAGE_ENTRY_TOOLS[page]
                    game.save.checkpoint(page, checkpoint)
                    game.save.update_combat([starter], starter, {starter: 1})
                    game.save.data["artist_adaptation"] = {}  # A pre-progression checkpoint.
                    game.save.write()
                    game.continue_game()
                    game.player.release_all_locks()
                    agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
                    self.assertGreater(game.player.center_x, agency.first.end_x+850)
                    # An old checkpoint may land beside a discoverable scrap.
                    # The later loan remains earned after walking into quiet paper.
                    game.player.x += 800
                    ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
                    held, ammo = game.weapons.current_id, game.weapons.current.ammo
                    first = game.artist_director.gift_for(page, game.weapons)
                    expected = (first, *(d.weapon_id for d in CHAPTER_DELIVERIES[page]))
                    for weapon in expected:
                        self.wait_for_letter_spacing(agency, ctx)
                        self.assertNotIn(weapon, game.weapons.unlocked)
                        agency.update(.01, ctx)
                        self.assertEqual(agency.operation, "support_tool")
                        self.assertEqual(agency.selected_weapon, weapon)
                        self.assertNotIn(weapon, game.weapons.unlocked, "unfinished ink must not grant a tool")
                        for _ in range(90):
                            agency.update(1/60, ctx)
                            if weapon in game.weapons.unlocked:
                                break
                        self.assertIn(weapon, game.weapons.available_ids)
                        self.assertEqual(game.weapons.current_id, held)
                        self.assertEqual(game.weapons.current.ammo, ammo)
                    saved = SaveSystem(game.save.path)
                    self.assertTrue(set(expected) <= set(saved.data["artist_adaptation"]["gifts"][str(page)]))

    def test_legacy_empty_hand_waits_for_the_entry_tool_before_progression_drawings(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/"legacy-empty.json")
            game.reset()
            game.save.checkpoint(0, "after_bamboo_static")
            game.save.update_combat([], "unarmed", {})
            game.save.write()
            game.continue_game()
            game.player.release_all_locks()
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency.update(.01, ctx)
            self.assertTrue(agency.first.completed)
            self.assertEqual(game.weapons.current_id, "unarmed")
            self.assertIsNone(agency.operation)
            self.assertFalse(agency.gift_page_done)

    def test_automatic_gifts_yield_to_notifications_interaction_and_ink_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/"gift-priority.json")
            game.reset()
            game.level.load_chapter(0, "after_moon_gate_duel", game.player, game.camera)
            game._attach_runtime()
            game.player.release_all_locks()
            game.weapons.lend_drawn_tool("folded_shuriken")
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency._restore(ctx)
            for field, owner in (("toast_time", game.level), ("weapon_reveal_time", game),
                                 ("achievement_time", game)):
                setattr(owner, field, 1.0)
                agency.update(.01, ctx)
                self.assertIsNone(agency.operation, field)
                self.assertIsNone(ctx.director.canvas_owner)
                setattr(owner, field, 0)
            agency.update(.01, ctx, interact=True)
            self.assertIsNone(agency.operation)
            game.weapons.fire_buffer = .1
            agency.update(.01, ctx)
            self.assertIsNone(agency.operation)
            game.weapons.fire_buffer = 0
            agency.update(.01, ctx)
            self.assertEqual(agency.operation, "support_tool")
            self.assertIs(ctx.director.canvas_owner, agency)
            for _ in range(75):agency.update(1/60, ctx)
            self.assertIsNone(agency.operation)
            self.assertGreater(agency.gift_cooldown, 3.0)
            agency.update(.01, ctx)
            self.assertIsNone(agency.operation, "do not chain the next gift into the previous note")

    def test_started_automatic_gift_yields_to_an_optional_challenge_and_remains_earned(self):
        from optional_encounters import OptionalGuardianPocket
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/"gift-interruption.json")
            game.reset()
            game.level.load_chapter(1, "start", game.player, game.camera)
            game._attach_runtime()
            game.player.release_all_locks()
            game.weapons.lend_drawn_tool("ink_pistol")
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency.first.completed = True
            game.player.x = agency.first.end_x+30
            agency.update(.25, ctx)
            self.assertEqual(agency.operation, "support_tool")
            pending = agency.selected_weapon
            held, ammo = game.weapons.current_id, game.weapons.current.ammo
            pocket = next(e for e in game.level.entities.items if isinstance(e, OptionalGuardianPocket))
            # The player has already unfolded this actual optional landing.
            pocket.entrance_open = True
            pocket.entrance_progress = 1
            for step in pocket.steps:
                step.enabled = True
                step.complete_drawing()
            game.player.x = pocket.bounds[0]+50-game.player.rect.width/2
            game.player.y = pocket.ground-game.player.rect.height
            agency.update(.01, ctx, interact=True)
            pocket.update(.01, ctx, interact=True)
            self.assertTrue(pocket.encounter_active, "one deliberate E press must begin the challenge")
            self.assertIsNone(agency.operation)
            self.assertEqual(agency.letter_time, 0)
            self.assertFalse(agency.hand.tool.visible)
            self.assertIs(ctx.director.canvas_owner, pocket)
            self.assertNotIn(pending, game.weapons.unlocked)
            self.assertNotIn(pending, game.artist_director.gifts_for(1))
            self.assertEqual((game.weapons.current_id, game.weapons.current.ammo), (held, ammo))
            pocket.abort(ctx)
            ctx.level.interaction_hint = ""
            game.player.x = agency.first.end_x+30
            game.player.y = 542
            self.wait_for_letter_spacing(agency, ctx)
            agency.update(.01, ctx)
            self.assertEqual(agency.operation, "support_tool")
            self.assertEqual(agency.selected_weapon, pending)
            for _ in range(75):agency.update(1/60, ctx)
            self.assertIn(pending, game.weapons.unlocked)
            self.assertIn(pending, game.artist_director.gifts_for(1))
            self.assertEqual((game.weapons.current_id, game.weapons.current.ammo), (held, ammo))

    def test_entering_a_drawn_combat_gate_defers_an_unfinished_automatic_gift(self):
        with tempfile.TemporaryDirectory() as directory:
            game = Game(self.screen, Path(directory)/"gift-combat-entry.json")
            game.reset()
            game.level.load_chapter(0, "start", game.player, game.camera)
            game._attach_runtime()
            game.player.release_all_locks()
            game.weapons.lend_drawn_tool("folded_shuriken")
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency.first.completed = True
            room = next(r for r in agency.arenas if r.arena_id == "practice_crossouts")
            # A previously visited room can have its cover drawn before entry.
            for stage in room.artist_stages:
                if getattr(stage, "cover", None) is not None:stage.cover.complete_drawing()
            game.player.x = agency.first.end_x+30
            agency.update(.25, ctx)
            pending = agency.selected_weapon
            self.assertEqual(agency.operation, "support_tool")
            game.player.x = room.start_x+30
            room.update(.01, ctx)
            self.assertTrue(room.encounter_active)
            self.assertTrue(room.enemies)
            agency.update(.01, ctx)
            self.assertIsNone(agency.operation)
            self.assertIsNone(ctx.director.canvas_owner)
            self.assertEqual(agency.letter_time, 0)
            self.assertTrue(agency.hand.tool.visible, "the hand may draw the new enemy instead")
            self.assertGreaterEqual(agency.hand.tool.x, room.start_x)
            self.assertFalse(agency.gift_page_done)
            self.assertNotIn(pending, game.weapons.unlocked)
            self.assertNotIn(pending, game.artist_director.gifts_for(0))

    def test_progression_drawing_is_not_granted_before_clears_or_during_fight(self):
        rooms=[SimpleNamespace(arena_id=str(index),mandatory=True,start_x=index*300,
                              end_x=index*300+200,completed=False) for index in range(3)]
        system,ctx=self.setup_weapon(0,"folded_shuriken")
        ctx.player.x=1100
        self.assertIsNone(next_delivery(0,rooms,ctx.player,system))
        rooms[1].completed=True
        self.assertIsNone(next_delivery(0,rooms,ctx.player,system),"a skipped first room is not a reward")
        rooms[0].completed=True
        ctx.player.x=200
        self.assertIsNone(next_delivery(0,rooms,ctx.player,system),"stay past the gate before drawing")
        ctx.player.x=1100
        self.assertEqual(next_delivery(0,rooms,ctx.player,system),"fold_crossbow")
        system.unlocked.clear()
        self.assertIsNone(next_delivery(0,rooms,ctx.player,system),"an empty starter must still be drawn")


if __name__ == "__main__":
    unittest.main()
