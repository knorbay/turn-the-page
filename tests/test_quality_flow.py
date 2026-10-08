"""Gameplay checks for the existing page rework, using the real controller."""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")

from types import SimpleNamespace
import tempfile
from pathlib import Path
import unittest
import pygame

from action_content import WeaponPickup
from camera import Camera
from chapters import build_chapter
from entities import LostSketch
from page_experiences import SketchTrial
from page_flow import FLOW_SECTIONS
from particles import ParticleSystem
from player import Player
from scripted_events import ArtistDirector
from sketch_discovery import SketchDiscovery
from sketches import SKETCHES
from weapons import WeaponSystem


class QualityFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120,700))

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def context(self,page,secret):
        runtime=build_chapter(page)
        sketch=next(e for e in runtime.entities.items
                    if isinstance(e,LostSketch) and e.secret_id==secret)
        discovery=sketch.discovery
        player=Player(sketch.x-12,sketch.y+20-48)
        player.on_ground=True
        collected=[]
        level=SimpleNamespace(entities=runtime.entities,flags=set(),chapter_index=page,
            interaction_hint="",toast="",toast_time=0,save_system=None,
            discover_secret=lambda secret,caption:collected.append(secret))
        weapons=WeaponSystem(player)
        weapons.configure_page(page)
        ctx=SimpleNamespace(player=player,world=runtime.world,level=level,
            director=ArtistDirector(),weapons=weapons,game=None,
            camera=Camera(1120),particles=ParticleSystem(),
            sounds=SimpleNamespace(play=lambda cue:None))
        return discovery,sketch,ctx,collected

    def test_campaign_content_and_saved_sketch_ids_are_preserved(self):
        found={}
        arenas=0
        trials=[]
        for page in range(5):
            runtime=build_chapter(page)
            arenas+=sum(getattr(e,"is_combat_arena",False) for e in runtime.entities.items)
            for e in runtime.entities.items:
                if isinstance(e,LostSketch):found[e.secret_id]=page
                if isinstance(e,SketchTrial):trials.append(e.sketch.secret_id)
        self.assertEqual(arenas,25)
        self.assertEqual(found,{s.secret_id:s.page for s in SKETCHES})
        self.assertEqual(trials,["practice_monster"])

    def test_fresh_opening_reaches_the_first_fight_with_its_drawn_fold(self):
        from game import Game
        from input_state import InputFrame
        with tempfile.TemporaryDirectory() as directory:
            game=Game(pygame.display.get_surface(),Path(directory)/"opening.json")
            game.reset()
            jump_index=0
            for frame in range(650):
                p=game.player
                thresholds=(720,980,1215)
                jump=jump_index<3 and p.on_ground and p.x>=thresholds[jump_index]
                if jump:jump_index+=1
                game.update(1/60,InputFrame(right=p.x<1530,jump_pressed=jump,jump_held=True))
                if frame%45==0:game._draw_scene(game.screen)
                if p.x>=1530 and not p.locked:break
            self.assertEqual(jump_index,3)
            self.assertGreater(game.player.x,1530)
            self.assertEqual(game.weapons.current_id,"folded_shuriken")
            self.assertEqual(game.behavior.count("deaths"),0)
            self.assertTrue(next(e for e in game.level.entities.items
                if isinstance(e,WeaponPickup) and e.weapon_id=="folded_shuriken").collected)

    def test_all_authored_new_landings_are_reachable_with_normal_jumps(self):
        particles=ParticleSystem()
        for page,sections in FLOW_SECTIONS.items():
            runtime=build_chapter(page)
            for name,span,landings,style in sections:
                with self.subTest(page=page,section=name):
                    mapping=runtime.pacing_map
                    span=tuple(mapping(x) for x in span)
                    landings=tuple((mapping(a),mapping(b),y) for a,b,y in landings)
                    player=Player(span[0]-105,542)
                    player.on_ground=True
                    for a,b,y in landings:
                        player.queue_jump()
                        reached=False
                        center=(a+b)/2
                        for frame in range(150):
                            axis=1 if player.center_x<center-4 else -1 if player.center_x>center+4 else 0
                            player.update(1/120,axis,runtime.world,particles)
                            if (player.on_ground and abs(player.rect.bottom-y)<2
                                    and a<=player.center_x<=b):
                                reached=True
                                break
                        self.assertTrue(reached,(name,(a,b,y),player.x,player.y))
                    self.assertLess(player.y,700)

    def test_covered_figure_cannot_be_collected_mid_eraser_stroke(self):
        discovery,sketch,ctx,collected=self.context(0,"old_first_figure")
        discovery.update(.15,ctx,True)
        sketch.update(.15,ctx,True)
        self.assertFalse(discovery.completed)
        self.assertEqual(collected,[])
        for _ in range(70):discovery.update(1/60,ctx)
        self.assertTrue(discovery.completed)
        self.assertIn("Its trick stays",discovery.letter)
        sketch.update(.016,ctx,True)
        sketch.update(.016,ctx,True)
        self.assertEqual(collected,["old_first_figure"])

    def test_walking_over_the_perforation_does_not_replace_the_dash_answer(self):
        discovery,sketch,ctx,_=self.context(1,"margin_battle_note")
        for _ in range(60):discovery.update(1/60,ctx)
        self.assertEqual(discovery.state,"waiting")
        self.assertTrue(ctx.player.start_dash(1))
        for _ in range(45):discovery.update(1/60,ctx)
        self.assertTrue(discovery.completed)

    def test_coffee_drawing_rewards_stopping_and_noticing_its_handle(self):
        discovery,sketch,ctx,_=self.context(1,"coffee_secret")
        ctx.player.facing=1
        for _ in range(90):discovery.update(1/60,ctx)
        self.assertFalse(discovery.completed)
        ctx.player.facing=-1
        ctx.player.vx=150
        for _ in range(90):discovery.update(1/60,ctx)
        self.assertFalse(discovery.completed)
        ctx.player.vx=0
        for _ in range(90):discovery.update(1/60,ctx)
        self.assertTrue(discovery.completed)

    def test_actual_projectile_reveals_the_wrong_outline(self):
        discovery,sketch,ctx,_=self.context(2,"bad_draft")
        ctx.player.x,ctx.player.y=sketch.x-150,422
        ctx.weapons.unlock("rubber_band")
        ctx.weapons.select("rubber_band")
        for _ in range(30):discovery.update(1/60,ctx)
        self.assertFalse(discovery.completed)
        self.assertTrue(ctx.weapons.handle_input(fire_pressed=True,
            aim=(sketch.x,sketch.y-15),ctx=ctx))
        for _ in range(120):
            ctx.weapons.update(1/60,ctx,[])
            discovery.update(1/60,ctx)
            if discovery.completed:break
        self.assertTrue(discovery.completed)

    def test_carbon_badge_and_independent_rifle_leave_the_equipped_pistol_intact(self):
        discovery,sketch,ctx,collected=self.context(3,"agent_badge")
        rifle=next(e for e in ctx.level.entities.items
                   if isinstance(e,WeaponPickup) and e.weapon_id=="carbon_lance")
        ctx.weapons.unlock("ink_pistol");ctx.weapons.select("ink_pistol")
        ctx.weapons.current.ammo=5
        self.assertFalse(rifle.requires_sketch)
        ctx.player.x,ctx.player.y=discovery.pressure_line.x1+60-12,430-48
        ctx.player.on_ground=True
        for _ in range(45):discovery.update(1/60,ctx)
        self.assertTrue(discovery.completed)
        sketch.update(.016,ctx,True)
        self.assertEqual(collected,["agent_badge"])
        ctx.player.x,ctx.player.y=rifle.x-12,542
        for _ in range(60):rifle.update(1/60,ctx)
        self.assertTrue(rifle.collected)
        self.assertIn("carbon_lance",ctx.weapons.available_ids)
        self.assertEqual(ctx.weapons.current_id,"ink_pistol")
        self.assertEqual(ctx.weapons.current.mag_size,8)
        self.assertEqual(ctx.weapons.current.ammo,5)

    def test_each_notebook_discovery_works_through_actual_game_updates_and_saves_once(self):
        from game import Game
        from input_state import InputFrame
        cases=(
            ("old_first_figure",0,"alive",(438,542),"ask"),
            ("shrine_roof",0,"after_practice_crossouts",(6748,297),"ask"),
            ("beyond_red",1,"coffee",(4688,462),"jump"),
            ("coffee_secret",1,"after_pistol_margin_drill",(3508,542),"notice"),
            ("margin_battle_note",1,"after_marker_margin_trial",(9700,542),"dash"),
            ("water_tower",1,"after_marker_margin_trial",(10193,297),"ask"),
            ("bad_draft",2,"start",(1500,422),"ink"),
            ("eraser_survivor_sketch",2,"after_zero_garden",(13463,502),"drop"),
            ("orbit_observatory",2,"after_zero_garden",(12678,297),"ask"),
            ("agent_badge",3,"after_carbon_crossfire",(4568,382),"pressure"),
            ("last_homework",4,"after_the_last_crossout",(8528,382),"ink"),
        )
        for secret,page,checkpoint,position,action in cases:
            with self.subTest(secret=secret),tempfile.TemporaryDirectory() as directory:
                game=Game(pygame.display.get_surface(),Path(directory)/"discovery.json")
                game.reset()
                game.level.load_chapter(page,checkpoint,game.player,game.camera)
                game._attach_runtime()
                if action=="ink":
                    # Take the real entry drawing; the fixture never grants a
                    # weapon or bypasses its Artist completion to fire a test.
                    weapon="rubber_band" if page==2 else "margin_maul"
                    gift=next(e for e in game.level.entities.items
                        if isinstance(e,WeaponPickup) and e.weapon_id==weapon)
                    game.player.x,game.player.y=gift.x-12,gift.y-48
                    for _ in range(150):game.update(1/60,InputFrame())
                    self.assertTrue(gift.collected)
                    self.assertEqual(game.weapons.current_id,weapon)
                player=game.player
                player.x,player.y=game.level.runtime.pacing_map(position[0]),position[1]
                player.vx=player.vy=0
                player.on_ground=True
                discovery=next(e for e in game.level.entities.items
                    if isinstance(e,SketchDiscovery) and e.sketch.secret_id==secret)
                sketch=discovery.sketch
                for frame in range(160):
                    game.update(1/60,InputFrame(
                        interact=action=="ask" and frame%20==0,
                        left=action=="notice" and frame<2,
                        right=action=="dash" and frame<12,
                        dash_pressed=action=="dash" and frame==0,
                        jump_pressed=action in ("jump","drop") and frame==0,
                        jump_held=action=="jump",down=action=="drop",
                        attack_pressed=action=="ink" and frame==0,
                        aim_x=sketch.x,aim_y=sketch.y-16))
                self.assertTrue(discovery.completed,(secret,discovery.state))
                self.assertIsNone(game.level.director.canvas_owner)
                # Move back to the exposed scrap and use the real collect
                # input. The upper margin house requires another actual jump.
                for _ in range(160):
                    distance=sketch.x-player.center_x
                    jump=player.on_ground and player.rect.bottom-sketch.y>=95
                    game.update(1/60,InputFrame(
                        left=distance<-8,right=distance>8,
                        jump_pressed=jump,jump_held=jump,interact=True))
                    if sketch.discovered:break
                self.assertTrue(sketch.discovered,(secret,player.x,player.rect.bottom))
                for _ in range(10):game.update(1/60,InputFrame(interact=True))
                self.assertEqual(game.save.data["secrets"].count(secret),1)
                self.assertEqual(discovery.letter_time,0)
                self.assertEqual(game.behavior.count("deaths"),0)
                game._draw_scene(game.screen)

    def test_started_discovery_finishes_after_leaving_the_drawing(self):
        discovery,sketch,ctx,_=self.context(0,"old_first_figure")
        discovery.update(.1,ctx,True)
        self.assertIs(ctx.director.canvas_owner,discovery)
        ctx.player.x+=1600
        for _ in range(60):
            ctx.director.update(1/60,ctx)
            discovery.update(1/60,ctx)
        self.assertTrue(discovery.completed)
        self.assertIsNone(ctx.director.canvas_owner)

    def test_every_completed_page_exit_accepts_a_jumping_walk_and_advances(self):
        from game import Game
        from input_state import InputFrame
        checkpoints=("after_moon_gate_duel","after_midnight_train",
                     "after_baby_face_interlude","after_scissor_office",
                     "after_final_margin_revision")
        for page,checkpoint in enumerate(checkpoints):
            with self.subTest(page=page),tempfile.TemporaryDirectory() as directory:
                game=Game(pygame.display.get_surface(),Path(directory)/"exit.json")
                game.reset()
                # Use the last legitimate completion snapshot; no fixture
                # manually completes gates or suppresses required entities.
                game.level.load_chapter(page,checkpoint,game.player,game.camera)
                game._attach_runtime()
                self.assertTrue(all(getattr(e,"completed",False)
                    for e in game.level.entities.items if getattr(e,"mandatory",False)))
                jumped=False
                for frame in range(360):
                    p=game.player
                    jump=not jumped and p.on_ground and p.x>=game.level.runtime.end_x-55
                    if jump:jumped=True
                    game.update(1/60,InputFrame(right=True,jump_pressed=jump,jump_held=True))
                    if game.transition_active or game.state=="ending":break
                self.assertTrue(jumped)
                self.assertTrue(game.level.chapter_complete,
                    (page,game.player.x,game.player.rect.bottom))
                self.assertEqual(game.behavior.count("deaths"),0)
                if page==4:
                    self.assertEqual(game.state,"ending")
                    self.assertFalse(game.transition_active)
                else:
                    self.assertTrue(game.transition_active)
                    for _ in range(180):game.update(1/60,InputFrame())
                    self.assertEqual(game.level.chapter_index,page+1)
                    self.assertEqual(game.state,"playing")
                    self.assertFalse(game.transition_active)
                    self.assertNotIn("page_transition",game.player.control_locks)

    def test_rejected_warrior_uses_real_fold_combat_then_draws_its_optional_blade(self):
        from game import Game
        from input_state import InputFrame
        with tempfile.TemporaryDirectory() as directory:
            game=Game(pygame.display.get_surface(),Path(directory)/"trial.json")
            game.reset()
            game.level.load_chapter(0,"after_practice_crossouts",game.player,game.camera)
            game._attach_runtime()
            gift=next(e for e in game.level.entities.items
                if isinstance(e,WeaponPickup) and e.weapon_id=="folded_shuriken")
            player=game.player
            player.x,player.y=gift.x-12,gift.y-48
            for _ in range(90):game.update(1/60,InputFrame())
            self.assertTrue(gift.collected)
            trial=next(e for e in game.level.entities.items if isinstance(e,SketchTrial))
            player.x,player.y=trial.sketch.x-20,505-48
            player.vx=player.vy=0
            player.on_ground=True
            game.update(1/60,InputFrame(interact=True))
            self.assertTrue(trial.encounter_active)
            self.assertIs(game.level.director.canvas_owner,trial)
            seen=set()
            for frame in range(1200):
                enemy=next((e for e in trial.enemies if not e.dead),None)
                if trial.completed or game.level.respawn_timer:break
                if enemy:seen.add(enemy.kind)
                drop=player.on_ground and player.rect.bottom<570
                distance=enemy.x-player.center_x if enemy else 0
                toward=enemy is not None and abs(distance)>205
                retreat=enemy is not None and abs(distance)<90 and enemy.state=="idle"
                axis=((1 if distance>0 else -1) if toward else
                      -(1 if distance>0 else -1) if retreat else 0)
                # Read the frozen blade or pounce warning and cross the
                # committed line. Fire the same real returning fold throughout.
                dash=bool(enemy and player.dash_ready and abs(distance)<230 and (
                    (enemy.state in ("sheath","echo_telegraph","snicker")
                     and enemy.state_time<.09)
                    or enemy.state in ("draw_cut","echo_slash","pounce")))
                if dash:axis=1 if distance>0 else -1
                game.update(1/60,InputFrame(left=axis<0,right=axis>0,
                    down=drop,jump_pressed=drop,jump_held=drop,
                    attack_pressed=True,dash_pressed=dash,
                    aim_x=enemy.x if enemy else None,
                    aim_y=enemy.rect.centery-12 if enemy else None))
                if frame%90==0:game._draw_scene(game.screen)
            self.assertTrue(trial.completed)
            self.assertEqual(seen,{"fold_duelist","goblin_scribble"})
            self.assertEqual(game.behavior.count("deaths"),0)
            self.assertNotIn("pencil_blade",game.weapons.unlocked)
            self.assertEqual(trial.tool_gift.draw_progress,0)
            for _ in range(180):
                distance=trial.sketch.x-player.center_x
                jump=player.on_ground and not trial.sketch.discovered
                game.update(1/60,InputFrame(left=distance<-8,right=distance>8,
                    jump_pressed=jump,jump_held=jump,interact=True))
                if trial.sketch.discovered and trial.tool_gift.collected:break
            self.assertTrue(trial.sketch.discovered)
            self.assertTrue(trial.tool_gift.collected)
            self.assertEqual(game.weapons.current_id,"pencil_blade")
            self.assertIn("practice_monster",game.save.data["secrets"])
            self.assertIn("pencil_blade",game.save.data["weapons"])


if __name__=="__main__":unittest.main()
