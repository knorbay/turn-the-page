"""A playable last page, filled by the player after the last battle.

This quiet world owns no campaign flags or save writes. Three deliberately
started drawings and one final signature complete the notebook; standing
still or walking to the far edge can never close it automatically.
"""
from dataclasses import dataclass
import math

import pygame

from camera import Camera
from page_arsenal import draw_weapon
from paper_renderer import jitter_line
from particles import ParticleSystem
from player import Player
from settings import HEIGHT, INK, INK_LIGHT, WIDTH
from sketches import draw_sketch_icon, sketch_for
from world import PaperWorld


@dataclass
class MemoryDrawing:
    key: str
    x: float
    title: str
    note: str
    icon: str
    accent: tuple
    progress: float = 0.0
    completed: bool = False


class Afterword:
    actions = ("REPLAY PAGES", "BACK PAGES", "TITLE")
    DRAW_SECONDS = 3.6
    SIGN_SECONDS = 3.2
    WORLD_WIDTH = 9600
    GROUND_Y = 590
    SEAL_X = 9160

    def __init__(self, secrets=()):
        self.world = PaperWorld(page=5, build_legacy=False)
        self.world.width = self.WORLD_WIDTH
        # A full-depth floor makes even a Down+jump safe. Decorative upper
        # lines are optional; none of the memories needs a precise platform.
        ground = self.world.add(-80,self.WORLD_WIDTH+80,self.GROUND_Y,52,
                                "afterword_ground",41001)
        ground.appearance = "handwriting"
        for index,x in enumerate((2180,4800,7420)):
            step=self.world.add(x,x+235,505,10,f"afterword_ledge_{index}",41020+index)
            step.appearance="handwriting"
        self.player = Player(180,self.GROUND_Y-Player.HEIGHT)
        self.player.on_ground=self.player.was_grounded=True
        self.player.page_style="plain"
        self.player.current_weapon="unarmed"
        self.camera = Camera(WIDTH)
        self.particles = ParticleSystem()
        self.world.refresh_drawings((self.player,))
        safe_keys = secrets if isinstance(secrets,(list,tuple,set)) else ()
        self.kept_sketches = tuple(sketch for key in sorted({key for key in safe_keys
                                      if isinstance(key,str)})
                                  if (sketch:=sketch_for(key)) is not None)
        self.memories = [
            MemoryDrawing("roads",1280,"THE ROADS I KEPT",
                          "Every wrong turn left a useful line.","house",(147,99,63)),
            MemoryDrawing("sky",3900,"THE SKY I REACHED",
                          "Even a copied line can point somewhere new.","moon",(70,113,139)),
            MemoryDrawing("figure",6560,"THE FIGURE I CHOSE",
                          "The old drafts taught me how to draw myself.","victory",(132,89,117)),
        ]
        self.complete=False
        self.menu_index=0
        self.time=0.0
        self.operation=None
        self.operation_time=0.0
        self.seal_progress=0.0
        self._scratch_tick=-1
        self.note="A few lines are still yours to draw."
        self.note_time=6.0

    @property
    def completed_memories(self):
        return sum(memory.completed for memory in self.memories)

    @property
    def near_memory(self):
        return next((memory for memory in self.memories
                     if abs(self.player.center_x-memory.x)<110
                     and abs(self.player.rect.bottom-self.GROUND_Y)<35),None)

    @property
    def near_seal(self):
        return (abs(self.player.center_x-self.SEAL_X)<120
                and abs(self.player.rect.bottom-self.GROUND_Y)<35)

    @staticmethod
    def _sound(sounds,name):
        play=getattr(sounds,"play",None)
        if callable(play):play(name)

    def action_rects(self):
        return tuple(pygame.Rect(WIDTH//2-260,375+index*75,520,54)
                     for index in range(len(self.actions)))

    def _begin(self,operation,sounds):
        self.operation=operation
        self.operation_time=0
        self._scratch_tick=-1
        self.player.acquire_lock("afterword_draw")
        self.player.vx=0
        self.player.jump_buffer=0
        self.note_time=0
        self._sound(sounds,"pencil")

    def update(self,dt,frame,sounds):
        dt=max(0.0,min(.05,float(dt)))
        self.time+=dt
        self.note_time=max(0.0,self.note_time-dt)
        if self.complete:
            # The game's menu key/hat events own selection. A held movement
            # frame must not apply that same event a second time here.
            self.particles.update(dt)
            return

        if self.operation is None:
            if frame.jump_pressed:
                if not (frame.down and self.player.drop_through(self.world)):
                    self.player.queue_jump()
            if frame.jump_released:self.player.release_jump()
            self.player.update(dt,frame.axis,self.world,self.particles)
            self.player.x=max(45,min(self.world.width-Player.WIDTH-45,self.player.x))
            if frame.interact:
                memory=self.near_memory
                if memory is not None and not memory.completed:
                    self._begin(memory,sounds)
                elif self.near_seal:
                    if self.completed_memories==len(self.memories):
                        self._begin("seal",sounds)
                    else:
                        self.note="Leave room for every memory."
                        self.note_time=4
                        self._sound(sounds,"paper_step")
        else:
            self.player.update(dt,0,self.world,self.particles)
            self.operation_time+=dt
            signing=self.operation=="seal"
            duration=self.SIGN_SECONDS if signing else self.DRAW_SECONDS
            progress=min(1.0,self.operation_time/duration)
            if signing:self.seal_progress=progress
            else:self.operation.progress=progress
            tick=int(self.operation_time*3)
            if tick!=self._scratch_tick:
                self._scratch_tick=tick
                self._sound(sounds,"pencil")
            if progress>=1:
                if signing:
                    self.complete=True
                    self._sound(sounds,"page")
                else:
                    self.operation.completed=True
                    self.note=self.operation.note
                    self.note_time=4.5
                    self.particles.paper_puff(self.operation.x,self.GROUND_Y-140,10)
                    self._sound(sounds,"pickup")
                self.player.release_lock("afterword_draw")
                self.player.look_target=None
                self.operation=None
        self.world.refresh_drawings((self.player,))
        self.camera.update(dt,self.player.center_x,self.world.width,self.player.vx,
                           self.player.rect.centery,self.player.locked)
        self.particles.update(dt)

    @staticmethod
    def _text(surface,renderer,text,y,font=None,color=INK):
        font=font or renderer.font
        image=font.render(text,True,color)
        if image.get_width()>surface.get_width()-70:
            scale=(surface.get_width()-70)/image.get_width()
            image=pygame.transform.smoothscale(image,
                (round(image.get_width()*scale),max(1,round(image.get_height()*scale))))
        surface.blit(image,image.get_rect(midtop=(surface.get_width()//2,y)))

    def _scene_strokes(self,memory):
        """Ordered graphite strokes give the moving pencil a real endpoint."""
        if memory.key=="roads":
            return [
                ((45,260),(190,170)),((190,170),(298,243)),
                ((298,243),(397,177)),((397,177),(615,260)),
                ((42,263),(620,263)),((140,241),(475,241)),
                ((190,235),(190,103)),((312,235),(312,103)),
                ((164,108),(340,108)),((156,97),(348,97)),
                ((171,84),(251,72)),((251,72),(336,84)),
                ((465,241),(483,170)),((483,170),(540,170)),
                ((540,170),(558,241)),((476,145),(550,145)),
                ((483,170),(483,115)),((540,170),(540,115)),
                ((483,115),(540,115)),((475,113),(551,113)),
                ((487,171),(548,236)),((538,171),(476,236)),
            ]
        if memory.key=="sky":
            return [
                ((50,258),(617,258)),((130,231),(130,143)),
                ((130,143),(205,143)),((205,143),(205,231)),
                ((216,246),(216,119)),((216,119),(282,119)),
                ((282,119),(282,246)),((150,163),(185,163)),
                ((150,184),(185,184)),((235,143),(263,143)),
                ((235,166),(263,166)),((235,189),(263,189)),
                ((381,164),(381,202)),((355,183),(407,183)),
                ((328,167),(353,167)),((353,167),(353,199)),
                ((353,199),(328,199)),((328,199),(328,167)),
                ((409,167),(434,167)),((434,167),(434,199)),
                ((434,199),(409,199)),((409,199),(409,167)),
                ((379,157),(386,151)),((379,205),(386,211)),
            ]
        return [
            ((63,260),(605,260)),((193,254),(223,254)),
            ((407,254),(437,254)),((315,175),(310,210)),
            ((310,210),(283,247)),((310,210),(344,247)),
            ((312,184),(278,156)),((278,156),(258,119)),
            ((312,184),(352,154)),((352,154),(372,117)),
            ((216,92),(237,73)),((409,92),(391,74)),
            ((217,101),(238,97)),((408,101),(387,98)),
        ]

    def _draw_memory(self,surface,renderer,memory):
        x=self.camera.screen_x(memory.x)-330
        y=218+self.camera.offset_y
        if x+670<-30 or x>surface.get_width()+30:return
        accent=memory.accent
        if memory.progress==0:
            draw_sketch_icon(surface,memory.icon,(x+330,y+128),82,
                             (167,162,145),(184,164,144))
            for dx in (36,610):
                pygame.draw.line(surface,(188,182,163),(x+dx,y+65),(x+dx,y+235),1)
        else:
            strokes=self._scene_strokes(memory)
            count=memory.progress*len(strokes)
            tip=None
            for index,(start,end) in enumerate(strokes):
                if index>=count:break
                amount=min(1,count-index)
                finish=(start[0]+(end[0]-start[0])*amount,
                        start[1]+(end[1]-start[1])*amount)
                color=accent if index>=len(strokes)*.65 else (92,87,75)
                jitter_line(surface,color,(x+start[0],y+start[1]),
                            (x+finish[0],y+finish[1]),2,43100+index,2,1.2)
                tip=(x+finish[0],y+finish[1])
            if memory.key=="sky" and memory.progress>.45:
                draw_sketch_icon(surface,"moon",(x+507,y+81),80,
                                 (90,103,112),accent)
                for dx,dy in ((360,55),(568,150),(316,101)):
                    pygame.draw.line(surface,accent,(x+dx-4,y+dy),(x+dx+4,y+dy),1)
                    pygame.draw.line(surface,accent,(x+dx,y+dy-4),(x+dx,y+dy+4),1)
            elif memory.key=="figure" and memory.progress>.4:
                pygame.draw.circle(surface,(75,68,69),(x+315,y+154),18,2)
                # Learned drawings become the little figure's own margins.
                icons=[sketch.icon for sketch in self.kept_sketches[:4]] or ["kite","ticket","badge"]
                for index,icon in enumerate(icons):
                    draw_sketch_icon(surface,icon,(x+115+index*143,y+50),35,
                                     (117,109,99),accent)
            if self.operation is memory and tip:
                draw_weapon(surface,"pencil_blade",4,(tip[0]-20,tip[1]+15),-.63,.65)
        title=renderer.font_small.render(memory.title,True,accent)
        surface.blit(title,title.get_rect(midtop=(x+330,y-32)))
        if memory.completed:
            pygame.draw.lines(surface,accent,False,
                              [(x+313,y+292),(x+326,y+302),(x+347,y+278)],2)

    def _draw_seal(self,surface,renderer,controller):
        x=self.camera.screen_x(self.SEAL_X)
        y=378+self.camera.offset_y
        if not -250<x<surface.get_width()+250:return
        rect=pygame.Rect(x-150,y-118,300,235)
        renderer.rough_rect(surface,(128,111,99),rect,2,44100)
        pygame.draw.line(surface,(156,129,111),(x-133,y-102),(x-133,y+100),2)
        for index,memory in enumerate(self.memories):
            color=memory.accent if memory.completed else (174,169,150)
            draw_sketch_icon(surface,memory.icon,(x-78+index*78,y-43),41,color,color)
        self._text_at(surface,renderer,"THESE LINES ARE MINE",(x,y+16),renderer.font_small)
        if self.seal_progress:
            length=230*self.seal_progress
            jitter_line(surface,(134,75,72),(x-115,y+67),(x-115+length,y+64),2,44103,2,1.4)
            tip=(x-115+length,y+64)
            if self.operation=="seal":
                draw_weapon(surface,"pencil_blade",4,(tip[0]-20,tip[1]+15),-.63,.65)
        if self.near_seal and self.operation is None:
            ready=self.completed_memories==len(self.memories)
            prompt=("PAD-Y / SIGN THE PAGE" if controller else "E / SIGN THE PAGE") if ready else "Leave room for every memory."
            self._text_at(surface,renderer,prompt,(x,y+145),renderer.font_small,
                          (137,77,68) if ready else INK_LIGHT)

    @staticmethod
    def _text_at(surface,renderer,text,center,font,color=INK):
        image=font.render(text,True,color)
        if image.get_width()>610:
            scale=610/image.get_width()
            image=pygame.transform.smoothscale(image,
                (610,max(1,round(image.get_height()*scale))))
        surface.blit(image,image.get_rect(midtop=center))

    def draw(self,surface,renderer,controller=False):
        renderer.background(surface,4)
        if self.complete:
            self._text(surface,renderer,"YOUR NOTEBOOK IS COMPLETE",85,renderer.font_big)
            self._text(surface,renderer,"The next blank page can wait.",164,renderer.font_small,INK_LIGHT)
            for index,memory in enumerate(self.memories):
                draw_sketch_icon(surface,memory.icon,(WIDTH//2-115+index*115,267),60,
                                 memory.accent,memory.accent)
            for index,(action,rect) in enumerate(zip(self.actions,self.action_rects())):
                color=(143,68,64) if index==self.menu_index else INK_LIGHT
                renderer.rough_rect(surface,color,rect,2 if index==self.menu_index else 1,44200+index)
                image=renderer.font.render(action,True,color)
                if image.get_width()>rect.width-30:
                    image=pygame.transform.smoothscale(image,(rect.width-30,
                         max(1,round(image.get_height()*(rect.width-30)/image.get_width()))))
                surface.blit(image,image.get_rect(center=rect.center))
            return
        # The last sheet starts empty and receives only drawings deliberately
        # placed here, instead of borrowing a repeating campaign backdrop.
        for platform in self.world.platforms:platform.draw(surface,self.camera)
        for memory in self.memories:self._draw_memory(surface,renderer,memory)
        self._draw_seal(surface,renderer,controller)
        self.player.draw(surface,self.camera)
        self.particles.draw(surface,self.camera)
        renderer.doodle_text(surface,"THE LAST PAGE",(35,29),INK,renderer.font)
        for index,memory in enumerate(self.memories):
            color=memory.accent if memory.completed else (174,168,151)
            draw_sketch_icon(surface,memory.icon,(surface.get_width()-165+index*57,47),30,color,color)
        memory=self.near_memory
        if self.operation is None and memory is not None and not memory.completed:
            self._text(surface,renderer,"PAD-Y / DRAW" if controller else "E / DRAW",625,
                       renderer.font_small,memory.accent)
        elif self.operation is None and self.note_time>0:
            self._text(surface,renderer,self.note,625,renderer.font_small,INK_LIGHT)
