from __future__ import annotations

import math
import pygame

from achievements import ACHIEVEMENTS, AchievementTracker
from major_update import ArtistCompanion
from audio import NotebookSounds
from behavior import BehaviorLedger
from camera import Camera
from chapters import CHAPTER_TITLES
from input_state import InputFrame
from level import Level
from paper_renderer import PaperRenderer, jitter_line
from particles import ParticleSystem
from player import Player
from save_system import SaveSystem
from settings import HEIGHT, INK, INK_LIGHT, RED_RULE, VERSION, WIDTH
from weapons import WEAPON_ORDER, WeaponSystem
from sketches import SKETCHES, apply_sketch_rewards, draw_sketch_card, wrap_text
from health_hud import draw_health
from localization import (translate, set_language, LocalizedFont,
                          SUPPORTED_LANGUAGES, LANGUAGE_NAMES, normalize_language)


WINDOW_PRESETS = ((1120, 700), (1280, 800), (1440, 900), (1680, 1050), (1920, 1200))
MIN_WINDOW_SIZE = (800, 500)
MUSIC_CREDITS_RECT = pygame.Rect(857, 646, 224, 34)
LANGUAGE_RECT = pygame.Rect(792, 32, 289, 36)


def fitted_label(font, text, color, max_width):
    """Keep translated labels inside their allotted row without dropping words."""
    image = font.render(text, True, color)
    if image.get_width() > max_width:
        height = max(1, round(image.get_height() * max_width / image.get_width()))
        image = pygame.transform.smoothscale(image, (max_width, height))
    return image


class Game:
    def __init__(self, screen: pygame.Surface, save_path=None):
        self.clock = pygame.time.Clock()
        self.save = SaveSystem(save_path)
        self.display = screen
        self.screen = pygame.Surface((WIDTH, HEIGHT)).convert()
        settings = self.save.data["settings"]
        set_language(settings["language"])
        self.windowed_size = self._bounded_window_size(
            (settings["window_width"], settings["window_height"])
        )
        self.fullscreen = False
        self.viewport = pygame.Rect(0, 0, WIDTH, HEIGHT)
        self._configure_initial_display()
        self.renderer = PaperRenderer()
        self.behavior = BehaviorLedger(self.save.data.get("behavior"))
        from adaptive_artist import AdaptiveArtist
        self.artist_director = AdaptiveArtist(self.save.data.get("artist_adaptation"))
        self.artist_companion = ArtistCompanion()
        self.achievements = AchievementTracker(self.save)
        self.achievement_banner = None
        self.achievement_time = 0.0
        self.sounds = NotebookSounds()
        self.sounds.apply_settings(settings)
        self.camera = Camera(WIDTH)
        from boss_cinematic import BossCinematic
        self.boss_cinematic = BossCinematic(self)
        self.particles = ParticleSystem()
        self.player = Player()
        self.level = Level(self.save, 0, "start")
        self.level.load_chapter(0, "start", self.player, self.camera)
        self.weapons = WeaponSystem(self.player)
        self._restore_weapons()
        self._attach_runtime()
        self.state = "title"
        self.previous_state = "title"
        self.time = 0.0
        self.session_seconds = float(self.save.data.get("play_seconds", 0))
        self.page_started_at = self.session_seconds
        self.running = True
        self.pending_input = InputFrame()
        self.menu_index = 0
        self.settings_index = 0
        self.pause_index = 0
        self.dragging_volume_index = None
        self.joysticks = {}
        self.last_input_device = "keyboard"
        self._connect_existing_joysticks()
        self.transition_active = False
        self.transition_progress = 0.0
        self.transition_snapshot = None
        self.transition_sound_stage = 0
        self.transition_weapon_erased = False
        self.transition_erased_label = ""
        self.ending_time = 0.0
        self.ending_tools_erased = False
        self.blank_player_x = 180.0
        self.hit_stop = 0.0
        self.damage_flash = 0.0
        self._buffered_actions = InputFrame()
        self.cursor_visible = True
        pygame.mouse.set_visible(False)
        self.sounds.start_ambience(0)

    def reset(self, new_game=True):
        if new_game:
            self.save.new_game()
        self.behavior = BehaviorLedger(self.save.data.get("behavior"))
        from adaptive_artist import AdaptiveArtist
        self.artist_director = AdaptiveArtist(self.save.data.get("artist_adaptation"))
        self.artist_companion = ArtistCompanion()
        self.achievements = AchievementTracker(self.save)
        self.achievement_banner = None
        self.achievement_time = 0.0
        self.session_seconds = 0
        self.page_started_at = 0
        self.particles = ParticleSystem()
        self.player = Player()
        self.camera = Camera(WIDTH)
        self.level = Level(self.save, 0, "start")
        self.level.load_chapter(0, "start", self.player, self.camera)
        self.weapons = WeaponSystem(self.player)
        self._restore_weapons()
        self._attach_runtime()
        self.transition_active = False
        self.transition_snapshot = None
        self.transition_sound_stage = 0
        self.transition_weapon_erased = False
        self.transition_erased_label = ""
        self.hit_stop = 0.0
        self.damage_flash = 0.0
        self._buffered_actions = InputFrame()
        self.state = "playing"
        self.sounds.set_combat(False)
        self.sounds.start_ambience(0)

    def continue_game(self):
        self.behavior = BehaviorLedger(self.save.data.get("behavior"))
        from adaptive_artist import AdaptiveArtist
        self.artist_director = AdaptiveArtist(self.save.data.get("artist_adaptation"))
        self.artist_companion = ArtistCompanion()
        self.achievements = AchievementTracker(self.save)
        self.achievement_banner = None
        self.achievement_time = 0.0
        self.particles = ParticleSystem()
        self.player = Player()
        self.camera = Camera(WIDTH)
        index = int(self.save.data.get("chapter", 0))
        checkpoint = str(self.save.data.get("checkpoint", "start"))
        self.level = Level(self.save, index, checkpoint)
        self.level.load_chapter(index, checkpoint, self.player, self.camera)
        self.weapons = WeaponSystem(self.player)
        self._restore_weapons()
        self._attach_runtime()
        self.session_seconds = float(self.save.data.get("play_seconds", 0))
        self.page_started_at = self.session_seconds
        self.hit_stop = 0.0
        self.damage_flash = 0.0
        self._buffered_actions = InputFrame()
        self.transition_active = False
        self.transition_snapshot = None
        self.transition_sound_stage = 0
        self.transition_weapon_erased = False
        self.ending_time = 0.0
        self.state = "playing"
        self.sounds.set_combat(False)
        self.sounds.start_ambience(index)

    def _restore_weapons(self):
        self.weapons.configure_page(self.level.chapter_index)
        self.weapons.restore({
            "unlocked": self.save.data.get("weapons", []),
            "current_id": self.save.data.get("current_weapon", "unarmed"),
            "ammo": self.save.data.get("weapon_ammo", {}),
        })

    def _attach_runtime(self):
        if hasattr(self, "boss_cinematic"):
            self.boss_cinematic.cancel()
        self.level.weapons = self.weapons
        self.level.game = self
        self._apply_page_identity()
        self._visual_weapon_id = self.weapons.current_id
        self.weapon_reveal_time = 0.0

    def _apply_page_identity(self):
        """Each world owns its temporary tools and player silhouette."""
        self.weapons.configure_page(self.level.chapter_index)
        apply_sketch_rewards(self.player, self.save.data.get("secrets", []))
        from page_arsenal import loadout_for, PAGE_ENTRY_TOOLS
        allowed = set(loadout_for(self.level.chapter_index))
        page_key = str(self.level.chapter_index)
        request = self.save.data.get("notebook_choices", {}).get(page_key)
        has_requested_tool = request in ("tool", "tool2")
        if has_requested_tool:
            from notebook_agency import NotebookAgency
            from weapons import WEAPON_ORDER
            requested = self.save.data.get("notebook_tools", {}).get(page_key, "margin_maul")
            if requested not in WEAPON_ORDER:
                requested = NotebookAgency.TOOL_OFFERS[self.level.chapter_index][request == "tool2"]
            allowed.add(requested)
        gifts = self.artist_director.gifts_for(self.level.chapter_index)
        allowed.update(gifts)
        self.weapons.constrain_page_inventory(
            allowed, reset=self.level.current_checkpoint == "start" and not (has_requested_tool or gifts))
        self.weapons.set_page_loadout(allowed)
        if (self.level.current_checkpoint not in ("start", "alive") and
                self.weapons.current_id == "unarmed"):
            # Older checkpoints can predate the page-owned loadout. Reuse
            # its entry drawing beside the redraw, rather than silently
            # granting a sword or leaving a restored fight unwinnable.
            from action_content import WeaponPickup
            tool = PAGE_ENTRY_TOOLS[self.level.chapter_index]
            pickup = next((entity for entity in self.level.entities.items
                           if isinstance(entity, WeaponPickup)
                           and entity.weapon_id == tool), None)
            if pickup is not None:
                pickup.x = self.player.center_x + 72
                pickup.y = self.player.rect.bottom
                pickup.collected = pickup.completed = False
                pickup.authored_by_director = False
                pickup.drawing = False
                pickup.draw_progress = 0
                pickup.draw_sound_played = False
        page_style = {
            0: "ronin",
            1: "cowboy",
            2: "astronaut",
            3: "ink_agent",
            4: "bad_drawing",
        }.get(self.level.chapter_index, "plain")
        if self.level.chapter_index in (0, 1, 2, 3, 4) and self.level.current_checkpoint == "start":
            page_style = "plain"
        self.player.page_style = page_style

    def persist_behavior(self, write=False):
        self.save.data["artist_adaptation"] = self.artist_director.snapshot()
        self.save.update_behavior(self.behavior.snapshot(), write=write)

    def run(self):
        while self.running:
            dt = min(.033, self.clock.tick(60) / 1000.0)
            self.handle_events()
            self.update(dt)
            self.draw()
            self._present()
            pygame.display.flip()
        self.save.write()

    @staticmethod
    def _bounded_window_size(size):
        try:
            width, height = int(size[0]), int(size[1])
        except (TypeError, ValueError, IndexError):
            return WIDTH, HEIGHT
        return max(MIN_WINDOW_SIZE[0], min(7680, width)), \
            max(MIN_WINDOW_SIZE[1], min(4320, height))

    def _configure_initial_display(self):
        settings = self.save.data["settings"]
        try:
            if settings.get("fullscreen", False):
                # The temporary startup surface is not the user's saved
                # windowed size, so do not remember it as the return target.
                self.fullscreen = True
                self._set_display_mode(fullscreen=True)
            elif self.display.get_size() != self.windowed_size:
                self._set_display_mode(self.windowed_size, fullscreen=False)
            else:
                self._refresh_viewport()
        except pygame.error:
            settings["fullscreen"] = False
            self.fullscreen = False
            self.display = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            self._refresh_viewport()

    def _set_display_mode(self, size=None, fullscreen=None):
        fullscreen = self.fullscreen if fullscreen is None else bool(fullscreen)
        if fullscreen:
            if not self.fullscreen:
                current = self.display.get_size()
                if current[0] >= MIN_WINDOW_SIZE[0] and current[1] >= MIN_WINDOW_SIZE[1]:
                    self.windowed_size = self._bounded_window_size(current)
            self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.windowed_size = self._bounded_window_size(size or self.windowed_size)
            self.display = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self.fullscreen = fullscreen
        self._refresh_viewport()

    def _refresh_viewport(self):
        display_width, display_height = self.display.get_size()
        scale = min(display_width / WIDTH, display_height / HEIGHT)
        view_width = max(1, round(WIDTH * scale))
        view_height = max(1, round(HEIGHT * scale))
        self.viewport = pygame.Rect(
            (display_width - view_width) // 2,
            (display_height - view_height) // 2,
            view_width,
            view_height,
        )

    def _present(self):
        """Scale the fixed art canvas into any window without distorting it."""
        if self.display.get_size() == (WIDTH, HEIGHT):
            self.display.blit(self.screen, (0, 0))
            return
        self.display.fill((24, 23, 22))
        scaled = pygame.transform.smoothscale(self.screen, self.viewport.size)
        self.display.blit(scaled, self.viewport.topleft)

    def _window_to_canvas(self, pos, clamp=False):
        if self.viewport.width <= 0 or self.viewport.height <= 0:
            return None
        x, y = pos
        if not self.viewport.collidepoint(x, y):
            if not clamp:
                return None
            x = max(self.viewport.left, min(self.viewport.right - 1, x))
            y = max(self.viewport.top, min(self.viewport.bottom - 1, y))
        canvas_x = (x - self.viewport.x) * WIDTH / self.viewport.width
        canvas_y = (y - self.viewport.y) * HEIGHT / self.viewport.height
        return canvas_x, canvas_y

    def _remember_window_size(self, write=False):
        self.save.update_settings({
            "window_width": self.windowed_size[0],
            "window_height": self.windowed_size[1],
            "fullscreen": self.fullscreen,
        }, write=write)

    def handle_events(self):
        self.pending_input.jump_pressed = False
        self.pending_input.jump_released = False
        self.pending_input.interact = False
        self.pending_input.attack_pressed = False
        self.pending_input.dash_pressed = False
        self.pending_input.reload_pressed = False
        self.pending_input.weapon_slot = None
        self.pending_input.weapon_cycle = 0
        self.pending_input.pause = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
                if self.state == "playing":
                    self.state = "pause"
                    self.pause_index = 0
                    self.pending_input = InputFrame()
                    self._buffered_actions = InputFrame()
            elif event.type == pygame.JOYDEVICEADDED:
                self._connect_joystick(event.device_index)
            elif event.type == pygame.JOYDEVICEREMOVED:
                self.joysticks.pop(event.instance_id, None)
            elif event.type == pygame.JOYBUTTONDOWN:
                self.last_input_device = "controller"
                self._controller_button_down(event.button)
            elif event.type == pygame.JOYBUTTONUP:
                self.last_input_device = "controller"
                self._controller_button_up(event.button)
            elif event.type == pygame.JOYHATMOTION:
                self.last_input_device = "controller"
                self._controller_hat(event.value)
            elif event.type == pygame.JOYAXISMOTION:
                self.last_input_device = "controller"
            elif event.type == pygame.VIDEORESIZE and not self.fullscreen:
                self._set_display_mode(event.size, fullscreen=False)
                self._remember_window_size(write=False)
            elif event.type == pygame.KEYDOWN:
                self.last_input_device = "keyboard"
                self._key_down(event.key)
            elif event.type == pygame.KEYUP and event.key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.pending_input.jump_released = True
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.last_input_device = "mouse"
                if self.state == "playing":
                    self.pending_input.attack_pressed = True
                else:
                    self._mouse_click(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                self.last_input_device = "mouse"
                if self.dragging_volume_index is not None:
                    pos = self._window_to_canvas(event.pos, clamp=True)
                    if pos is not None:
                        self._set_volume_from_canvas(pos[0], write=False)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.last_input_device = "mouse"
                if self.dragging_volume_index is not None:
                    pos = self._window_to_canvas(event.pos, clamp=True)
                    if pos is not None:
                        self._set_volume_from_canvas(pos[0], write=True)
                    self.dragging_volume_index = None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 3 and self.state == "playing":
                self.last_input_device = "mouse"
                self.pending_input.dash_pressed = True
            elif event.type == pygame.MOUSEWHEEL and self.state == "playing":
                self.last_input_device = "mouse"
                self.pending_input.weapon_cycle = -1 if event.y > 0 else 1

    def _connect_existing_joysticks(self):
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        for device_index in range(pygame.joystick.get_count()):
            self._connect_joystick(device_index)

    def _connect_joystick(self, device_index):
        try:
            joystick = pygame.joystick.Joystick(device_index)
            joystick.init()
            instance_id = (joystick.get_instance_id()
                           if hasattr(joystick, "get_instance_id") else joystick.get_id())
            self.joysticks[instance_id] = joystick
            if hasattr(self, "level"):
                self.level.toast = "CONTROLLER READY"
                self.level.toast_time = 2.0
        except pygame.error:
            return

    def _active_joystick(self):
        return next(iter(self.joysticks.values()), None)

    def _controller_button_down(self, button):
        # SDL's common pad order maps 0/1/2/3 to south/east/west/north.
        if self.state == "playing":
            if button == 0:
                self.pending_input.jump_pressed = True
            elif button == 1:
                self.pending_input.dash_pressed = True
            elif button == 2:
                self.pending_input.attack_pressed = True
            elif button == 3:
                self.pending_input.interact = True
            elif button == 4:
                self.pending_input.weapon_cycle = -1
            elif button == 5:
                self.pending_input.reload_pressed = True
            elif button == 7:
                self.pause_index = 0
                self.state = "pause"
        elif self.state == "title":
            if button == 0:
                options = self._title_options()
                self._activate_title(options[self.menu_index % len(options)])
            elif button == 3:
                self.previous_state, self.state = "title", "credits"
        elif self.state == "pause":
            if button == 0:
                options = self._pause_options()
                self._activate_pause(options[self.pause_index % len(options)])
            elif button in (1, 7):
                self.state = "playing"
        elif self.state == "settings":
            if button == 0:
                if self.settings_index in (3, 4, 5):
                    self._change_setting(1)
                elif self.settings_index == 6:
                    self._return_to_previous()
            elif button == 1:
                self._return_to_previous()
        elif self.state == "back_pages":
            if button in (0, 1):
                self._return_to_previous()
            elif button in (4, 5):
                self.sketch_page = (getattr(self,"sketch_page",0)+(-1 if button==4 else 1)) % ((len(SKETCHES)+8)//9)
        elif self.state == "credits":
            if button in (0, 1):
                self._return_to_previous()
            elif button in (4, 5):
                self._turn_music_credits(-1 if button == 4 else 1)
        elif self.state == "controls" and button in (0, 1):
            self._return_to_previous()
        elif self.state == "achievements":
            if button in (0, 1):
                self._return_to_previous()
            elif button in (4, 5):
                self._turn_achievement_page(-1 if button == 4 else 1)
        elif self.state == "replay_pages":
            if button == 0:
                self._activate_replay_page()
            elif button == 1:
                self._return_to_title()
        elif self.state == "ending":
            if not hasattr(self, "afterword"):
                if button == 0:
                    self._return_to_title()
            elif button == 1:
                self._return_to_title()
            elif self.afterword.complete and button == 0:
                self._activate_afterword_action()
            elif button == 0:
                self.pending_input.jump_pressed = True
            elif button == 3:
                self.pending_input.interact = True

    def _controller_button_up(self, button):
        if button == 0 and self.state in ("playing", "ending"):
            self.pending_input.jump_released = True

    def _controller_hat(self, value):
        horizontal, vertical = value
        if self.state == "title":
            options = self._title_options()
            if vertical > 0:
                self.menu_index = (self.menu_index - 1) % len(options)
            elif vertical < 0:
                self.menu_index = (self.menu_index + 1) % len(options)
        elif self.state == "pause":
            if vertical > 0:
                self.pause_index = (self.pause_index - 1) % len(self._pause_options())
            elif vertical < 0:
                self.pause_index = (self.pause_index + 1) % len(self._pause_options())
        elif self.state == "settings":
            if vertical > 0:
                self.settings_index = (self.settings_index - 1) % 7
            elif vertical < 0:
                self.settings_index = (self.settings_index + 1) % 7
            if horizontal:
                self._change_setting(1 if horizontal > 0 else -1)
        elif self.state == "replay_pages":
            self.replay_page_index = (self.replay_page_index + horizontal - 2*vertical) % 6
        elif self.state == "ending" and hasattr(self, "afterword") and self.afterword.complete:
            self.afterword.menu_index = (self.afterword.menu_index + horizontal - vertical) % 3
        elif self.state == "credits" and horizontal:
            self._turn_music_credits(1 if horizontal > 0 else -1)
        elif self.state == "playing" and horizontal:
            self.pending_input.weapon_cycle = 1 if horizontal > 0 else -1

    @staticmethod
    def _joystick_button(joystick, button):
        try:
            return bool(joystick and joystick.get_numbuttons() > button
                        and joystick.get_button(button))
        except pygame.error:
            return False

    @staticmethod
    def _joystick_axis(joystick, axis):
        try:
            return (joystick.get_axis(axis)
                    if joystick and joystick.get_numaxes() > axis else 0.0)
        except pygame.error:
            return 0.0

    @staticmethod
    def _joystick_hat(joystick):
        try:
            return joystick.get_hat(0) if joystick and joystick.get_numhats() else (0, 0)
        except pygame.error:
            return 0, 0

    def _key_down(self, key):
        if key == pygame.K_F11:
            self._toggle_fullscreen()
            return
        if self.state == "title":
            options = self._title_options()
            if key in (pygame.K_UP, pygame.K_w):
                self.menu_index = (self.menu_index - 1) % len(options)
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.menu_index = (self.menu_index + 1) % len(options)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_title(options[self.menu_index])
            elif key == pygame.K_c:
                self.previous_state, self.state = "title", "credits"
            elif key == pygame.K_ESCAPE:
                self.running = False
        elif self.state == "playing":
            if key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.pending_input.jump_pressed = True
            elif key == pygame.K_e:
                self.pending_input.interact = True
            elif key in (pygame.K_f, pygame.K_j):
                self.pending_input.attack_pressed = True
            elif key in (pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_k):
                self.pending_input.dash_pressed = True
            elif key == pygame.K_r:
                self.pending_input.reload_pressed = True
            elif key == pygame.K_q:
                self.pending_input.weapon_cycle = 1
            elif pygame.K_1 <= key <= pygame.K_6:
                self.pending_input.weapon_slot = key - pygame.K_1
            elif key == pygame.K_ESCAPE:
                self.pause_index = 0
                self.state = "pause"
        elif self.state == "pause":
            if key == pygame.K_ESCAPE:
                self.state = "playing"
            elif key in (pygame.K_UP, pygame.K_w):
                self.pause_index = (self.pause_index - 1) % len(self._pause_options())
            elif key == pygame.K_DOWN:
                self.pause_index = (self.pause_index + 1) % len(self._pause_options())
            elif key == pygame.K_RETURN:
                self._activate_pause(self._pause_options()[self.pause_index])
            elif key == pygame.K_r:
                self._activate_pause("RESTART PAGE")
            elif key == pygame.K_s:
                self._activate_pause("SETTINGS")
            elif key == pygame.K_b:
                self._activate_pause("BACK PAGES")
            elif key == pygame.K_a:
                self._activate_pause("ACHIEVEMENTS")
            elif key == pygame.K_q:
                self._activate_pause("TITLE")
        elif self.state == "back_pages":
            if key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.sketch_page = (getattr(self, "sketch_page", 0) + (-1 if key == pygame.K_LEFT else 1)) % ((len(SKETCHES)+8)//9)
            elif key == pygame.K_a:
                self.collection_parent = self.previous_state
                self.previous_state = "back_pages"
                self.state = "achievements"
            elif key == pygame.K_c:
                self.collection_parent = self.previous_state
                self.previous_state = "back_pages"
                self.state = "controls"
            elif key in (pygame.K_ESCAPE, pygame.K_b, pygame.K_RETURN):
                self._return_to_previous()
        elif self.state == "credits":
            if key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._turn_music_credits(-1 if key == pygame.K_LEFT else 1)
            elif key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self._return_to_previous()
        elif self.state == "controls":
            if key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self._return_to_previous()
        elif self.state == "achievements":
            if key in (pygame.K_LEFT, pygame.K_RIGHT):
                self._turn_achievement_page(-1 if key == pygame.K_LEFT else 1)
            if key in (pygame.K_ESCAPE, pygame.K_a, pygame.K_RETURN):
                self._return_to_previous()
        elif self.state == "settings":
            if key in (pygame.K_UP, pygame.K_w):
                self.settings_index = (self.settings_index - 1) % 7
            elif key in (pygame.K_DOWN, pygame.K_s):
                self.settings_index = (self.settings_index + 1) % 7
            elif key in (pygame.K_LEFT, pygame.K_a):
                self._change_setting(-1)
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self._change_setting(1)
            elif key == pygame.K_RETURN and self.settings_index in (3, 4, 5):
                self._change_setting(1)
            elif key in (pygame.K_RETURN, pygame.K_ESCAPE) and self.settings_index == 6:
                self._return_to_previous()
            elif key == pygame.K_ESCAPE:
                self._return_to_previous()
        elif self.state == "replay_pages":
            if key in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
                self.replay_page_index = (self.replay_page_index + (-1 if key in (pygame.K_LEFT, pygame.K_a) else 1)) % 6
            elif key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                self.replay_page_index = (self.replay_page_index + (-2 if key in (pygame.K_UP, pygame.K_w) else 2)) % 6
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._activate_replay_page()
            elif key == pygame.K_ESCAPE:
                self._return_to_title()
        elif self.state == "ending":
            if not hasattr(self, "afterword"):
                if key in (pygame.K_RETURN, pygame.K_ESCAPE):
                    self._return_to_title()
            elif key == pygame.K_ESCAPE:
                self._return_to_title()
            elif self.afterword.complete:
                if key in (pygame.K_LEFT, pygame.K_UP, pygame.K_a):
                    self.afterword.menu_index = (self.afterword.menu_index-1) % 3
                elif key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_d):
                    self.afterword.menu_index = (self.afterword.menu_index+1) % 3
                elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
                    self._activate_afterword_action()
            elif key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
                self.pending_input.jump_pressed = True
            elif key in (pygame.K_e, pygame.K_RETURN):
                self.pending_input.interact = True

    def _return_to_title(self):
        if hasattr(self, "boss_cinematic"):
            self.boss_cinematic.cancel()
        self.sounds.set_combat(False)
        self.sounds.start_ambience(0)
        self.sounds.quiet_ambience(False)
        self.state = "title"

    def _return_to_previous(self):
        target = self.previous_state
        if target == "back_pages":
            self.previous_state = getattr(self, "collection_parent", "pause")
        self.state = target

    def _title_options(self):
        resume = "REPLAY PAGES" if self.save.data.get("completed") else "CONTINUE"
        options = [resume, "NEW GAME"] if self.save.can_continue else ["NEW GAME"]
        return options + ["TRAINING", "BACK PAGES", "SETTINGS", "QUIT"]

    def _open_replay_pages(self):
        self.sounds.set_combat(False)
        self.sounds.start_ambience(0)
        self.sounds.quiet_ambience(False)
        self.replay_page_index = 0
        self.state = "replay_pages"

    def _activate_replay_page(self):
        page = self.replay_page_index
        if page == 5:
            from afterword import Afterword
            self.afterword = Afterword(self.save.data.get("secrets", ()))
            self.ending_time = 3.3
            self.ending_tools_erased = True
            self.transition_snapshot = self.screen.copy()
            self.state = "ending"
            self.sounds.set_combat(False)
            self.sounds.quiet_ambience(True)
            return
        seconds = float(self.save.data.get("play_seconds", 0))
        self.reset(False)
        self.level.load_chapter(page, "start", self.player, self.camera)
        self._restore_weapons()
        self._attach_runtime()
        self.session_seconds = self.page_started_at = seconds
        self.sounds.start_ambience(page)
        self.save.checkpoint(page, "start", seconds)
        self.pending_input = InputFrame()

    def _activate_afterword_action(self):
        option = self.afterword.actions[self.afterword.menu_index]
        if option == "REPLAY PAGES":
            self._open_replay_pages()
        elif option == "BACK PAGES":
            self.previous_state, self.state = "ending", "back_pages"
        else:
            self._return_to_title()

    def start_training(self):
        from save_system import TrainingSave
        self.campaign_save = self.save
        self.save = TrainingSave(self.campaign_save)
        self.reset(False)
        self.training_only = True
        self.title_notice = ""

    def finish_training(self, completed=False):
        if not getattr(self, "training_only", False):
            return
        self.campaign_save.data["settings"].update(self.save.data["settings"])
        self.save = self.campaign_save
        self.training_only = False
        self.achievements = AchievementTracker(self.save)
        self._return_to_title()
        self.menu_index = 0
        self.title_notice = "TRAINING COMPLETE / your campaign progress is kept" if completed else ""

    def _activate_title(self, option):
        if option == "NEW GAME":
            self.reset(True)
        elif option == "CONTINUE":
            self.continue_game()
        elif option == "REPLAY PAGES":
            self._open_replay_pages()
        elif option == "TRAINING":
            self.start_training()
        elif option == "SETTINGS":
            self.previous_state = "title"
            self.state = "settings"
        elif option == "ACHIEVEMENTS":
            self.previous_state = "title"
            self.state = "achievements"
        elif option == "BACK PAGES":
            self.previous_state = "title"
            self.state = "back_pages"
        elif option == "QUIT":
            self.running = False

    def _mouse_click(self, pos):
        pos = self._window_to_canvas(pos)
        if pos is None:
            return
        if self.state == "title":
            if MUSIC_CREDITS_RECT.collidepoint(pos):
                self.previous_state, self.state = "title", "credits"
                return
            if LANGUAGE_RECT.collidepoint(pos):
                self.settings_index = 5
                self._change_setting(1)
                return
            options = self._title_options()
            for i, option in enumerate(options):
                if self._menu_rect(i, len(options)).collidepoint(pos):
                    self.menu_index = i
                    self._activate_title(option)
                    return
        elif self.state == "replay_pages":
            from page_replay import replay_rects
            for i, rect in enumerate(replay_rects()):
                if rect.collidepoint(pos):
                    self.replay_page_index = i
                    self._activate_replay_page()
                    return
        elif self.state == "ending" and hasattr(self, "afterword") and self.afterword.complete:
            for i, rect in enumerate(self.afterword.action_rects()):
                if rect.collidepoint(pos):
                    self.afterword.menu_index = i
                    self._activate_afterword_action()
                    return
        elif self.state == "pause":
            options = self._pause_options()
            for i, option in enumerate(options):
                if self._pause_rect(i).collidepoint(pos):
                    self.pause_index = i
                    self._activate_pause(option)
                    return
        elif self.state == "settings":
            for i in range(7):
                if not self._settings_row_rect(i).collidepoint(pos):
                    continue
                self.settings_index = i
                if i < 3 and pos[0] >= 615:
                    self.dragging_volume_index = i
                    self._set_volume_from_canvas(pos[0], write=False)
                elif i in (3, 4, 5):
                    self._change_setting(1)
                elif i == 6:
                    self._return_to_previous()
                return
        elif self.state == "back_pages":
            if self._back_pages_close_rect().collidepoint(pos):
                self._return_to_previous()
            elif pygame.Rect(705,65,170,38).collidepoint(pos):
                self.collection_parent = self.previous_state
                self.previous_state = "back_pages"
                self.state = "achievements"
            elif pygame.Rect(885,65,160,38).collidepoint(pos):
                self.collection_parent = self.previous_state
                self.previous_state = "back_pages"
                self.state = "controls"
            elif pygame.Rect(880,595,140,32).collidepoint(pos):
                self.sketch_page = (getattr(self,"sketch_page",0)+1) % ((len(SKETCHES)+8)//9)
        elif self.state == "credits":
            from soundtrack_credits import (CREDITS_BACK_RECT, CREDITS_PREVIOUS_RECT,
                                           CREDITS_NEXT_RECT)
            if CREDITS_BACK_RECT.collidepoint(pos):
                self._return_to_previous()
            elif CREDITS_PREVIOUS_RECT.collidepoint(pos):
                self._turn_music_credits(-1)
            elif CREDITS_NEXT_RECT.collidepoint(pos):
                self._turn_music_credits(1)
        elif self.state == "controls":
            if self._back_pages_close_rect().collidepoint(pos):
                self._return_to_previous()
        elif self.state == "achievements":
            if self._achievements_close_rect().collidepoint(pos):
                self._return_to_previous()
            elif pygame.Rect(300,580,140,34).collidepoint(pos):
                self._turn_achievement_page(-1)
            elif pygame.Rect(680,580,140,34).collidepoint(pos):
                self._turn_achievement_page(1)

    def _turn_music_credits(self, step):
        from soundtrack_credits import music_credit_page_count
        from scene_music import MUSIC_CREDITS
        self.music_credit_page = (getattr(self, "music_credit_page", 0)+step) % music_credit_page_count(MUSIC_CREDITS)

    @staticmethod
    def _pause_options():
        return ("CONTINUE", "BACK PAGES", "SETTINGS", "CONTROLS", "RESTART PAGE", "TITLE")

    @staticmethod
    def _pause_rect(index):
        if index < 4:
            return pygame.Rect(355, 229 + index * 59, 410, 48)
        return pygame.Rect(355 + (index-4)*215, 483, 195, 40)

    def _activate_pause(self, option):
        if option == "CONTINUE":
            self.state = "playing"
        elif option == "SETTINGS":
            self.previous_state = "pause"
            self.state = "settings"
        elif option == "ACHIEVEMENTS":
            self.previous_state = "pause"
            self.state = "achievements"
        elif option == "BACK PAGES":
            self.previous_state = "pause"
            self.state = "back_pages"
        elif option == "CONTROLS":
            self.previous_state = "pause"
            self.state = "controls"
        elif option == "RESTART PAGE":
            if hasattr(self, "boss_cinematic"):
                self.boss_cinematic.cancel()
            self.level.restart_chapter(self.player, self.camera)
            self.weapons.erase_page_tools()
            self._apply_page_identity()
            self.particles = ParticleSystem()
            self.hit_stop = self.damage_flash = self.weapon_reveal_time = 0
            self._buffered_actions = InputFrame()
            self.transition_active = False
            self.transition_snapshot = None
            self.sounds.set_combat(False)
            self.sounds.start_ambience(self.level.chapter_index)
            self.state = "playing"
        elif option == "TITLE":
            if getattr(self, "training_only", False):
                self.finish_training()
            else:
                self._return_to_title()

    @staticmethod
    def _settings_row_rect(index):
        return pygame.Rect(235, 165 + index * 59, 700, 48)

    @staticmethod
    def _back_pages_close_rect():
        return pygame.Rect(WIDTH // 2 - 165, 620, 330, 48)

    @staticmethod
    def _achievements_close_rect():
        return pygame.Rect(WIDTH // 2 - 165, 628, 330, 42)

    def _set_volume_from_canvas(self, canvas_x, write=False):
        index = self.dragging_volume_index
        if index is None or not 0 <= index < 3:
            return
        key = ("master_volume", "sfx_volume", "music_volume")[index]
        value = round(max(0.0, min(1.0, (float(canvas_x) - 640) / 210)), 2)
        settings = self.save.data["settings"]
        settings[key] = value
        self.save.update_settings(settings, write=write)
        self.sounds.apply_settings(settings)

    def _toggle_fullscreen(self):
        settings = self.save.data["settings"]
        settings["fullscreen"] = not self.fullscreen
        try:
            self._set_display_mode(self.windowed_size,
                                   fullscreen=settings["fullscreen"])
        except pygame.error:
            settings["fullscreen"] = False
            self._set_display_mode(self.windowed_size, fullscreen=False)
        settings["window_width"], settings["window_height"] = self.windowed_size
        self.save.update_settings(settings)

    def _change_setting(self, direction):
        settings = self.save.data["settings"]
        keys = ["master_volume", "sfx_volume", "music_volume"]
        if self.settings_index < 3:
            key = keys[self.settings_index]
            try:
                current = float(settings.get(key, 0.8))
            except (TypeError, ValueError, OverflowError):
                current = 0.8
            if not math.isfinite(current):
                current = 0.8
            settings[key] = max(0.0, min(1.0, round(current + direction * .1, 1)))
        elif self.settings_index == 3 and direction:
            current_size = self.windowed_size
            nearest = min(range(len(WINDOW_PRESETS)),
                          key=lambda index: abs(WINDOW_PRESETS[index][0] - current_size[0])
                          + abs(WINDOW_PRESETS[index][1] - current_size[1]))
            target = WINDOW_PRESETS[(nearest + direction) % len(WINDOW_PRESETS)]
            self.windowed_size = target
            if not self.fullscreen:
                self._set_display_mode(target, fullscreen=False)
            settings["window_width"], settings["window_height"] = target
        elif self.settings_index == 4 and direction:
            self._toggle_fullscreen()
            settings = self.save.data["settings"]
        elif self.settings_index == 5 and direction:
            current = SUPPORTED_LANGUAGES.index(normalize_language(settings["language"]))
            step = 1 if direction > 0 else -1
            settings["language"] = SUPPORTED_LANGUAGES[(current + step) % len(SUPPORTED_LANGUAGES)]
            set_language(settings["language"])
            from notebook_notes import NotebookAnnotations
            self.renderer.notebook_notes = NotebookAnnotations()
            self.renderer.notebook.tiles.clear()
        self.save.update_settings(settings)
        self.sounds.apply_settings(settings)

    def _sample_input(self):
        keys = pygame.key.get_pressed()
        mouse_x, mouse_y = self._window_to_canvas(pygame.mouse.get_pos(), clamp=True)
        joystick = self._active_joystick()
        stick_x = self._joystick_axis(joystick, 0)
        hat_x, hat_y = self._joystick_hat(joystick)
        controller_left = stick_x < -.24 or hat_x < 0
        controller_right = stick_x > .24 or hat_x > 0
        controller_attack = self._joystick_button(joystick, 2)
        assisted_attack = bool(keys[pygame.K_f] or keys[pygame.K_j] or controller_attack)
        return InputFrame(
            left=bool(keys[pygame.K_a] or keys[pygame.K_LEFT] or controller_left),
            right=bool(keys[pygame.K_d] or keys[pygame.K_RIGHT] or controller_right),
            down=bool(keys[pygame.K_s] or keys[pygame.K_DOWN] or hat_y < 0
                      or self._joystick_axis(joystick, 1) > .5),
            jump_pressed=self.pending_input.jump_pressed,
            jump_held=bool(keys[pygame.K_SPACE] or keys[pygame.K_w] or keys[pygame.K_UP]
                           or self._joystick_button(joystick, 0)),
            jump_released=self.pending_input.jump_released,
            interact=self.pending_input.interact,
            attack_pressed=self.pending_input.attack_pressed,
            attack_held=bool(assisted_attack or pygame.mouse.get_pressed()[0]),
            dash_pressed=self.pending_input.dash_pressed,
            reload_pressed=self.pending_input.reload_pressed,
            weapon_slot=self.pending_input.weapon_slot,
            weapon_cycle=self.pending_input.weapon_cycle,
            # F/J deliberately use the stable facing/nearest-target assist.
            # Mouse attacks invert the complete camera transform so screen
            # shake never bends a projectile away from the pointer.
            aim_x=None if assisted_attack else self.camera.x + mouse_x - self.camera.offset_x,
            aim_y=None if assisted_attack else mouse_y - self.camera.offset_y,
            pause=self.pending_input.pause,
        )

    def update(self, dt, input_frame: InputFrame | None = None):
        self.time += dt
        self.sounds.update(dt)
        self._update_achievements(dt)
        if self.state not in ("playing", "ending"):
            return
        if self.state == "ending":
            self._update_ending(dt, input_frame or self._sample_input())
            return
        if self.transition_active:
            self._update_transition(dt)
            return
        frame = input_frame or self._sample_input()
        if self.boss_cinematic.active:
            self.boss_cinematic.update(dt)
            self.particles.update(dt*.15)
            self.session_seconds += dt
            return
        self.damage_flash = max(0.0, self.damage_flash - dt)
        if self.hit_stop > 0:
            # Freeze the simulation, not the player's intent.  A jump, dash,
            # reload, or attack tapped during a freeze frame is replayed on
            # the first live frame instead of being silently discarded.
            self._buffer_action_input(frame)
            self.hit_stop = max(0.0, self.hit_stop - dt)
            self.particles.update(dt * .2)
            return
        frame = self._consume_action_buffer(frame)
        if frame.jump_pressed:
            if not (frame.down and self.player.drop_through(self.level.world)):
                self.player.queue_jump()
        if frame.jump_released:
            self.player.release_jump()
        if frame.dash_pressed and self.player.start_dash(frame.axis, self.particles):
            self.sounds.play("dash")
            self.behavior.record("dash", page=self.level.chapter_index)
        context = self.level.context(self.player, self.camera, self.particles, self.sounds)
        selected = None
        if frame.weapon_slot is not None and 0 <= frame.weapon_slot < len(WEAPON_ORDER):
            selected = WEAPON_ORDER[frame.weapon_slot]
        if frame.aim_x is not None and frame.aim_y is not None:
            aim = (frame.aim_x, frame.aim_y)
        else:
            # Keyboard attacks get a mild arena-only aim assist.  The mouse
            # remains fully manual, while F/J can still use ranged weapons and
            # will not repeatedly swing away from a doodle that crossed over
            # the tiny stick figure during a lunge.
            live = [enemy for entity in self.level.entities.items
                    if getattr(entity, "encounter_active", False)
                    for enemy in self.weapons.aim_targets(getattr(entity, "enemies", ()))
                    if not getattr(enemy, "dead", False)]
            nearest = min(live, key=lambda enemy: abs(enemy.x - self.player.center_x),
                          default=None)
            aim = ((nearest.rect.centerx, nearest.rect.centery - 12) if nearest is not None
                   else (self.player.center_x + self.player.facing * 140,
                         self.player.rect.centery - 5))
        # Preserve the difference between a deliberate press and a held
        # trigger.  Pistol and rubber band opt into automatic fire; the blade,
        # shotgun and cannon use their short input buffer for intentional beats.
        fired = self.weapons.handle_input(selected, frame.weapon_cycle, frame.attack_pressed,
                                          frame.attack_held, aim, context, frame.reload_pressed)
        if fired:
            self.behavior.record("attack", weapon=self.weapons.current_id,
                                 page=self.level.chapter_index)
        aim_angle = math.atan2(self.weapons.aim_direction.y, self.weapons.aim_direction.x)
        current_weapon = self.weapons.current
        reload_progress = (1 - current_weapon.reload_timer /
                           max(.001, getattr(current_weapon, "reload_duration",
                                             current_weapon.reload_time))) if current_weapon.reloading else None
        self.player.set_weapon_pose(self.weapons.current_id, aim_angle,
                                    .7 if fired else 0, reload_progress)
        self.level.refresh_drawings(self.player)
        self.player.update(dt, frame.axis, self.level.world, self.particles)
        lesson = getattr(self.level.runtime, "training", None)
        if lesson is not None:
            lesson.observe(frame, self.player)
        combatants = [enemy for entity in self.level.entities.items
                      if getattr(entity, "encounter_active", False)
                      for enemy in getattr(entity, "enemies", ())]
        self.behavior.observe_combat(dt, self.player, combatants)
        self.level.update(dt, self.player, self.camera, self.particles, self.sounds,
                          frame.interact, self.session_seconds)
        self._update_combat_music()
        if self.boss_cinematic.maybe_begin():
            return
        # Respawn can replace the world during Level.update. Never let old
        # projectiles or a pending attack operate on the discarded page.
        if context.world is not self.level.world:
            context = self.level.context(self.player, self.camera, self.particles, self.sounds)
        if self.level.respawn_timer <= 0 and self.player.health > 0:
            self.weapons.update(dt, context, self.level.entities)
        if self.weapons.current_id != self._visual_weapon_id:
            self._visual_weapon_id = self.weapons.current_id
            self.weapon_reveal_time = 2.4 if self.weapons.current_id != "unarmed" else 0
        elif self._can_show_weapon_reveal():
            self.weapon_reveal_time = max(0.0, self.weapon_reveal_time - dt)
        self.artist_companion.update(dt, self, frame)
        self.particles.update(dt)
        self.camera.update(dt, self.player.center_x, self.level.world.width,
                           self.player.vx, self.player.y, player_locked=self.player.locked)
        self.session_seconds += dt
        if getattr(self, "training_only", False) and lesson is not None and lesson.completed:
            self.finish_training(completed=True)
            return
        if self.level.chapter_complete:
            final_index = int(getattr(self.level.runtime, "campaign_last_index", 4))
            if self.level.chapter_index >= final_index:
                self._start_ending()
            else:
                self._start_transition()

    def _update_combat_music(self):
        active_rooms = [room for room in self.level.entities.items
                        if getattr(room, "encounter_active", False)
                        and not getattr(room, "completed", False)]
        if not active_rooms or self.level.respawn_timer > 0:
            self.sounds.set_combat(False)
            return
        boss_room = next((room for room in active_rooms
                         if getattr(room, "boss_cue_started", False)
                         and getattr(room, "boss_kind", None)), None)
        boss = next((enemy for room in active_rooms for enemy in getattr(room, "enemies", ())
                     if getattr(enemy, "is_boss", False)), None)
        # Arena victory waits for its clear beat after the boss body vanishes.
        # Keep that encounter's identity until it actually opens the gates.
        boss_kind = (boss_room.boss_kind if boss_room is not None
                     else getattr(boss, "kind", None))
        self.sounds.set_combat(True, boss_room is not None or boss is not None, boss_kind)

    def _update_achievements(self, dt):
        if self.state in ("playing", "ending"):
            self.achievements.evaluate(self)
        if not self._quiet_notification_context():
            return
        self.achievement_time = max(0.0, self.achievement_time - dt)
        if self.achievement_time <= 0 and self.achievements.pending:
            self.achievement_banner = self.achievements.pending.popleft()
            self.achievement_time = 4.2
            self.sounds.play("pickup")

    def _quiet_notification_context(self):
        """Critical page messages and live warnings own the notebook margin."""
        return (self.state == "playing" and not self.transition_active
                and self.player.health > 0 and not self.player.locked
                and self.player.draw_amount >= 1
                and self.level.respawn_timer <= 0 and self.level.toast_time <= 0
                and self.level.director.canvas_owner is None
                and not self.level.director.tool.visible
                and not any(getattr(e, "letter_time", 0) > 0 or
                            (getattr(e, "encounter_active", False) and
                             not getattr(e, "completed", False))
                            for e in self.level.entities.items))

    def _can_show_weapon_reveal(self):
        return (self._quiet_notification_context() and self.achievement_time <= 0
                and not any(getattr(e, "boss_intro_time", 0) > 0
                            for e in self.level.entities.items))

    def request_hit_stop(self, duration):
        """Request a short combat freeze without coupling enemies to Game internals."""
        self.hit_stop = max(self.hit_stop, max(0.0, min(.09, float(duration))))

    def request_player_damage_feedback(self, duration=.045):
        self.request_hit_stop(duration)
        self.damage_flash = max(self.damage_flash, .18)
        self.behavior.record("damage", page=self.level.chapter_index)
        self.artist_director.record_damage(self)

    def _buffer_action_input(self, frame):
        buffered = self._buffered_actions
        buffered.jump_pressed = buffered.jump_pressed or frame.jump_pressed
        buffered.jump_released = buffered.jump_released or frame.jump_released
        buffered.interact = buffered.interact or frame.interact
        buffered.attack_pressed = buffered.attack_pressed or frame.attack_pressed
        buffered.down = buffered.down or (frame.down and frame.jump_pressed)
        buffered.dash_pressed = buffered.dash_pressed or frame.dash_pressed
        buffered.reload_pressed = buffered.reload_pressed or frame.reload_pressed
        if frame.weapon_slot is not None:
            buffered.weapon_slot = frame.weapon_slot
        buffered.weapon_cycle += frame.weapon_cycle
        if frame.aim_x is not None:
            buffered.aim_x = frame.aim_x
        if frame.aim_y is not None:
            buffered.aim_y = frame.aim_y

    def _consume_action_buffer(self, frame):
        buffered = self._buffered_actions
        frame.down = frame.down or buffered.down
        frame.jump_pressed = frame.jump_pressed or buffered.jump_pressed
        frame.jump_released = frame.jump_released or buffered.jump_released
        frame.interact = frame.interact or buffered.interact
        frame.attack_pressed = frame.attack_pressed or buffered.attack_pressed
        frame.dash_pressed = frame.dash_pressed or buffered.dash_pressed
        frame.reload_pressed = frame.reload_pressed or buffered.reload_pressed
        if buffered.weapon_slot is not None:
            frame.weapon_slot = buffered.weapon_slot
        frame.weapon_cycle += buffered.weapon_cycle
        if frame.aim_x is None:
            frame.aim_x = buffered.aim_x
        if frame.aim_y is None:
            frame.aim_y = buffered.aim_y
        self._buffered_actions = InputFrame()
        return frame

    def _start_transition(self):
        self._record_page_complete()
        self.transition_active = True
        self.transition_progress = 0
        self.transition_snapshot = None
        self.transition_sound_stage = 0
        self.transition_weapon_erased = False
        self.transition_erased_label = self.weapons.current.label
        self.player.acquire_lock("page_transition")
        self.sounds.quiet_ambience(True)

    def _update_transition(self, dt):
        self.transition_progress = min(1, self.transition_progress + dt / 2.85)
        if not self.transition_weapon_erased and self.transition_progress >= .21:
            self._erase_current_page_tools()
            self.transition_weapon_erased = True
            self.sounds.play("erase")
        if self.transition_sound_stage == 0 and self.transition_progress >= .34:
            self.sounds.play("page")
            self.transition_sound_stage = 1
        if self.transition_sound_stage == 1 and self.transition_progress >= .68:
            # Every new sheet is another lesson. The score is already ducked
            # for the page curl, leaving the school bell clearly audible.
            self.sounds.play("bell")
            self.transition_sound_stage = 2
        if self.transition_progress >= 1:
            self.transition_active = False
            self.transition_snapshot = None
            self.level.next_chapter(self.player, self.camera, self.session_seconds)
            self.page_started_at = self.session_seconds
            self._apply_page_identity()
            self.sounds.start_ambience(self.level.chapter_index)
            self.player.release_lock("page_transition")

    def _erase_current_page_tools(self):
        erased = self.weapons.erase_page_tools()
        snapshot = self.weapons.snapshot()
        self.save.update_combat(snapshot["unlocked"], snapshot["current_id"],
                                snapshot["ammo"])
        if erased:
            self.behavior.record("page_tools_erased", page=self.level.chapter_index,
                                 tools=erased)
            self.persist_behavior(write=False)

    def _start_ending(self):
        self._record_page_complete()
        self.state = "ending"
        self.ending_time = 0
        self.ending_tools_erased = False
        self.transition_erased_label = self.weapons.current.label
        self.transition_snapshot = None
        self.blank_player_x = 150
        self.sounds.quiet_ambience(True)
        self.save.mark_complete(self.session_seconds)
        from afterword import Afterword
        self.afterword = Afterword(self.save.data.get("secrets", ()))

    def _record_page_complete(self):
        if getattr(self.level, "completion_recorded", False):
            return
        self.level.completion_recorded = True
        self.behavior.record("page_complete", page=self.level.chapter_index,
                             seconds=max(0.0, self.session_seconds - self.page_started_at))
        self.persist_behavior(write=True)

    def _update_ending(self, dt, frame=None):
        self.ending_time += dt
        if not self.ending_tools_erased and self.ending_time >= .58:
            self._erase_current_page_tools()
            self.ending_tools_erased = True
            self.sounds.play("erase")
        if self.ending_time >= 1.0 and self.ending_time - dt < 1.0:
            self.sounds.play("page")
        if self.ending_time > 3.3 and hasattr(self, "afterword"):
            self.afterword.update(min(dt, self.ending_time-3.3), frame or InputFrame(), self.sounds)
            self.session_seconds += dt

    def draw(self):
        if self.state == "title":
            self._draw_title()
        elif self.state == "settings":
            self._draw_settings()
        elif self.state == "back_pages":
            self._draw_back_pages()
        elif self.state == "achievements":
            self._draw_achievements()
        elif self.state == "controls":
            self._draw_controls()
        elif self.state == "credits":
            from scene_music import MUSIC_CREDITS
            from soundtrack_credits import draw_music_credits
            draw_music_credits(self.screen, self.renderer, MUSIC_CREDITS,
                               self.save.data["settings"]["language"],
                               getattr(self, "music_credit_page", 0))
        elif self.state == "ending":
            self._draw_ending()
        elif self.state == "replay_pages":
            from page_replay import draw_replay_pages
            draw_replay_pages(self.screen, self.renderer, self.replay_page_index,
                              controller=self.last_input_device == "controller")
        else:
            self._draw_scene(self.screen)
            if self.damage_flash > 0:
                self._draw_damage_feedback()
            if self.transition_active:
                self._draw_hud()
                self._draw_transition()
            else:
                self._draw_hud()
            if self.state == "pause":
                self._draw_pause()
        if self.state == "playing" and not self.transition_active and not self.boss_cinematic.active:
            self._draw_aim_cursor()
            if self.weapon_reveal_time > 0 and self._can_show_weapon_reveal():
                self._draw_weapon_reveal()
            if (not self.player.locked and self.level.toast_time <= 0 and self.achievement_time <= 0
                    and self.level.director.canvas_owner is None
                    and not self.level.director.tool.visible
                    and not any(getattr(e,'letter_time',0)>0 or
                                (getattr(e,'encounter_active',False) and
                                 not getattr(e,'completed',False))
                                for e in self.level.entities.items)) :
                self.artist_companion.draw(self.screen, self.renderer, self.last_input_device == "controller")
        if (self.achievement_banner is not None and self.achievement_time > 0
                and self._quiet_notification_context()):
            self._draw_achievement_banner()
        if self.state in ("title", "settings", "pause", "back_pages", "achievements", "controls", "credits", "replay_pages"):
            self._draw_pencil_cursor()

    def _draw_scene(self, target):
        world = self.level.world
        self.renderer.background(target, world.page)
        boss_arena = next((e for e in self.level.entities.items
            if getattr(e, "is_combat_arena", False) and getattr(e, "boss", False)
            and e.start_x-350 <= self.player.center_x <= e.end_x+350), None)
        self.renderer.draw_world_backdrop(target, self.camera, world.page, self.time, arena=boss_arena)
        if world.active_layer == 1:
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((70, 61, 49, 20))
            target.blit(shade, (0, 0))
        # Draw onto the opaque paper canvas. The native macOS blitter can
        # miscompose a full-screen intermediate RGBA layer and hide the page.
        ink = target
        world.draw(ink, self.camera, self.renderer, self.time,
                   show_notes=not self.boss_cinematic.active)
        if not self.boss_cinematic.active:
            self.level.director.draw_messages(ink, self.camera, self.renderer)
        if self.boss_cinematic.active:
            self.boss_cinematic.owner.draw(ink, self.camera, self.renderer)
        else:
            self.level.draw_entities(ink, self.camera, self.renderer)
        self.weapons.draw_world(ink, self.camera, self.renderer)
        self.particles.draw(ink, self.camera)
        self.player.draw(ink, self.camera)
        if not self.boss_cinematic.active:
            self.level.director.draw_tool(target, self.camera)
            self.level.draw_artist_overlay(target, self.camera, self.renderer)
        if not self.boss_cinematic.active:
            for entity in self.level.entities.items:
                draw_overlay = getattr(entity, "draw_overlay", None)
                if callable(draw_overlay):
                    draw_overlay(target, self.camera, self.renderer)
        if self.level.fold_progress > 0:
            self._draw_fold(target, self.level.fold_progress)
        self.boss_cinematic.draw_hand(target, self.camera, self.renderer)
        self.boss_cinematic.present(target, self.renderer)

    def _draw_fold(self, target, progress):
        width = round(270 * progress)
        if width <= 0:
            return
        flap = pygame.Surface((width, 240), pygame.SRCALPHA)
        pygame.draw.polygon(flap, (226, 220, 199, 205), [(0, 0), (width, 110), (0, 240)])
        pygame.draw.line(flap, (119, 111, 96, 150), (0, 0), (width, 110), 2)
        target.blit(flap, (WIDTH - width, 80))

    def _draw_damage_feedback(self):
        strength = min(1.0, self.damage_flash / .18)
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((137, 35, 38, round(20 * strength)))
        self.screen.blit(veil, (0, 0))
        color = (139, 45, 48)
        inset = round(8 + (1 - strength) * 10)
        for index in range(3):
            pad = inset + index * 7
            pygame.draw.line(self.screen, color, (pad, pad), (WIDTH - pad, pad), 1)
            pygame.draw.line(self.screen, color, (pad, HEIGHT - pad),
                             (WIDTH - pad, HEIGHT - pad), 1)

    def _draw_transition(self):
        if self.transition_snapshot is None:
            self.transition_snapshot = self.screen.copy()
        erase_phase = .32
        if self.transition_progress < erase_phase:
            self.screen.blit(self.transition_snapshot, (0, 0))
            self._draw_tool_erasure(self.transition_progress / erase_phase)
            return
        next_page = pygame.Surface((WIDTH, HEIGHT))
        next_index = min(4, self.level.chapter_index + 1)
        self.renderer.background(next_page, next_index)
        self.renderer.notebook.draw(next_page, Camera(WIDTH), next_index)
        promises = {1: "Who drew the gun?", 2: "I did not draw that moon.",
                    3: "Someone is cutting the notebook.", 4: "He has been reading your moves."}
        self.renderer.notebook.hand(next_page, "next lesson...", (200,315), INK_LIGHT)
        self.renderer.notebook.hand(next_page, promises[next_index], (200,355), INK)
        from advanced_enemies import create_enemy
        glimpse = create_enemy({1:'wanted_sketch',2:'orbital_mistake',3:'scissor_director',4:'final_editor'}[next_index],810)
        old_clip=next_page.get_clip()
        next_page.set_clip(pygame.Rect(690,400,230,180))
        glimpse.draw(next_page,Camera(WIDTH),self.renderer)
        next_page.set_clip(old_clip)
        jitter_line(next_page, INK, (0, 590), (WIDTH, 590), 3, 700 + next_index, 2, 1.5)
        page_progress = (self.transition_progress - erase_phase) / (1 - erase_phase)
        self.renderer.page_turn(self.screen, self.transition_snapshot, next_page, page_progress)

    def _draw_tool_erasure(self, progress):
        """Artist visibly removes the current page's weapon before the curl."""
        p = max(0.0, min(1.0, progress))
        targets = [
            (self.camera.screen_x(self.player.center_x),
             round(self.player.rect.centery + self.camera.offset_y)),
            (245, 638),
        ]
        for index, (target_x, target_y) in enumerate(targets):
            local = max(0.0, min(1.0, p * 1.65 - index * .48))
            if local <= 0:
                continue
            start_x = target_x - 92
            cursor_x = round(start_x + 184 * local)
            for stroke in range(8):
                y = target_y - 24 + stroke * 7
                pygame.draw.line(self.screen, (218, 212, 196),
                                 (start_x, y), (cursor_x, y + (stroke % 3 - 1) * 2),
                                 5)
                pygame.draw.line(self.screen, (174, 168, 154),
                                 (start_x, y + 2), (cursor_x, y), 1)
            eraser = pygame.Rect(cursor_x - 24, target_y - 18, 48, 27)
            pygame.draw.rect(self.screen, (218, 157, 153), eraser, border_radius=4)
            pygame.draw.rect(self.screen, INK_LIGHT, eraser, 2, border_radius=4)
            pygame.draw.line(self.screen, (244, 232, 211),
                             (eraser.centerx, eraser.top + 2),
                             (eraser.centerx, eraser.bottom - 2), 2)
        if p > .52:
            self.renderer.doodle_text(self.screen,
                                      f"{self.transition_erased_label} belonged to this page",
                                      (390, 548), INK_LIGHT,
                                      self.renderer.font_small, -1)

    def _draw_hud(self):
        if self.boss_cinematic.active:
            return
        self.weapons.draw_hud(self.screen, self.renderer,
                              controller=self.last_input_device == "controller")
        # The margin carries only a spent ability. A ready dash does not
        # need a permanent panel competing with the fight.
        if self.player.dash_cooldown > 0 and not self.player.locked:
            duration = .68 - getattr(self.player, "sketch_dash_recovery", 0)
            fill = max(0.0, min(1.0, 1 - self.player.dash_cooldown / duration))
            rect = pygame.Rect(948, 645, 148, 39)
            plate = pygame.Surface(rect.size, pygame.SRCALPHA)
            plate.fill((247, 243, 224, 228))
            self.screen.blit(plate, rect)
            self.renderer.doodle_text(self.screen, "dash", (960, 647), INK_LIGHT,
                                      self.renderer.font_small)
            jitter_line(self.screen, (176, 162, 141), (959, 676), (1082, 676),
                        2, 477, 1, .7)
            jitter_line(self.screen, INK, (959, 676), (959 + 123 * fill, 676),
                        3, 478, 1, .7)
        draw_health(self.screen, self.renderer, self.player, self.time)
        if self.level.page_title_time > 0 and self.level.toast_time <= 0:
            alpha = min(1, self.level.page_title_time, 4.2 - self.level.page_title_time)
            panel = pygame.Surface((440, 90), pygame.SRCALPHA)
            panel.fill((247, 243, 224, 225))
            self.renderer.doodle_text(panel, self.level.title, (18, 13), INK_LIGHT, self.renderer.font_small)
            subtitle = fitted_label(self.renderer.font, self.level.subtitle, INK, 404)
            panel.blit(subtitle, (18, 37))
            panel.set_alpha(round(255 * max(0, alpha)))
            self.screen.blit(panel, (210, 18))
        if self.level.interaction_hint:
            hint = translate(self.level.interaction_hint)
            if self.last_input_device == "controller":
                if hint.startswith("E  "):
                    hint = "PAD-Y  " + hint[3:]
                elif hint.startswith("E / "):
                    hint = "PAD-Y / " + hint[4:]
            text = fitted_label(self.renderer.font_small, hint, INK, 810)
            bg = pygame.Surface((text.get_width() + 26, 38), pygame.SRCALPHA)
            bg.fill((247, 243, 224, 218))
            x = WIDTH // 2 - bg.get_width() // 2
            self.screen.blit(bg, (x, HEIGHT - 148))
            self.screen.blit(text, (x + 13, HEIGHT - 138))
        if self.level.toast_time > 0 and str(self.level.toast).strip():
            lines = wrap_text(self.level.toast, self.renderer.font_small, 520)
            width = max(self.renderer.font_small.size(line)[0] for line in lines) + 28
            panel = pygame.Surface((width, 22 + 22 * len(lines)), pygame.SRCALPHA)
            panel.fill((247, 243, 224, 232))
            x = WIDTH - width - 24
            for i, line in enumerate(lines):
                panel.blit(self.renderer.font_small.render(line, True, INK),
                           (14, 10 + 22 * i))
            panel.set_alpha(round(255 * min(1, self.level.toast_time / .35)))
            self.screen.blit(panel, (x, 19))

    def _draw_weapon_reveal(self):
        """Briefly show the actual new drawing at readable size after equipping."""
        if self.weapons.current_id == "unarmed":
            return
        from page_arsenal import draw_weapon_icon
        profile = self.weapons.profile()
        panel = pygame.Surface((314, 126), pygame.SRCALPHA)
        panel.fill((247, 243, 224, 238))
        self.renderer.rough_rect(panel, INK_LIGHT, pygame.Rect(3, 3, 308, 120), 1, 8102)
        self.renderer.doodle_text(panel, "IN HAND", (14, 10), profile.accent,
                                  self.renderer.font_small, -1)
        label_lines = wrap_text(profile.label, self.renderer.font_small, 157)[:2]
        for index, line in enumerate(label_lines):
            self.renderer.doodle_text(panel, line, (14, 38 + 20 * index), INK,
                                      self.renderer.font_small)
        role_y = 42 + 20 * len(label_lines)
        role_lines = 1 if len(label_lines) > 1 else 2
        for index, line in enumerate(wrap_text(profile.role, self.renderer.font_small, 157)[:role_lines]):
            self.renderer.doodle_text(panel, line, (14, role_y + 20 * index), INK_LIGHT,
                                      self.renderer.font_small)
        pygame.draw.line(panel, INK_LIGHT, (176, 23), (176, 106), 1)
        draw_weapon_icon(panel, self.weapons.current_id, self.level.chapter_index,
                         (245, 66), size=94)
        panel.set_alpha(round(255 * min(1.0, self.weapon_reveal_time / .35)))
        self.screen.blit(panel, (WIDTH - 334, 91 if self.level.toast_time > 0 else 12))

    def _draw_title(self):
        self.renderer.background(self.screen, 0)
        self.renderer.doodle_text(self.screen, "TURN THE PAGE", (143,100), INK,
                                  self.renderer.font_big,-1)
        self.renderer.doodle_text(self.screen, getattr(self, "title_notice", "") or "Every line leaves a mark.",
                                  (154,181), INK_LIGHT, self.renderer.font_small,1)
        jitter_line(self.screen,INK,(151,225),(963,225),3,82,2,1.4)
        options = self._title_options()
        self.menu_index %= len(options)
        active_index = self._active_menu_index(self.menu_index,
            tuple(self._menu_rect(i, len(options)) for i in range(len(options))))
        for i, option in enumerate(options):
            rect = self._menu_rect(i,len(options))
            selected = i == active_index
            pygame.draw.rect(self.screen, (231,222,193) if selected else (245,239,216),rect)
            self.renderer.rough_rect(self.screen,INK if selected else INK_LIGHT,rect,2 if selected else 1,100+i*7)
            label = fitted_label(self.renderer.font, option, INK, rect.width - 90)
            self.screen.blit(label,(rect.x+34,rect.centery-label.get_height()//2))
            if selected:
                self.renderer.doodle_text(self.screen,">",(rect.right-35,rect.y+15),INK,self.renderer.font)
        # A physical notebook cover and its actual tools share the title screen.
        from page_arsenal import draw_weapon_icon
        panel = pygame.Rect(595,278,382,284)
        pygame.draw.polygon(self.screen,(235,226,198),[(panel.x+8,panel.y),(panel.right,panel.y+9),
                            (panel.right-7,panel.bottom),(panel.x,panel.bottom-12)])
        self.renderer.rough_rect(self.screen,INK_LIGHT,panel,2,20301)
        self.renderer.doodle_text(self.screen,"FIELD NOTES / "+".".join(VERSION.split(".")[:2]),
                                  (615,294),(139,57,50),self.renderer.font_small,-1)
        for weapon,page,center in (("fold_crossbow",0,(665,402)),("orbit_saw",2,(786,402)),
                                    ("carbon_lance",3,(905,402))):
            draw_weapon_icon(self.screen,weapon,page,center,size=100)
        slogan = fitted_label(self.renderer.font_small, "Hidden margins. Optional routes.", INK, panel.width-40)
        self.screen.blit(slogan, (615,486))
        language = translate("Language") + " / " + LANGUAGE_NAMES[normalize_language(self.save.data["settings"]["language"])]
        self.renderer.rough_rect(self.screen,INK_LIGHT,LANGUAGE_RECT,1,20211)
        language_image = fitted_label(self.renderer.font_small, language, INK_LIGHT, LANGUAGE_RECT.width - 20)
        self.screen.blit(language_image, language_image.get_rect(center=LANGUAGE_RECT.center))
        self.renderer.doodle_text(self.screen,
                                  "PAD-A: choose" if self.last_input_device == "controller" else "Enter / click: choose",
                                  (154,632),INK_LIGHT,self.renderer.font_small)
        self.renderer.doodle_text(self.screen,"v"+VERSION.split("-")[0],(154,661),INK_LIGHT,self.renderer.font_small)
        self.renderer.rough_rect(self.screen, INK_LIGHT, MUSIC_CREDITS_RECT, 1, 20319)
        credit_label = translate("MUSIC CREDITS")
        credit_key = "Y" if self.last_input_device == "controller" else "C"
        credit_image = fitted_label(self.renderer.font_small, credit_label + " / " + credit_key, INK_LIGHT, MUSIC_CREDITS_RECT.width - 20)
        self.screen.blit(credit_image, credit_image.get_rect(center=MUSIC_CREDITS_RECT.center))

    def _menu_rect(self,index,count):
        return pygame.Rect(154,270+index*(55 if count >= 6 else 62),354,48 if count >= 6 else 52)

    def _active_menu_index(self, selected, rects):
        if self.last_input_device == "mouse":
            mouse_pos = self._window_to_canvas(pygame.mouse.get_pos())
            if mouse_pos is not None:
                return next((i for i, rect in enumerate(rects)
                             if rect.collidepoint(mouse_pos)), selected)
        return selected

    def _draw_controls(self):
        self.renderer.background(self.screen,0)
        self.renderer.doodle_text(self.screen,"CONTROLS",(112,65),INK,self.renderer.font_big,-1)
        rows = (("Move","A / D  ·  ← / →"),("Jump","Space / W / Up  ·  release for a short jump"),
                ("Attack","F / J  ·  left click aims at the pointer"),("Dash / return","Shift / K  ·  right click"),
                ("Interact / sketch","E"),("Reload / switch","R  /  Q or mouse wheel"),
                ("Drop through","S or Down + any jump key"),("Pause / fullscreen","ESC  /  F11"))
        for index,(label,keys) in enumerate(rows):
            y = 206+index*45
            label_image = fitted_label(self.renderer.font, label, INK, 290)
            self.screen.blit(label_image, (121, y))
            key_image = fitted_label(self.renderer.font_small, keys, INK_LIGHT, 578)
            self.screen.blit(key_image, (432, y+5))
            pygame.draw.line(self.screen,(194,181,149),(115,y+34),(1010,y+34),1)
        rect=self._back_pages_close_rect()
        self.renderer.rough_rect(self.screen,INK_LIGHT,rect,1,20500)
        label=self.renderer.font_small.render(
            "PAD-A / PAD-B   Back" if self.last_input_device == "controller"
            else "ENTER / ESC   Back", True, INK)
        self.screen.blit(label,label.get_rect(center=rect.center))

    def _draw_pause(self):
        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((244, 240, 220, 205))
        self.screen.blit(veil, (0, 0))
        heading = self.renderer.font_big.render("page held open", True, INK)
        self.screen.blit(heading, heading.get_rect(center=(WIDTH//2, 158)))
        options = self._pause_options()
        self.pause_index %= len(options)
        active_index = self._active_menu_index(self.pause_index,
            tuple(self._pause_rect(i) for i in range(len(options))))
        for i, text in enumerate(options):
            rect = self._pause_rect(i)
            selected = i == active_index
            if selected:
                pygame.draw.rect(self.screen, (232, 225, 201), rect, border_radius=3)
            self.renderer.rough_rect(self.screen, INK if selected else INK_LIGHT,
                                     rect, 2, 610 + i * 13)
            label = fitted_label(self.renderer.font_small, text, INK, rect.width-22)
            self.screen.blit(label, label.get_rect(center=rect.center))
        footer = ("D-PAD choose   •   PAD-A confirm   •   PAD-B continue"
                  if self.last_input_device == "controller"
                  else "ESC continue  ·  arrows select  ·  ENTER confirm")
        footer_image = fitted_label(self.renderer.font_small, footer, INK_LIGHT, WIDTH-160)
        self.screen.blit(footer_image, footer_image.get_rect(center=(WIDTH//2, 589)))

    def _draw_back_pages(self):
        self.renderer.background(self.screen, 4)
        heading = fitted_label(self.renderer.font_big, "BACK PAGES", INK, 560)
        self.screen.blit(heading, (118, 48))
        self.renderer.doodle_text(
            self.screen,
            "Learned techniques survive every redraw.",
            (78, 149), INK_LIGHT, self.renderer.font_small,
        )
        secrets = set(self.save.data.get("secrets", []))
        page = getattr(self,"sketch_page",0) % ((len(SKETCHES)+8)//9)
        for index, sketch in enumerate(SKETCHES[page*9:(page+1)*9]):
            col, row = index % 3, index // 3
            rect = pygame.Rect(78 + col * 325, 192 + row * 132, 315, 123)
            draw_sketch_card(self.screen, rect, sketch, self.renderer,
                             sketch.secret_id in secrets, self.weapons.available_ids)
        for text,rect in (("ACHIEVEMENTS",pygame.Rect(705,65,170,38)),("CONTROLS",pygame.Rect(885,65,160,38))):
            self.renderer.rough_rect(self.screen,INK_LIGHT,rect,1,rect.x)
            image = fitted_label(self.renderer.font_small, text, INK, rect.width-16)
            self.screen.blit(image,image.get_rect(center=rect.center))
        self.renderer.doodle_text(self.screen,f"RUNES: {len(secrets)} / {len(SKETCHES)}",(80,586),INK_LIGHT,self.renderer.font_small)
        self.renderer.doodle_text(self.screen,f"PAGE {page+1} / {(len(SKETCHES)+8)//9}",(530,586),INK_LIGHT,self.renderer.font_small)
        self.renderer.rough_rect(self.screen,INK_LIGHT,pygame.Rect(880,595,140,32),1,2323)
        self.renderer.doodle_text(self.screen,"next  >",(903,599),INK,self.renderer.font_small)
        close_rect = self._back_pages_close_rect()
        self.renderer.rough_rect(self.screen, INK_LIGHT, close_rect, 2, 1881)
        close_label = ("PAD-A / PAD-B   close the back cover"
                       if self.last_input_device == "controller"
                       else "B / ESC   close the back cover")
        close = fitted_label(self.renderer.font_small, close_label, INK_LIGHT, close_rect.width-16)
        self.screen.blit(close, close.get_rect(center=close_rect.center))

    def _turn_achievement_page(self, delta):
        self.achievement_page = (getattr(self, 'achievement_page', 0)+delta) % ((len(ACHIEVEMENTS)+15)//16)

    def _draw_achievements(self):
        self.renderer.background(self.screen, 4)
        self.renderer.doodle_text(self.screen, "ACHIEVEMENTS", (86, 52), INK,
                                  self.renderer.font_big, -1)
        self.renderer.doodle_text(
            self.screen,
            f"{self.achievements.count} / {self.achievements.total} clipped into the notebook",
            (90, 116), INK_LIGHT, self.renderer.font_small, 1,
        )
        if not hasattr(self.renderer,"font_caption"):
            self.renderer.font_caption = LocalizedFont(pygame.font.Font(pygame.font.match_font("arial,dejavusans"),17))
        page = getattr(self, 'achievement_page', 0) % ((len(ACHIEVEMENTS)+15)//16)
        for index, achievement in enumerate(ACHIEVEMENTS[page*16:(page+1)*16]):
            column, row = index % 2, index // 2
            rect = pygame.Rect(55 + column * 515, 140 + row * 54, 495, 51)
            unlocked = achievement.achievement_id in self.achievements.unlocked
            paper = (238, 232, 210) if unlocked else (230, 226, 211)
            pygame.draw.rect(self.screen, paper, rect, border_radius=4)
            color = INK if unlocked else (151, 145, 132)
            self.renderer.rough_rect(self.screen, color, rect, 2, 7400 + index * 19)
            mark = "X" if unlocked else "—"
            self.renderer.doodle_text(self.screen, mark, (rect.x + 14, rect.y + 14),
                                      color, self.renderer.font, -2)
            title = ("?????" if achievement.hidden and not unlocked
                     else achievement.title)
            self.renderer.doodle_text(self.screen, title,
                                      (rect.x + 48, rect.y + 3), color,
                                      self.renderer.font_small, -1 if index % 2 else 1)
            description = (achievement.description if unlocked else
                           "condition not written down" if achievement.hidden else
                           achievement.description)
            small = self.renderer.font_caption.render(description, True,
                                                    INK_LIGHT if unlocked else color)
            if small.get_width() > rect.width - 60:
                small = pygame.transform.scale(small,
                    (rect.width-60, max(16, round(small.get_height()*(rect.width-60)/small.get_width()))))
            self.screen.blit(small, (rect.x + 48, rect.y + 30))
        for direction, label, x in ((-1, "<  previous", 300), (1, "next  >", 680)):
            button = pygame.Rect(x, 580, 140, 34)
            self.renderer.rough_rect(self.screen, INK_LIGHT, button, 1, 7920+x)
            text = self.renderer.font_small.render(label, True, INK)
            self.screen.blit(text, text.get_rect(center=button.center))
        total_pages = (len(ACHIEVEMENTS)+15)//16
        text = self.renderer.font_small.render(f"{page+1} / {total_pages}", True, INK_LIGHT)
        self.screen.blit(text, text.get_rect(center=(560,597)))
        close_rect = self._achievements_close_rect()
        self.renderer.rough_rect(self.screen, INK_LIGHT, close_rect, 2, 7811)
        label = ("PAD-A / PAD-B   close"
                 if self.last_input_device == "controller" else "A / ESC   close")
        close = self.renderer.font_small.render(label, True, INK_LIGHT)
        self.screen.blit(close, close.get_rect(center=close_rect.center))

    def _draw_achievement_banner(self):
        achievement = self.achievement_banner
        if achievement is None:
            return
        progress = min(1.0, (4.2 - self.achievement_time) / .28,
                       self.achievement_time / .35)
        x = round(WIDTH - 420 + (1 - max(0, progress)) * 430)
        rect = pygame.Rect(x, 22, 392, 78)
        pygame.draw.rect(self.screen, (244, 238, 216), rect, border_radius=5)
        self.renderer.rough_rect(self.screen, RED_RULE, rect, 3, 7901)
        self.renderer.doodle_text(self.screen, "ACHIEVEMENT", (x + 18, 34), RED_RULE,
                                  self.renderer.font_small, -1)
        self.renderer.doodle_text(self.screen, achievement.title, (x + 18, 61), INK,
                                  self.renderer.font, 1)

    def _draw_settings(self):
        self.renderer.background(self.screen, 0)
        self.renderer.doodle_text(self.screen, "SETTINGS", (420, 85), INK, self.renderer.font_big, -1)
        settings = self.save.data["settings"]
        rows = [
            ("Master volume", settings["master_volume"]),
            ("SFX volume", settings["sfx_volume"]),
            ("Music volume", settings["music_volume"]),
            ("Window size", f"{self.windowed_size[0]} x {self.windowed_size[1]}"),
            ("Fullscreen", "YES" if settings["fullscreen"] else "NO"),
            ("Language", LANGUAGE_NAMES[normalize_language(settings["language"])]),
            ("Back", "PAD-A" if self.last_input_device == "controller" else "ENTER"),
        ]
        active_index = self._active_menu_index(self.settings_index,
            tuple(self._settings_row_rect(i) for i in range(len(rows))))
        for i, (label, value) in enumerate(rows):
            y = 174 + i * 59
            selected = i == active_index
            if selected:
                pygame.draw.rect(self.screen, (235, 229, 208), self._settings_row_rect(i),
                                 border_radius=3)
                self.renderer.doodle_text(self.screen, ">", (290, y), INK, self.renderer.font)
            label_image = fitted_label(self.renderer.font, label, INK, 288)
            self.screen.blit(label_image, (330, y))
            if i < 3:
                value = max(0.0, min(1.0, float(value)))
                pygame.draw.line(self.screen, INK_LIGHT, (640, y + 15), (850, y + 15), 2)
                pygame.draw.circle(self.screen, INK, (round(640 + 210 * value), y + 15), 8, 2)
                self.renderer.doodle_text(self.screen, f"{round(value * 100):d}%",
                                          (875, y), INK_LIGHT, self.renderer.font_small)
            else:
                value_image = fitted_label(self.renderer.font, str(value), INK_LIGHT, 228)
                self.screen.blit(value_image, (680, y))
        footer = ("D-PAD change  •  PAD-A confirm  •  PAD-B returns"
                  if self.last_input_device == "controller"
                  else "click or use arrows  •  F11 fullscreen  •  ESC returns")
        footer_image = fitted_label(self.renderer.font_small, footer, INK_LIGHT, WIDTH-160)
        self.screen.blit(footer_image, footer_image.get_rect(center=(WIDTH//2, 637)))

    def _draw_ending(self):
        if self.transition_snapshot is None:
            self._draw_scene(self.screen)
            self._draw_hud()
            self.transition_snapshot = self.screen.copy()
        if self.ending_time < 1.0:
            self.screen.blit(self.transition_snapshot, (0, 0))
            self._draw_tool_erasure(self.ending_time / .9)
            return
        blank = pygame.Surface((WIDTH, HEIGHT))
        blank.fill((250, 248, 235))
        # Fibres, but no rules: this is the first truly blank page.
        for i in range(80):
            x = (i * 137) % WIDTH
            y = (i * 83) % HEIGHT
            pygame.draw.line(blank, (235, 232, 216), (x, y), (x + 12, y), 1)
        if self.ending_time < 3.3:
            self.renderer.page_turn(self.screen, self.transition_snapshot, blank,
                                    (self.ending_time - 1.0) / 2.3)
            return
        self.afterword.draw(self.screen, self.renderer,
                            self.last_input_device == "controller")

    def _draw_pencil_cursor(self):
        pos = self._window_to_canvas(pygame.mouse.get_pos(), clamp=True)
        if pos is None:
            return
        x, y = pos
        pygame.draw.polygon(self.screen, (42, 40, 38), [(x, y), (x + 6, y + 14), (x + 11, y + 8)])
        pygame.draw.polygon(self.screen, (220, 177, 91), [(x + 6, y + 14), (x + 11, y + 8),
                                                         (x + 23, y + 24), (x + 17, y + 29)])

    def _draw_aim_cursor(self):
        if self.weapons.current_id == "unarmed" or self.player.locked:
            return
        if self.last_input_device == "controller":
            return
        pos = self._window_to_canvas(pygame.mouse.get_pos(), clamp=True)
        if pos is None:
            return
        x, y = round(pos[0]), round(pos[1])
        pygame.draw.circle(self.screen, (247, 243, 224), (x, y), 12)
        melee = self.weapons.current_id in ("pencil_blade", "excalibur")
        color = (151, 55, 55) if self.weapons.current_id == "excalibur" else INK
        if melee:
            pygame.draw.arc(self.screen, color, (x - 12, y - 12, 24, 24), .35, 2.15, 2)
            pygame.draw.line(self.screen, color, (x - 7, y + 8), (x + 8, y - 7), 2)
            pygame.draw.circle(self.screen, color, (x, y), 2)
        else:
            pygame.draw.circle(self.screen, color, (x, y), 8, 2)
            pygame.draw.line(self.screen, color, (x - 13, y), (x - 6, y), 2)
            pygame.draw.line(self.screen, color, (x + 6, y), (x + 13, y), 2)
            pygame.draw.line(self.screen, color, (x, y - 13), (x, y - 6), 2)
            pygame.draw.line(self.screen, color, (x, y + 6), (x, y + 13), 2)
