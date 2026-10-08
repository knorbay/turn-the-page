"""The last page is reached and filled through real movement and four inputs."""
import os
from unittest.mock import patch
import unittest

os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")

import pygame

from afterword import Afterword
from camera import Camera
from input_state import InputFrame
from localization import SUPPORTED_LANGUAGES, get_language, set_language
from paper_renderer import PaperRenderer
from player import Player
from sketches import draw_sketch_icon
from world import PaperWorld


class SilentSounds:
    def __init__(self):self.played=[]
    def play(self,name):self.played.append(name)


class AfterwordContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1120,700))
        cls.renderer=PaperRenderer()

    @classmethod
    def tearDownClass(cls):pygame.quit()

    def setUp(self):
        self.afterword=Afterword()
        self.sounds=SilentSounds()
        self.language=get_language()
        self.addCleanup(set_language,self.language)

    def advance(self,seconds,frame=None):
        for _ in range(round(seconds*60)):
            self.afterword.update(1/60,frame or InputFrame(),self.sounds)

    def walk_to(self,x):
        for _ in range(2200):
            dx=x-self.afterword.player.center_x
            if abs(dx)<48:
                self.advance(.16)
                return
            self.afterword.update(1/60,InputFrame(right=dx>0,left=dx<0),self.sounds)
        self.fail(f"could not walk to {x}")

    def place_at(self,x):
        self.afterword.player.x=x-Player.WIDTH/2
        self.afterword.player.y=self.afterword.GROUND_Y-Player.HEIGHT
        self.afterword.player.vx=self.afterword.player.vy=0
        self.advance(.05)

    def draw_memory(self,memory):
        self.place_at(memory.x)
        self.afterword.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(self.afterword.DRAW_SECONDS+.1)
        self.assertTrue(memory.completed)

    def finish(self):
        for memory in self.afterword.memories:self.draw_memory(memory)
        self.place_at(self.afterword.SEAL_X)
        self.afterword.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(self.afterword.SIGN_SECONDS+.1)

    def test_real_player_camera_world_are_safe_unarmed_and_do_not_touch_campaign(self):
        scene=self.afterword
        self.assertIsInstance(scene.player,Player)
        self.assertIsInstance(scene.camera,Camera)
        self.assertIsInstance(scene.world,PaperWorld)
        self.assertEqual(scene.player.current_weapon,"unarmed")
        self.assertEqual(scene.player.health,3)
        self.assertTrue(scene.player.on_ground)
        self.assertFalse(hasattr(scene,"save"))
        self.assertFalse(scene.complete)
        self.assertEqual(scene.completed_memories,0)

    def test_waiting_and_running_to_the_far_edge_never_fill_or_finish_the_page(self):
        self.advance(60)
        self.advance(45,InputFrame(right=True))
        self.assertGreater(self.afterword.player.x,self.afterword.SEAL_X)
        self.assertFalse(self.afterword.complete)
        self.assertEqual(self.afterword.completed_memories,0)
        self.assertTrue(all(memory.progress==0 for memory in self.afterword.memories))
        self.assertEqual(self.afterword.seal_progress,0)
        self.assertIsNone(self.afterword.operation)

    def test_every_memory_and_signature_is_reachable_with_ground_movement_in_about_45_seconds(self):
        scene=self.afterword
        for memory in scene.memories:
            self.walk_to(memory.x)
            self.assertIs(scene.near_memory,memory)
            scene.update(1/60,InputFrame(interact=True),self.sounds)
            self.assertIs(scene.operation,memory)
            self.assertFalse(memory.completed)
            self.advance(scene.DRAW_SECONDS+.05)
            self.assertTrue(memory.completed)
            self.assertFalse(scene.player.locked)
        self.walk_to(scene.SEAL_X)
        self.assertTrue(scene.near_seal)
        self.assertFalse(scene.complete,"reaching the notebook is still not signing it")
        scene.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(scene.SIGN_SECONDS+.05)
        self.assertTrue(scene.complete)
        self.assertGreater(scene.time,43)
        self.assertLess(scene.time,53)
        self.assertEqual(scene.player.health,3)
        self.assertIn("page",self.sounds.played)

    def test_drawing_progress_is_visible_and_locked_but_the_player_must_start_it(self):
        memory=self.afterword.memories[0]
        self.place_at(memory.x)
        self.advance(10)
        self.assertEqual(memory.progress,0)
        self.afterword.update(1/60,InputFrame(interact=True),self.sounds)
        self.assertTrue(self.afterword.player.locked)
        start=self.afterword.player.x
        self.advance(self.afterword.DRAW_SECONDS/2,InputFrame(right=True,interact=True))
        self.assertGreater(memory.progress,.4)
        self.assertLess(memory.progress,.6)
        self.assertFalse(memory.completed)
        self.assertEqual(self.afterword.player.x,start)
        self.advance(self.afterword.DRAW_SECONDS/2+.05)
        self.assertEqual(memory.progress,1)
        self.assertTrue(memory.completed)
        self.assertFalse(self.afterword.player.locked)
        self.assertFalse(self.afterword.complete)

    def test_signing_rejects_missing_memory_even_when_other_two_are_done(self):
        for memory in self.afterword.memories[1:]:self.draw_memory(memory)
        self.place_at(self.afterword.SEAL_X)
        self.afterword.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(10)
        self.assertFalse(self.afterword.complete)
        self.assertEqual(self.afterword.seal_progress,0)
        self.assertIsNone(self.afterword.operation)
        self.assertEqual(self.afterword.completed_memories,2)
        self.assertEqual(self.afterword.note,"Leave room for every memory.")

    def test_signature_has_its_own_final_manual_drawing_and_cannot_replay_a_memory(self):
        scene=self.afterword
        for memory in scene.memories:self.draw_memory(memory)
        self.place_at(scene.memories[0].x)
        scene.update(1/60,InputFrame(interact=True),self.sounds)
        self.assertIsNone(scene.operation)
        self.place_at(scene.SEAL_X)
        self.advance(5)
        self.assertFalse(scene.complete)
        self.assertEqual(scene.seal_progress,0)
        scene.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(scene.SIGN_SECONDS/2)
        self.assertFalse(scene.complete)
        self.assertAlmostEqual(scene.seal_progress,.5,places=2)
        self.advance(scene.SIGN_SECONDS/2+.05)
        self.assertTrue(scene.complete)
        self.assertEqual(scene.seal_progress,1)
        self.assertFalse(scene.player.locked)

    def test_jump_release_and_optional_ledge_leave_all_ground_memories_safe(self):
        scene=self.afterword
        scene.update(1/60,InputFrame(jump_pressed=True,jump_held=True),self.sounds)
        self.assertLess(scene.player.vy,0)
        self.advance(.08)
        scene.update(1/60,InputFrame(jump_released=True),self.sounds)
        self.advance(1.1)
        self.assertTrue(scene.player.on_ground)
        self.assertEqual(scene.player.rect.bottom,scene.GROUND_Y)
        self.place_at(2180+100)
        scene.update(1/60,InputFrame(jump_pressed=True,jump_held=True),self.sounds)
        self.advance(1.0)
        self.assertTrue(scene.player.on_ground)
        self.assertEqual(scene.player.rect.bottom,505)
        scene.update(1/60,InputFrame(down=True,jump_pressed=True),self.sounds)
        self.advance(.7)
        self.assertEqual(scene.player.rect.bottom,scene.GROUND_Y)
        self.walk_to(scene.memories[1].x)
        self.assertIs(scene.near_memory,scene.memories[1])

    def test_kept_sketches_change_the_last_drawing_without_granting_rewards(self):
        keys=["agent_badge","water_tower","shrine_roof","unknown"]
        scene=Afterword(keys)
        keys.clear()
        self.assertEqual({sketch.secret_id for sketch in scene.kept_sketches},
                         {"agent_badge","water_tower","shrine_roof"})
        memory=scene.memories[2]
        memory.progress=1
        scene.camera.x=memory.x-560
        surface=pygame.Surface((1120,700))
        with patch("afterword.draw_sketch_icon",wraps=draw_sketch_icon) as icons:
            scene.draw(surface,self.renderer)
        drawn={call.args[1] for call in icons.call_args_list}
        self.assertTrue({sketch.icon for sketch in scene.kept_sketches}.issubset(drawn))
        self.assertEqual(scene.player.max_health,3)
        self.assertEqual(scene.player.current_weapon,"unarmed")

    def test_completed_menu_has_three_clickable_bounds_and_held_movement_does_not_double_navigate(self):
        self.finish()
        scene=self.afterword
        self.assertEqual(scene.actions,("REPLAY PAGES","BACK PAGES","TITLE"))
        rects=scene.action_rects()
        self.assertEqual(len(rects),3)
        screen=pygame.Rect(0,0,1120,700)
        for index,rect in enumerate(rects):
            self.assertTrue(screen.contains(rect))
            self.assertTrue(all(not rect.colliderect(other) for other in rects[index+1:]))
        scene.menu_index=2
        self.advance(2,InputFrame(right=True,down=True))
        self.assertEqual(scene.menu_index,2,"game menu events own selection exactly once")

    def test_blank_drawing_and_complete_menu_render_in_every_language_and_preserve_clip(self):
        scene=self.afterword
        surface=pygame.Surface((1120,700))
        blank=None
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            clip=pygame.Rect(12,12,1096,676)
            surface.set_clip(clip)
            scene.draw(surface,self.renderer,controller=language=="de")
            self.assertEqual(surface.get_clip(),clip)
            if blank is None:blank=pygame.image.tobytes(surface,"RGB")
        memory=scene.memories[0]
        self.place_at(memory.x)
        scene.update(1/60,InputFrame(interact=True),self.sounds)
        self.advance(1.8)
        scene.draw(surface,self.renderer)
        partial=pygame.image.tobytes(surface,"RGB")
        self.advance(1.9)
        scene.draw(surface,self.renderer)
        painted=pygame.image.tobytes(surface,"RGB")
        self.assertNotEqual(blank,partial)
        self.assertNotEqual(partial,painted)
        self.finish()
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            scene.draw(surface,self.renderer,controller=True)
            self.assertEqual(surface.get_clip(),clip)


if __name__=="__main__":unittest.main()
