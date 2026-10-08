"""Room scale and encounter rhythm for the living notebook campaign.

The room additions are authored in the same coordinate space as the original
route.  They join the campaign's monotonic map, so a wider arena carries its
exit, retry points, all later discoveries and drawing triggers with it.
"""
from __future__ import annotations

from collections import defaultdict


# (physical room width, number of authored waves).  A short teaching duel,
# combinations, and three-part gauntlets use different rhythms on each page.
ROOM_LAYOUTS = {
    "first_crossout": (1100, 1),
    "practice_crossouts": (1500, 2),
    "bamboo_static": (1800, 3),
    "moon_gate_duel": (2400, 1),
    "pistol_margin_drill": (1250, 1),
    "coffee_crossfire": (1800, 3),
    "marker_margin_trial": (2300, 1),
    "midnight_train": (2600, 1),
    "safe_pocket_counterattack": (1350, 1),
    "orbital_debris": (1850, 2),
    "zero_garden": (2450, 1),
    "eraser_calibration": (1900, 3),
    "baby_face_interlude": (2200, 1),
    "agent_checkpoint": (1400, 1),
    "carbon_crossfire": (1800, 2),
    "redacted_rooftops": (1900, 3),
    "office_ambush": (1800, 2),
    "evidence_vault": (1750, 1),
    "scissor_office": (2700, 1),
    "last_lesson": (1500, 1),
    "erased_answers": (1800, 2),
    "margin_revolt": (1950, 3),
    "the_last_crossout": (1900, 2),
    "unfinished_corridor": (1600, 1),
    "final_margin_revision": (2800, 1),
}

BOSS_KINDS = {
    "moon_gate_duel": "moon_compass",
    "marker_margin_trial": "wanted_sketch",
    "midnight_train": "railroad_stapler",
    "zero_garden": "orbital_mistake",
    "scissor_office": "scissor_director",
    "final_margin_revision": "final_editor",
}

# Three bodies fill ordinary rooms without adding another wave or shrinking
# movement space. Four-body combinations belong to earlier/middle phases;
# every last wave leaves room for the Artist's existing +1 skill response.
# A close or moving threat joins the guns/area denial instead of multiplying
# the same firing line. The pressure coordinator still owns warning timing.
NORMAL_WAVES = {
    # Collage: grounded blades, jumping goblins and occasional floating ink.
    "first_crossout": (("ink_samurai", "goblin_scribble", "ruler_guard"),),
    "practice_crossouts": (
        ("ink_samurai", "origami_drone", "goblin_scribble"),
        ("goblin_scribble", "ruler_guard", "lantern_yokai"),
    ),
    "bamboo_static": (
        ("fold_duelist", "gutter_lantern", "goblin_scribble"),
        ("origami_drone", "goblin_scribble", "ruler_guard", "fold_duelist"),
        ("ruler_guard", "ink_samurai", "lantern_yokai"),
    ),
    # Western: quickdraws punctuated by rolling paper and diving tickets.
    "pistol_margin_drill": (("ink_outlaw", "tumbleweed_thing", "ticket_vulture"),),
    "coffee_crossfire": (
        ("ink_outlaw", "ticket_vulture", "tumbleweed_thing"),
        ("tumbleweed_thing", "rake_cactus", "ticket_vulture", "goblin_scribble"),
        ("goblin_scribble", "ink_outlaw", "tumbleweed_thing"),
    ),
    # Space: a ground pursuer keeps airborne locks from becoming a gun row.
    "safe_pocket_counterattack": (("star_scout", "moon_bot", "comet_hound"),),
    "orbital_debris": (
        ("eraser_brute", "crumpled_one", "comet_hound", "star_scout"),
        ("ember_hound", "moon_bot", "satellite_sentry"),
    ),
    "eraser_calibration": (
        ("eraser_brute", "doodle_turret", "comet_hound"),
        ("moon_bot", "ember_hound", "satellite_sentry"),
        ("star_scout", "moon_bot", "comet_hound"),
    ),
    # Office: runners/gliders cross the agent's lane; the vault stays one room.
    "agent_checkpoint": (("redaction_agent", "ink_clone", "ruler_guard"),),
    "carbon_crossfire": (
        ("redaction_agent", "ruler_guard", "folder_glider", "file_runner"),
        ("margin_sniper", "ink_clone", "file_runner"),
    ),
    "redacted_rooftops": (
        ("folder_glider", "redaction_agent", "ink_clone"),
        ("ink_clone", "eraser_brute", "file_runner", "ruler_guard"),
        ("split_lantern", "file_runner", "ink_clone"),
    ),
    "office_ambush": (
        ("redaction_agent", "crumpled_one", "ink_clone", "folder_glider"),
        ("folder_glider", "doodle_turret", "ink_clone"),
    ),
    "evidence_vault": (("redaction_agent", "carbon_stamper", "folder_glider"),),
    # Final page recalls distinct earlier combinations, not extra boss guards.
    "last_lesson": (("ink_samurai", "redaction_agent", "gutter_lantern"),),
    "erased_answers": (
        ("eraser_brute", "doodle_turret", "ink_clone", "file_runner"),
        ("satellite_sentry", "redaction_agent", "ink_clone"),
    ),
    "margin_revolt": (
        ("rake_cactus", "tumbleweed_thing", "ticket_vulture", "ink_clone"),
        ("redaction_agent", "file_runner", "folder_glider"),
        ("ruler_guard", "fold_duelist", "goblin_scribble"),
    ),
    "the_last_crossout": (
        ("ink_clone", "redaction_agent", "moon_bot", "folder_glider"),
        ("margin_sniper", "ember_hound", "fold_duelist"),
    ),
    "unfinished_corridor": (("fold_duelist", "redaction_agent", "ruler_guard"),),
}


def prepare_encounters(runtime):
    """Author new room widths before the one shared route-coordinate pass."""
    if getattr(runtime, "encounter_revision_prepared", False):
        return runtime
    runtime.encounter_revision_prepared = True
    insertions = []
    raised = []
    for arena in runtime.entities.items:
        if not getattr(arena, "is_combat_arena", False):
            continue
        desired, waves = ROOM_LAYOUTS[arena.arena_id]
        old_width = arena.end_x-arena.start_x
        arena.authored_width = old_width
        arena.room_layout_width = desired
        arena.authored_wave_count = waves
        if desired > old_width:
            # A midpoint insertion stretches the continuous safety floor,
            # while every point after the room is moved by the same amount.
            insertions.append(((arena.start_x+arena.end_x)*.5, desired-old_width))
        for platform in runtime.world.platforms:
            if (platform.layer == arena.layer and platform.thickness < 45
                    and platform.y < 570
                    and arena.start_x-5 <= platform.x1
                    and platform.x2 <= arena.end_x+5):
                raised.append((platform, arena,
                    ((platform.x1+platform.x2)*.5-arena.start_x)/old_width,
                    platform.x2-platform.x1))
        if arena.arena_id in BOSS_KINDS:
            # The room opens directly on its named boss: no normal doormen.
            arena.enemy_specs = [{"wave": 0, "kind": BOSS_KINDS[arena.arena_id]}]
        elif arena.arena_id in NORMAL_WAVES:
            arena.enemy_specs = [
                {"wave": wave, "kind": kind}
                for wave, kinds in enumerate(NORMAL_WAVES[arena.arena_id])
                for kind in kinds
            ]
        arena.wave_ids = sorted({int(spec.get("wave", 0))
                                 for spec in arena.enemy_specs})
    runtime.encounter_insertions = tuple(sorted(insertions))
    runtime.encounter_raised_platforms = raised
    return runtime


def finish_encounters(runtime):
    """Keep short ledges short, with open ground and separated spawn lanes."""
    if getattr(runtime, "encounter_revision_applied", False):
        return runtime
    runtime.encounter_revision_applied = True
    # A 190px cover must not become a 900px ceiling when its room expands.
    for platform, arena, center_fraction, width in runtime.encounter_raised_platforms:
        center = arena.start_x+center_fraction*(arena.end_x-arena.start_x)
        platform.x1, platform.x2 = center-width*.5, center+width*.5
        # Existing owned holes, if any, cannot refer to pre-restyled cover.
        platform.erased[:] = []
        platform._owned_erases.clear()
        platform._pending_restores[:] = []
    del runtime.encounter_raised_platforms

    page_style = ("torn_edge", "ruler_line", "construction", "carbon", "handwriting")[runtime.index]
    arenas = [e for e in runtime.entities.items if getattr(e, "is_combat_arena", False)]
    for room_index, arena in enumerate(arenas):
        span = arena.end_x-arena.start_x
        groups = defaultdict(list)
        for spec in arena.enemy_specs:
            groups[int(spec.get("wave", 0))].append(spec)
        for wave, specs in groups.items():
            count = len(specs)
            normal_group = arena.arena_id in NORMAL_WAVES and count > 1
            if normal_group:
                if wave == 0:
                    # At the gate, the following camera sees about 600px
                    # ahead. Keep the whole opening cast in that approach,
                    # with 110/160px between centres rather than one pile.
                    group_left = 260 if count == 4 else 270
                    group_span = 330 if count == 4 else 320
                else:
                    # Once the player has entered the fight, later phases
                    # use a wider combination and alternate the cast order.
                    group_span = min(720 if count == 4 else 640, span*.44)
                    center = min(span*.5, 800)+(60 if wave % 2 == 0 else 0)
                    group_left = center-group_span*.5
            for index, spec in enumerate(specs):
                spec.pop("x", None)
                # Bosses have a long readable approach; normal threats span
                # the actual room in separate, evenly spaced drawing lanes.
                if arena.arena_id in BOSS_KINDS or arena.arena_id == "baby_face_interlude":
                    fraction = .60
                elif normal_group:
                    lane = count-1-index if wave % 2 else index
                    spec["offset"] = round(group_left+lane*group_span/(count-1))
                    continue
                elif count == 1:
                    fraction = (.53, .67, .41)[wave % 3]
                else:
                    fraction = .34+index*.48/(count-1)
                    if wave % 2:
                        fraction = .82-index*.48/(count-1)
                spec["offset"] = round(span*fraction)
        # Replace the old repeated flank recipe with room-specific clear
        # approaches.  Raised cover from Artist beats remains a real drawing.
        runtime.world.platforms[:] = [p for p in runtime.world.platforms
            if not (p.name.startswith("quality_flank_"+arena.arena_id+"_")
                    or p.name == "quality_high_"+arena.arena_id)]
        if arena.boss or arena.arena_id == "baby_face_interlude":
            layout = ((.12, 505, 205), (.78, 505, 205))
        elif room_index % 3 == 0:
            layout = ((.18, 515, 190), (.72, 495, 210))
        elif room_index % 3 == 1:
            layout = ((.17, 510, 190), (.60, 455, 195), (.81, 510, 190))
        else:
            layout = ((.21, 500, 215), (.76, 500, 215))
        for index, (fraction, y, width) in enumerate(layout):
            x = arena.start_x+span*fraction
            platform = runtime.world.add(x, min(x+width, arena.end_x-110), y, 10,
                f"room_angle_{arena.arena_id}_{index}",
                27500+runtime.index*100+room_index*5+index, arena.layer)
            platform.appearance = page_style
        arena.lane_layout = layout
    runtime.checkpoints.sort(key=lambda cp: float(cp.trigger_x or cp.x))
    return runtime


__all__ = ["ROOM_LAYOUTS", "BOSS_KINDS", "prepare_encounters", "finish_encounters"]
