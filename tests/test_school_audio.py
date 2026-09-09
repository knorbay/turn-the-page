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
from audio_composer import NotebookComposer


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


if __name__ == "__main__":
    unittest.main()
