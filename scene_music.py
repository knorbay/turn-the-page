"""Original page music and twelve short, contrasting recorded boss phrases.

The historical notebook tracks remain archived in original/manifest.json;
the selected recorded boss score is verified in boss/manifest.json.
"""
from __future__ import annotations

MUSIC_PROFILES = (
    {"page": 0, "name": "Brush mountains and shrine garden",
     "palette": "koto, shamisen and piano; koto and shakuhachi in combat",
     "calm_title": "Koto with Shamisen and Piano",
     "action_title": "Japoi 3 / Koto with Shakuhachi"},
    {"page": 1, "name": "Dust town and railway",
     "palette": "the original Desert Theme and The Cowboy's Theme recordings",
     "calm_title": "Desert Theme", "action_title": "The Cowboy's Theme"},
    {"page": 2, "name": "Orbital station and planet survey",
     "palette": "the original Airy and Urgent sci-fi recordings",
     "calm_title": "Airy", "action_title": "Urgent"},
    {"page": 3, "name": "Carbon city and records office",
     "palette": "original ink and pencil motifs, airy harmony, bass and scratch rhythm",
     "calm_title": "Original notebook / Agent",
     "action_title": "Original notebook / Agent combat"},
    {"page": 4, "name": "The surviving drafts",
     "palette": "original ink and pencil motifs, airy harmony, bass and scratch rhythm",
     "calm_title": "Original notebook / Final page",
     "action_title": "Original notebook / Final page combat"},
)

BOSS_PROFILES = {
    "moon_compass": {"page": 0, "name": "Moon Ronin", "tempo": 76},
    "wanted_sketch": {"page": 1, "name": "Wanted Sketch", "tempo": 108},
    "railroad_stapler": {"page": 1, "name": "Railroad Stapler", "tempo": 108},
    "orbital_mistake": {"page": 2, "name": "Orbital Sentinel", "tempo": 68},
    "scissor_director": {"page": 3, "name": "Head of Redaction", "tempo": 66},
    "final_editor": {"page": 4, "name": "Final Editor", "tempo": 76},
    "baby_face_giant": {"page": 2, "name": "Lost Expedition giant", "tempo": 76},
    "cloud_kite": {"page": 0, "name": "Cloud Kite", "tempo": 76},
    "brass_tumbleweed": {"page": 1, "name": "Brass Tumbleweed", "tempo": 124},
    "orbit_crab": {"page": 2, "name": "Orbit Crab", "tempo": 135},
    "carbon_hound": {"page": 3, "name": "Carbon Hound", "tempo": 76},
    "draft_moth": {"page": 4, "name": "Draft Moth", "tempo": 128},
}

SELECTED_PAGE_TRACKS = {
    0: {"calm": "music/page_0_calm.ogg", "action": "music/page_0_action.ogg",
        "boss": "page_0_boss.wav"},
    1: {"calm": "music/page_1_calm.mp3", "action": "music/page_1_action.mp3",
        "boss": "page_1_boss.wav"},
    2: {"calm": "music/page_2_calm.mp3", "action": "music/page_2_action.mp3",
        "boss": "page_2_boss.wav"},
    3: {"calm": "page_3_calm.wav", "action": "page_3_action.wav",
        "boss": "page_3_boss.wav"},
    4: {"calm": "page_4_calm.wav", "action": "page_4_action.wav",
        "boss": "page_4_boss.wav"},
}

from boss_soundtrack import BOSS_RECORDINGS

SELECTED_BOSS_TRACKS = {
    item["kind"]: item["file"] for item in BOSS_RECORDINGS
}
for _recording in BOSS_RECORDINGS:
    # A source tempo is descriptive metadata, independent of AI pacing.
    BOSS_PROFILES[_recording["kind"]]["tempo"] = _recording["phrase_bpm"]
    BOSS_PROFILES[_recording["kind"]]["recording"] = _recording["title"]
    BOSS_PROFILES[_recording["kind"]]["duration_seconds"] = _recording["duration_seconds"]
BOSS_ENTRANCE_TRACKS = {}
BOSS_ENTRY_DELAYS = {}
SCORE_MANIFEST = "original/manifest.json"
BOSS_SCORE_MANIFEST = "boss/manifest.json"

_CC0 = "https://creativecommons.org/publicdomain/zero/1.0/"
_ORIGINAL_RECORDINGS = (
    ("Koto with Shamisen and Piano", "Tozan", "music/page_0_calm.ogg",
     "Midi Pack 1 — 24 New Tunes", "https://opengameart.org/content/midi-pack-1-24-new-tunes"),
    ("Japoi 3 / Koto with Shakuhachi", "Tozan", "music/page_0_action.ogg",
     "Midi Pack 1 — 24 New Tunes", "https://opengameart.org/content/midi-pack-1-24-new-tunes"),
    ("Desert Theme", "Umplix", "music/page_1_calm.mp3",
     "Wild West Music", "https://opengameart.org/content/wild-west-music"),
    ("The Cowboy's Theme", "Umplix", "music/page_1_action.mp3",
     "Wild West Music", "https://opengameart.org/content/wild-west-music"),
    ("Airy", "SRG774", "music/page_2_calm.mp3",
     "Dark Sci-Fi Audio Pack", "https://opengameart.org/content/dark-sci-fi-audio-pack"),
    ("Urgent", "SRG774", "music/page_2_action.mp3",
     "Dark Sci-Fi Audio Pack", "https://opengameart.org/content/dark-sci-fi-audio-pack"),
)
MUSIC_CREDITS = [
    {"title": title, "composer": composer, "file": file,
     "source_id": collection, "collection": collection,
     "source": source, "source_url": source,
     "license": "CC0 1.0", "license_url": _CC0,
     "credit": f'"{title}" — {composer}. {collection}, OpenGameArt. CC0 1.0.'}
    for title, composer, file, collection, source in _ORIGINAL_RECORDINGS
]
MUSIC_CREDITS.extend(BOSS_RECORDINGS)
ORIGINAL_SCORE_NOTE = {
    "tr": "4. ve 5. sayfanın keşif müzikleri oyunun özgün defter besteleridir.",
    "en": "Page 4–5 exploration music uses the game's original notebook compositions.",
}
