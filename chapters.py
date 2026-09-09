from __future__ import annotations

from dataclasses import dataclass, field
import pygame

from entities import (DoodleCreature, EntitySystem, FallingDoodle, LostSketch,
                      PressureSwitch, TearPortal)
from scripted_events import (ArtistDirector, ArtistTool, EraserChase, EventSequence,
                             EventStep, FinaleDirector, draw_platform_event)
from world import MaterialZone, PaperNote, PaperWorld


CHAPTER_TITLES = [
    ("PAGE I", "Ink of the Ronin"),
    ("PAGE II", "Dust & Bad Decisions"),
    ("PAGE III", "A Very Wrong Future"),
    ("CHAPTER 3", "Under the Ink"),
    ("FINALE", "Turn the Page"),
]


@dataclass
class Checkpoint:
    checkpoint_id: str
    x: float
    y: float
    layer: int = 0
    trigger_x: float = 0
    facing: int = 1
    requires: tuple[str, ...] = ()


@dataclass
class ChapterRuntime:
    index: int
    title: str
    subtitle: str
    world: PaperWorld
    spawn: tuple[float, float]
    end_x: float
    checkpoints: list[Checkpoint]
    director: ArtistDirector = field(default_factory=ArtistDirector)
    entities: EntitySystem = field(default_factory=EntitySystem)
    live_events: list[object] = field(default_factory=list)
    intro_text: str = ""
    allow_margin_secret: bool = False
    blank_ending_x: float | None = None


def note(world, x, y, text, size="small", angle=0, crossed=False):
    world.notes.append(PaperNote(x, y, text, size, angle=angle, crossed=crossed))


def ground(world, x1, x2, y=590, name="ground", seed=1, layer=0):
    return world.add(x1, x2, y, 16, name, seed, layer)


def build_chapter(index: int, discovered=None) -> ChapterRuntime:
    if index >= 3:
        from campaign import build_new_page
        chapter = build_new_page(index)
        for entity in chapter.entities.items:
            if isinstance(entity, LostSketch):
                entity.discovered = entity.secret_id in set(discovered or [])
        return chapter
    builders = [_prologue, _margins, _mistakes, _under_ink, _finale]
    chapter = builders[index]()
    authored_end_x = chapter.end_x
    from expanded_content import expand_chapter
    expand_chapter(chapter)
    # The action pass is deliberately separate from both the original paper
    # story and its puzzle rooms.  That keeps combat pacing easy to tune while
    # preserving every authored Artist/eraser/fold event underneath it.
    from action_content import expand_action_chapter
    expand_action_chapter(chapter)
    # Keep the large old route as a mechanics catalogue, but make the actual
    # playable beta a curated three-page experience.
    from identity_content import apply_identity_pass
    apply_identity_pass(chapter, authored_end_x)
    discovered = set(discovered or [])
    for entity in chapter.entities.items:
        if isinstance(entity, LostSketch) and entity.secret_id in discovered:
            entity.discovered = True
    return chapter


def _prologue():
    world = PaperWorld(0, False)
    world.width = 5550
    world.page = 0
    ground(world, -120, 760, seed=1)
    # These lines are authored but become physical only as the Artist draws them.
    stair1 = world.add(790, 1010, 545, 11, "first_step", 2); stair1.draw_progress = 0
    stair2 = world.add(1040, 1250, 500, 11, "second_step", 3); stair2.draw_progress = 0
    stair3 = world.add(1280, 1500, 545, 11, "third_step", 4); stair3.draw_progress = 0
    ground(world, 1500, 2300, seed=5)
    bridge = world.add(2300, 2780, 590, 11, "first_bridge", 6); bridge.draw_progress = 0
    ground(world, 2780, 3700, seed=7)
    world.add(3520, 3770, 505, 11, "practice_step", 8)
    world.add(3830, 4080, 455, 11, "practice_step_2", 9)
    world.add(4130, 4380, 520, 11, "practice_step_3", 10)
    ground(world, 4400, 5580, seed=11)

    note(world, 1770, 310, "the first line is always the hardest", angle=-1)
    note(world, 3200, 330, "7 / ? / 20__", crossed=True)
    note(world, 4860, 270, "next page", angle=1)

    entities = EntitySystem([
        LostSketch(95, 570, "old_first_figure", "an earlier little figure, erased before it could stand"),
    ])
    director = ArtistDirector()

    def intro_update(ctx, progress):
        ctx.player.draw_amount = progress
        ctx.director.tool = ArtistTool("pencil", ctx.player.center_x + 8,
                                       ctx.player.y + 8 + progress * 42, True, -.65)
        if int(progress * 50) % 4 == 0:
            ctx.particles.pencil_speck(ctx.player.center_x, ctx.player.y + progress * 48)

    def intro_finish(ctx):
        ctx.player.draw_amount = 1
        ctx.level.set_checkpoint("alive")
        ctx.sounds.play("pencil")

    director.add(EventSequence("player_drawn", lambda ctx: True, [
        EventStep(.6, lock_player=True),
        EventStep(2.8, update=intro_update, finish=intro_finish, lock_player=True,
                  camera_x=ctx_x(220)),
        EventStep(.35, lock_player=True),
    ]))

    def controls(ctx, progress):
        ctx.director.tool = ArtistTool("pencil", 540 + progress * 90, 410, True)
        ctx.director.write(505, 405, "A    D", progress)

    director.add(EventSequence("movement_note", lambda ctx: ctx.player.x > 340, [
        EventStep(1.0, update=controls),
    ]))
    director.add(draw_platform_event("first_step_drawn", 390, stair1, .65, False))
    director.add(draw_platform_event("second_step_drawn", 650, stair2, .65, False))
    director.add(draw_platform_event("third_step_drawn", 910, stair3, .65, False))

    def jump_note(ctx, progress):
        ctx.director.write(1650, 470, "SPACE", progress)
        ctx.director.tool = ArtistTool("pencil", 1650 + 80 * progress, 485, True)

    director.add(EventSequence("jump_note", lambda ctx: ctx.player.x > 1530, [EventStep(.8, update=jump_note)]))
    director.add(draw_platform_event("first_bridge_drawn", 2080, bridge, 2.2, True, "this way"))

    return ChapterRuntime(0, *CHAPTER_TITLES[0], world, (220, 520), 5280,
                          [Checkpoint("start", 220, 520, trigger_x=0),
                           Checkpoint("alive", 220, 520, trigger_x=0),
                           Checkpoint("bridge", 2860, 510, trigger_x=2860, requires=("first_bridge_drawn",)),
                           Checkpoint("last_steps", 4480, 520, trigger_x=4480)],
                          director, entities, [], "A small mark wakes on an empty page.")


def ctx_x(value):
    # Named helper makes static camera framing values self-documenting in chapter data.
    return value


def _margins():
    world = PaperWorld(1, False)
    world.width = 7600
    world.page = 1
    ground(world, -100, 900, seed=20)
    line1 = world.add(940, 1250, 540, 10, "ruled_line_1", 21); line1.draw_progress = 0
    line2 = world.add(1300, 1640, 485, 10, "ruled_line_2", 22); line2.draw_progress = 0
    line3 = world.add(1690, 2040, 535, 10, "ruled_line_3", 23); line3.draw_progress = 0
    ground(world, 2070, 2800, seed=24)
    ground(world, 2815, 3580, seed=25)
    world.zones.extend([
        MaterialZone(pygame.Rect(2830, 405, 510, 235), "coffee_slippery", "thin coffee ring", 1.0, (115, 69, 35, 38)),
        MaterialZone(pygame.Rect(3340, 430, 430, 210), "coffee_sticky", "dark coffee sediment", 1.0, (91, 49, 27, 58)),
    ])
    world.add(3630, 3980, 525, 10, "coffee_jump", 26)
    ground(world, 4010, 4840, seed=27)
    # The red margin becomes a low-gravity column rather than decoration.
    world.zones.append(MaterialZone(pygame.Rect(4610, 80, 270, 560), "margin_gravity", "outside the margin", .58,
                                    (197, 75, 75, 28)))
    world.add(4570, 4770, 510, 10, "margin_step_1", 28)
    world.add(4720, 4930, 420, 10, "margin_step_2", 29)
    world.add(4870, 5110, 330, 10, "margin_step_3", 30)
    world.add(5130, 5410, 450, 10, "margin_return", 31)
    ground(world, 5430, 6140, seed=32)
    final_bridge = world.add(6140, 6600, 590, 10, "margin_bridge", 33); final_bridge.draw_progress = 0
    ground(world, 6600, 7650, seed=34)
    world.zones.append(MaterialZone(pygame.Rect(2260, 565, 190, 75), "ink_sticky", "wet ink", 1,
                                    (26, 27, 31, 110)))
    note(world, 2150, 325, "do not smudge", crossed=True)
    note(world, 3020, 330, "coffee / Tuesday 08:14")
    note(world, 4520, 245, "MARGIN", angle=90)
    note(world, 5650, 300, "->", size="large")
    note(world, 6990, 260, "good.", angle=-2)

    entities = EntitySystem([
        LostSketch(4700, 290, "beyond_red", "a house drawn where the Artist said nothing should be"),
        LostSketch(3520, 565, "coffee_secret", "a tiny umbrella hiding beneath the old stain"),
    ])
    director = ArtistDirector()
    director.add(draw_platform_event("ruled_one", 390, line1, .8, False))
    director.add(draw_platform_event("ruled_two", 850, line2, .8, False))
    director.add(draw_platform_event("ruled_three", 1210, line3, .8, False))

    def margin_question(ctx, progress):
        ctx.director.write(4520, 180, "?", progress)
        ctx.director.tool = ArtistTool("pencil", 4560, 205, True)
    director.add(EventSequence("artist_questions_margin", lambda ctx: ctx.player.x > 4630 and ctx.player.y < 470,
                               [EventStep(.65, update=margin_question)]))
    director.add(draw_platform_event("margin_exit", 5900, final_bridge, 1.7, True, "->"))
    return ChapterRuntime(1, *CHAPTER_TITLES[1], world, (180, 520), 7380,
                          [Checkpoint("start", 180, 520), Checkpoint("ruled", 2110, 520, trigger_x=2110),
                           Checkpoint("coffee", 4050, 520, trigger_x=4050),
                           Checkpoint("beyond_red", 5480, 520, trigger_x=5480),
                           Checkpoint("margin_exit", 6660, 520, trigger_x=6660)],
                          director, entities, [], "The rules are lines. The red one may be a suggestion.", True)


def _mistakes():
    world = PaperWorld(2, False)
    world.width = 7850
    world.page = 2
    ground(world, -100, 1250, seed=40)
    support = world.add(1320, 1780, 470, 13, "wrong_support", 41)
    ground(world, 1250, 2440, seed=42)
    fixed_steps = [world.add(1830 + i * 180, 1970 + i * 180, 535 - i * 35, 10,
                             f"fixed_step_{i}", 43 + i) for i in range(3)]
    for p in fixed_steps: p.draw_progress = 0
    ground(world, 2440, 2920, seed=47)
    chase = world.add(2920, 4200, 535, 13, "correction_bridge", 48)
    ground(world, 4200, 5050, seed=49)
    world.add(4560, 4810, 470, 10, "safe_pocket", 50)
    ground(world, 5050, 5790, seed=51)
    circuit = world.add(5790, 6300, 540, 12, "circuit_gate", 52); circuit.draw_progress = 0
    ground(world, 6300, 7900, seed=53)
    world.zones.append(MaterialZone(pygame.Rect(5300, 565, 120, 75), "ink_hazard", "fresh ink", 1,
                                    (22, 23, 29, 155)))
    note(world, 890, 300, "NO NO NO", crossed=True)
    note(world, 1550, 245, "too steep", angle=-3)
    note(world, 3370, 280, "run?", crossed=True)
    note(world, 4590, 350, "GOOD", crossed=True)
    note(world, 5460, 270, "V = I x R", angle=1)
    note(world, 6490, 310, "stay", angle=-2)

    creature = DoodleCreature(2300, 560, "blot", True)
    weight = FallingDoodle(1480, 300, 92, 88, "support_erased", "weight_landed")
    entities = EntitySystem([
        PressureSwitch(1130, 590, "erase_wrong"), weight,
        creature,
        PressureSwitch(5530, 590, "blot_on_switch", require_creature=True),
        LostSketch(1660, 445, "bad_draft", "a fierce monster with an apologetic smile"),
    ])
    director = ArtistDirector()

    def erase_support(ctx, progress):
        if "erase_wrong" not in ctx.level.flags:
            return
        cursor = support.x1 + (support.x2 - support.x1) * progress
        support.erase(support.x1, cursor)
        ctx.director.tool = ArtistTool("eraser", cursor, support.y, True)
        ctx.particles.eraser_dust(cursor, support.y, 4)

    director.add(EventSequence("support_erased", lambda ctx: "erase_wrong" in ctx.level.flags, [
        EventStep(1.4, update=erase_support, start=lambda ctx: ctx.sounds.play("erase"),
                  lock_player=True, camera_x=1550),
    ]))

    def redraw(ctx, progress):
        for i, platform in enumerate(fixed_steps):
            platform.draw_progress = max(0, min(1, progress * len(fixed_steps) - i))
        active = next((p for p in fixed_steps if p.draw_progress < 1), fixed_steps[-1])
        ctx.director.tool = ArtistTool("pencil", active.visible_x2, active.y, True)
        ctx.particles.pencil_speck(active.visible_x2, active.y)

    director.add(EventSequence("bad_draft_fixed", lambda ctx: "weight_landed" in ctx.level.flags, [
        EventStep(2.1, update=redraw, start=lambda ctx: ctx.sounds.play("pencil"),
                  lock_player=True, camera_x=2050),
    ]))
    eraser = EraserChase("bridge_correction", chase, 3050, 4050, 270)

    def circuit_draw(ctx, progress):
        circuit.draw_progress = progress
        ctx.director.tool = ArtistTool("pencil", circuit.visible_x2, circuit.y, True)
        ctx.director.write(5850, 420, "STAY", progress, True)
    director.add(EventSequence("circuit_complete", lambda ctx: "blot_on_switch" in ctx.level.flags, [
        EventStep(1.6, update=circuit_draw, start=lambda ctx: ctx.sounds.play("pencil"), camera_x=6040),
    ]))
    return ChapterRuntime(2, *CHAPTER_TITLES[2], world, (170, 520), 7580,
                          [Checkpoint("start", 170, 520),
                           Checkpoint("redrawn", 2460, 510, trigger_x=2460, requires=("bad_draft_fixed",)),
                           Checkpoint("chase", 2870, 500, trigger_x=2870, requires=("bad_draft_fixed",)),
                           Checkpoint("safe_pocket", 4250, 510, trigger_x=4250, requires=("bridge_correction",)),
                           Checkpoint("circuit", 6350, 510, trigger_x=6350, requires=("circuit_complete",))],
                          director, entities, [eraser], "Some mistakes move after the pencil leaves.")


def _under_ink():
    world = PaperWorld(3, False)
    world.width = 7900
    world.page = 3
    ground(world, -100, 1850, seed=60, layer=0)
    ground(world, 4200, 4900, seed=61, layer=0)
    fold_bridge = world.add(4900, 5580, 535, 13, "fold_bridge", 62, layer=0); fold_bridge.draw_progress = 0
    ground(world, 5580, 7900, seed=63, layer=0)
    # Old pale drawing below the page.
    ground(world, 1650, 2470, 610, seed=64, layer=1)
    world.add(2380, 2690, 525, 11, "old_step_1", 65, layer=1)
    world.add(2740, 3080, 470, 11, "old_step_2", 66, layer=1)
    world.add(3130, 3480, 535, 11, "old_step_3", 67, layer=1)
    ground(world, 3500, 4350, 610, seed=68, layer=1)
    world.zones.append(MaterialZone(pygame.Rect(1280, 470, 530, 170), "ink_wall", "black ink", 1,
                                    (20, 20, 24, 190)))
    note(world, 420, 270, "old words show through here", crossed=True)
    note(world, 2300, 260, "199_", angle=-3)
    note(world, 3700, 350, "can you see me?", crossed=True)
    note(world, 4950, 280, "fold along dotted line")
    note(world, 6660, 260, "don't turn yet", angle=2)

    creature = DoodleCreature(4400, 560, "blot", True)
    entities = EntitySystem([
        TearPortal(pygame.Rect(1100, 545, 105, 48), 1780, 545, 1, "slip beneath the ink", True),
        TearPortal(pygame.Rect(3980, 565, 110, 45), 4280, 500, 0, "climb through", True),
        LostSketch(2920, 445, "under_character", "the same little hero, drawn years earlier", False),
        creature,
        PressureSwitch(4560, 590, "fold_ready", require_creature=True),
        LostSketch(5270, 510, "inside_fold", "a note hidden where the page used to touch itself"),
    ])
    # Layer-bound entities are tagged dynamically; EntitySystem filters them in Level.
    entities.items[0].layer = 0
    entities.items[1].layer = 1
    entities.items[2].layer = 1
    director = ArtistDirector()

    def fold_update(ctx, progress):
        ctx.level.fold_progress = progress
        fold_bridge.draw_progress = progress
        ctx.director.tool = ArtistTool("pencil", 4900 + progress * 650, 470 - progress * 80, True)
        if int(progress * 30) % 5 == 0:
            ctx.particles.paper_puff(4900 + progress * 650, 535, 2)

    director.add(EventSequence("page_folded", lambda ctx: "fold_ready" in ctx.level.flags, [
        EventStep(.4, lock_player=True),
        EventStep(2.2, update=fold_update, start=lambda ctx: ctx.sounds.play("fold"),
                  lock_player=True, camera_x=5250),
        EventStep(.3, lock_player=True),
    ]))
    return ChapterRuntime(3, *CHAPTER_TITLES[3], world, (170, 520), 7600,
                          [Checkpoint("start", 170, 520),
                           Checkpoint("under_page", 1810, 545, 1, trigger_x=1900),
                           Checkpoint("surface", 4280, 500, 0, trigger_x=4250),
                           Checkpoint("folded", 5630, 500, 0, trigger_x=5630, requires=("page_folded",)),
                           Checkpoint("half_turn", 6880, 500, 0, trigger_x=6880)],
                          director, entities, [], "There is another drawing beneath this one.")


def _finale():
    world = PaperWorld(4, False)
    world.width = 6900
    world.page = 4
    ground(world, -100, 1050, seed=80)
    intended = world.add(1050, 1600, 520, 11, "intended_end", 81)
    ground(world, 1600, 2210, seed=82)
    dynamic = []
    for i, (x1, x2, y) in enumerate([
        (2210, 2630, 560), (2670, 3070, 505), (3110, 3520, 550),
        (3560, 3970, 485), (4010, 4450, 545), (4490, 4890, 500),
    ]):
        p = world.add(x1, x2, y, 11, f"final_draw_{i}", 83 + i)
        p.draw_progress = 0
        dynamic.append(p)
    ground(world, 4930, 5550, seed=90)
    world.add(5250, 5500, 455, 10, "quiet_step", 91)
    final_line = world.add(5550, 6250, 590, 10, "last_line", 92); final_line.draw_progress = 0
    ground(world, 6250, 6940, seed=93)
    world.zones.append(MaterialZone(pygame.Rect(3750, 440, 370, 200), "coffee_slippery", "old coffee", 1,
                                    (105, 61, 33, 36)))
    note(world, 650, 275, "-> END", size="large")
    note(world, 1260, 335, "the correct way", crossed=True)
    note(world, 1850, 280, "not that way", angle=-2)
    note(world, 5200, 300, "...")
    entities = EntitySystem([
        LostSketch(1880, 560, "wrong_ending", "an ending the Artist crossed out but never erased"),
    ])
    director = ArtistDirector()
    finale = FinaleDirector(dynamic)
    director.add(draw_platform_event("last_rescue_line", 5250, final_line, 2.0, True, None))
    return ChapterRuntime(4, *CHAPTER_TITLES[4], world, (180, 520), 6650,
                          [Checkpoint("start", 180, 520), Checkpoint("wrong_way", 1660, 510, trigger_x=1660),
                           Checkpoint("chase", 2150, 500, trigger_x=2150),
                           Checkpoint("quiet", 4980, 510, trigger_x=4980),
                           Checkpoint("edge", 6300, 510, trigger_x=6300)],
                          director, entities, [finale], "The arrow points toward somebody else's ending.",
                          blank_ending_x=6650)
