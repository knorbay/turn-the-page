"""Four short, optional upper-margin duels, independent of the main road.

Defeating a guardian and collecting its rune are separate saved facts. An
unclaimed rune remains available after a retry; a completed duel never resets.
"""
from __future__ import annotations

from dataclasses import dataclass
import pygame

from action_content import claim_artist_canvas, release_artist_canvas
from paper_renderer import jitter_line
from scripted_events import ArtistDirector, ArtistTool, artist_canvas_free
from settings import INK_LIGHT, RED_RULE


@dataclass(frozen=True)
class OptionalDuel:
    page: int
    cut: int
    offset: int
    kind: str
    title: str
    rule: str
    rune: str
    caption: str


OPTIONAL_DUELS = (
    OptionalDuel(1, 10950, 1140, "brass_tumbleweed", "BRASS TUMBLEWEED",
                 "JUMP THE ROLL. LEAVE THE LASSO MARK.", "brass_spur",
                 "a brass spur from the abandoned high-noon sketch"),
    OptionalDuel(2, 7040, 1140, "orbit_crab", "ORBIT CRAB",
                 "JUMP THE RING. LEAVE THE CRATER MARK.", "orbit_shell",
                 "a shell drawn around a forgotten satellite"),
    OptionalDuel(3, 10800, 910, "carbon_hound", "CARBON HOUND",
                 "JUMP THE RUSH. LEAVE THE STAMP MARK.", "carbon_fang",
                 "a carbon fang clipped from the rejected case file"),
    OptionalDuel(4, 10800, 910, "draft_moth", "DRAFT MOTH",
                 "STAY BETWEEN THE PAGES. LEAVE THE WINGS.", "draft_wing",
                 "a moth wing saved from the last discarded draft"),
)


class OptionalGuardianPocket:
    active = True
    mandatory = False
    layer = 0
    is_optional_guardian = True

    def __init__(self, runtime, base, spec, discovered=()):
        from major_campaign import SecretSketch
        self.world = runtime.world
        self.page, self.base, self.spec = runtime.index, base, spec
        self.kind = self.boss_kind = spec.kind
        self.title = spec.title
        self.ground = 295
        self.bounds = (base+460, base+980)
        self.enemies = []
        self.encounter_active = self.boss_cue_started = False
        self.completed = spec.rune in set(discovered or ())
        self.entrance_open = self.completed
        self.entrance_progress = 1.0 if self.completed else 0.0
        self.entered = self.completed
        self.reveal = self.duel_elapsed = 0.0
        self.hand = ArtistDirector()
        self.letter, self.letter_time = "", 0.0
        self.sketch = SecretSketch(self.bounds[1]-60, self.ground-18,
                                   spec.rune, spec.caption, self.completed)
        self.sketch.pocket = self
        self.steps = []
        for i, y in enumerate((520, 445, 370, 295)):
            landing = self.world.add(base+30+i*115, base+175+i*115,
                y, 10, f"optional_{self.kind}_step_{i}", 28000+self.page*20+i)
            self.steps.append(landing)
        self.steps.append(self.world.add(*self.bounds, self.ground, 12,
            f"optional_{self.kind}_deck", 28010+self.page*20))
        for landing in self.steps:
            landing.appearance = "ghost_line"
            landing.enabled = self.entrance_open
            landing.draw_progress = self.entrance_progress
        runtime.entities.add(self)
        runtime.entities.add(self.sketch)

    def _save(self, ctx):
        return getattr(ctx.level, "save_system", None)

    def restore_saved_completion(self, save):
        """Also used before the first render after loading a chapter."""
        if save is not None and self.kind in save.data.get("optional_bosses", ()):
            self.completed = self.entrance_open = self.entered = True
            self.entrance_progress = 1.0
            for landing in self.steps:
                landing.enabled = True
                landing.complete_drawing()

    def _near(self, player, x, y, distance=72):
        return abs(player.center_x-x) < distance and abs(player.rect.bottom-y) < 65

    def begin(self, ctx):
        """Challenge only a fully drawn deck, from its actual upper landing."""
        if (self.completed or self.encounter_active or self.entrance_progress < 1
                or ctx.player.health <= 0 or ctx.player.locked
                or not self._near(ctx.player, self.bounds[0]+50, self.ground, 110)
                or not artist_canvas_free(ctx, self)
                or not claim_artist_canvas(ctx, self)):
            return False
        from margin_guardians import GUARDIAN_CLASSES
        enemy = GUARDIAN_CLASSES[self.kind](self.bounds[1]-120, self.ground,
                                            28300+self.page)
        enemy.notebook_reveal = 0.0
        self.enemies = [enemy]
        self.encounter_active = self.boss_cue_started = True
        self.reveal = self.duel_elapsed = 0.0
        self.letter_time = 0.0
        ctx.sounds.play("pencil")
        return True

    def abort(self, ctx):
        for enemy in self.enemies:
            restore = getattr(enemy, "_restore_temporary_erases", None)
            if callable(restore):
                restore(force=True)
            getattr(enemy, "projectiles", []).clear()
        self.enemies.clear()
        self.encounter_active = self.boss_cue_started = False
        self.reveal = self.duel_elapsed = self.letter_time = 0.0
        self.hand.tool.visible = False
        release_artist_canvas(ctx, self)

    def _complete(self, ctx):
        self.completed = True
        self.abort(ctx)
        save = self._save(ctx)
        if save is not None:
            cleared = set(save.data.get("optional_bosses", ()))
            if self.kind not in cleared:
                save.data["optional_bosses"] = sorted((*cleared, self.kind))
                save.write()
        self.letter = "Rune uncovered. E to keep it; its numbers stay across pages."
        self.letter_time = 5.0
        ctx.sounds.play("sketch_found")
        ctx.particles.paper_puff(self.sketch.x, self.sketch.y, 12)
        game = getattr(ctx, "game", None)
        if game is not None:
            game.behavior.record("secret_pocket", page=self.page, kind=self.kind)

    def update(self, dt, ctx, interact=False):
        self.letter_time = max(0.0, self.letter_time-dt)
        self.hand.tool.visible = False
        if ctx.world is not self.world:
            self.abort(ctx)
            return
        self.restore_saved_completion(self._save(ctx))
        player = ctx.player
        other_fight = any(getattr(e, "encounter_active", False)
            and not getattr(e, "completed", False)
            for e in ctx.level.entities.items if e is not self)
        departed = (player.rect.bottom > self.ground+145 or
            player.center_x < self.bounds[0]-160 or player.center_x > self.bounds[1]+160)
        if player.health <= 0 or (self.encounter_active and (departed or other_fight)):
            self.abort(ctx)
            return
        if self.completed:
            release_artist_canvas(ctx, self)
            return
        if player.locked or other_fight:
            return
        if self.entrance_progress < 1:
            if not self.entrance_open:
                if self._near(player, self.base+60, 590, 52):
                    ctx.level.interaction_hint = "E / lift the loose paper corner"
                    if interact and claim_artist_canvas(ctx, self):
                        self.entrance_open = True
                        for landing in self.steps:
                            landing.enabled = True
                        ctx.sounds.play("fold")
            elif claim_artist_canvas(ctx, self):
                self.entrance_progress = min(1.0, self.entrance_progress+dt/.8)
                for landing in self.steps:
                    landing.draw_progress = self.entrance_progress
                tip = self.steps[min(4, int(self.entrance_progress*5))]
                self.hand.tool = ArtistTool("pencil", tip.visible_x2, tip.y, True)
                if self.entrance_progress >= 1:
                    release_artist_canvas(ctx, self)
            return
        if self._near(player, (self.bounds[0]+self.bounds[1])/2, self.ground, 320):
            self.entered = True
        if not self.encounter_active:
            if self._near(player, self.bounds[0]+50, self.ground, 110):
                ctx.level.interaction_hint = f"E  challenge {self.title.lower()} / optional"
                if interact:
                    self.begin(ctx)
            return
        self.duel_elapsed += dt
        if self.reveal < 1:
            if not claim_artist_canvas(ctx, self):
                return
            enemy = self.enemies[0]
            self.reveal = min(1.0, self.reveal+dt/.85)
            if self.reveal >= 1 and enemy.rect.colliderect(player.rect.inflate(8, 4)):
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

    def draw(self, surface, camera, renderer):
        if not self.entrance_open:
            x, y = camera.screen_x(self.base+60), round(578+camera.offset_y)
            pygame.draw.polygon(surface, (222,214,187), [(x-16,y),(x+16,y),(x+16,y-27)])
            pygame.draw.lines(surface, INK_LIGHT, False, [(x-16,y),(x+16,y-27),(x+16,y)], 1)
            return
        left, right = map(camera.screen_x, self.bounds)
        if right < -120 or left > surface.get_width()+120:
            return
        if self.entered and not self.encounter_active:
            renderer.doodle_text(surface, self.title, (left, self.ground-140+camera.offset_y),
                                 RED_RULE, renderer.font_small, -1)
        # Four differently colored stitches identify the optional ink above
        # the road without repeating traversal instructions.
        colors = ((154,112,69),(91,130,152),(109,100,121),(154,91,112))
        color = colors[self.page-1]
        for i in range(5):
            jitter_line(surface, color, (left+16+i*100, self.ground+camera.offset_y+6),
                (left+50+i*100, self.ground+camera.offset_y+6), 1, 28500+self.page*10+i)
        for enemy in self.enemies:
            old_clip = surface.get_clip()
            if self.reveal < 1:
                surface.set_clip(old_clip.clip(pygame.Rect(camera.screen_x(enemy.x)-100,
                    enemy.rect.top+camera.offset_y, 200, round(enemy.height*self.reveal))))
            enemy.draw(surface, camera, renderer)
            surface.set_clip(old_clip)
            if self.reveal >= 1:
                from staging import draw_enemy_read
                draw_enemy_read(surface, camera, renderer, enemy)

    def draw_overlay(self, surface, camera, renderer):
        self.hand.draw(surface, camera, renderer)
        if self.encounter_active and self.duel_elapsed < 2.8:
            from boss_presentation import draw_boss_entrance
            guardian = next((enemy for enemy in self.enemies if not enemy.dead), None)
            draw_boss_entrance(surface, renderer, self.kind, self.title,
                              self.spec.rule, self.duel_elapsed, boss=guardian)
        elif self.letter_time > 0:
            renderer.notebook.artist_note(surface, self.letter)


def add_optional_duels(runtime, discovered=()):
    spec = next((duel for duel in OPTIONAL_DUELS if duel.page == runtime.index), None)
    if spec is not None:
        left = next(left for cut, left, _ in runtime.pacing_map.pockets() if cut == spec.cut)
        OptionalGuardianPocket(runtime, left+spec.offset, spec, discovered)


__all__ = ["OPTIONAL_DUELS", "OptionalGuardianPocket", "add_optional_duels"]
