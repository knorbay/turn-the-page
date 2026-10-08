"""Reshape existing pages into climbs, drops and generous fighting spaces.

No encounters, page length, collectibles or campaign gates are added here.
The main edits cut short sections out of overlapping ground strokes, so a
decorative upper route no longer sits above an identical straight corridor.
"""
from __future__ import annotations

import pygame

from paper_renderer import jitter_line
from world import PaperNote


# A section is (name, erased ground span, physical landing strokes, motif).
# All of these sit in existing quiet intervals, clear of retry and arena gates.
FLOW_SECTIONS = {
    0: (("bamboo_roots", (5750, 6170),
         ((5720, 5870, 535), (5890, 6050, 475), (6080, 6250, 535)),
         "handwriting"),),
    1: (("dry_canyon", (7710, 8050),
         ((7650, 7835, 535), (7855, 8020, 480), (8045, 8210, 535)),
         "torn_edge"),),
    2: (("gravity_work", (6400, 6890),
         ((6340, 6540, 510), (6560, 6750, 440), (6780, 6990, 510)),
         "construction"),),
    3: (("service_tunnel", (2340, 2700),
         ((2320, 2740, 655), (2600, 2680, 605)), "carbon"),),
    4: (("exam_margin", (4220, 4580),
         ((4170, 4350, 525), (4370, 4530, 450), (4560, 4730, 525)),
         "annotation"),),
}

FLOW_NOTES = {
    "bamboo_roots": "the roots are lines too",
    "dry_canyon": "the page tears down here",
    "gravity_work": "gravity homework / use the working lines",
    "service_tunnel": "original above / carbon copy below",
    "exam_margin": "the answer climbs out of the margin",
}


def _line(world, name, a, b, y, style, seed):
    p = world.add(a, b, y, 10, name, seed)
    p.appearance = style
    return p


def _open_ground(world, a, b):
    # Some shipping stretches have both original ground and a later page
    # floor. Cut every real ground stroke; otherwise an invisible duplicate
    # would silently turn the authored ascent into another straight run.
    for p in world.platforms:
        if p.layer == 0 and 578 <= p.y <= 603 and p.thickness <= 40:
            p.erase(a, b)


class RouteWorking:
    """Pale supports and torn-sheet depth stay subordinate to real landings."""
    active = True
    mandatory = False
    layer = 0

    def __init__(self, page, sections):
        self.page, self.sections = page, sections

    def update(self, dt, ctx, interact=False):
        pass

    def draw(self, surface, camera, renderer):
        colors = ((146, 135, 115), (155, 127, 101), (124, 145, 151),
                  (137, 142, 136), (145, 136, 115))
        color = colors[self.page]
        oy = camera.offset_y
        for name, span, landings, _ in self.sections:
            a, b = map(camera.screen_x, span)
            if b < -80 or a > surface.get_width()+80:
                continue
            for i, (left, right, y) in enumerate(landings):
                x1, x2 = camera.screen_x(left), camera.screen_x(right)
                if y < 600:
                    for x in (x1+18, x2-17):
                        jitter_line(surface,color,(x,y+16+oy),(x+7,667+oy),
                                    1,round(left)+i,2,2)
                elif name == "service_tunnel":
                    for x in range(x1+15,x2,53):
                        pygame.draw.line(surface,color,(x,y-32+oy),(x+8,y-18+oy),1)
            # A pencilled depth mark makes the recoverable lower page visible.
            jitter_line(surface,color,(a,604+oy),(a,650+oy),1,round(span[0]),2,2)
            pygame.draw.lines(surface,color,False,
                [(a-4,644+oy),(a,651+oy),(a+5,643+oy)],1)


def _shape_landmarks(runtime):
    """Use the same three existing landmarks as different kinds of climb."""
    page = runtime.index
    if page == 0:
        runtime.world.notes[:] = [n for n in runtime.world.notes
            if n.text != "UP: a lost sketch     /     ground: onward"]
        runtime.world.notes.append(PaperNote(6290,282,"one roof fold hangs loose",angle=-1))
    elif page == 1:
        layout = ((9920,505),(10100,430),(10120,345),(10320,430),(10495,500))
        for i,(x,y) in enumerate(layout):
            p=runtime.world.platform_named(f"vignette_water_tower_{i}")
            if p:
                p.x1,p.x2,p.y=x,x+160,y
        for sketch in runtime.entities.items:
            if getattr(sketch,"secret_id",None)=="water_tower":
                sketch.x,sketch.y=10205,327
        runtime.route_landmarks[:]=[(p,10205 if p==1 else center)
                                    for p,center in runtime.route_landmarks]
        runtime.world.notes[:] = [n for n in runtime.world.notes
            if n.text != "UP: a lost sketch     /     ground: onward"]
        runtime.world.notes.append(PaperNote(9930,282,"the timetable has a missing corner"))
    elif page == 2:
        layout=((12200,505),(12375,425),(12570,345),(12765,425),(12940,505))
        for i,(x,y) in enumerate(layout):
            p=runtime.world.platform_named(f"vignette_orbit_observatory_{i}")
            if p:
                p.x1,p.x2,p.y=x,x+(185 if i==2 else 160),y
        runtime.world.notes[:] = [n for n in runtime.world.notes
            if n.text != "UP: a lost sketch     /     ground: onward"]
        runtime.world.notes.append(PaperNote(12210,282,"why did I draw the moon twice?"))


def _arena_landings(runtime):
    for arena in runtime.entities.items:
        if not getattr(arena,"is_combat_arena",False):
            continue
        span=arena.end_x-arena.start_x
        # Tiny teaching rooms stay simple. The wide bosses get two distinct
        # retreat angles, not platforms spread across their entire attack lane.
        if not arena.boss and span < 1000:
            continue
        style=("torn_edge","ruler_line","construction","carbon","handwriting")[runtime.index]
        offsets=((180,495),(span-340,495)) if arena.boss else ((span-345,510),)
        for i,(offset,y) in enumerate(offsets):
            _line(runtime.world,f"quality_flank_{arena.arena_id}_{i}",
                  arena.start_x+offset,arena.start_x+offset+160,y,style,
                  19000+runtime.index*100+int(arena.start_x)+i)
        if arena.boss and arena.arena_id in ("moon_gate_duel","zero_garden"):
            _line(runtime.world,f"quality_high_{arena.arena_id}",
                  arena.start_x+245,arena.start_x+400,415,style,19110+int(arena.start_x))


def compose_quality_flow(runtime):
    if getattr(runtime,"quality_flow_applied",False):
        return runtime
    runtime.quality_flow_applied=True
    sections=FLOW_SECTIONS.get(runtime.index,())
    for order,(name,span,landings,style) in enumerate(sections):
        _open_ground(runtime.world,*span)
        for i,(a,b,y) in enumerate(landings):
            _line(runtime.world,f"quality_route_{name}_{i}",a,b,y,style,
                  18000+runtime.index*100+order*10+i)
        # A missed line lands on the visibly torn lower edge. It is never an
        # arena bypass: these spans lie wholly between existing closed rooms.
        _line(runtime.world,f"quality_catch_{name}",span[0]-110,span[1]+110,
              690 if runtime.index==3 else 675,"torn_edge",18180+runtime.index)
        runtime.world.notes.append(PaperNote(span[0]-25,300,FLOW_NOTES[name],angle=-1))

    if runtime.index==2:
        # An upper proof line and a lower rejected draft share this short
        # stretch. Jump over it, or descend and discover what was erased.
        _open_ground(runtime.world,13320,13660)
        for name,a,b,y,style in (
            ("proof",13295,13700,550,"construction"),
            ("discard",13280,13725,675,"ghost_line"),
            ("return",13545,13740,615,"equation_box")):
            _line(runtime.world,"quality_underfold_"+name,a,b,y,style,18410+int(y))
        runtime.world.notes.append(PaperNote(13280,315,"a second draft under the proof line",angle=-2))
    _shape_landmarks(runtime)
    _arena_landings(runtime)
    if sections:runtime.entities.add(RouteWorking(runtime.index,sections))
    return runtime


__all__=["compose_quality_flow","FLOW_SECTIONS"]
