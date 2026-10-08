"""A brief protected drawing entrance shared by every real boss encounter."""
from __future__ import annotations
import math
import pygame
from action_content import release_artist_canvas
from input_state import InputFrame
from scripted_events import ArtistDirector, ArtistTool


class BossCinematic:
    DURATION = 3.2
    DRAW_START = .45
    DRAW_END = 2.45

    def __init__(self, game):
        self.game = game
        self.active = False
        self.elapsed = 0.0
        self.owner = self.boss = self.world = None
        self.hand = ArtistDirector()
        self.zoom = 1.0

    def maybe_begin(self):
        game = self.game
        if self.active or game.player.health <= 0 or game.level.respawn_timer > 0:
            return False
        for room in game.level.entities.items:
            if not getattr(room, 'encounter_active', False) or getattr(room, 'completed', False):
                continue
            for boss in getattr(room, 'enemies', ()):
                if ((getattr(boss, 'is_boss', False) or getattr(boss, 'kind', '') == 'baby_face_giant') and not boss.dead
                        and not getattr(boss, 'notebook_spawn_pending', False)
                        and not getattr(boss, 'cinematic_seen', False)):
                    return self.begin(room, boss)
        return False

    def begin(self, room, boss):
        game = self.game
        self.active, self.elapsed = True, 0.0
        self.owner, self.boss, self.world = room, boss, game.level.world
        self.context = game.level.context(game.player, game.camera, game.particles, game.sounds)
        boss.cinematic_seen = True
        boss.cinematic_active = True
        boss.notebook_reveal = 0.0
        getattr(boss, 'projectiles', []).clear()
        room.boss_intro_time = 0.0
        if hasattr(room, 'letter_time'):
            room.letter_time = 0.0
        game.level.toast_time = game.level.page_title_time = 0.0
        game.damage_flash = 0.0
        room.cinematic_active = True
        game.level.interaction_hint = ''
        game.player.acquire_lock('boss_cinematic')
        self.velocity = (game.player.vx, game.player.vy)
        game.player.vx = game.player.vy = 0
        game.player.look_target = (boss.x, boss.rect.centery)
        game.hit_stop = 0
        game._buffered_actions = InputFrame()
        game.camera.shake_time = game.camera.shake_strength = 0
        game.camera.set_script_target(boss.x, 'boss_cinematic')
        self.title = getattr(room, 'title', getattr(room, 'display_name', boss.kind.replace('_', ' ').upper()))
        game.sounds.play('boss_reveal')
        self._last_pencil = -1.0
        return True

    def update(self, dt):
        game = self.game
        if (game.level.world is not self.world or game.player.health <= 0
                or not getattr(self.owner, 'encounter_active', False) or self.boss.dead):
            self.cancel()
            return
        self.elapsed = min(self.DURATION, self.elapsed+max(0.0, dt))
        progress = max(0.0, min(1.0, (self.elapsed-self.DRAW_START)/(self.DRAW_END-self.DRAW_START)))
        self.boss.notebook_reveal = progress
        if hasattr(self.owner, 'reveal'):
            self.owner.reveal = progress
        self.hand.tool = ArtistTool('pencil', self.boss.x,
            self.boss.rect.top+self.boss.rect.height*progress, 0 < progress < 1)
        # The first moment frames the figure; the final beat gives the player
        # a clear full drawing before the camera returns to the fighting lane.
        enter = min(1.0, self.elapsed/.65)
        leave = min(1.0, max(0.0, (self.DURATION-self.elapsed)/.65))
        smooth = lambda value: value*value*(3-2*value)
        self.zoom = 1.0+.7*min(smooth(enter), smooth(leave))
        game.camera.zoom = self.zoom
        game.camera.set_script_target(self.boss.x, 'boss_cinematic')
        game.camera.update(dt, game.player.center_x, self.world.width, 0,
                           self.boss.rect.centery, player_locked=True)
        if 0 < progress < 1 and self.elapsed-self._last_pencil >= .22:
            game.sounds.play('pencil')
            self._last_pencil = self.elapsed
        if self.elapsed >= self.DURATION:
            self.finish()

    def finish(self):
        self.boss.notebook_reveal = 1.0
        self.boss.notebook_activation_blocked = False
        if hasattr(self.owner, 'reveal'):
            self.owner.reveal = 1.0
        if hasattr(self.owner, 'duel_elapsed'):
            self.owner.duel_elapsed = max(3.2, self.owner.duel_elapsed)
        if hasattr(self.owner, 'hand'):
            self.owner.hand.tool.visible = False
        release_artist_canvas(self.context, self.owner)
        self.cancel(restore_velocity=True)

    def cancel(self, restore_velocity=False):
        game = self.game
        if self.active and restore_velocity:
            game.player.vx, game.player.vy = self.velocity
        if hasattr(game, 'player'):
            game.player.release_lock('boss_cinematic')
            game.player.look_target = None
        game.camera.zoom = self.zoom = 1.0
        game.camera.release_script_target('boss_cinematic')
        self.hand.tool.visible = False
        if self.boss is not None:
            self.boss.cinematic_active = False
        if self.owner is not None:
            self.owner.cinematic_active = False
            release_artist_canvas(self.context, self.owner)
            if hasattr(self.owner, "hand"):
                self.owner.hand.tool.visible = False
        self.active = False
        self.owner = self.boss = self.world = None
        if hasattr(game, 'pending_input'):
            game.pending_input = InputFrame()
        if hasattr(game, '_buffered_actions'):
            game._buffered_actions = InputFrame()

    def draw_hand(self, target, camera, renderer):
        if self.active:
            self.hand.draw(target, camera, renderer)

    def present(self, target, renderer):
        if not self.active:
            return
        width, height = target.get_size()
        crop = pygame.Rect(0, 0, max(1, round(width/self.zoom)), max(1, round(height/self.zoom)))
        crop.center = (self.game.camera.screen_x(self.boss.x),
                       round(self.boss.rect.centery+self.game.camera.offset_y))
        crop.clamp_ip(target.get_rect())
        enlarged = pygame.transform.smoothscale(target.subsurface(crop), target.get_size())
        target.blit(enlarged, (0, 0))
        # No duplicate portrait or combat rule: the actual figure is the focus.
        label = renderer.font.render(self.title, True, (70, 59, 50))
        if label.get_width() > width-120:
            label = pygame.transform.smoothscale(label, (width-120, label.get_height()))
        self._caption(target, label, (width//2, 86))
        if self.elapsed < self.DRAW_END:
            status = renderer.font_small.render('THE ARTIST IS DRAWING', True, (104, 89, 72))
            self._caption(target, status, (width//2, 125))

    @staticmethod
    def _caption(target, image, center):
        # Keep the writing legible over pre-existing page formulas. The small
        # clear strip borrows the local paper shade, without another border.
        rect = image.get_rect(center=center)
        paper = rect.inflate(14, 8).clip(target.get_rect())
        shade = pygame.Surface(paper.size, pygame.SRCALPHA)
        color = pygame.transform.average_color(target, paper)
        shade.fill((*color[:3], 247))
        target.blit(shade, paper)
        target.blit(image, rect)
