"""Living Runes: roomier routes and small optional notebook expeditions.

Insertions happen between sealed fights. A monotonic coordinate map moves the
entire authored room together, retaining retry IDs, enemy offsets and gates.
The twelve old sketch IDs stay valid; three optional pockets add saved runes.
"""
from __future__ import annotations

import math
from types import SimpleNamespace
import pygame

from action_content import claim_artist_canvas, release_artist_canvas
from entities import LostSketch
from paper_renderer import jitter_line
from scripted_events import ArtistDirector, ArtistTool, artist_canvas_free
from settings import INK, INK_LIGHT, RED_RULE
from world import PaperNote


PACING_INSERTIONS = {
    0: ((1550, 4000), (4480, 1900), (5650, 1900), (8910, 2100)),
    1: ((7000, 2300), (10950, 2100)),
    2: ((7040, 2100), (8880, 2100), (13080, 1800), (15310, 2200)),
    3: ((2790, 1800), (4850, 1800), (6440, 1800), (8460, 1900), (10800, 1700)),
    4: ((2240, 1800), (4750, 1800), (6280, 1800), (8900, 1800), (10800, 1700)),
}


class PacingMap:
    def __init__(self, insertions):
        self.insertions = tuple(insertions)

    def __call__(self, x):
        return x + sum(width for cut, width in self.insertions if x >= cut)

    def inverse(self, x):
        offset = 0
        for cut, width in self.insertions:
            left = cut + offset
            if x < left:
                break
            if x < left + width:
                return cut - .001
            offset += width
        return x - offset

    def pockets(self):
        offset = 0
        for cut, width in self.insertions:
            yield cut, cut + offset, width
            offset += width


class _TriggerPlayer:
    """Predicates read authored coordinates while actors use physical ones."""
    def __init__(self, player, mapping):
        self.player, self.mapping = player, mapping

    def __getattr__(self, name):
        value = getattr(self.player, name)
        if name in ("x", "center_x"):
            return self.mapping.inverse(value)
        if name == "rect":
            value = value.copy()
            value.x = round(self.mapping.inverse(value.x))
        return value


def _move_authored_route(runtime, mapping):
    world = runtime.world
    gate_offsets = [(e, e.entrance_gate.x1-e.start_x, e.entrance_gate.x2-e.start_x,
                     e.exit_gate.x1-e.end_x, e.exit_gate.x2-e.end_x)
                    for e in runtime.entities.items if getattr(e, 'is_combat_arena', False)]
    checkpoint_offsets = []
    for cp in runtime.checkpoints:
        for arena, *_ in gate_offsets:
            if cp.checkpoint_id == 'before_'+arena.arena_id:
                checkpoint_offsets.append((cp, arena, 'start_x', cp.x-arena.start_x,
                                           cp.trigger_x-arena.start_x))
            elif cp.checkpoint_id == 'after_'+arena.arena_id:
                checkpoint_offsets.append((cp, arena, 'end_x', cp.x-arena.end_x,
                                           cp.trigger_x-arena.end_x))
    for p in world.platforms:
        p.x1, p.x2 = mapping(p.x1), mapping(p.x2)
        p.erased[:] = [(mapping(a), mapping(b)) for a, b in p.erased]
        p._owned_erases = {owner: (mapping(a), mapping(b))
                           for owner, (a, b) in p._owned_erases.items()}
        p._pending_restores[:] = [(mapping(a), mapping(b))
                                  for a, b in p._pending_restores]
    for note in world.notes:
        note.x = mapping(note.x)
    for zone in world.zones:
        left, right = mapping(zone.rect.left), mapping(zone.rect.right)
        zone.rect.x, zone.rect.width = round(left), round(right-left)
    for cp in runtime.checkpoints:
        cp.x = mapping(cp.x)
        if cp.trigger_x:
            cp.trigger_x = mapping(cp.trigger_x)
    runtime.spawn = (mapping(runtime.spawn[0]), runtime.spawn[1])
    runtime.end_x = mapping(runtime.end_x)
    world.width = runtime.end_x + 220
    runtime.route_landmarks = [(page, mapping(center))
                              for page, center in getattr(runtime, "route_landmarks", ())]
    if runtime.blank_ending_x is not None:
        runtime.blank_ending_x = mapping(runtime.blank_ending_x)

    visited = set()
    def move_entity(entity):
        if entity is None or id(entity) in visited:
            return
        visited.add(id(entity))
        for name in ("x", "start_x", "end_x", "gift_x", "offer_x"):
            value = getattr(entity, name, None)
            if isinstance(value, (float, int)):
                setattr(entity, name, mapping(value))
        for name in ("source", "receiver", "pull_target", "carrier_position"):
            value = getattr(entity, name, None)
            if isinstance(value, tuple) and len(value) == 2:
                setattr(entity, name, (mapping(value[0]), value[1]))
        marks = getattr(entity, "marks", None)
        if marks:
            entity.marks = tuple((mapping(x), y) for x, y in marks)
        bounds = getattr(entity, "bounds", None)
        if isinstance(bounds, tuple) and len(bounds) == 2:
            entity.bounds = tuple(mapping(x) for x in bounds)
        sections = getattr(entity, "sections", None)
        if sections:
            entity.sections = tuple((name, tuple(mapping(x) for x in span),
                tuple((mapping(a), mapping(b), y) for a, b, y in landings), style)
                for name, span, landings, style in sections)
        for name in ("sketch", "tool_gift", "first", "arena", "target"):
            child = getattr(entity, name, None)
            if child is not None:
                move_entity(child)
        for child in getattr(entity, "arenas", ()):
            move_entity(child)
    for entity in runtime.entities.items:
        move_entity(entity)
    for arena, a, b, c, d in gate_offsets:
        arena.entrance_gate.x1, arena.entrance_gate.x2 = arena.start_x+a, arena.start_x+b
        arena.exit_gate.x1, arena.exit_gate.x2 = arena.end_x+c, arena.end_x+d
    for cp, arena, anchor_name, offset, trigger_offset in checkpoint_offsets:
        anchor = getattr(arena, anchor_name)
        cp.x, cp.trigger_x = anchor+offset, anchor+trigger_offset
    for event in runtime.live_events:
        move_entity(event)
    for event in runtime.director.events:
        original = event.trigger
        def trigger(ctx, predicate=original):
            proxy = SimpleNamespace(**vars(ctx))
            proxy.player = _TriggerPlayer(ctx.player, mapping)
            return predicate(proxy)
        event.trigger = trigger
        for step in event.steps:
            if step.camera_x is not None:
                step.camera_x = mapping(step.camera_x)


class SecretSketch(LostSketch):
    """A normal saved pickup that remains hidden until its pocket is solved."""
    pocket = None

    def update(self, dt, ctx, interact=False):
        if self.pocket is not None and not self.pocket.completed and not self.discovered:
            self.pulse += dt
            return
        super().update(dt, ctx, interact)

    def draw(self, surface, camera, renderer):
        if self.pocket is not None and not self.pocket.completed and not self.discovered:
            return
        super().draw(surface, camera, renderer)


class SecretPocket:
    """A short upper route with an opt-in duel or a two-mark physical puzzle.

    No gates touch the main path. Dropping back down cancels hostile ink and
    releases the Artist immediately; the player can return and try again.
    """
    active = True
    mandatory = False
    layer = 0
    is_secret_pocket = True

    def __init__(self, runtime, base, kind, sketch_id, discovered=()):
        self.page, self.base, self.kind = runtime.index, base, kind
        self.title = {"cloud": "ABOVE THE CLOUDS",
                      "fold": "THE FOLDED REFUGE",
                      "carbon": "THE MISSING ORIGINAL"}[kind]
        self.ground = 295 if kind == "cloud" else 345
        self.bounds = (base+580, base+1110) if kind == "cloud" else (base+290, base+1050)
        self.enemies = []
        self.encounter_active = False
        self.completed = sketch_id in set(discovered or ())
        self.phase = 2 if self.completed else 0
        self.entrance_open = kind != "cloud" or self.completed
        self.entrance_progress = 1.0 if self.entrance_open else 0.0
        self.entered = self.completed
        self.steps = []
        self.reveal = 0.0
        self.timer = 0.0
        self.duel_elapsed = 0.0
        self.hand = ArtistDirector()
        self.letter = ""
        self.letter_time = 0.0
        self.sketch = SecretSketch(self.bounds[1]-65, self.ground-18,
            sketch_id, {"cloud": "a wing drawn above the last cloud",
                        "fold": "a folded shield rejected for being too stubborn",
                        "carbon": "the original signature beneath two carbon copies"}[kind],
            self.completed)
        self.sketch.pocket = self
        heights = (520, 445, 370, 295) if kind == "cloud" else (520, 440, 345)
        for i, y in enumerate(heights):
            x = base+30+i*115
            p = runtime.world.add(x, x+145, y, 10,
                f"secret_{kind}_step_{i}", 22000+self.page*100+i)
            p.appearance = "ghost_line" if kind == "cloud" else "fold_edge" if kind == "fold" else "carbon"
            self.steps.append(p)
        deck = runtime.world.add(*self.bounds, self.ground, 12,
                                 f"secret_{kind}_deck", 22080+self.page)
        deck.appearance = "ghost_line" if kind == "cloud" else "fold_edge" if kind == "fold" else "carbon"
        self.steps.append(deck)
        self.mark_positions = ((self.bounds[0]+65, self.ground),
                               (self.bounds[0]+305, self.ground-65))
        self.revision = runtime.world.add(self.bounds[0]+220,
            self.bounds[0]+390, self.ground-65, 10, f"secret_{kind}_revision", 22090+self.page)
        self.revision.begin_drawing()
        self.revision.appearance = "handwriting"
        if not self.entrance_open:
            for platform in self.steps:
                platform.enabled = False
                platform.draw_progress = 0
        if self.completed:
            self.revision.complete_drawing()
        runtime.entities.add(self)
        runtime.entities.add(self.sketch)

    def _near(self, player, position, distance=72):
        return abs(player.center_x-position[0]) < distance and abs(player.rect.bottom-position[1]) < 65

    def _begin_duel(self, ctx):
        if not artist_canvas_free(ctx, self) or not claim_artist_canvas(ctx, self):
            return False
        from secret_guardian import CloudKiteGuardian
        enemy = CloudKiteGuardian(self.bounds[1]-115, self.ground, 22300+self.page)
        enemy.notebook_reveal = 0
        self.enemies = [enemy]
        self.encounter_active = True
        self.reveal = self.timer = 0
        self.duel_elapsed = 0.0
        self.letter = "A kite wakes in the clouds. Its wind stays low; the tail mark does not move."
        self.letter_time = 6.8
        ctx.sounds.play("pencil")
        return True

    def _complete(self, ctx):
        self.completed = True
        self.encounter_active = False
        self.enemies.clear()
        self.revision.complete_drawing()
        release_artist_canvas(ctx, self)
        self.letter = "Rune uncovered. E to keep it; its numbers stay across pages."
        self.letter_time = 5
        ctx.sounds.play("sketch_found")
        ctx.particles.paper_puff(self.sketch.x, self.sketch.y, 12)
        game = getattr(ctx, "game", None)
        if game is not None:
            game.behavior.record("secret_pocket", page=self.page, kind=self.kind)

    def update(self, dt, ctx, interact=False):
        self.letter_time = max(0, self.letter_time-dt)
        self.hand.tool.visible = False
        player = ctx.player
        other_fight = any(getattr(e, "encounter_active", False) and
            not getattr(e, "completed", False) for e in ctx.level.entities.items if e is not self)
        departed = (player.rect.bottom > self.ground+145 or
                    player.center_x < self.bounds[0]-200 or player.center_x > self.bounds[1]+200)
        if player.health <= 0 or (self.encounter_active and (departed or other_fight)):
            self.enemies.clear()
            self.encounter_active = False
            self.reveal = 0
            release_artist_canvas(ctx, self)
            return
        if self.completed:
            release_artist_canvas(ctx, self)
            return
        if player.locked or other_fight:
            return
        if self.kind == "cloud" and self.entrance_progress < 1:
            if not self.entrance_open:
                if abs(player.center_x-(self.base+60)) < 52 and player.rect.bottom > 535:
                    ctx.level.interaction_hint = "E / lift the loose paper corner"
                    if interact and claim_artist_canvas(ctx, self):
                        self.entrance_open = True
                        for platform in self.steps:
                            platform.enabled = True
                        ctx.sounds.play("fold")
            else:
                if claim_artist_canvas(ctx, self):
                    self.entrance_progress = min(1, self.entrance_progress+dt/.8)
                    for platform in self.steps:
                        platform.draw_progress = self.entrance_progress
                    self.hand.tool = ArtistTool("pencil", self.steps[0].visible_x2,
                                               self.steps[0].y, True)
                    if self.entrance_progress >= 1:
                        release_artist_canvas(ctx, self)
            return
        if self._near(player, (self.bounds[0]+100, self.ground), self.bounds[1]-self.bounds[0]):
            self.entered = True
        if self.kind == "cloud":
            if not self.encounter_active:
                if self._near(player, (self.bounds[0]+50, self.ground), 110):
                    ctx.level.interaction_hint = "E  challenge the cloud guardian / optional"
                    if interact:
                        self._begin_duel(ctx)
                return
            self.duel_elapsed += dt
            if self.reveal < 1:
                if not claim_artist_canvas(ctx, self):
                    return
                self.reveal = min(1, self.reveal+dt/.85)
                enemy = self.enemies[0]
                if self.reveal == 1 and enemy.rect.colliderect(player.rect.inflate(8, 4)):
                    self.reveal = .98
                enemy.notebook_reveal = self.reveal
                self.hand.tool = ArtistTool("pencil", enemy.x,
                    enemy.rect.top+enemy.height*self.reveal, True)
                if self.reveal >= 1:
                    release_artist_canvas(ctx, self)
            else:
                for enemy in self.enemies:
                    enemy.update(dt, ctx, self.bounds)
                if self.enemies and all(enemy.dead for enemy in self.enemies):
                    self._complete(ctx)
        else:
            mark = self.mark_positions[min(self.phase, 1)]
            if self.phase < 2 and self._near(player, mark):
                ctx.level.interaction_hint = ("E  unfold the lower mark" if self.kind == "fold" else
                                               "E  rub the original signature") if self.phase == 0 else "E  connect the second mark"
                if interact and claim_artist_canvas(ctx, self):
                    self.phase += 1
                    if self.phase == 2:
                        self._complete(ctx)
                        return
                    self.timer = 0
                    ctx.sounds.play("fold" if self.kind == "fold" else "pencil")
            if self.phase > 0:
                if not claim_artist_canvas(ctx, self):
                    return
                self.timer += dt
                self.revision.draw_progress = min(1, self.timer/.6)
                self.hand.tool = ArtistTool("pencil", self.revision.visible_x2, self.revision.y, True)
                if self.revision.draw_progress >= 1:
                    release_artist_canvas(ctx, self)
                    if self.phase == 2:
                        self._complete(ctx)

    def draw(self, surface, camera, renderer):
        if self.kind == "cloud" and not self.entrance_open:
            # A small folded corner is the clue. Nothing advertises the reward
            # or draws the upper route before the player examines the paper.
            x = camera.screen_x(self.base+60)
            y = round(578+camera.offset_y)
            pygame.draw.polygon(surface, (222,214,187), [(x-16,y),(x+16,y),(x+16,y-27)])
            pygame.draw.lines(surface, INK_LIGHT, False, [(x-16,y),(x+16,y-27),(x+16,y)], 1)
            return
        left, right = map(camera.screen_x, self.bounds)
        if right < -120 or left > surface.get_width()+120:
            return
        oy = camera.offset_y
        if self.entered and not getattr(self, "cinematic_active", False):
            renderer.doodle_text(surface, self.title, (left, self.ground-140+oy),
                                 RED_RULE, renderer.font_small, -1)
        if self.kind == "cloud":
            for i in range(5):
                cx = left+i*125
                color = (154, 175, 175)
                pygame.draw.arc(surface, color, (cx-55, self.ground-43+oy, 104, 65), math.pi, math.tau, 2)
                jitter_line(surface, color, (cx-58, self.ground+oy), (cx+61, self.ground+oy), 1, 22500+i)
        elif not self.completed:
            for i, (mx, y) in enumerate(self.mark_positions):
                color = (76, 108, 121) if self.phase > i else INK_LIGHT
                sx = camera.screen_x(mx)
                pygame.draw.circle(surface, color, (sx, round(y-28+oy)), 15, 2)
                renderer.doodle_text(surface, str(i+1), (sx-5, y-36+oy), color, renderer.font_small)
        for enemy in self.enemies:
            old = surface.get_clip()
            if self.reveal < 1:
                surface.set_clip(old.clip(pygame.Rect(camera.screen_x(enemy.x)-100,
                    enemy.rect.top+oy, 200, round(enemy.height*self.reveal))))
            enemy.draw(surface, camera, renderer)
            surface.set_clip(old)
            if self.reveal >= 1:
                from staging import draw_enemy_read
                draw_enemy_read(surface, camera, renderer, enemy)

    def draw_overlay(self, surface, camera, renderer):
        self.hand.draw(surface, camera, renderer)
        entering = (self.kind == "cloud" and self.encounter_active
                    and not self.completed and self.duel_elapsed < 2.8)
        if entering:
            from boss_presentation import draw_boss_entrance
            guardian = next((enemy for enemy in self.enemies
                             if not getattr(enemy, "dead", False)), None)
            draw_boss_entrance(surface, renderer, "cloud_kite", "CLOUD KITE",
                              "JUMP THE GUST. LEAVE THE TAIL MARK.", self.duel_elapsed,
                              boss=guardian)
        elif self.letter_time > 0:
            renderer.notebook.artist_note(surface, self.letter)


def _fill_insertions(runtime, mapping):
    style = ("handwriting", "torn_edge", "construction", "carbon", "annotation")[runtime.index]
    pockets = tuple(mapping.pockets())
    encounter_cuts = {c for c, _ in getattr(runtime, "encounter_insertions", ())}
    secret_cuts = {0: {5650}, 1: {7000}, 3: {8460}}.get(runtime.index, set())
    eligible = [i for i, (cut, _, _) in enumerate(pockets)
                if cut not in encounter_cuts and cut not in secret_cuts
                and not (runtime.index == 0 and cut == 1550)]
    # One useful recovery detour near the middle of each page; the remaining
    # walks have different scenery and low lines, without copied objectives.
    heart_index = eligible[(len(eligible)-1)//2] if eligible else None
    for i, (cut, left, width) in enumerate(pockets):
        # Always add a real floor. An insertion can land between two old
        # ground strokes instead of inside one long stroke.
        floor = runtime.world.add(left-30, left+width+35, 590, 14,
            f"pacing_rest_{runtime.index}_{i}", 23000+runtime.index*100+i)
        floor.appearance = style
        if cut in encounter_cuts:
            # Arena widening supplies floor only; blue-waypoint expeditions
            # belong to the authored quiet gaps between the sealed rooms.
            continue
        secret = cut in secret_cuts
        training = runtime.index == 0 and cut == 1550
        if not secret and not training:
            from route_expeditions import RouteExpedition, RouteScenery
            route = RouteExpedition if i == heart_index else RouteScenery
            runtime.entities.add(route(runtime, left, width, i))


def compose_extended_campaign(runtime, discovered=()):
    if getattr(runtime, "extended_campaign_applied", False):
        return runtime
    runtime.extended_campaign_applied = True
    mapping = PacingMap(sorted((*PACING_INSERTIONS[runtime.index],
                               *getattr(runtime, "encounter_insertions", ()))))
    runtime.pacing_map = mapping
    runtime.pacing_insertions = mapping.insertions
    runtime.authored_route_end = runtime.end_x
    _move_authored_route(runtime, mapping)
    _fill_insertions(runtime, mapping)
    for cut, left, width in mapping.pockets():
        if runtime.index == 0 and cut == 5650:
            SecretPocket(runtime, left+15, "cloud", "cloud_heart", discovered)
        elif runtime.index == 1 and cut == 7000:
            SecretPocket(runtime, left+35, "fold", "fold_bastion", discovered)
        elif runtime.index == 3 and cut == 8460:
            SecretPocket(runtime, left-90, "carbon", "carbon_echo", discovered)
    from optional_encounters import add_optional_duels
    add_optional_duels(runtime, discovered)
    runtime.checkpoints.sort(key=lambda cp: float(cp.trigger_x or cp.x))
    return runtime


__all__ = ["PACING_INSERTIONS", "PacingMap", "SecretPocket", "SecretSketch", "compose_extended_campaign"]
