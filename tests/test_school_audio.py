from __future__ import annotations

from array import array
import math
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from audio import NotebookSounds
from audio_composer import NotebookComposer, SFX_VARIANT_COUNTS


ROOT = Path(__file__).resolve().parents[1]


def rms(samples):
    return math.sqrt(sum(value * value for value in samples) / max(1, len(samples)))


class SchoolAudioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_bell_has_two_distinct_rings_and_a_decaying_tail(self):
        with wave.open(str(ROOT / "assets/audio/sfx_bell.wav")) as source:
            rate = source.getframerate()
            samples = array("h", source.readframes(source.getnframes()))
        window = lambda start, end: samples[round(start * rate):round(end * rate)]
        self.assertAlmostEqual(len(samples) / rate, 2.85, places=3)
        between = rms(window(.82, 1.02))
        self.assertGreater(rms(window(.05, .65)), between * 2)
        self.assertGreater(rms(window(1.12, 1.67)), between * 2)
        self.assertGreater(rms(window(2.2, 2.55)), 30)
        self.assertLess(rms(window(2.75, 2.85)), 5)
        self.assertLess(max(abs(sample) for sample in samples), 30000)

    def test_classroom_is_quiet_nonempty_and_seamless(self):
        with wave.open(str(ROOT / "assets/audio/classroom_babble.wav")) as source:
            samples = array("h", source.readframes(source.getnframes()))
            self.assertEqual(source.getnframes(), 24 * source.getframerate())
        self.assertGreater(rms(samples) / 32767, .01)
        self.assertLess(rms(samples) / 32767, .05)
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)
        # Speech-like phrasing has audible gaps instead of stationary hiss.
        windows = [rms(samples[i:i + 2205]) for i in range(0, len(samples), 2205)]
        self.assertGreater(max(windows), min(windows) * 5)

    def test_combat_burst_cannot_steal_bell_or_classroom_and_sliders_work(self):
        sounds = NotebookSounds()
        sounds.start_ambience(0)
        pygame.time.wait(1450)  # Let actual SDL fade-in finish before checking gains.
        sounds._apply_mix()
        calm_gain = sounds.score_channel.get_volume()
        with patch("pygame.time.get_ticks", return_value=5000):
            sounds.play("bell")
            self.assertLess(sounds.score_channel.get_volume(), calm_gain * .6)
            for _ in range(40):
                sounds.play("heavy_hit")
            self.assertIs(sounds.bell_channel.get_sound(), sounds.sounds["bell"])
            self.assertIs(sounds.classroom_channel.get_sound(), sounds.classroom_sound)
            self.assertIs(sounds.score_channel.get_sound(), sounds.score_low[0])
        with patch("pygame.time.get_ticks", return_value=9000):
            sounds.update(1 / 60)
            self.assertEqual(sounds.bell_duck_until, 0)
            self.assertAlmostEqual(sounds.score_channel.get_volume(), calm_gain, delta=.008)
            sounds.apply_settings({"music_volume": 0})
            for channel in (sounds.ambient_channel, sounds.score_channel,
                            sounds.combat_channel, sounds.classroom_channel):
                self.assertEqual(channel.get_volume(), 0)
            self.assertGreater(sounds.bell_channel.get_volume(), 0)
            sounds.apply_settings({"master_volume": 0})
            self.assertEqual(sounds.bell_channel.get_volume(), 0)
        pygame.mixer.stop()

    def test_new_material_cues_are_audibly_different_and_preserve_hero_bank(self):
        composer = NotebookComposer(22050)
        cues = [composer.sfx(name) for name in
                ("katana_draw", "katana_cut", "staple", "snip",
                 "ink_burst", "compass_sweep", "stamp")]
        self.assertEqual(len({samples.tobytes() for samples in cues}), len(cues))
        for samples in cues:
            self.assertGreater(rms(samples) / 32767, .015)
            self.assertLess(max(abs(sample) for sample in samples), 32767)
        for name in ("hero_reveal", "hero_sword", "giant_step", "giant_stomp"):
            with wave.open(str(ROOT / f"assets/audio/sfx_{name}.wav")) as source:
                shipped = source.readframes(source.getnframes())
            self.assertEqual(shipped, composer.sfx(name).tobytes())

    def test_layered_combat_bank_has_distinct_materials_and_takes(self):
        composer = NotebookComposer(22050)
        material_cues = (
            "bowie_cut", "ion_slice", "field_knife", "revolver",
            "suppressed_shot", "double_barrel", "breach_shotgun",
            "null_cannon", "orbit_pulse", "enemy_telegraph",
            "enemy_telegraph_ranged", "enemy_telegraph_heavy",
            "enemy_telegraph_air", "enemy_hit_paper", "enemy_hit_ink",
            "enemy_hit_metal", "enemy_death_paper", "enemy_death_ink",
            "enemy_death_metal", "boss_phase_shift", "boss_opening",
            "boss_signature",
        )
        canonical = [composer.sfx(name) for name in material_cues]
        self.assertEqual(len({cue.tobytes() for cue in canonical}), len(canonical))
        for name, samples in zip(material_cues, canonical):
            self.assertGreater(rms(samples) / 32767, .025, name)
            self.assertLess(max(abs(sample) for sample in samples), 32767, name)
            takes = [composer.sfx(name, variation) for variation in
                     range(SFX_VARIANT_COUNTS.get(name, 1))]
            self.assertEqual(len({take.tobytes() for take in takes}), len(takes), name)
            for variation, take in enumerate(takes):
                suffix = "" if variation == 0 else f"_v{variation + 1}"
                path = ROOT / f"assets/audio/sfx_{name}{suffix}.wav"
                with wave.open(str(path)) as source:
                    shipped = source.readframes(source.getnframes())
                self.assertEqual(shipped, take.tobytes(), path.name)

    def test_runtime_rotates_variants_and_honors_pitch_volume_and_cooldown(self):
        sounds = NotebookSounds()
        with patch("pygame.time.get_ticks", return_value=1000):
            first = sounds.play("enemy_hit_paper", pitch=1.0, volume=.5,
                                cooldown_ms=90)
            blocked = sounds.play("enemy_hit_paper", pitch=1.0, volume=.5,
                                  cooldown_ms=90)
        self.assertIsNotNone(first)
        self.assertIsNone(blocked)
        self.assertIs(first.get_sound(), sounds.sound_variants["enemy_hit_paper"][0])
        self.assertLess(first.get_volume(), sounds.master_volume * sounds.sfx_volume)
        with patch("pygame.time.get_ticks", return_value=1091):
            second = sounds.play("enemy_hit_paper", pitch=1.0, cooldown_ms=90)
        self.assertIsNotNone(second)
        self.assertIs(second.get_sound(), sounds.sound_variants["enemy_hit_paper"][1])

        base_length = sounds.sound_variants["enemy_telegraph"][0].get_length()
        with patch("pygame.time.get_ticks", return_value=1200):
            pitched = sounds.play("enemy_telegraph", variant=0, pitch=1.25,
                                  cooldown_ms=0)
        self.assertIsNotNone(pitched)
        self.assertLess(pitched.get_sound().get_length(), base_length * .84)
        pygame.mixer.stop()

    def test_page_tools_resolve_to_their_drawn_material(self):
        sounds = NotebookSounds()
        expected = {
            1: {"blade": "bowie_cut", "pistol": "revolver",
                "shotgun": "double_barrel"},
            2: {"blade": "ion_slice", "cannon": "null_cannon",
                "rubber": "orbit_pulse"},
            3: {"blade": "field_knife", "pistol": "suppressed_shot",
                "shotgun": "breach_shotgun"},
        }
        for page, mappings in expected.items():
            sounds.ambient_chapter = page
            for legacy, material in mappings.items():
                self.assertEqual(sounds.resolve_cue(legacy), material)
        pygame.mixer.stop()

    def test_combat_mix_pushes_classroom_back_and_cues_make_headroom(self):
        sounds = NotebookSounds()
        sounds.start_ambience(0)
        sounds._apply_mix()
        calm_classroom = sounds.classroom_channel.get_volume()
        calm_score = sounds.score_channel.get_volume()
        sounds.set_combat(True, boss=True)
        sounds.intensity = 1.0
        sounds._apply_mix()
        self.assertLess(sounds.classroom_channel.get_volume(), calm_classroom * .2)

        with patch("pygame.time.get_ticks", return_value=5000):
            before_cue = sounds.score_channel.get_volume()
            channel = sounds.play("boss_phase_shift", variant=1, pitch=1.0)
            after_cue = sounds.score_channel.get_volume()
        self.assertIs(channel, sounds.cue_channel)
        self.assertLess(after_cue, before_cue * .8)
        with patch("pygame.time.get_ticks", return_value=5500):
            sounds.update(1 / 60)
        self.assertGreater(sounds.score_channel.get_volume(), after_cue)
        self.assertLess(sounds.score_channel.get_volume(), calm_score)
        pygame.mixer.stop()


if __name__ == "__main__":
    unittest.main()
