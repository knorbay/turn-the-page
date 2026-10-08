"""Existing Lost Sketches discovered through the notebook, rather than kills.

Discovery is a small optional state machine attached to the real saved pickup.
It adds no collectibles or enemies. Only the rejected-warrior scrap retains
its combat trial; the other drawings use their own page, movement or ink.
"""
from __future__ import annotations

import math
import pygame

from entities import LostSketch
from action_content import claim_artist_canvas,release_artist_canvas
from paper_renderer import jitter_line
from scripted_events import ArtistDirector, ArtistTool, artist_canvas_free
from sketches import draw_sketch_icon, sketch_for
from settings import INK, INK_LIGHT, RED_RULE


DISCOVERIES = {
    "old_first_figure": ("erase", (450,570), "E  ask about the rubbed-out figure"),
    "shrine_roof": ("traversal", None, ""),
    "beyond_red": ("height", None, "the little roof continues above the red rule"),
    "coffee_secret": ("notice", None, "a handle? face the stain and let it settle"),
    "margin_battle_note": ("perforation", (9810,570), "the loose seam has a dashed arrow"),
    "water_tower": ("fold", None, "E  unfold the timetable's corner"),
    "bad_draft": ("shot", None, "the wrong outline rings when ink touches it"),
    "eraser_survivor_sketch": ("underfold", (13475,650), "the rejected draft is under the proof line"),
    "orbit_observatory": ("redraw", None, "E  ask why the moon has two outlines"),
    "agent_badge": ("carbon", None, "pressure on the upper copy leaves a face"),
    "last_homework": ("impact", None, "the old answer is under those crossouts"),
}


class AuthoredLostSketch(LostSketch):
    """The normal saved/reward path activates only after physical discovery."""
    discovery = None

    def update(self,dt,ctx,interact=False):
        if self.discovery is not None and not self.discovery.completed and not self.discovered:
            self.pulse+=dt
            self.near=(abs(ctx.player.center_x-self.x)<62
                and abs(ctx.player.rect.bottom-self.y)<95)
            return
        super().update(dt,ctx,interact)

    def draw(self,surface,camera,renderer):
        if self.discovery is not None and not self.discovery.completed and not self.discovered:
            return
        super().draw(surface,camera,renderer)


class SketchDiscovery:
    active=True
    mandatory=False
    layer=0
    encounter_active=False

    def __init__(self,runtime,sketch,kind,prompt):
        self.sketch,self.page,self.kind=sketch,runtime.index,kind
        self.prompt=prompt
        self.completed=sketch.discovered or kind=="traversal"
        self.state="ready" if self.completed else "waiting"
        self.timer=0.0
        self.reveal=1.0 if self.completed else 0.0
        self.notice_time=0.0
        self.near=False
        self.hand=ArtistDirector()
        self.letter_time=0.0
        self.letter=""
        self.pressure_line=runtime.world.platform_named("branch_1") if kind=="carbon" else None
        sketch.discovery=self

    def begin(self,ctx):
        if self.state!="waiting" or not artist_canvas_free(ctx,self) or ctx.player.locked:
            return False
        if not claim_artist_canvas(ctx,self):return False
        self.state="revealing"
        self.timer=0
        ctx.sounds.play("erase" if self.kind in ("erase","impact") else
                        "tear" if self.kind=="perforation" else "pencil")
        return True

    def _ink_touches(self,ctx):
        weapons=getattr(ctx,"weapons",None)
        if weapons is None:return False
        target=pygame.Rect(round(self.sketch.x-39),round(self.sketch.y-58),78,75)
        for shot in getattr(weapons,"projectiles",()):
            if not getattr(shot,"active",True):continue
            rect=getattr(shot,"rect",None)
            if rect is not None and target.colliderect(rect):return True
            trail=getattr(shot,"trail",())
            if trail and target.clipline(trail[-1],(shot.x,shot.y)):return True
        if self.kind=="impact":
            swing=getattr(weapons,"melee",None)
            if swing is not None and getattr(swing,"primary_active",False):
                return target.colliderect(swing.hit_rect(ctx.player))
        return False

    def update(self,dt,ctx,interact=False):
        self.hand.tool.visible=False
        self.letter_time=max(0,self.letter_time-dt)
        if self.sketch.discovered:
            self.completed=True
            self.state="ready"
            self.letter_time=0
            release_artist_canvas(ctx,self)
            return
        if self.completed:return
        p=ctx.player
        self.near=(abs(p.center_x-self.sketch.x)<100
                   and abs(p.rect.bottom-self.sketch.y)<140)
        if p.health<=0:
            release_artist_canvas(ctx,self)
            return
        if p.locked:return
        if not artist_canvas_free(ctx,self):return
        if self.state=="waiting":
            if self.near:ctx.level.interaction_hint=self.prompt
            trigger=False
            if self.kind in ("erase","fold","redraw"):
                trigger=self.near and interact
            elif self.kind=="notice":
                attentive=self.near and p.on_ground and abs(p.vx)<28 and p.facing<0
                self.notice_time=self.notice_time+dt if attentive else 0
                trigger=self.notice_time>=.6
            elif self.kind=="height":
                trigger=abs(p.center_x-self.sketch.x)<160 and p.rect.bottom<375
            elif self.kind=="perforation":
                trigger=self.near and p.dashing
            elif self.kind=="shot" or self.kind=="impact":
                trigger=self._ink_touches(ctx)
            elif self.kind=="underfold":
                trigger=abs(p.center_x-self.sketch.x)<125 and p.rect.bottom>625
            elif self.kind=="carbon":
                line=self.pressure_line
                trigger=(line is not None and p.on_ground
                    and line.x1<=p.center_x<=line.x2
                    and abs(p.rect.bottom-line.y)<4
                    and getattr(line,"collider_active",True))
            if trigger:self.begin(ctx)
        if self.state!="revealing":return
        self.timer+=dt
        duration=.78 if self.kind in ("erase","redraw","impact") else .56
        self.reveal=min(1,self.timer/duration)
        x=self.sketch.x-42+84*self.reveal
        y=self.sketch.y-20
        if self.kind in ("erase","impact"):
            self.hand.tool=ArtistTool("eraser",x,y,True,-.2,.74)
            if int(self.timer*35)%4==0:ctx.particles.eraser_dust(x,y,2)
        elif self.kind in ("redraw","shot","carbon","height","notice"):
            self.hand.tool=ArtistTool("pencil",x,y,True,-.65,.82)
            if int(self.timer*35)%4==0:ctx.particles.pencil_speck(x,y)
        if self.reveal>=1:
            self.completed=True
            self.state="ready"
            self.hand.tool.visible=False
            release_artist_canvas(ctx,self)
            ctx.particles.paper_puff(self.sketch.x,self.sketch.y-16,7)
            if self.sketch.secret_id=="old_first_figure":
                self.letter="Lost Sketches = discarded ideas.\nKeep one. Its trick stays across pages."
                self.letter_time=5.5
            elif self.kind=="carbon":
                self.letter="The original left a face.\nKeep the badge; I can draw its rifle."
                self.letter_time=4
            if getattr(ctx,"game",None) is not None:
                ctx.game.behavior.record("sketch_discovered",sketch=self.sketch.secret_id,
                                         method=self.kind,page=self.page)

    def draw(self,s,camera,renderer):
        if self.completed or self.sketch.discovered:return
        x,y=camera.screen_x(self.sketch.x),round(self.sketch.y+camera.offset_y)
        if x < -140 or x > s.get_width()+140:return
        color=(120,107,86)
        red=(151,75,65)
        # The rejected idea belongs to the page drawing. A full collectible
        # slip and reward card appear only when its covering mark is changed.
        if self.kind=="notice":
            pygame.draw.ellipse(s,(148,111,77),(x-45,y-43,90,39),2)
            pygame.draw.arc(s,(89,78,60),(x-4,y-17,20,21),math.pi,math.tau,2)
            for i in range(3):pygame.draw.line(s,(151,113,80),(x-34+i*24,y-22),(x-30+i*24,y-9),1)
        elif self.kind=="redraw" or self.kind=="height":
            if self.kind=="redraw":
                for shift in (-10,10):pygame.draw.circle(s,(129,148,154),(x+shift,y-16),35,1)
                renderer.doodle_text(s,"?",(x-5,y-25),red,renderer.font_small,2)
            else:
                pygame.draw.lines(s,(143,120,106),False,
                    [(x-28,y-4),(x,y-31),(x+29,y-4),(x+20,y-4),(x+20,y+12),(x-20,y+12)],1)
        elif self.kind=="perforation":
            for i in range(7):
                xx=x-49+i*15
                pygame.draw.line(s,red,(xx,y-21),(xx+7,y-26),2)
            pygame.draw.lines(s,red,False,[(x-29,y-42),(x+29,y-42),(x+21,y-49)],2)
        elif self.kind=="carbon":
            renderer.rough_rect(s,(125,130,124),pygame.Rect(x-40,y-58,80,70),1,151)
            for i in range(5):
                pygame.draw.line(s,(156,162,154),(x-30,y-47+i*10),(x+25,y-50+i*10),1)
            pygame.draw.circle(s,(124,136,133),(x-14,y-34),10,1)
        elif self.kind=="fold" or self.kind=="underfold":
            points=[(x-47,y-49),(x+33,y-51),(x+45,y-29),(x+38,y+7),(x-44,y+12)]
            pygame.draw.polygon(s,(227,218,193),points)
            pygame.draw.lines(s,color,True,points,1)
            pygame.draw.lines(s,red,False,[(x+33,y-51),(x+20,y-26),(x+45,y-29)],2)
            for dy in (-34,-21,-7):pygame.draw.line(s,color,(x-30,y+dy),(x+10,y+dy-2),1)
        else:
            definition=sketch_for(self.sketch.secret_id)
            draw_sketch_icon(s,definition.icon if definition else "figure",(x,y-17),47,
                             (137,127,107),(159,120,98))
            remaining=1-self.reveal
            for i in range(max(0,round(9*remaining))):
                yy=y-44+i*6
                jitter_line(s,red if self.kind=="impact" else INK_LIGHT,
                            (x-35,yy+4),(x+36,yy-3),2,217+i,2,2.6)
        if self.state=="revealing" and self.kind in ("fold","underfold","perforation"):
            # A loose sheet opens; it is not an Artist-created weapon or actor.
            hinge=x+round(40*(1-self.reveal))
            pygame.draw.lines(s,(172,98,83),False,
                [(hinge,y-49),(x+45,y-29),(hinge,y+8)],2)

    def draw_overlay(self,s,camera,renderer):
        self.hand.draw(s,camera,renderer)
        if self.letter_time>0:
            x=max(18,min(s.get_width()-420,camera.screen_x(self.sketch.x)-120))
            y=round(self.sketch.y-198+camera.offset_y)
            for i,line in enumerate(self.letter.splitlines()):
                renderer.notebook.hand(s,line,(x,y+i*25),INK,True)


def attach_discoveries(runtime):
    """Replace acquisition rules, retaining every shipped sketch/save ID."""
    result=[]
    for item in runtime.entities.items:
        spec=DISCOVERIES.get(getattr(item,"secret_id",None))
        if not isinstance(item,LostSketch) or spec is None:
            result.append(item)
            continue
        kind,position,prompt=spec
        if position:item.x,item.y=position
        sketch=AuthoredLostSketch(item.x,item.y,item.secret_id,item.caption,
            item.discovered,item.pulse,item.near,item.acquired_time)
        discovery=SketchDiscovery(runtime,sketch,kind,prompt)
        result.extend((discovery,sketch))
    runtime.entities.items[:]=result
    return runtime


__all__=["DISCOVERIES","SketchDiscovery","AuthoredLostSketch","attach_discoveries"]
