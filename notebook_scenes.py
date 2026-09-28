"""Page-local marginalia: individual locations and drawings along the route."""
import math
import random
import pygame
from paper_renderer import jitter_line
from sketch_marks import rough_circle

ZONES = (
 ('first attempt','bamboo exercise','broken footbridge','ink dojo','roof of the shrine','lantern festival','rejected warriors','moon gate','the sword lesson','after the duel','a quieter line','end of the scroll'),
 ('railway timetable','wanted / alive?','six shots only','coffee spill town','beyond the red rule','empty saloon','windmill repairs','cactus country','water tower','midnight freight','bounty archive','last station','train home','missed the train'),
 ('gravity homework','failed launch','orbit laboratory','zero garden','telescope repairs','debris forecast','moon survey','radio silence','null chamber','star nursery','wrong equation','escape velocity','observatory','erased orbit','the big mistake','one giant baby','back to earth','end of experiment'),
 ('classified homework','checkpoint sketch','service tunnel','carbon copy office','missing personnel','rooftop surveillance','dead letter drop','the archive','office floor plan','director of redaction','case closed','unsigned report'),
 ('last lesson','unfinished answer','discard pile','paper cemetery','what survived','the rebels','wrong endings','your handwriting','the final question','a new ending','keep drawing','after the bell'),
)
NOTES = (
 ('do not sharpen the sword','bamboo bends / ink does not','balance before speed','three cuts, then breathe'),
 ('depart 23:07 / never on time','reward: one clean sheet','wind from the coffee stain','draw another way out'),
 ('mass = mistake / time²','signal lost ... try again','oxygen? forgot that part','the moon is drifting'),
 ('copy 03 / original missing','NO NAMES PAST THIS LINE','blind spot: roof access','evidence must not be erased'),
 ('not every mistake needs fixing','this answer is yours','I kept the first version','the last word is unwritten'),
)

def draw_scene(n,s,page,index):
    ink=(116,111,99); blue=(113,133,145); red=(158,89,78)
    rng=random.Random(page*181+index*37)
    cx,cy=655+rng.randrange(-25,25),190
    variant=index%(6 if page>=3 else 4)
    def line(a,b,w=1,c=ink,k=0):jitter_line(s,c,a,b,w,index*41+k,2,1.9)
    def path(points,c=ink,w=1):
        for j in range(len(points)-1):line(points[j],points[j+1],w,c,j)
    def circle(x,y,r,k=1,c=ink,squash=(1,1)):
        rough_circle(s,c,(x,y),r,index+k,1,2,squash=squash,wobble=2)
    def text(t,x,y,c=red):n.hand(s,t,(x,y),c,True,index)
    # Each location has its own title and numbered corrections.
    zones=ZONES[page];title=zones[index%len(zones)]
    n.hand(s,title,(100,52),red,seed=index)
    text(NOTES[page][index%4],98,106,blue)
    text(('try %02d / crossed out' % (index+1)) if index%2 else 'revised after the bell',110,145,blue)
    if page==0:
        if variant==0: # a shrine, in uneven perspective
            path([(cx-104,cy+8),(cx,cy-66),(cx+119,cy+11),(cx-104,cy+8)])
            path([(cx-75,cy+10),(cx-76,cy+95),(cx+81,cy+93),(cx+79,cy+10)])
            for dx in (-49,49):line((cx+dx,cy+15),(cx+dx,cy+93),2)
            path([(cx-115,cy+103),(cx+121,cy+105),(cx+141,cy+122),(cx-133,cy+121)])
            text('roof route?',cx-48,cy+139)
        elif variant==1:
            for j in range(5):
                x=cx-78+j*37;top=cy-80+rng.randrange(0,50)
                line((x,cy+128),(x+10,top),2)
                for yy in range(top+16,cy+110,27):
                    line((x-3,yy),(x+15,yy+2));line((x+6,yy),(x-26,yy-19),1,blue)
                    line((x+6,yy),(x+32,yy-12),1,blue)
            text('wind ->',cx-155,cy-82)
        elif variant==2:
            for j in range(6):
                xx=cx-104+j*40;yy=cy+int(math.sin(j)*12)
                path([(xx,yy),(xx+26,yy-10),(xx+30,yy+58),(xx+2,yy+61),(xx,yy)])
                line((xx+13,yy-35),(xx+13,yy-4));line((xx+12,yy+62),(xx+7,yy+85),1,red)
            text('a different face in every lantern',cx-115,cy+111)
        else:
            circle(cx,cy,82,c=blue);circle(cx+5,cy-3,69)
            path([(cx-90,cy+108),(cx-90,cy-100),(cx+91,cy-101),(cx+91,cy+109)],w=2)
            for j in range(11):line((cx-86+j*16,cy-100),(cx-84+j*16,cy-84))
            text('do not draw the moon twice',cx-116,cy+137)
    elif page==1:
        if variant==0:
            path([(cx-110,cy-65),(cx+70,cy-59),(cx+87,cy+104),(cx-112,cy+98),(cx-110,cy-65)])
            text('WANTED',cx-67,cy-48)
            circle(cx-10,cy+9,29);line((cx-57,cy-6),(cx+36,cy-7),2)
            path([(cx-38,cy-6),(cx-30,cy-28),(cx+12,cy-26),(cx+23,cy-7)])
            text('for stealing my lunch',cx-95,cy+66)
        elif variant==1:
            for yy in (cy+95,cy+112):line((cx-143,yy),(cx+150,yy),2)
            path([(cx-100,cy+76),(cx-100,cy+6),(cx+8,cy+8),(cx+8,cy+76),(cx-100,cy+76)])
            path([(cx+15,cy+74),(cx+15,cy-17),(cx+70,cy-17),(cx+70,cy+15),(cx+112,cy+15),(cx+136,cy+73),(cx+15,cy+74)])
            for dx in (-76,-23,37,100):circle(cx+dx,cy+83,19)
            for j in range(4):circle(cx+72+j*17,cy-42-j*16,11+j*4,c=blue)
            text('next stop: wrong side of the page',cx-132,cy+136)
        elif variant==2:
            for dx in (-38,38):line((cx+dx,cy-16),(cx+dx*1.6,cy+126),2)
            path([(cx-62,cy-74),(cx+62,cy-74),(cx+62,cy-16),(cx-62,cy-16),(cx-62,cy-74)])
            for yy in range(cy-65,cy-17,10):line((cx-60,yy),(cx+60,yy),1,blue)
            path([(cx-44,cy+96),(cx+39,cy+23),(cx-34,cy+25),(cx+55,cy+96)])
            text('water / probably coffee',cx-89,cy+146)
        else:
            path([(cx-120,cy-31),(cx+110,cy-26),(cx+110,cy+111),(cx-120,cy+106),(cx-120,cy-31)])
            text('SALOON',cx-51,cy-14)
            for dx in (-88,54):path([(cx+dx,cy+31),(cx+dx+33,cy+31),(cx+dx+33,cy+66),(cx+dx,cy+66),(cx+dx,cy+31)])
            path([(cx-27,cy+110),(cx-26,cy+31),(cx+26,cy+31),(cx+26,cy+110)])
            text('closed during maths',cx-85,cy+134)
    elif page==2:
        if variant==0:
            for j in range(3):circle(cx,cy+12,96-j*17,j,blue,(1,.40+j*.19))
            circle(cx,cy+12,27);circle(cx+87,cy-29,14,c=red)
            for j in range(7):
                angle=j*math.tau/7
                xx,yy=cx+math.cos(angle)*126,cy+12+math.sin(angle)*92
                line((xx-4,yy),(xx+4,yy),1,blue);line((xx,yy-4),(xx,yy+4),1,blue)
            text('the missing moon goes here ->',cx-125,cy+128)
        elif variant==1:
            path([(cx-30,cy+105),(cx-35,cy-24),(cx,cy-97),(cx+31,cy-24),(cx+32,cy+106),(cx-30,cy+105)])
            circle(cx,cy-9,17,c=blue)
            for side in (-1,1):path([(cx+side*31,cy+48),(cx+side*70,cy+116),(cx+side*32,cy+101)])
            for j in range(5):line((cx-23+j*11,cy+112),(cx-33+j*16,cy+145),1,red)
            text('launch postponed (again)',cx-118,cy+168)
        elif variant==2:
            path([(cx-73,cy-26),(cx+73,cy-84),(cx+91,cy-39),(cx-51,cy+10),(cx-73,cy-26)],w=2)
            path([(cx-3,cy-13),(cx-8,cy+65),(cx-62,cy+117),(cx-8,cy+65),(cx+64,cy+116)])
            circle(cx+105,cy-55,22,c=blue)
            text('someone is looking back',cx-111,cy+142)
        else:
            for j in range(4):
                x=cx-106+j*61;y=cy+rng.randrange(-60,60)
                path([(x-12,y),(x+16,y-21),(x+29,y+9),(x+5,y+32),(x-12,y)])
                line((x-60,y-30),(x-20,y-4),1,red)
            text('debris / do not stand here',cx-118,cy+132)
    elif page==3:
        if variant==0:
            for j in range(3):
                x=cx-111+j*75;y=cy-58+j*8
                path([(x,y),(x+63,y-2),(x+65,y+152),(x,y+150),(x,y)])
                for k in range(3):
                    yy=y+12+k*47;path([(x+6,yy),(x+56,yy),(x+56,yy+35),(x+6,yy+35),(x+6,yy)])
                    line((x+20,yy+15),(x+42,yy+15),2)
            text('ORIGINAL / COPY / COPY?',cx-116,cy+133)
        elif variant==1:
            path([(cx-120,cy-70),(cx+110,cy-68),(cx+110,cy+108),(cx-120,cy+108),(cx-120,cy-70)])
            for j in range(6):
                yy=cy-45+j*23;line((cx-98,yy),(cx+88-rng.randrange(0,50),yy),5 if j%2 else 1)
            text('names removed by the Director',cx-134,cy+133)
        elif variant==2:
            path([(cx-121,cy-73),(cx+108,cy-73),(cx+109,cy+108),(cx-121,cy+108),(cx-121,cy-73)])
            for x in (-45,36):line((cx+x,cy-70),(cx+x,cy+55),2)
            line((cx-120,cy+14),(cx+109,cy+14),2)
            path([(cx-94,cy+82),(cx+72,cy+82),(cx+72,cy+39)],red,2)
            circle(cx+72,cy+38,12,c=red)
            text('my route / his blind spot',cx-105,cy+138)
        elif variant==3:
            path([(cx-91,cy-50),(cx+28,cy-50),(cx+65,cy-15),(cx-82,cy-9),(cx-91,cy-50)],w=2)
            circle(cx+67,cy-29,22,c=red)
            path([(cx-43,cy-10),(cx-49,cy+30),(cx-89,cy+32)])
            for j in range(3):line((cx+89,cy-29),(cx+157,cy-95+j*67),1,red)
            text('it follows the line, not you',cx-121,cy+137)
        elif variant==4:
            # A file the player can recognise again in the Evidence Vault.
            path([(cx-117,cy-56),(cx-37,cy-56),(cx-23,cy-70),
                  (cx+119,cy-70),(cx+119,cy+107),(cx-117,cy+107),(cx-117,cy-56)],w=2)
            path([(cx-97,cy-25),(cx+86,cy-25),(cx+86,cy+80),(cx-97,cy+80),(cx-97,cy-25)],blue)
            for j in range(4):
                yy=cy-6+j*20
                line((cx-78,yy),(cx+64-j*19,yy),4 if j==2 else 1,red if j==2 else ink)
            circle(cx+83,cy+82,20,c=red)
            text('FILE 04 / missing original',cx-106,cy+137)
        else:
            # The Director's office plan includes a route the pencil crossed out.
            path([(cx-116,cy-70),(cx+117,cy-70),(cx+117,cy+111),
                  (cx-116,cy+111),(cx-116,cy-70)],w=2)
            for xx in (cx-38,cx+43):line((xx,cy-68),(xx,cy+108),1,blue)
            for yy in (cy-13,cy+55):line((cx-113,yy),(cx+115,yy),1,blue)
            path([(cx-88,cy+82),(cx-68,cy+82),(cx-68,cy+14),
                  (cx+10,cy+14),(cx+10,cy-44),(cx+86,cy-44)],red,3)
            line((cx+75,cy-54),(cx+88,cy-44),2,red)
            line((cx+75,cy-34),(cx+88,cy-44),2,red)
            text('archive route / guard crossed out',cx-128,cy+139)
    else:
        if variant<4:
            for j in range(3):
                x=cx-91+j*87;yy=cy-17+j%2*25
                circle(x,yy-28,17,j,c=blue if j==2 else ink)
                for a,b in [((x,yy-10),(x,yy+47)),((x,yy+7),(x-27,yy+29)),((x,yy+7),(x+26,yy+18)),((x,yy+47),(x-23,yy+81)),((x,yy+47),(x+25,yy+81))]:line(a,b,2)
                if j != (index%3):line((x-38,yy-58),(x+36,yy+88),1,red)
            text(('keep the crooked one','some endings are only drafts','your turn to answer','no perfect version')[variant],cx-112,cy+142)
        elif variant==4:
            # Earlier page shapes overlap as unfinished homework, not scenery.
            path([(cx-111,cy-70),(cx+104,cy-70),(cx+104,cy+109),
                  (cx-111,cy+109),(cx-111,cy-70)],w=2)
            for j,label in enumerate(('SWORD','TICKET','ORBIT','FILE')):
                yy=cy-48+j*37
                path([(cx-94,yy),(cx-71,yy+11),(cx-94,yy+22)],blue)
                text(label,cx-51,yy+2,ink)
                if j<3:line((cx+40,yy+10),(cx+89,yy+5),2,red)
            text('keep one answer',cx-74,cy+139)
        else:
            path([(cx-107,cy+75),(cx-65,cy-42),(cx-7,cy+52),
                  (cx+54,cy-57),(cx+113,cy+73)],w=2)
            path([(cx-108,cy+89),(cx-60,cy-26),(cx-6,cy+70),
                  (cx+59,cy-39),(cx+118,cy+91)],blue)
            for j in range(5):
                xx=cx-97+j*50
                circle(xx,cy+104,5,j,c=red if j==4 else ink)
            text('a line can still change direction',cx-129,cy+146)
    # Distinct erasures and teacher annotations; location-specific instead of a
    # full-screen filter that would obscure characters or native rendering.
    text('see page '+str(index+2)+' ->',100,183,ink)
    for j in range(5):
        xx=140+j*25;yy=288+rng.randrange(-10,11)
        line((xx,yy),(xx+75,yy-12),3,(205,200,180),j)
    text(('unfinished','check this','needs another line','not on the test')[variant],120,322)
