"""One optional rejected-warrior fight, plus varied notebook discoveries."""
import pygame
from advanced_enemies import create_enemy
from entities import LostSketch
from notebook_art import redraw_doodle
from scripted_events import ArtistDirector, ArtistTool, artist_canvas_free
from action_content import claim_artist_canvas, release_artist_canvas
from paper_renderer import jitter_line
from settings import INK, RED_RULE

# Different opponents and conversations for each page, not one repeated patrol.
TRIALS = (
    ('THE REJECTED CAST', ('goblin_scribble', 'fold_duelist'),
     'I left my first attempts here. They do not want to be forgotten.',
     'You gave the old drawing a second chance. Keep what it taught you.'),
    ('THE BOUNTY IN THE MARGIN', ('ink_outlaw', 'cactus_gunner'),
     'That scrap has a bounty on it. Shall I draw the ones hunting it?',
     'I was going to write a price. You made it a name instead.'),
    ('THE FAILED EXPERIMENT', ('star_scout', 'moon_bot'),
     'This experiment escaped the calculation. Help me finish it?',
     'The mistake was useful. I will leave your answer in the margin.'),
    ('THE CARBON ARCHIVE', ('redaction_agent', 'ink_clone'),
     'That file is being watched. Open it and they will know you are here.',
     'A copy can hide a name. It cannot hide what you just did.'),
    ('THE UNFINISHED ANSWER', ('crumpled_one', 'fold_duelist'),
     'These are the endings I threw away. Can you face them?',
     'All right. Your answer stays. I am putting the eraser down.'),
)

class SketchTrial:
    active = True
    mandatory = False
    layer = 0

    def __init__(self, runtime, sketch, index):
        self.sketch, self.page, self.index = sketch, runtime.index, index
        self.title, self.cast, self.invitation, self.answer = TRIALS[self.page]
        self.enemies = []
        self.encounter_active = False
        self.completed = sketch.discovered
        self.wave = 0
        self.reveal = 0
        self.letter_time = 0
        self.letter = ''
        self.reply_pending = False
        self.pending_spawn = False
        self.hand = ArtistDirector()
        # Fight on an existing broad landing below/near the collectible. Do not
        # add floors across authored pits or make elevated scraps trivial.
        floors = [p for p in runtime.world.collision_rects() if p.width >= 210]
        floor = min(floors, key=lambda p: max(p.left-sketch.x, sketch.x-p.right, 0)+abs(p.top-590)*2) if floors else pygame.Rect(sketch.x-220,590,440,12)
        center = max(floor.left+100, min(floor.right-100, sketch.x))
        self.bounds = (max(floor.left+6, center-265), min(floor.right-6, center+265))
        self.ground = floor.top
        self.reward = {'practice_monster':'pencil_blade'}.get(sketch.secret_id)
        self.tool_gift = None
        if sketch.discovered and self.reward:
            from action_content import WeaponPickup
            self.tool_gift=WeaponPickup(sketch.x,self.ground,self.reward,page_index=self.page)
        sketch.trial = self

    def begin(self, ctx):
        if self.completed or self.encounter_active or ctx.player.locked:
            return False
        if any(getattr(e,'encounter_active',False) and not getattr(e,'completed',False)
               for e in ctx.level.entities.items if e is not self):
            return False
        if not artist_canvas_free(ctx,self) or not claim_artist_canvas(ctx,self):
            return False
        self.encounter_active = True
        self.wave = 0
        self._spawn(ctx)
        self.letter, self.letter_time = self.invitation, 5.5
        self.reply_pending = False
        return True

    def _spawn(self, ctx):
        if not artist_canvas_free(ctx,self) or not claim_artist_canvas(ctx,self):
            self.pending_spawn = True
            return False
        self.pending_spawn = False
        kind = self.cast[(self.index+self.wave)%len(self.cast)]
        # This one rejected-warrior discovery earns its answer in two rounds.
        left, right = self.bounds
        x = right-40 if abs(ctx.player.center_x-(right-40)) > abs(ctx.player.center_x-(left+40)) else left+40
        enemy = create_enemy(kind, x, self.ground, 12000+self.page*100+self.index*5+self.wave)
        enemy.notebook_reveal = 0
        self.enemies = [enemy]
        self.reveal = 0
        ctx.sounds.play('pencil')
        return True

    def update(self, dt, ctx, interact=False):
        self.letter_time = max(0,self.letter_time-dt)
        self.hand.tool.visible = False
        if self.sketch.discovered:
            self.completed = True
            release_artist_canvas(ctx,self)
        if self.completed and self.tool_gift is not None:
            self.tool_gift.update(dt,ctx,interact)
        if not self.encounter_active:
            release_artist_canvas(ctx,self)
            if any(getattr(e,'encounter_active',False) and getattr(e,'mandatory',False)
                   and not getattr(e,'completed',False) for e in ctx.level.entities.items):
                self.letter_time = 0
            if self.completed and self.reply_pending and self.sketch.near and interact:
                self.reply_pending = False
                self.letter = self.answer
                self.letter_time = 5
            return
        # No abandoned projectiles, remote kills, or fights following a respawn.
        if (ctx.player.health <= 0 or abs(ctx.player.center_x-self.sketch.x)>800
                or any(getattr(e,'encounter_active',False) and getattr(e,'mandatory',False)
                       and not getattr(e,'completed',False)
                       for e in ctx.level.entities.items if e is not self)):
            self.enemies.clear()
            self.encounter_active = False
            self.pending_spawn = False
            self.letter_time = 0
            release_artist_canvas(ctx,self)
            return
        if ctx.player.locked:
            return
        if self.pending_spawn and not self._spawn(ctx):return
        if self.reveal<1:
            if not artist_canvas_free(ctx,self) or not claim_artist_canvas(ctx,self):return
            next_reveal = min(1,self.reveal+dt/.95)
            # Keep an unfinished footprint inactive while occupied. Once the
            # figure is live, walking into it must not undo its finished ink.
            occupied=any(e.rect.colliderect(ctx.player.rect.inflate(8,4)) for e in self.enemies)
            self.reveal = .98 if next_reveal>=1 and occupied else next_reveal
        if self.reveal>=1:release_artist_canvas(ctx,self)
        for enemy in self.enemies:
            enemy.notebook_reveal = self.reveal
            if self.reveal < 1:
                self.hand.tool = ArtistTool('pencil',enemy.x,enemy.rect.top+enemy.height*self.reveal,True)
            else:
                enemy.update(dt,ctx,self.bounds)
        if self.enemies and all(e.dead for e in self.enemies):
            self.wave += 1
            rounds = 1 if self.sketch.secret_id=='old_first_figure' else 2
            if self.wave < rounds:
                self.enemies.clear()
                self._spawn(ctx)
                self.letter = 'One more line. This one fights differently.'
                self.letter_time = 3
            else:
                self.completed = True
                self.encounter_active = False
                self.enemies.clear()
                release_artist_canvas(ctx,self)
                self.letter = 'You earned the drawing. E to keep it and answer me.'
                self.letter_time = 5
                self.reply_pending = True
                if self.reward and ctx.weapons:
                    from action_content import WeaponPickup
                    self.tool_gift=WeaponPickup(self.sketch.x,self.ground,self.reward,page_index=self.page)
                if ctx.game:
                    ctx.game.behavior.record('sketch_trial',page=self.page,sketch=self.sketch.secret_id)
                    ctx.game.persist_behavior(write=True)

    def draw(self, s, camera, renderer):
        if self.tool_gift is not None:self.tool_gift.draw(s,camera,renderer)
        if not self.sketch.discovered:
            x,y=camera.screen_x(self.sketch.x),round(self.sketch.y+camera.offset_y)
            if -300<x<s.get_width()+300:
                if not self.completed:
                    for dy in (-24,-8):jitter_line(s,RED_RULE,(x-29,y+dy),(x+30,y+dy-3),2,dy,2,1)
                if self.sketch.near:
                    renderer.notebook.hand(s,self.title,(max(20,x-145),max(95,y-188)),RED_RULE,True)
                    if self.encounter_active:
                        renderer.notebook.hand(s,'guard below / defeat the rejected drawing',(max(20,x-155),max(120,y-165)),INK,True)
        for enemy in self.enemies:
            old=s.get_clip()
            if self.reveal<1:
                s.set_clip(pygame.Rect(camera.screen_x(enemy.x)-100,enemy.rect.top+camera.offset_y,200,round(enemy.height*self.reveal)))
            if not redraw_doodle(enemy,s,camera,renderer):enemy.draw(s,camera,renderer)
            s.set_clip(old)

    def draw_overlay(self,s,camera,renderer):
        self.hand.draw(s,camera,renderer)
        if self.letter_time>0:renderer.notebook.artist_note(s,self.letter)


def add_page_experiences(runtime):
    from sketch_discovery import attach_discoveries
    attach_discoveries(runtime)
    sketches=[e for e in runtime.entities.items if isinstance(e,LostSketch)]
    for index,sketch in enumerate(sketches):
        # Combat is one way to discover a drawing. The roof, stain, carbon
        # pressure, torn seam and erased draft now have their own answers.
        if sketch.secret_id=='practice_monster':
            runtime.entities.add(SketchTrial(runtime,sketch,index))
    # This tool is an independent physical drawing. The badge only teaches
    # its sidearm technique; collecting a sketch never changes the weapon.
    if runtime.index==3:
        from action_content import WeaponPickup
        runtime.entities.add(WeaponPickup(6520,590,'carbon_lance',page_index=3))
