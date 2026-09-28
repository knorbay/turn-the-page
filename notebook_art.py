"""Notebook material and authored doodles: no imported sprites or frame noise."""
import math
import random
import pygame
from settings import WIDTH, HEIGHT
from paper_renderer import jitter_line
from sketch_marks import rough_circle

PAPER_COLORS=((244,240,220),(242,234,212),(232,239,226),(235,232,220),(246,239,222))
PENCIL=(60,57,55)
BLUE=(92,115,143)
RED=(159,70,65)

class NotebookMaterial:
    def __init__(self):
        self.tiles={}
        self.face=pygame.font.match_font('noteworthy,chalkboard,comic sans ms')
        self.font=pygame.font.Font(self.face,20)
        self.small=pygame.font.Font(self.face,15)
        self.grain=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)
        rng=random.Random(91)
        for _ in range(5600):
            x,y=rng.randrange(WIDTH),rng.randrange(HEIGHT)
            pygame.draw.line(self.grain,(247,243,223,rng.randrange(45,150)),(x,y),(x+rng.randrange(1,4),y),1)
        self.masked=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA)

    def paper(self,page):
        s=pygame.Surface((WIDTH,HEIGHT));base=PAPER_COLORS[page];s.fill(base)
        rng=random.Random(241+page)
        spacing=(30,34,25,32,30)[page]
        for y in range(18,HEIGHT,spacing):
            jitter_line(s,(191,202,200),(0,y),(WIDTH,y+1),1,y,1,.5)
        if page==2:
            for x in range(0,WIDTH,25):pygame.draw.line(s,(208,215,203),(x,0),(x,HEIGHT),1)
        for x in (76,80):jitter_line(s,(201,148,143),(x,0),(x,HEIGHT),1,x,1,.8)
        for y in range(70,HEIGHT,118):
            rough_circle(s,(162,157,145),(23,y),12,y,2,2,wobble=1)
            pygame.draw.circle(s,(214,207,185),(23,y),8)
            jitter_line(s,(77,75,70),(-8,y-6),(25,y+2),3,y,2,1)
        for _ in range(4500):
            x,y=rng.randrange(WIDTH),rng.randrange(HEIGHT)
            s.set_at((x,y),tuple(max(0,c-rng.randrange(1,12)) for c in base))
        # Faint pressure marks from the previous sheet, deliberately incomplete.
        for i in range(13):
            x,y=rng.randrange(100,WIDTH),rng.randrange(80,HEIGHT-80)
            pygame.draw.arc(s,tuple(c-13 for c in base),(x,y,90,26),.4,4.6,1)
        return s

    def hand(self,s,text,pos,color=PENCIL,small=False,seed=1):
        rng=random.Random(seed);x,y=pos;f=self.small if small else self.font
        for word in text.split():
            glyph=f.render(word,True,color)
            glyph=pygame.transform.rotate(glyph,rng.choice((-2,-1,1,2)))
            s.blit(glyph,(round(x),round(y+rng.uniform(-2,2))))
            x+=f.size(word+' ')[0]

    def artist_note(self,s,text,reply=''):
        # A rubbed space on the sheet keeps marginalia out of the message.
        patch=pygame.Surface((820,91),pygame.SRCALPHA)
        for row in range(6,88,7):
            jitter_line(patch,(244,240,220,235),(4,row),(814,row),10,row,1,2)
        s.blit(patch,(180,218))
        self.hand(s,'the Artist:',(195,220),RED,True)
        words=text.split();lines=['']
        for word in words:
            candidate=(lines[-1]+' '+word).strip()
            if self.font.size(candidate)[0]>765:lines.append(word)
            else:lines[-1]=candidate
        for i,line in enumerate(lines[:2]):
            self.hand(s,line,(195,242+i*25),RED,seed=i)
        if reply:self.hand(s,reply,(785,287),RED,True)

    def tile(self,page,index):
        key=(page,index)
        if key in self.tiles:return self.tiles[key]
        rng=random.Random(page*971+index*53+71)
        s=pygame.Surface((960,HEIGHT),pygame.SRCALPHA)
        base=PAPER_COLORS[page]
        from notebook_scenes import draw_scene
        draw_scene(self,s,page,index)
        # Warm cup ring and fingerprints in the margins, not scenic mountains.
        if index%3==1:
            for j in range(4):rough_circle(s,(155,121,89,25),(180,365),58+j*2,j,2,1,squash=(1,.7),wobble=2)
        for j in range(6):
            x=40+j*6
            pygame.draw.arc(s,(106,102,86,20),(x,340-j*3,72,28),.2,3.9,1)
        self.hand(s,('boring lesson','do not tear','turn me over','ink on my hand')[index%4],(60,648),RED,True,index)
        self.tiles[key]=s
        return s

    def draw(self,s,camera,page):
        # Full world speed: writing is glued to paper, never a parallax sky.
        first=math.floor(camera.x/960)
        for index in range(first,first+3):
            s.blit(self.tile(page,index),(round(index*960-camera.x),0))

    def ink_pass(self,target,layer):
        # Keep the original RGBA drawing intact. Reusing a texture mask with
        # disabled pixel alpha can cover the entire native macOS canvas.
        # The rough strokes already carry graphite texture; a separate ghost
        # copy provides the erased registration without an RGBA multiply pass.
        ghost=layer.copy()
        ghost.set_alpha(26)
        target.blit(ghost,(2,1))
        target.blit(layer,(0,0))


def redraw_doodle(enemy,s,camera,renderer):
    """Use the original authored bodies; details belong to their native draw."""
    return False
