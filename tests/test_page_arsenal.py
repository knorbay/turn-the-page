"""Player-facing arsenal contracts: page handling, earned tools, and counterplay."""
import math
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pygame

from camera import Camera
from page_arsenal import draw_weapon, draw_weapon_icon
from particles import ParticleSystem
from player import Player
from weapons import WeaponSystem
from world import PaperWorld


class PageArsenalContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120,700))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setup_weapon(self,page,weapon_id):
        player=Player(100,542)
        system=WeaponSystem(player)
        system.configure_page(page)
        system.unlock(weapon_id)
        system.select(weapon_id)
        world=PaperWorld(page=(page or 0)+1,build_legacy=False)
        world.width=1200
        ctx=SimpleNamespace(player=player,world=world,particles=ParticleSystem(),
                            sounds=SimpleNamespace(play=lambda _:None),camera=Camera(1120),
                            game=SimpleNamespace(hit_stop=0))
        ctx.weapons=system
        return system,ctx

    def test_page_change_does_not_grant_tools_and_checkpoint_keeps_magazine(self):
        system,ctx=self.setup_weapon(1,"ink_pistol")
        system.current.ammo=2
        system.configure_page(1)
        self.assertEqual(system.current.ammo,2,"reapplying a page cannot refill a magazine")
        checkpoint=system.snapshot()
        restored=WeaponSystem(Player())
        restored.configure_page(1)
        restored.restore(checkpoint)
        self.assertEqual(restored.current.mag_size,6)
        self.assertEqual(restored.current.ammo,2)
        self.assertEqual(restored.unlocked,{"pencil_blade","ink_pistol"})
        restored.configure_page(3)
        self.assertEqual(restored.current.mag_size,9)
        self.assertEqual(restored.unlocked,{"pencil_blade","ink_pistol"})
        self.assertEqual(restored.label_for(),"SUPPRESSED PISTOL")

    def test_western_revolver_and_agent_pistol_change_actual_fire_rhythm(self):
        results=[]
        for page in (1,3):
            system,ctx=self.setup_weapon(page,"ink_pistol")
            count=0
            for _ in range(90):
                count+=bool(system.handle_input(fire_held=True,aim={"direction":(1,0)},ctx=ctx))
                system.update(1/60,ctx,[])
            results.append((count,ctx.player.vx,system.current.ammo))
        self.assertEqual(results[0][0],4)
        self.assertEqual(results[1][0],6)
        self.assertLess(results[0][1],-60,"revolver should have a physical recoil impulse")
        self.assertEqual(results[1][1],0,"silenced pistol lets a running agent keep momentum")
        self.assertEqual(results[0][2],2)
        self.assertEqual(results[1][2],3)

    def test_two_barrels_reload_after_second_shot_and_breach_has_tighter_coverage(self):
        west,ctx=self.setup_weapon(1,"marker_shotgun")
        self.assertTrue(west.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx))
        self.assertFalse(west.current.reloading)
        spread_west=max(abs(math.degrees(math.atan2(p.vy,p.vx))) for p in west.projectiles)
        for _ in range(37): west.update(1/60,ctx,[])
        self.assertTrue(west.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx))
        self.assertTrue(west.current.reloading)
        self.assertEqual(west.current.ammo,0)
        self.assertFalse(west.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx))
        agent,ctx=self.setup_weapon(3,"marker_shotgun")
        agent.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        spread_agent=max(abs(math.degrees(math.atan2(p.vy,p.vx))) for p in agent.projectiles)
        self.assertLess(spread_agent,spread_west/2)
        # A flank target inside the Western scatter cone but outside the
        # agent's narrow corridor is an actual shot-placement decision.
        for page,expected in ((1,True),(3,False)):
            system,ctx=self.setup_weapon(page,"marker_shotgun")
            flank=SimpleNamespace(rect=pygame.Rect(244,583,14,14),hp=10,dead=False,active=True,vx=0)
            system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
            for _ in range(24): system.update(1/60,ctx,[flank])
            self.assertEqual(flank.hp<10,expected,(page,flank.hp))

    def test_orbit_pulse_banks_off_ink_and_hits_target_behind_player(self):
        system,ctx=self.setup_weapon(2,"rubber_band")
        ctx.world.add(225,245,480,150,"bank_wall",1)
        target=SimpleNamespace(rect=pygame.Rect(55,547,20,30),hp=3,dead=False,active=True,vx=0)
        system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        shot=system.projectiles[0]
        start_y=shot.y
        self.assertEqual(shot.bounces,3)
        for _ in range(28): system.update(1/60,ctx,[target])
        self.assertLess(target.hp,3,"a banked pulse must remain capable of dealing damage")
        self.assertEqual(shot.y,start_y,"orbit pulses do not sag under gravity")
        self.assertEqual(shot.visual,"pulse")

    def test_null_cannon_erases_a_wider_volley_and_has_straight_flight(self):
        system,ctx=self.setup_weapon(2,"eraser_cannon")
        system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        shot=system.projectiles[0]
        start_y=shot.y
        hostile=SimpleNamespace(rect=pygame.Rect(round(shot.x+16),round(shot.y+35),8,8),life=3)
        enemy=SimpleNamespace(rect=pygame.Rect(900,540,25,50),hp=3,dead=False,active=True,vx=0,
                              projectiles=[hostile])
        for _ in range(12): system.update(1/60,ctx,[enemy])
        self.assertEqual(hostile.life,0)
        self.assertEqual(shot.y,start_y)
        self.assertEqual(shot.pierce,2)

    def test_sketch_bonuses_change_reach_reload_pierce_and_orbit_flight(self):
        system,ctx=self.setup_weapon(0,"pencil_blade")
        system.combo_index=2;system.combo_window=1
        ctx.player.sketch_finisher_reach=12
        system.handle_input(fire_pressed=True,ctx=ctx)
        self.assertAlmostEqual(system.melee.reach,91*1.18+12)
        system,ctx=self.setup_weapon(3,"ink_pistol")
        ctx.player.sketch_pistol_reload=.85
        ctx.player.sketch_pistol_pierce=1
        ctx.player.sketch_pistol_velocity=1.2
        system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
        self.assertEqual(system.projectiles[0].pierce,1)
        self.assertAlmostEqual(system.projectiles[0].vx,960*1.2)
        system.reload()
        self.assertAlmostEqual(system.current.reload_timer,1.12*.85)
        system,ctx=self.setup_weapon(2,"rubber_band")
        ctx.player.sketch_rubber_bounces=1
        ctx.player.sketch_rubber_lifetime=1.25
        system.handle_input(fire_pressed=True,ctx=ctx)
        self.assertEqual(system.projectiles[0].bounces,4)
        self.assertAlmostEqual(system.projectiles[0].life,2.7*1.25)

    def test_inventory_draws_only_earned_allowed_silhouettes_without_slot_numbers(self):
        system,ctx=self.setup_weapon(1,"pencil_blade")
        system.set_page_loadout(("pencil_blade","ink_pistol","marker_shotgun"))
        surface=pygame.Surface((1120,700))
        calls=[]
        renderer=SimpleNamespace(font_small=None,doodle_text=lambda surf,text,*args:calls.append(text))
        with patch.object(system,"draw_icon") as icon:
            system.draw_hud(surface,renderer)
            self.assertEqual([c.args[1] for c in icon.call_args_list],["pencil_blade"])
            self.assertNotIn("Q / wheel",calls)
            system.unlock("eraser_cannon")
            system.unlock("ink_pistol")
            icon.reset_mock();calls.clear()
            system.draw_hud(surface,renderer)
            self.assertEqual([c.args[1] for c in icon.call_args_list],["pencil_blade","ink_pistol"])
            self.assertIn("Q / wheel",calls)
            self.assertFalse(any(text in ("1","2","3","4","5","6") for text in calls))

    def test_page_profiles_keep_signature_sword_attack_exactly_unchanged(self):
        signature=[]
        for page in (None,0,1,2,3,4):
            system,ctx=self.setup_weapon(page,"excalibur")
            system.handle_input(fire_pressed=True,aim={"direction":(1,0)},ctx=ctx)
            swing=system.melee
            signature.append((swing.duration,swing.active_from,swing.active_to,swing.damage,
                              swing.reach,swing.knockback,system.current.cooldown,ctx.player.vx))
        self.assertTrue(all(item==signature[0] for item in signature))

    def test_every_profile_has_a_distinct_reusable_drawn_silhouette(self):
        images=[]
        for page in range(5):
            surface=pygame.Surface((120,100));surface.fill((245,236,213))
            draw_weapon(surface,"pencil_blade",page,(40,50),angle=-.25)
            images.append(pygame.image.tobytes(surface,"RGB"))
            for weapon_id in ("ink_pistol","marker_shotgun","eraser_cannon","rubber_band","excalibur"):
                draw_weapon_icon(surface,weapon_id,page,(50,50))
        self.assertEqual(len(set(images)),5)

    def test_aiming_left_mirrors_firearms_without_turning_grips_upside_down(self):
        for page,weapon_id in ((1,"ink_pistol"),(1,"marker_shotgun"),(2,"rubber_band"),
                               (2,"eraser_cannon"),(3,"ink_pistol"),(3,"marker_shotgun")):
            right=pygame.Surface((121,101),pygame.SRCALPHA)
            left=right.copy()
            draw_weapon(right,weapon_id,page,(60,50))
            draw_weapon(left,weapon_id,page,(60,50),angle=math.pi)
            expected=pygame.transform.flip(right,True,False).get_bounding_rect()
            actual=left.get_bounding_rect()
            # Pygame gives even-width strokes a one-pixel raster bias, so
            # compare shape extents rather than demanding mirrored pixels.
            self.assertEqual(actual.top,expected.top,(page,weapon_id))
            self.assertEqual(actual.bottom,expected.bottom,(page,weapon_id))
            self.assertLessEqual(abs(actual.left-expected.left),1)
            self.assertLessEqual(abs(actual.right-expected.right),1)

    def test_buffered_followup_waits_for_finisher_recovery(self):
        system,ctx=self.setup_weapon(0,"pencil_blade")
        system.combo_index=2;system.combo_window=1
        system.handle_input(fire_pressed=True,ctx=ctx)
        self.assertGreater(system.current.cooldown,system.melee.active_to)
        for _ in range(20):system.update(1/60,ctx,[])
        self.assertFalse(system.handle_input(fire_pressed=True,ctx=ctx))
        self.assertEqual(system.attack_serial,1)
        fired=False
        for _ in range(7):
            system.update(1/60,ctx,[])
            fired=system.handle_input(ctx=ctx) or fired
        self.assertTrue(fired,"the buffered tap should launch after the committed finishing stroke")
        self.assertEqual(system.attack_serial,2)

    def test_lethal_frame_cannot_fire_before_the_redraw_lock_arrives(self):
        system,ctx=self.setup_weapon(3,"ink_pistol")
        ctx.player.health=0
        ctx.player.control_locks.clear()
        self.assertFalse(system.handle_input(fire_pressed=True,fire_held=True,ctx=ctx))
        self.assertEqual(system.current.ammo,system.current.mag_size)
        self.assertFalse(system.projectiles)


if __name__=="__main__":unittest.main()
