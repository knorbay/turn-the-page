"""Five-page beta: new combat chapters, physical edits and persistent retries."""
import math
import pygame
from chapters import ChapterRuntime, Checkpoint
from combat import CombatArena
from action_content import (WeaponPickup, ArenaPaperBeat, register_artist_stage,
                            claim_artist_stage, release_artist_stage, cleared_wave)
from page_arsenal import label_for
from entities import LostSketch
from scripted_events import ArtistTool, EventSequence, EventStep
from world import PaperWorld, PaperNote

NEW_ROOMS={
 3: (
  ('agent_checkpoint',1100,2120,('redaction_agent','ink_clone'),('redaction_agent','paper_wasp','ink_clone')),
  ('carbon_crossfire',3000,4200,('redaction_agent','ruler_guard'),('doodle_turret','redaction_agent','comet_hound')),
  ('redacted_rooftops',5000,6200,('paper_wasp','redaction_agent'),('ink_clone','eraser_brute','redaction_agent')),
  ('office_ambush',7000,8240,('redaction_agent','crumpled_one','ink_clone'),('paper_wasp','doodle_turret','redaction_agent')),
  ('scissor_office',9000,10320,('redaction_agent','ink_clone'),('scissor_director',)),
 ),
 4: (
  ('last_lesson',900,2040,('ink_samurai','redaction_agent'),('lantern_yokai','comet_hound','ruler_guard')),
  ('erased_answers',2800,4020,('eraser_brute','doodle_turret'),('moon_bot','redaction_agent','ink_clone')),
  ('margin_revolt',4800,6040,('cactus_gunner','goblin_scribble','origami_drone'),('redaction_agent','comet_hound','ruler_guard')),
  ('the_last_crossout',6900,8140,('ink_clone','redaction_agent','moon_bot'),('eraser_brute','paper_wasp','ink_samurai')),
  ('final_margin_revision',9000,10520,('final_editor',)),
 )
}
ROOM_BRIEFS={
 'agent_checkpoint':('01 / FALSE ID','The agent commits to three shots. Then reloads.'),
 'carbon_crossfire':('02 / CARBON CROSSFIRE','Climb the ink line; drop behind the shield.'),
 'redacted_rooftops':('03 / ROOFTOP REVISION','Air and ground threats. Keep a landing line.'),
 'office_ambush':('04 / THE OFFICE BITES','Deal with the turret before the next copy.'),
 'scissor_office':('THE HEAD OF REDACTION','Jump the low cut. Leave the X. Hit the open hinge.'),
 'last_lesson':('01 / WRONG CLASS','Five pages of enemies. One small stick figure.'),
 'erased_answers':('02 / ERASED ANSWERS','A platform can save you. Watch the eraser.'),
 'margin_revolt':('03 / MARGIN REVOLT','Break the ranged line before chasing the hound.'),
 'the_last_crossout':('04 / THE LAST CROSSOUT','Every enemy has a pause. Find yours.'),
 'final_margin_revision':('THE FINAL EDITOR','Read the proof. Attack when the binder opens.'),
}

class ArtistCombatHand:
    """A useful new flank is drawn in the pause after the first cleared wave."""
    active=True
    mandatory=False
    layer=0
    def __init__(self,arena,platform):
        self.arena=arena;self.platform=platform
        self.phase='waiting';self.timer=0;self.completed=False;self.helped=False
        register_artist_stage(arena,self)
    @property
    def entry_ready(self):
        return True
    @property
    def wave_ready(self):
        return self.completed or self.arena.wave+1>=len(self.arena.wave_ids)
    def update(self,dt,ctx,interact=False):
        if self.arena.completed:
            self.completed=True
            self.platform.draw_progress=1
            release_artist_stage(self.arena,self)
            return
        if self.completed or not cleared_wave(self.arena) or self.wave_ready:return
        if not claim_artist_stage(self.arena,self):return
        if self.phase=='waiting':
            self.phase='warn';self.timer=0
            ctx.level.toast='THE ARTIST: New landing. Try the upper angle.'
            ctx.level.toast_time=2.4
            ctx.sounds.play('pencil')
        self.timer+=dt
        if self.phase=='warn':
            if self.timer>=.32:
                self.phase='edit';self.timer=0
        elif self.phase=='edit':
            # Redraw a lower step instead of removing the player's support.
            # The actual interval and its collision grow under the pencil.
            self.platform.draw_progress=min(1,self.timer/.76)
            ctx.director.tool=ArtistTool('pencil',self.platform.visible_x2,self.platform.y,True)
            ctx.particles.pencil_speck(self.platform.visible_x2,self.platform.y)
            if self.timer>=.76:
                self.completed=True
                self.helped=True
                release_artist_stage(self.arena,self)
                ctx.sounds.play('paper_step')
                if ctx.game:
                    ctx.game.behavior.record('artist_help',kind='real_landing',page=ctx.level.chapter_index)
    def draw(self,surface,camera,renderer):
        if self.phase!='warn' or self.completed:return
        a,b=camera.screen_x(self.platform.x1),camera.screen_x(self.platform.x2)
        y=round(self.platform.y+camera.offset_y)
        for x in range(a,b,18):pygame.draw.line(surface,(161,105,90),(x,y),(min(b,x+7),y),1)

class FinalPageEdit:
    active=True
    mandatory=False
    layer=0
    def __init__(self,arena,world):
        self.arena=arena;self.world=world;self.applied=False;self.completed=False
        self.timer=0;self.scenario=None;self.platforms=[]
    def update(self,dt,ctx,interact=False):
        if not self.arena.encounter_active:return
        boss=next((e for e in self.arena.enemies if e.kind=='final_editor'),None)
        if boss is None or boss.scenario is None:return
        if not self.applied:
            self.applied=True;self.scenario=boss.scenario
            # Different geometry accompanies the four attack scripts.
            layout={
              'aggressive':((250,495),(1040,495)),
              'avoidant':((580,500),(790,425)),
              'precise':((300,500),(1080,500),(690,415)),
              'unreadable':((420,500),(890,460)),
            }[self.scenario]
            for i,(offset,y) in enumerate(layout):
                p=self.world.add(self.arena.start_x+offset,self.arena.start_x+offset+145,y,10,f'final_edit_{i}',8100+i)
                p.draw_progress=0;p.appearance='handwriting';self.platforms.append(p)
            ctx.sounds.play('pencil')
            ctx.level.toast='THE ARTIST: I kept your working notes.'
            ctx.level.toast_time=3
        self.timer+=dt
        if self.timer<2.4:
            for i,p in enumerate(self.platforms):
                p.draw_progress=min(1,max(0,(self.timer-.45-i*.3)/.7))
                if 0<p.draw_progress<1:
                    ctx.particles.pencil_speck(p.visible_x2,p.y)
        else:self.completed=True
    def draw(self,surface,camera,renderer):
        if not self.applied or self.completed:return
        # The final encounter keeps its authored live geometry edit. A local
        # pencil tip and a hatched preview leave the boss telegraphs readable.
        for p in self.platforms:
            a,b=camera.screen_x(p.x1),camera.screen_x(p.x2)
            y=round(p.y+camera.offset_y)
            if p.draw_progress==0:
                for x in range(a,b,18):
                    pygame.draw.line(surface,(137,132,121),(x,y),(min(b,x+7),y),1)
            elif p.draw_progress<1:
                x=camera.screen_x(p.visible_x2)
                pygame.draw.polygon(surface,(177,136,77),[(x,y),(x+17,y-14),(x+23,y-7)])
                pygame.draw.line(surface,(48,47,47),(x,y),(x+7,y-5),3)

def build_new_page(index):
    world=PaperWorld(index,False)
    end=10800
    title,subtitle=('PAGE IV','The Carbon Agent') if index==3 else ('PAGE V','The Last Draft')
    runtime=ChapterRuntime(index,title,subtitle,world,(180,542),end,[Checkpoint('start',180,542)])
    runtime.campaign_last_index=4
    runtime.page_style='carbon_agent' if index==3 else 'last_draft'
    runtime.route_landmarks=[]
    # Continuous safety floor between authored fights; physical raised choices
    # inside rooms change projectile paths, flanks and jump timing.
    for i in range(12):
        p=world.add(i*950-30,(i+1)*950+10,590,16,f'campaign_floor_{i}',7000+index*100+i)
        p.appearance='carbon' if index==3 else 'handwriting'
    gift_specs=((650,'ink_pistol'),(4550,'marker_shotgun')) if index==3 else ((460,'rubber_band'),(2350,'eraser_cannon'),(6350,'marker_shotgun'))
    for x,weapon in gift_specs:
        runtime.entities.add(WeaponPickup(x,590,weapon,label=label_for(index,weapon),page_index=index))
    for room_index,row in enumerate(NEW_ROOMS[index]):
        room,start,end_x,*waves=row
        specs=[]
        for wave,kinds in enumerate(waves):
            for i,kind in enumerate(kinds):
                specs.append({'wave':wave,'kind':kind,'offset':((end_x-start)*.58 if len(kinds)==1 else 260+i*(end_x-start-430)/max(1,len(kinds)-1))})
        boss=room in ('scissor_office','final_margin_revision')
        arena=CombatArena(world,start,end_x,room,specs,0,boss)
        arena.mandatory=True
        arena.display_name,arena.boss_rule=ROOM_BRIEFS[room]
        runtime.entities.add(arena)
        # A clearly drawn lower margin catches a missed floor edit. Two short
        # return steps keep a fall recoverable without bypassing either gate.
        for gate in (arena.entrance_gate, arena.exit_gate):
            gate.thickness = 520
        catch = world.add(start-45, end_x-22, 690, 12, f"catch_{room}", 7900+room_index)
        catch.appearance = "torn_edge"
        for side_x in (start+25, end_x-215):
            step = world.add(side_x, side_x+125, 640, 10, f"return_{room}_{int(side_x)}", 7950+room_index)
            step.appearance = "handwriting"
        runtime.entities.add(ArenaPaperBeat(world,arena,'draw_cover' if room_index%2==0 else 'erase_cover'))
        world.notes.append(PaperNote(start-360,270,ROOM_BRIEFS[room][1],'small',(75,72,70),-1,False,True))
        # No checkpoint inside a sealed room. Both a pre-fight and post-fight
        # retry preserve acquisitions and never skip an uncleared encounter.
        requirements=tuple(r[0] for r in NEW_ROOMS[index][:room_index])
        runtime.checkpoints.append(Checkpoint('before_'+room,start-160,542,trigger_x=start-180,requires=requirements))
        runtime.checkpoints.append(Checkpoint('after_'+room,end_x+70,542,trigger_x=end_x+45,requires=(*requirements,room)))
        if not boss:
            p=world.add(start+145,start+325,505,10,f'hand_landing_{room}',7600+room_index)
            p.draw_progress=0;p.appearance='handwriting'
            runtime.entities.add(ArtistCombatHand(arena,p))
        if room=='final_margin_revision':runtime.entities.add(FinalPageEdit(arena,world))
    # A compact optional rooftop detour, clear of arena entrance strokes.
    base=4350 if index==3 else 8350
    for i,y in enumerate((505,430,505)):
        p=world.add(base+i*170,base+i*170+125,y,10,f'branch_{i}',7800+i)
        p.appearance='carbon' if index==3 else 'ruler_line'
    runtime.entities.add(LostSketch(base+230,410,'agent_badge' if index==3 else 'last_homework',
        'an ID card with a badly forged face' if index==3 else 'homework that fought back'))
    runtime.required_ids=tuple(row[0] for row in NEW_ROOMS[index])
    runtime.checkpoints.sort(key=lambda cp:cp.trigger_x)
    world.width=runtime.end_x+220
    def costume(ctx,p):
        ctx.player.page_style=('ink_agent' if index==3 else 'bad_drawing') if p>.2 else 'plain'
        ctx.director.tool=ArtistTool('pencil',ctx.player.center_x+8,ctx.player.y+8,True)
        ctx.director.write(ctx.player.x+70,ctx.player.y-75,
            'Totally inconspicuous.' if index==3 else 'No more neat versions.',p)
    runtime.director.add(EventSequence(f'page_{index}_costume',lambda ctx:ctx.player.x>=180,[
        EventStep(.85,update=costume,start=lambda ctx:ctx.sounds.play('pencil'),lock_player=True)]))
    world.notes.append(PaperNote(runtime.end_x-180,250,'the next page is classified' if index==3 else 'You may turn the page.','small',(75,72,70)))
    return runtime
