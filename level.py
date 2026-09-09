from __future__ import annotations

import math
import pygame

from chapters import Checkpoint, build_chapter
from scripted_events import ArtistTool, EventContext
from settings import INK, INK_LIGHT
from sketches import apply_sketch_rewards, collection_message


class Level:
    """Campaign chapter runtime, stable checkpoints, and scripted-paper lifecycle."""

    def __init__(self, save_system=None, chapter_index=0, checkpoint_id="start"):
        self.save_system = save_system
        self.chapter_index = chapter_index
        self.flags: set[str] = set()
        self.interaction_hint = ""
        self.toast = ""
        self.toast_time = 0.0
        self.fold_progress = 0.0
        self.chapter_complete = False
        self.respawn_timer = 0.0
        self.respawn_committed = False
        self.respawn_duration = 1.55
        self.respawn_cause = "unknown"
        self.respawn_arena = ""
        self.respawn_message = ""
        self.respawn_variant = "clean"
        self.respawn_origin = (0.0, 0.0)
        self.respawn_sound_played = False
        self.completion_recorded = False
        self.current_checkpoint = checkpoint_id
        self.load_chapter(chapter_index, checkpoint_id)

    @property
    def world(self):
        return self.runtime.world

    @property
    def director(self):
        return self.runtime.director

    @property
    def entities(self):
        return self.runtime.entities

    @property
    def title(self):
        return self.runtime.title

    @property
    def subtitle(self):
        return self.runtime.subtitle

    def load_chapter(self, index, checkpoint_id="start", player=None, camera=None):
        self.chapter_index = max(0, min(4, int(index)))
        secrets = self.save_system.data["secrets"] if self.save_system else []
        self.runtime = build_chapter(self.chapter_index, secrets)
        self.flags = set(getattr(self.runtime, "initial_flags", ()))
        self.interaction_hint = ""
        self.toast = ""
        self.toast_time = 0
        self.fold_progress = 0
        self.chapter_complete = False
        self.completion_recorded = False
        valid_ids = {cp.checkpoint_id for cp in self.runtime.checkpoints}
        self.current_checkpoint = checkpoint_id if checkpoint_id in valid_ids else "start"
        self._apply_checkpoint_snapshot(self.current_checkpoint)
        cp = self.checkpoint_spec(self.current_checkpoint)
        if player is not None:
            player.x, player.y = cp.x, cp.y
            player.vx = player.vy = 0
            player.facing = cp.facing
            player.release_all_locks()
            player.draw_amount = 1 if self.chapter_index > 0 or cp.checkpoint_id != "start" else 0
            player.redraw_alpha = 1
            if self.respawn_committed:
                player.redraw_variant = self.respawn_variant
            player.page_style = {
                0: "ronin", 1: "cowboy", 2: "astronaut",
                3: "ink_agent", 4: "bad_drawing",
            }.get(self.chapter_index, "plain")
            if self.chapter_index in (0, 1, 2, 3, 4) and cp.checkpoint_id == "start":
                player.page_style = "plain"
            player.health = player.max_health
            player.health_restore_flash = 0.0
            player.hurt_flash = 0.0
            player.invulnerable = 0
            apply_sketch_rewards(player, secrets)
        if camera is not None:
            camera.x = camera.target_x = max(0, cp.x - 360)
            camera.script_target = None
            camera.vertical_offset = 0
        self.world.active_layer = cp.layer
        weapons = getattr(self, "weapons", None)
        if weapons is not None:
            weapons.projectiles.clear()
            weapons.impacts.clear()
            weapons.melee = None
        self.page_title_time = 4.2
        return cp

    def checkpoint_spec(self, checkpoint_id=None):
        checkpoint_id = checkpoint_id or self.current_checkpoint
        return next((cp for cp in self.runtime.checkpoints if cp.checkpoint_id == checkpoint_id),
                    self.runtime.checkpoints[0])

    def set_checkpoint(self, checkpoint_id, play_seconds=0):
        if checkpoint_id == self.current_checkpoint:
            return
        cp = self.checkpoint_spec(checkpoint_id)
        if cp.checkpoint_id != checkpoint_id:
            return
        self.current_checkpoint = checkpoint_id
        self.toast = "checkpoint — redrawn here"
        self.toast_time = 2.0
        if self.save_system:
            weapons = getattr(self, "weapons", None)
            if weapons is not None:
                snapshot = weapons.snapshot()
                self.save_system.update_combat(snapshot["unlocked"], snapshot["current_id"],
                                               snapshot["ammo"])
            self.save_system.checkpoint(self.chapter_index, checkpoint_id, play_seconds)
        game = getattr(self, "game", None)
        if game is not None:
            game.persist_behavior(write=False)

    def discover_secret(self, secret_id, caption):
        is_new = self.save_system.discover(secret_id) if self.save_system else True
        if is_new:
            self.toast = collection_message(secret_id)
            self.toast_time = 5.5
            game = getattr(self, "game", None)
            if game is not None:
                apply_sketch_rewards(game.player, self.save_system.data.get("secrets", [])
                                     if self.save_system else [secret_id])
                game.behavior.record("lost_sketch", sketch=secret_id,
                                     page=self.chapter_index)
                game.persist_behavior(write=True)

    def context(self, player, camera, particles, sounds):
        return EventContext(player, self.world, camera, particles, sounds, self, self.director,
                            getattr(self, "weapons", None), getattr(self, "game", None))

    def update(self, dt, player, camera, particles, sounds, interact=False, play_seconds=0):
        self.interaction_hint = ""
        self.toast_time = max(0, self.toast_time - dt)
        self.page_title_time = max(0, self.page_title_time - dt)
        if self.respawn_timer > 0:
            return self._update_respawn(dt, player, camera, particles, sounds)
        if player.health <= 0:
            cause, _ = self._active_threat_context(player)
            self.begin_respawn(player, cause, particles, sounds)
            return

        ctx = self.context(player, camera, particles, sounds)
        self.director.update(dt, ctx)
        for event in self.runtime.live_events:
            event.update(dt, ctx)
        for entity in self.entities.items:
            layer = getattr(entity, "layer", self.world.active_layer)
            if layer == self.world.active_layer and getattr(entity, "active", True):
                entity.update(dt, ctx, interact)

        if self.director.tool.visible:
            player.look_target = (self.director.tool.x, self.director.tool.y)
        else:
            player.look_target = None

        for cp in self.runtime.checkpoints:
            if (cp.trigger_x and player.x >= cp.trigger_x and player.on_ground and
                    cp.layer == self.world.active_layer and all(flag in self.flags for flag in cp.requires) and
                    self._checkpoint_after(cp, self.current_checkpoint)):
                self.set_checkpoint(cp.checkpoint_id, play_seconds)

        dangerous = [z for z in self.world.material_at(player.rect) if z.kind in ("ink_hazard", "ink_wall")]
        if dangerous:
            sounds.play("ink")
            self.begin_respawn(player, dangerous[0].kind, particles, sounds)
        if player.y > 850:
            self.begin_respawn(player, "fall", particles, sounds)
        if player.health <= 0:
            cause, _ = self._active_threat_context(player)
            self.begin_respawn(player, cause, particles, sounds)
        mandatory_ready = all(getattr(entity, "completed", False)
                              for entity in self.entities.items if getattr(entity, "mandatory", False))
        if player.x >= self.runtime.end_x and player.on_ground and mandatory_ready:
            self.chapter_complete = True

    def _checkpoint_after(self, candidate: Checkpoint, current_id):
        ids = [cp.checkpoint_id for cp in self.runtime.checkpoints]
        return ids.index(candidate.checkpoint_id) > ids.index(current_id)

    def _active_threat_context(self, player):
        arena = next((entity for entity in self.entities.items
                      if getattr(entity, "is_combat_arena", False)
                      and getattr(entity, "encounter_active", False)), None)
        if arena is None:
            return "unknown", ""
        live = [enemy for enemy in getattr(arena, "enemies", ())
                if not getattr(enemy, "dead", False)]
        nearest = min(live, key=lambda enemy: abs(getattr(enemy, "x", 0) - player.center_x),
                      default=None)
        cause = getattr(nearest, "kind", None) or getattr(arena, "arena_id", "enemy")
        return str(cause), str(getattr(arena, "arena_id", ""))

    def begin_respawn(self, player, cause=None, particles=None, sounds=None):
        if self.respawn_timer > 0:
            return
        inferred, arena = self._active_threat_context(player)
        self.respawn_cause = str(cause or inferred or "unknown")
        self.respawn_arena = arena
        self.respawn_timer = self.respawn_duration
        self.respawn_committed = False
        self.respawn_sound_played = False
        self.respawn_origin = (player.center_x, player.rect.centery)
        game = getattr(self, "game", None)
        if game is not None:
            game.behavior.record("death", cause=self.respawn_cause,
                                 arena=self.respawn_arena,
                                 weapon=getattr(getattr(self, "weapons", None), "current_id", ""),
                                 page=self.chapter_index)
            self.respawn_message = game.behavior.death_reaction(
                self.respawn_cause,
                getattr(getattr(self, "weapons", None), "current_id", ""),
                self.respawn_arena,
            )
            self.respawn_variant = game.behavior.redraw_variant()
            game.persist_behavior(write=True)
        else:
            self.respawn_message = "Again, then."
            self.respawn_variant = "clean"
        if particles is not None:
            particles.enemy_break(player.center_x, player.rect.centery, 1, 22)
            particles.paper_puff(player.center_x, player.rect.bottom, 14)
        if sounds is not None:
            sounds.play("paper_break")
            combat_audio = getattr(sounds, "set_combat", None)
            if callable(combat_audio):
                combat_audio(False)
        player.acquire_lock("respawn")

    def _update_respawn(self, dt, player, camera, particles=None, sounds=None):
        self.director.tool.visible = False
        self.respawn_timer -= dt
        elapsed = self.respawn_duration - max(0, self.respawn_timer)
        collapse_end = .34
        commit_at = .50
        redraw_end = 1.27
        if elapsed < collapse_end:
            progress = elapsed / collapse_end
            player.redraw_alpha = max(0, 1 - progress)
            player.draw_amount = max(.12, 1 - progress * .55)
        elif elapsed < commit_at:
            player.redraw_alpha = 0
            player.draw_amount = 0
        elif not self.respawn_committed:
            self.respawn_committed = True
            self.load_chapter(self.chapter_index, self.current_checkpoint, player, camera)
            player.acquire_lock("respawn")
            player.redraw_alpha = 0
            player.draw_amount = 0
            player.redraw_variant = self.respawn_variant
            if sounds is not None:
                sounds.play("redraw")
            self.respawn_sound_played = True
        else:
            progress = min(1.0, max(0.0, (elapsed - commit_at) / (redraw_end - commit_at)))
            eased = progress * progress * (3 - 2 * progress)
            player.redraw_alpha = min(1, .25 + eased * .75)
            player.draw_amount = eased
            tip_x, tip_y = player.redraw_tip()
            self.director.tool = ArtistTool("pencil", tip_x, tip_y,
                                            True, -.64, 1.15)
            self.director.write(player.x + 62, max(330, player.y - 86),
                                self.respawn_message, min(1, progress * 1.55))
            if particles is not None and int(elapsed * 42) % 3 == 0:
                particles.pencil_speck(tip_x, tip_y)
        if self.respawn_timer <= 0:
            self.respawn_timer = 0
            player.redraw_alpha = 1
            player.draw_amount = 1
            player.release_lock("respawn")

    def draw_artist_overlay(self, surface, camera, renderer):
        """Death debris remains visible while the new figure is stroked in."""
        if self.respawn_timer <= 0:
            return
        elapsed = self.respawn_duration - self.respawn_timer
        if elapsed > .52:
            return
        x = camera.screen_x(self.respawn_origin[0])
        y = round(self.respawn_origin[1] + camera.offset_y)
        fade = max(0.0, 1 - elapsed / .52)
        color = tuple(round(c * (.55 + .45 * fade)) for c in INK_LIGHT)
        for index in range(9):
            angle = index * math.tau / 9 + .25
            reach = 12 + index % 4 * 8 + elapsed * 32
            start = (x + math.cos(angle) * 4, y + math.sin(angle) * 4)
            end = (x + math.cos(angle) * reach, y + math.sin(angle) * reach * .72)
            pygame.draw.line(surface, color, start, end, 1 + (index % 3 == 0))
        renderer.doodle_text(surface, "x", (x - 5, y - 13), INK, renderer.font_small,
                             -8)

    def restart_chapter(self, player, camera):
        self.current_checkpoint = "start"
        self.load_chapter(self.chapter_index, "start", player, camera)
        if self.save_system:
            self.save_system.checkpoint(self.chapter_index, "start")

    def next_chapter(self, player, camera, play_seconds=0):
        if self.chapter_index >= 4:
            return False
        next_index = self.chapter_index + 1
        self.load_chapter(next_index, "start", player, camera)
        if self.save_system:
            self.save_system.checkpoint(next_index, "start", play_seconds)
        return True

    def _apply_checkpoint_snapshot(self, checkpoint_id):
        cp = self.checkpoint_spec(checkpoint_id)
        spawn_x = cp.x
        # A checkpoint is a stable snapshot, so its own prerequisites are
        # already true when loading it from disk or after a redraw.
        self.flags.update(cp.requires)
        if self.chapter_index == 0:
            if checkpoint_id != "start":
                self.flags.add("player_drawn")
                self._finish_director("player_drawn")
            if spawn_x >= 2860:
                for name in ("first_step", "second_step", "third_step", "first_bridge"):
                    p = self.world.platform_named(name)
                    if p: p.draw_progress = 1
                for event in self.director.events:
                    event.done = True
        elif self.chapter_index == 1:
            if spawn_x >= 2110:
                for name in ("ruled_line_1", "ruled_line_2", "ruled_line_3"):
                    self.world.platform_named(name).draw_progress = 1
            if spawn_x >= 6660:
                self.world.platform_named("margin_bridge").draw_progress = 1
                for event in self.director.events:
                    event.done = True
        elif self.chapter_index == 2:
            if getattr(self.runtime, "page_style", "") == "space_age":
                for name in ("wrong_support", "correction_bridge", "circuit_gate",
                             "fixed_step_0", "fixed_step_1", "fixed_step_2"):
                    platform = self.world.platform_named(name)
                    if platform is not None:
                        platform.draw_progress = 1
                        platform.erased[:] = []
            else:
                if spawn_x >= 2460:
                    self.world.platform_named("wrong_support").erase(1320, 1780)
                    for i in range(3):
                        self.world.platform_named(f"fixed_step_{i}").draw_progress = 1
                    self.flags.update(("support_erased", "weight_landed", "bad_draft_fixed"))
                if spawn_x >= 4250:
                    self.world.platform_named("correction_bridge").erase(2920, 4050)
                    self.flags.add("bridge_correction")
                    for event in self.runtime.live_events:
                        if getattr(event, "name", "") == "bridge_correction":
                            event.done = True
                if spawn_x >= 6350:
                    self.world.platform_named("circuit_gate").draw_progress = 1
                    self.flags.add("circuit_complete")
                    for event in self.director.events:
                        event.done = True
        elif self.chapter_index == 3 and self.runtime.page_style != "carbon_agent":
            self.world.active_layer = cp.layer
            if cp.layer == 0 and spawn_x >= 5630:
                self.world.platform_named("fold_bridge").draw_progress = 1
                self.fold_progress = 1
                self.flags.add("page_folded")
                for event in self.director.events:
                    event.done = True
        elif self.chapter_index == 4 and self.runtime.page_style != "last_draft":
            if spawn_x >= 2150:
                for i in range(6):
                    self.world.platform_named(f"final_draw_{i}").draw_progress = 1
            if spawn_x >= 6300:
                self.world.platform_named("last_line").draw_progress = 1
                for event in self.director.events:
                    event.done = True
        checkpoint_requires = set(cp.requires)
        if self.chapter_index in (0, 1, 2, 3, 4) and checkpoint_id != "start":
            self._finish_director(f"page_{self.chapter_index}_costume")
        for entity in self.entities.items:
            gate = getattr(entity, "gate", None)
            flag = getattr(entity, "arena_id", getattr(entity, "puzzle_id", None))
            passed = gate is not None and spawn_x > gate.x2 + 35
            if gate is not None and (passed or flag in checkpoint_requires):
                entity.completed = True
                gate.enabled = False
                entrance = getattr(entity, "entrance_gate", None)
                if entrance is not None:
                    entrance.enabled = False
                entity.encounter_active = False if hasattr(entity, "encounter_active") else getattr(entity, "active", True)
                if flag:
                    self.flags.add(flag)

    def _finish_director(self, name):
        for event in self.director.events:
            if event.name == name:
                event.done = True

    def draw_entities(self, surface, camera, renderer):
        for entity in self.entities.items:
            layer = getattr(entity, "layer", self.world.active_layer)
            if layer == self.world.active_layer and getattr(entity, "active", True):
                entity.draw(surface, camera, renderer)
