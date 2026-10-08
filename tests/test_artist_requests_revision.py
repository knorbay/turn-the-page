"""The Artist observes fights; no request changes weapons or creatures."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame
from game import Game
from input_state import InputFrame
from notebook_agency import NotebookAgency
from adaptive_artist import AdaptiveArtist, CLOSE_TOOLS, SUPPORT_TOOLS
from advanced_enemies import InkSamurai
from page_arsenal import PAGE_ENTRY_TOOLS, draw_weapon_icon, label_for
from localization import set_language, translate
from save_system import SaveSystem
from settings import WIDTH, HEIGHT

class ObservedArtistContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init();cls.screen=pygame.display.set_mode((WIDTH,HEIGHT))
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'save.json'
        self.game=Game(self.screen,self.path);self.game.reset()
    def tearDown(self):self.temp.cleanup();set_language('tr')
    def load(self,page=0):
        g=self.game;g.level.load_chapter(page,'start',g.player,g.camera);g._attach_runtime()
        g.player.release_all_locks();g.player.draw_amount=1;g.save.checkpoint(page,'start')
        a=next(e for e in g.level.entities.items if isinstance(e,NotebookAgency))
        ctx=g.level.context(g.player,g.camera,g.particles,g.sounds);a._restore(ctx)
        return a,ctx
    def equip(self,page,weapon=None):
        w=self.game.weapons;weapon=weapon or PAGE_ENTRY_TOOLS[page]
        w.unlock(weapon);w.select(weapon);return w
    def finish(self,a,ctx):
        for _ in range(75):a.update(1/60,ctx)
        self.assertIsNone(a.operation);self.assertIsNone(ctx.director.canvas_owner)
    def activate(self,a,ctx):
        r=a.first;r.encounter_active=True;r.encounter_time=3.1
        r.enemies=[InkSamurai(r.start_x+240)]
        self.game.artist_director.prepare_encounter(r,ctx)
        return r
    def test_interaction_cannot_request_a_weapon_route_or_health(self):
        a,ctx=self.load();before=self.game.weapons.snapshot()
        for choice in ('tool','tool2','road','patch_player'):
            self.assertFalse(a.choose(choice,ctx))
        a.update(.1,ctx,True)
        self.assertIsNone(a.operation);self.assertEqual(before,self.game.weapons.snapshot())
        self.assertEqual(a.platforms,[])
    def test_every_page_draws_an_alternate_range_after_a_fight_without_switching(self):
        for page in range(5):
            with self.subTest(page=page):
                self.game.reset();a,ctx=self.load(page);w=self.equip(page)
                held=w.current_id;ammo=w.current.ammo
                a.first.completed=True;self.game.player.x=a.first.end_x+30
                a.update(.01,ctx)
                expected=CLOSE_TOOLS[page] if page<4 else 'rubber_band'
                self.assertEqual(a.operation,'support_tool');self.assertEqual(a.selected_weapon,expected)
                self.assertNotIn(expected,w.unlocked);self.finish(a,ctx)
                self.assertIn(expected,w.available_ids);self.assertEqual(w.current_id,held)
                self.assertEqual(w.current.ammo,ammo)
                saved=SaveSystem(self.path)
                self.assertIn(expected,saved.data['artist_adaptation']['gifts'][str(page)])
                self.game.continue_game()
                restored=next(e for e in self.game.level.entities.items if isinstance(e,NotebookAgency))
                restored.update(0,self.game.level.context(self.game.player,self.game.camera,self.game.particles,self.game.sounds))
                self.assertIn(expected,self.game.weapons.available_ids)
                self.assertEqual(self.game.weapons.current_id,held)
    def test_low_health_triggers_once_without_interaction_or_enemy_erasure(self):
        a,ctx=self.load();r=self.activate(a,ctx);enemy=r.enemies[0];hp=enemy.hp
        self.game.player.health=1;a.update(.01,ctx)
        self.assertEqual(a.operation,'patch_player');self.finish(a,ctx)
        self.assertEqual(self.game.player.health,2);self.assertEqual(enemy.hp,hp)
        self.assertFalse(enemy.dead);self.assertFalse(getattr(enemy,'artist_erasing',False))
        self.assertFalse(r.completed);self.assertFalse(hasattr(a,'pets'))
        self.game.player.health=1;a.update(.01,ctx);self.assertIsNone(a.operation)
    def test_real_death_and_redraw_record_difficulty_and_keep_support_on_retry(self):
        a,ctx=self.load();r=self.activate(a,ctx);self.game.player.x=r.start_x+110
        arena_id=r.arena_id
        for attempt in range(2):
            self.game.player.health=0;self.game.level.begin_respawn(self.game.player,'ink_samurai',self.game.particles,self.game.sounds)
            self.assertGreater(self.game.level.respawn_timer,0)
            for _ in range(240):self.game.update(1/60,InputFrame())
            self.assertEqual(self.game.level.respawn_timer,0)
            self.game.player.release_all_locks()
            r=next(e for e in self.game.level.entities.items if getattr(e,'arena_id',None)==arena_id)
            ctx=self.game.level.context(self.game.player,self.game.camera,self.game.particles,self.game.sounds)
            r.encounter_active=True;r.encounter_time=3.1;r.enemies=[InkSamurai(r.start_x+240)]
        self.assertEqual(self.game.artist_director.room(0,r)['deaths'],2)
        self.assertEqual(self.game.artist_director.mode_for(0,r),'support')
        self.game.persist_behavior(write=True)
        self.assertEqual(AdaptiveArtist(SaveSystem(self.path).data['artist_adaptation']).mode_for(0,r),'support')
    def test_three_losses_draw_a_stronger_tool_without_replacing_the_held_one(self):
        a,ctx=self.load(3);w=self.equip(3);held=w.current_id;ammo=w.current.ammo
        self.game.artist_director.room(3,a.first)['deaths']=3
        r=self.activate(a,ctx);self.game.player.health=3;a.update(.01,ctx)
        self.assertEqual(a.selected_weapon,SUPPORT_TOOLS[3]);self.assertEqual(a.operation,'support_tool')
        self.finish(a,ctx);self.assertEqual(w.current_id,held);self.assertEqual(w.current.ammo,ammo)
        self.assertIn(SUPPORT_TOOLS[3],w.available_ids)
    def test_clean_wins_add_one_regular_foe_but_never_boss_guards(self):
        a,ctx=self.load();p=self.game.artist_director
        p.data['recent']=[{'result':'clear','damage':0,'seconds':22,'boss':False}]*2
        room=a.first;original=len(room.enemy_specs);p.prepare_encounter(room,ctx)
        self.assertEqual(len(room.enemy_specs),original+1)
        self.assertEqual(sum(s.get('artist_challenge',False) for s in room.enemy_specs),1)
        p.prepare_encounter(room,ctx);self.assertEqual(len(room.enemy_specs),original+1)
        boss=next(r for r in a.arenas if r.boss);original=list(boss.enemy_specs)
        p.prepare_encounter(boss,ctx);self.assertEqual(boss.enemy_specs,original)
    def test_authored_interlude_deaths_do_not_count_as_player_failure(self):
        a,ctx=self.load(2);r=next(r for r in a.arenas if r.arena_id=='baby_face_interlude')
        p=self.game.artist_director;p.observe_death(r,ctx,'baby_face_giant')
        self.assertEqual(p.data['recent'],[]);self.assertEqual(p.mode_for(2,r),'standard')
    def test_actual_tool_reveal_uses_its_own_drawing_and_restores_clip(self):
        a,ctx=self.load(3);self.equip(3);self.game.artist_director.room(3,a.first)['deaths']=3
        self.activate(a,ctx);a.update(.575,ctx)
        camera=self.game.camera;camera.x=a.gift_x-500;camera.offset_y=95
        surface=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA);clip=pygame.Rect(80,200,900,400);surface.set_clip(clip)
        with patch('notebook_agency.draw_weapon_icon',wraps=draw_weapon_icon) as draw:a.draw(surface,camera,self.game.renderer)
        self.assertEqual(draw.call_args.args[1],SUPPORT_TOOLS[3])
        self.assertEqual(draw.call_args.args[3],(camera.screen_x(a.gift_x),a.gift_y+95))
        self.assertEqual(surface.get_clip(),clip)
    def test_automatic_dialogue_and_added_tool_are_fully_turkish(self):
        a,ctx=self.load(3);self.equip(3);self.game.artist_director.room(3,a.first)['deaths']=3
        self.activate(a,ctx);a.update(.01,ctx);set_language('tr')
        self.assertNotEqual(translate(a.letter),a.letter)
        text=translate('TOOL ADDED — '+label_for(3,'carbon_lance')+' / Q to try it')
        self.assertIn('KARBON',text);self.assertNotIn('try',text)
        self.assertEqual(translate('CLEAR THE ROOM'),'ODAYI TEMİZLE')
    def test_incomplete_observed_drawing_is_cancelled_on_death(self):
        a,ctx=self.load(3);self.equip(3);self.game.artist_director.room(3,a.first)['deaths']=3
        self.activate(a,ctx);a.update(.25,ctx);self.game.player.health=0;a.update(.01,ctx)
        self.assertIsNone(a.operation);self.assertIsNone(ctx.director.canvas_owner)
        self.assertNotIn(SUPPORT_TOOLS[3],self.game.weapons.unlocked)
        self.assertNotIn('3',self.game.save.data['artist_adaptation'].get('gifts',{}))
    def test_old_requested_tools_and_routes_still_restore_without_a_new_menu(self):
        a,ctx=self.load();self.game.save.data['notebook_choices']={'0':'tool2'}
        self.game.save.data['notebook_tools']={'0':'chalk_bomb'};a._restore(ctx)
        self.assertIn('chalk_bomb',self.game.weapons.unlocked);self.assertFalse(a.choose('road',ctx))
        self.game.save.data['notebook_choices']={'0':'road'};a._restore(ctx)
        self.assertTrue(all(p.collision_rects() for p in a.platforms))

if __name__=='__main__':unittest.main()
