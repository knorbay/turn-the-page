"""Prepare reviewed licensed recordings; never used by the game at runtime.

Usage: python tools/import_audio_revision.py --sources /path/to/audio-source
The development tool uses numpy and the libsndfile bundled with pygame on macOS.
Source archives and author downloads are listed in assets/audio/THIRD_PARTY.md.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import wave

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import numpy as np
import pygame

ROOT = Path(__file__).resolve().parents[1]
RATE = 22050


class SoundInfo(ctypes.Structure):
    _fields_ = [("frames", ctypes.c_int64), ("samplerate", ctypes.c_int),
                ("channels", ctypes.c_int), ("format", ctypes.c_int),
                ("sections", ctypes.c_int), ("seekable", ctypes.c_int)]


def decoder():
    bundled = list((Path(pygame.__file__).parent / ".dylibs").glob("libsndfile.*.dylib"))
    library = ctypes.CDLL(str(bundled[0]) if bundled else ctypes.util.find_library("sndfile"))
    library.sf_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.POINTER(SoundInfo)]
    library.sf_open.restype = ctypes.c_void_p
    library.sf_readf_float.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_float), ctypes.c_int64]
    library.sf_readf_float.restype = ctypes.c_int64
    library.sf_close.argtypes = [ctypes.c_void_p]
    return library


def read(library, path):
    info = SoundInfo()
    handle = library.sf_open(str(path).encode(), 0x10, ctypes.byref(info))
    if not handle:
        if path.suffix == '.mp3':
            if not pygame.mixer.get_init():pygame.mixer.init(RATE,-16,1)
            sound = pygame.mixer.Sound(str(path))
            samples = np.frombuffer(sound.get_raw(),dtype=np.int16).astype(np.float32)/32767
            if len(samples):return samples
        raise ValueError(f"Cannot decode {path}")
    audio = np.empty(info.frames * info.channels, dtype=np.float32)
    try:
        frames = library.sf_readf_float(handle, audio.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), info.frames)
    finally:
        library.sf_close(handle)
    audio = audio[:frames * info.channels].reshape((-1, info.channels)).mean(axis=1)
    if info.samplerate != RATE:
        count = round(len(audio) * RATE / info.samplerate)
        audio = np.interp(np.arange(count) * info.samplerate / RATE,
                          np.arange(len(audio)), audio).astype(np.float32)
    return audio


def prepare(audio, music=False):
    if not len(audio):
        raise ValueError("Empty decoded audio")
    audio = audio.astype(np.float64)
    audio -= audio.mean()
    # The distant range recordings have long background-noise heads. Cue
    # slices below select actual single attacks; trim only sub-audible edges.
    audible = np.flatnonzero(abs(audio) > (.002 if music else .008))
    if len(audible):
        pad = round(RATE * (.006 if music else .002))
        audio = audio[max(0, audible[0] - pad):min(len(audio), audible[-1] + pad + 1)]
    peak = float(np.max(abs(audio)))
    rms = float(np.sqrt(np.mean(audio * audio)))
    gain = min((.78 if music else .68) / max(peak, 1e-8),
               (.16 if music else .14) / max(rms, 1e-8))
    audio *= gain
    fade = min(len(audio) // 2, round(RATE * (.009 if music else .002)))
    if fade:
        audio[:fade] *= np.linspace(0, 1, fade)
        audio[-fade:] *= np.linspace(1, 0, fade)
    return np.rint(audio * 32767).astype(np.int16)


def write(path, audio):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(RATE)
        handle.writeframes(audio.tobytes())


def run(source):
    library = decoder()
    asset_root = ROOT / "assets/audio"
    cache = {}
    manifest = {"prepared_on": "2026-10-02", "format": "22050 Hz mono PCM16",
                "processing": "single attack selection; DC removal; energy/peak matching; edge taper",
                "boss_tracks": {}, "recorded_banks": {}}

    def load(name):
        path = source / name
        if name not in cache:
            cache[name] = read(library, path)
        return cache[name]

    def record(name, inputs, starts=None, duration=None, layer=None):
        files = []
        for index, input_name in enumerate(inputs):
            samples = load(input_name)
            start = starts[index] if starts else 0
            begin = round(start * RATE)
            end = round((start + duration) * RATE) if duration else len(samples)
            audio = samples[begin:end].copy()
            if layer:
                companion = load(layer)[:len(audio)]
                audio[:len(companion)] += companion * .24
            relative = f"recorded/combat/{name}_{index + 1}.wav"
            output = asset_root / relative
            pcm = prepare(audio)
            write(output, pcm)
            files.append(relative)
            manifest["recorded_banks"].setdefault(name, []).append({
                "file": relative, "source": input_name, "start": start,
                "duration": len(pcm) / RATE, "layer": layer,
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            })
        return tuple(files)

    impact = lambda stem, count=3: [f"impact-sounds/Audio/{stem}_{i:03}.ogg" for i in range(count)]
    sci = lambda stem, count=3: [f"sci-fi-sounds/Audio/{stem}_{i:03}.ogg" for i in range(count)]
    rpg = lambda stem: f"rpg-audio/Audio/{stem}.ogg"
    banks = {}
    banks["page"] = record("page", [rpg(f"bookFlip{i}") for i in (1, 2, 3)])
    banks["fold"] = record("fold", [rpg("bookClose"), rpg("cloth2"), rpg("cloth4")])
    banks["reload"] = record("reload", ["gunreload1.wav", "shotguncock.wav", rpg("metalLatch")])
    banks["katana_draw"] = record("katana_draw", [rpg(f"drawKnife{i}") for i in (1, 2, 3)])
    knife = [rpg("knifeSlice"), rpg("knifeSlice2"), rpg("chop")]
    for cue in ("katana_cut", "bowie_cut", "field_knife", "enemy_attack_melee", "snip"):
        banks[cue] = record(cue, knife, layer=rpg("cloth1") if cue == "field_knife" else None)
    # Four isolated shots from the author's own recordings, without long
    # range chatter or the next shot in the source recording.
    banks["pistol"] = record("pistol", ["firearm/sounds/cz.wav"] * 4,
                              [.205, 2.805, 4.025, 5.525], .27)
    banks["revolver"] = record("revolver", ["firearm/sounds/mosin.wav"] * 4,
                                [.42, 3.54, 5.96, 8.82], .43)
    banks["suppressed_shot"] = record("suppressed_shot", ["firearm/sounds/cz.wav"] * 4,
                                       [.205, 2.805, 4.025, 5.525], .115,
                                       layer=rpg("metalClick"))
    banks["shotgun"] = record("shotgun", ["firearm/sounds/shotty.wav"] * 3,
                               [.09, .105, .12], .40)
    banks["double_barrel"] = record("double_barrel", ["firearm/sounds/shotty.wav"] * 3,
                                     [.09, .105, .12], .49, layer=impact("impactPunch_heavy")[0])
    banks["breach_shotgun"] = record("breach_shotgun", ["firearm/sounds/shotty.wav"] * 3,
                                      [.09, .105, .12], .28, layer=rpg("metalLatch"))
    banks["cannon"] = record("cannon", sci("explosionCrunch"), duration=.8)
    banks["null_cannon"] = record("null_cannon", sci("laserLarge"), duration=.7)
    banks["ion_slice"] = record("ion_slice", sci("laserRetro"), duration=.35)
    banks["orbit_pulse"] = record("orbit_pulse", sci("forceField"), duration=.5)
    banks["enemy_attack_ranged"] = record("enemy_attack_ranged", sci("laserSmall"), duration=.28)
    banks["hit"] = record("hit", impact("impactPunch_medium", 4))
    banks["heavy_hit"] = record("heavy_hit", impact("impactPunch_heavy"))
    banks["blocked"] = record("blocked", impact("impactMetal_light"))
    banks["enemy_hit_metal"] = record("enemy_hit_metal", impact("impactMetal_medium", 4))
    banks["enemy_hit_paper"] = record("enemy_hit_paper", impact("impactSoft_heavy", 4))
    banks["enemy_hit_ink"] = record("enemy_hit_ink", impact("impactSoft_medium", 4))
    banks["enemy_death_metal"] = record("enemy_death_metal", impact("impactPlate_heavy"))
    banks["enemy_death_paper"] = record("enemy_death_paper", [rpg(f"bookFlip{i}") for i in (3, 1, 2)],
                                         layer=impact("impactPlank_medium")[0])
    banks["enemy_death_ink"] = record("enemy_death_ink", sci("slime", 2) + sci("slime", 1), starts=[0, 0, .06], duration=.42)
    banks["paper_break"] = record("paper_break", impact("impactPlank_medium"), layer=rpg("cloth2"))
    banks["paper_step"] = record("paper_step", [f"impact-sounds/Audio/footstep_carpet_{i:03}.ogg" for i in (0, 1, 3)])
    banks["staple"] = record("staple", impact("impactTin_medium"))
    banks['enemy_telegraph'] = record('enemy_telegraph', [rpg('drawKnife1'),rpg('drawKnife2'),rpg('metalLatch')], duration=.4)
    banks['enemy_telegraph_ranged'] = record('enemy_telegraph_ranged', sci('forceField'), duration=.5)
    banks['enemy_telegraph_heavy'] = record('enemy_telegraph_heavy', impact('impactMetal_heavy'), duration=.5)
    banks['enemy_telegraph_air'] = record('enemy_telegraph_air', [rpg('cloth1'),rpg('cloth2'),rpg('cloth3')], duration=.4)

    music = {
        "moon_compass": (ROOT / "assets/audio/music/page_0_action.ogg", "Tozan — Japoi 3 / Koto with Shakuhachi"),
        "wanted_sketch": (ROOT / "assets/audio/music/page_1_action.mp3", "Umplix — The Cowboy's Theme"),
        "railroad_stapler": (source / "boss8.ogg", "Spring Spring — Boss 8"),
        "orbital_mistake": (source / "final_stand.ogg", "Centurion_of_war — Final Stand, phase 1.3"),
        "scissor_director": (source / "battle_rpg.ogg", "Cleyton Kauffman — Battle RPG Theme Var."),
        "final_editor": (source / "final_battle.ogg", "skrjablin — The Final Battle"),
        "baby_face_giant": (source / "massive_hunt.wav", "Eldritch Grim — Massive Battle"),
        "cloud_kite": (source / "hope.ogg", "MintoDog — Hope (Orchestral battle music)"),
    }
    boss_tracks = {}
    for kind, (input_path, credit) in music.items():
        audio = read(library, input_path)
        pcm = prepare(audio, music=True)
        relative = f"bosses/{kind}.wav"
        output = asset_root / relative
        write(output, pcm)
        boss_tracks[kind] = relative
        manifest["boss_tracks"][kind] = {"file": relative, "credit": credit,
            "duration": len(pcm) / RATE, "rms": float(np.sqrt(np.mean((pcm.astype(float) / 32767) ** 2))),
            "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    license_dir = asset_root / "licenses"
    license_dir.mkdir(exist_ok=True)
    for pack in ("impact-sounds", "rpg-audio", "sci-fi-sounds"):
        shutil.copyfile(source / pack / "License.txt", license_dir / f"kenney_{pack}.txt")
    shutil.copyfile(source / "firearm/sounds/creativecommons.txt", license_dir / "vincent_sevedge.txt")
    (asset_root / "revision_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "audio_catalog.py").write_text(
        '"""Reviewed audio asset selections; source credits live beside the assets."""\n'
        + "SELECTED_BOSS_TRACKS = " + repr(boss_tracks) + "\n\n"
        + "RECORDED_COMBAT_BANKS = " + repr(banks) + "\n")
    print(json.dumps({"boss_tracks": len(boss_tracks), "recorded_cue_families": len(banks),
                      "recorded_takes": sum(map(len, banks.values()))}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, required=True)
    run(parser.parse_args().sources)
