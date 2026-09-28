"""Readable, avoidable edits on the expanded final two page approaches."""
import pygame
from paper_renderer import jitter_line
from settings import RED_RULE


class CorridorInk:
    active = True
    mandatory = False
    layer = 0

    def __init__(self, x, page):
        self.x = float(x)
        self.page = page
        self.timer = 0.0
        self.state = 'rest'
        self.cooldown = 0.0
        self.visible = False

    def update(self, dt, ctx, interact=False):
        del interact
        self.visible = abs(ctx.player.center_x-self.x) < 690
        if not self.visible or ctx.player.locked:
            return
        self.timer += dt
        self.cooldown = max(0, self.cooldown-dt)
        period = 3.3 if self.page == 3 else 3.7
        local = (self.timer + (self.x % 7)*.17) % period
        self.state = 'warn' if local < .82 else 'ink' if local < 1.43 else 'rest'
        if self.state != 'ink' or self.cooldown > 0:
            return
        player = ctx.player
        # Agent scanners block a narrow vertical band. The final page edits a
        # low strip, so an upper landing or a jump is the intended answer.
        danger = (pygame.Rect(round(self.x-10), 360, 20, 230) if self.page == 3 else
                  pygame.Rect(round(self.x-72), 531, 144, 59))
        if danger.colliderect(player.rect) and player.hurt(self.x):
            self.cooldown = 1.25
            ctx.sounds.play('ink')
            ctx.camera.kick(3.5,.14)
            ctx.particles.paper_puff(player.center_x,player.rect.centery,5)
            if ctx.game:
                ctx.game.behavior.record('margin_hazard',page=self.page)

    def draw(self,surface,camera,renderer):
        if not self.visible or self.state == 'rest':
            return
        sx = camera.screen_x(self.x)
        active = self.state == 'ink'
        color = RED_RULE if active else (164,118,109)
        if self.page == 3:
            for offset in (-4,0,4) if active else (0,):
                jitter_line(surface,color,(sx+offset,360),(sx+offset,590),
                            3 if active else 1,int(self.x)+offset,2,1.3)
            renderer.doodle_text(surface,'SCAN / WAIT' if not active else 'CARBON SCAN',
                                 (sx-52,324),color,renderer.font_small,-1)
        else:
            for offset in (0,5) if active else (0,):
                jitter_line(surface,color,(sx-75,536+offset),(sx+75,536+offset),
                            4 if active else 1,int(self.x)+offset,2,1.4)
            renderer.doodle_text(surface,'ERASER / JUMP' if not active else 'ERASE',
                                 (sx-57,502),color,renderer.font_small,1)
