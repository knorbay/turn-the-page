"""Chapter casts that alternate duels, mixed patrols and larger finales.

Counts are authored along the route, rather than padded to the same three
bodies in every room.  Existing attack admission still permits only two
pressure sources, and the Artist may add one announced challenge opponent.
Boss entrances, training exercises and optional routes stay separate.
"""
from __future__ import annotations


MAX_AUTHORED_ENEMIES = 5
MAX_ADAPTED_ENEMIES = 6

# Each tuple is one wave. Small casts make their individual rules legible;
# later larger casts combine a moving front line with an aerial/ranged angle.
CHAPTER_CASTS = {
    0: {
        "first_crossout": (("ink_samurai", "goblin_scribble"),),
        "practice_crossouts": (
            ("ink_samurai", "origami_drone", "goblin_scribble"),
            ("ruler_guard", "lantern_yokai"),
        ),
        "bamboo_static": (
            ("fold_duelist", "gutter_lantern", "goblin_scribble"),
            ("origami_drone", "goblin_scribble", "ruler_guard", "fold_duelist"),
            ("ruler_guard", "ink_samurai", "lantern_yokai", "goblin_scribble", "origami_drone"),
        ),
    },
    1: {
        "pistol_margin_drill": (("ink_outlaw", "tumbleweed_thing"),),
        "coffee_crossfire": (
            ("ink_outlaw", "ticket_vulture", "tumbleweed_thing", "cactus_gunner"),
            ("tumbleweed_thing", "rake_cactus"),
            ("ink_outlaw", "ticket_vulture", "tumbleweed_thing", "rake_cactus", "goblin_scribble"),
        ),
    },
    2: {
        "safe_pocket_counterattack": (("star_scout", "moon_bot", "comet_hound"),),
        "orbital_debris": (
            ("eraser_brute", "crumpled_one", "comet_hound", "star_scout"),
            ("ember_hound", "satellite_sentry"),
        ),
        "eraser_calibration": (
            ("eraser_brute", "doodle_turret"),
            ("moon_bot", "ember_hound", "satellite_sentry", "comet_hound", "star_scout"),
            ("star_scout", "moon_bot", "comet_hound"),
        ),
    },
    3: {
        "agent_checkpoint": (("redaction_agent", "ink_clone"),),
        "carbon_crossfire": (
            ("redaction_agent", "folder_glider", "file_runner"),
            ("margin_sniper", "ink_clone", "file_runner", "ruler_guard"),
        ),
        "redacted_rooftops": (
            ("folder_glider", "redaction_agent", "ink_clone", "file_runner"),
            ("eraser_brute", "file_runner"),
            ("split_lantern", "file_runner", "ink_clone", "ruler_guard", "folder_glider"),
        ),
        "office_ambush": (
            ("redaction_agent", "crumpled_one"),
            ("folder_glider", "doodle_turret", "ink_clone", "file_runner"),
        ),
        "evidence_vault": (("redaction_agent", "carbon_stamper", "folder_glider"),),
    },
    4: {
        "last_lesson": (("ink_samurai", "redaction_agent", "gutter_lantern"),),
        "erased_answers": (
            ("eraser_brute", "doodle_turret", "ink_clone", "file_runner"),
            ("satellite_sentry", "redaction_agent"),
        ),
        "margin_revolt": (
            ("rake_cactus", "tumbleweed_thing", "ticket_vulture"),
            ("redaction_agent", "file_runner", "folder_glider", "ink_clone", "carbon_stamper"),
            ("ruler_guard", "fold_duelist", "goblin_scribble", "gutter_lantern"),
        ),
        "the_last_crossout": (
            ("ink_clone", "moon_bot"),
            ("margin_sniper", "ember_hound", "fold_duelist", "folder_glider", "redaction_agent"),
        ),
        "unfinished_corridor": (("fold_duelist", "redaction_agent", "ruler_guard"),),
    },
}


def compose_encounter_variety(runtime):
    """Apply final casts after all room-coordinate and cover edits are done."""
    if getattr(runtime, "encounter_variety_applied", False):
        return runtime
    runtime.encounter_variety_applied = True
    casts = CHAPTER_CASTS[runtime.index]
    for arena in runtime.entities.items:
        waves = casts.get(getattr(arena, "arena_id", ""))
        if waves is None or getattr(arena, "boss", False):
            continue
        specs = []
        span = arena.end_x-arena.start_x
        for wave, kinds in enumerate(waves):
            count = len(kinds)
            if not 2 <= count <= MAX_AUTHORED_ENEMIES:
                raise ValueError("A chapter cast must contain two to five distinct drawings")
            if wave == 0:
                # The opening is readable in the approach camera. More bodies
                # get more physical drawing space rather than one spawn pile.
                left = 260 if count >= 4 else 270
                cast_span = {2: 220, 3: 320, 4: 330, 5: 400}[count]
            else:
                cast_span = min(840, 190*(count-1), span*.48)
                center = min(span*.5, 820)+(70 if wave % 2 == 0 else 0)
                left = center-cast_span*.5
            for index, kind in enumerate(kinds):
                lane = count-1-index if wave % 2 else index
                specs.append({"wave": wave, "kind": kind,
                              "offset": round(left+lane*cast_span/(count-1))})
        arena.enemy_specs = specs
        arena.wave_ids = list(range(len(waves)))
        arena.authored_wave_count = len(waves)
        arena.authored_max_enemies = MAX_AUTHORED_ENEMIES
        arena.adapted_max_enemies = MAX_ADAPTED_ENEMIES
    return runtime
