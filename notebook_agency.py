"""Player-authored requests and combat revisions built on existing paper geometry."""
import math
import pygame
from scripted_events import ArtistDirector, ArtistTool
from paper_renderer import jitter_line
from sketch_marks import rough_circle
from page_arsenal import draw_weapon
from settings import INK, INK_LIGHT

class NotebookAgency:
    active=True
    mandatory=False
    layer=0
    def __init__(self,runtime):
        self.runtime=runtime
        self.page=runtime.index
        self.arenas=[e for e in runtime.entities.items if getattr(e,'is_combat_arena',False)]
        self.first=self.arenas[0] if self.arenas else None
        self.offer_x=440 if self.page==0 else self.first.start_x-540 if self.first else 400
        self.choice=''
        self.restored=False
        self.timer=0.0
        self.operation=None
        self.platforms=[]
        self.pets=[]
        self.used_erasers=set()
        self.boss_phases=set()
        self.hand=ArtistDirector()
        self.letter=''
        self.letter_time=0
        self.target=None
        self.last_scratch=-1

    def _save_choice(self,ctx,choice):
        if not ctx.game:return
        ctx.game.save.data.setdefault('notebook_choices',{})[str(self.page)]=choice
        ctx.game.behavior.record('artist_request',page=self.page,choice=choice)
        ctx.game.persist_behavior(write=True)

    def _platform(self,ctx,x,y,width,name):
        p=ctx.world.add(x,x+width,y,10,name,8700+len(self.platforms))
        p.appearance='handwriting';p.draw_progress=0
        self.platforms.append(p)
        return p

    def _route(self,ctx):
        if self.platforms:return
        if self.page==0:
            self._platform(ctx,680,520,300,'requested_road_a')
            self._platform(ctx,1005,465,270,'requested_road_b')
        elif self.first:
            self._platform(ctx,self.first.start_x+115,510,190,'requested_road_a')
            self._platform(ctx,self.first.start_x+350,445,180,'requested_road_b')

    def _give_tool(self,ctx,select=True):
        if not ctx.weapons:return
        ctx.weapons.unlock('margin_maul')
        if ctx.weapons.active_loadout is not None:ctx.weapons.active_loadout.add('margin_maul')
        if select:ctx.weapons.select('margin_maul')
        if ctx.game:
            snapshot=ctx.weapons.snapshot()
            ctx.game.save.update_combat(snapshot['unlocked'],snapshot['current_id'],snapshot['ammo'])

    def choose(self,choice,ctx):
        if self.choice or choice not in ('tool','road'):return False
        self.choice=choice
        self.operation=choice;self.timer=0
        if choice=='road':self._route(ctx)
        self._save_choice(ctx,choice)
        self.letter=('Too heavy? You asked for it. Q swaps back.' if choice=='tool'
                     else 'All right. Your way. Jump onto the new line.')
        self.letter_time=6
        ctx.sounds.play('pencil')
        return True

    def _restore(self,ctx):
        self.restored=True
        raw=ctx.game.save.data.get('notebook_choices',{}) if ctx.game else {}
        self.choice=raw.get(str(self.page),'') if isinstance(raw,dict) else ''
        if self.choice=='tool':self._give_tool(ctx,False)
        elif self.choice=='road':
            self._route(ctx)
            for p in self.platforms:p.draw_progress=1

    def _begin_rescue(self,ctx,arena):
        live=[e for e in arena.enemies if not e.dead]
        ordinary=[e for e in live if not getattr(e,'is_boss',False) and e.kind!='baby_face_giant']
        if not ordinary:return False
        self.target=min(ordinary,key=lambda e:abs(e.x-ctx.player.center_x))
        self.target.artist_still=1.4
        self.target.projectiles.clear()
        self.operation='erase_enemy';self.timer=0
        self.used_erasers.add(arena.arena_id)
        self.letter='Too many teeth. Let me fix that.';self.letter_time=4.0
        ctx.sounds.play('erase')
        return True

    def update(self,dt,ctx,interact=False):
        if not self.restored:self._restore(ctx)
        self.letter_time=max(0,self.letter_time-dt)
        self.hand.tool.visible=False
        for pet in self.pets:
            pet[2]+=dt;pet[0]+=math.sin(pet[2])*dt*28
        if ctx.player.health<=0:return
        active=next((a for a in self.arenas if a.encounter_active and not a.completed),None)
        if not self.choice and not active and not ctx.player.locked:
            nearest=min((('tool',self.offer_x),('road',self.offer_x+250)),key=lambda item:abs(ctx.player.center_x-item[1]))
            if abs(ctx.player.center_x-nearest[1])<95:
                ctx.level.interaction_hint='E  ASK THE ARTIST: '+('DRAW A HEAVY PENCIL' if nearest[0]=='tool' else 'DRAW A HIGH ROAD')
                if interact:self.choose(nearest[0],ctx)
        if active and self.operation is None:
            # Explicit requests change a dangerous drawing, once per room.
            if (ctx.player.health==1 and active.arena_id not in self.used_erasers
                    and any(not e.dead and not getattr(e,'is_boss',False) and e.kind!='baby_face_giant' for e in active.enemies)):
                ctx.level.interaction_hint='E  ASK THE ARTIST TO ERASE A FOE (once this room)'
                if interact:self._begin_rescue(ctx,active)
            for boss in active.enemies:
                if self.operation is not None:break
                if not getattr(boss,'is_boss',False):continue
                phase=getattr(boss,'phase',1);key=(active.arena_id,phase)
                if phase>=2 and key not in self.boss_phases:
                    self.boss_phases.add(key)
                    # A new flank is additive, never removes the current support.
                    side=-1 if ctx.player.center_x<boss.x else 1
                    x=max(active.start_x+45,min(active.end_x-225,ctx.player.center_x+side*110))
                    p=self._platform(ctx,x,500,165,'artist_boss_step_'+active.arena_id+'_'+str(phase))
                    self.operation='boss_road';self.target=p;self.timer=0
                    self.letter='He changed the rules. So can we. Use this line.';self.letter_time=4
                    ctx.sounds.play('pencil')
                    if ctx.game:ctx.game.behavior.record('boss_redraw',kind=boss.kind,phase=phase)
                    break
        if self.operation:
            self.timer+=dt
            p=min(1,self.timer/1.15)
            if self.operation=='tool':
                self.hand.tool=ArtistTool('pencil',self.offer_x-35+p*125,428,True)
                if p>=1:self._give_tool(ctx);self.operation=None
            elif self.operation in ('road','boss_road'):
                platforms=[self.target] if self.operation=='boss_road' else self.platforms[:2]
                local=p*len(platforms)
                for i,platform in enumerate(platforms):
                    platform.draw_progress=min(1,max(0,local-i))
                drawing=platforms[min(len(platforms)-1,int(local))]
                self.hand.tool=ArtistTool('pencil',drawing.visible_x2,drawing.y,True)
                if p>=1:self.operation=None
            else:
                enemy=self.target
                self.hand.tool=ArtistTool('eraser',enemy.x+math.sin(p*34)*25,enemy.y-25,True)
                ctx.particles.eraser_dust(enemy.x,enemy.y-25,1)
                if p>=1:
                    if not enemy.dead:
                        enemy.dead=True;enemy.projectiles.clear()
                        restore=getattr(enemy,"_restore_temporary_erases",None)
                        if callable(restore):restore(force=True)
                        self.pets.append([enemy.x,enemy.ground_y,0])
                        if ctx.game:ctx.game.behavior.record('artist_mercy',kind=enemy.kind)
                    self.operation=None
            tick=int(self.timer*5)
            if tick!=self.last_scratch:
                self.last_scratch=tick
                ctx.sounds.play('erase' if self.operation=='erase_enemy' else 'pencil')
        elif active:
            drawing=next((e for e in active.enemies if getattr(e,'notebook_reveal',1)<1),None)
            if drawing is not None:
                p=drawing.notebook_reveal
                self.hand.tool=ArtistTool('pencil',drawing.x+math.sin(p*30)*15,
                    drawing.rect.top+drawing.rect.height*p,True)
        if self.hand.tool.visible:
            ctx.player.look_target=(self.hand.tool.x,self.hand.tool.y)

    def draw(self,s,camera,renderer):
        material=renderer.notebook
        if not self.choice:
            for choice,x in (('tool',self.offer_x),('road',self.offer_x+250)):
                sx=camera.screen_x(x)
                if sx < -220 or sx>1300:continue
                rough_circle(s,(135,97,86),(sx,425),43,811,1,2,squash=(1.3,.6),wobble=3)
                material.hand(s,'draw me...',(sx-67,379),(134,65,58),True)
                material.hand(s,'a weapon' if choice=='tool' else 'a way up',(sx-56,464),INK,True)
                if choice=='tool':draw_weapon(s,'margin_maul',self.page,(sx-32,424),-.12,scale=.68)
                else:
                    for i in range(3):jitter_line(s,INK,(sx-30+i*22,445-i*16),(sx-3+i*22,445-i*16),2,i)
        elif self.operation=='tool':
            old=s.get_clip();x=camera.screen_x(self.offer_x)-50
            s.set_clip(pygame.Rect(x,385,round(155*min(1,self.timer/1.15)),80))
            draw_weapon(s,'margin_maul',self.page,(x+15,428),0,scale=1.2)
            s.set_clip(old)
        for x,y,t in self.pets:
            sx=camera.screen_x(x)
            rough_circle(s,(91,103,93),(sx,y-15),13,22,2)
            rough_circle(s,(91,103,93),(sx+18,y-26),9,23,2)
            for dx in (-8,9):jitter_line(s,INK,(sx+dx,y-8),(sx+dx+math.sin(t*9)*4,y),2,8)
            material.hand(s,'better.',(sx-25,y-58),(139,88,80),True)

    def draw_overlay(self,s,camera,renderer):
        self.hand.draw(s,camera,renderer)
        if self.letter_time>0:
            # On-page handwriting, not a modal dialogue card.
            renderer.notebook.artist_note(s,self.letter)
