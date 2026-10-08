"""Short recorded phrases, drawing dynamics and audible attack warnings."""
from array import array
import hashlib
import json
import math
import os
from pathlib import Path
import unittest
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from audio import NotebookSounds, BOSS_MUSIC_BUS_GAIN, BOSS_REVEAL_RISE_SECONDS
from boss_soundtrack import BOSS_RECORDINGS
from scene_music import SELECTED_BOSS_TRACKS

ROOT = Path(__file__).resolve().parents[1] / "assets/audio"


def rms(sound):
    values = array("h", sound.get_raw())
    return math.sqrt(sum(value*value for value in values)/len(values))/32768


class VolumeTrace:
    """Read the configured mix independently of SDL's wall-clock fade."""
    def __init__(self, channel):
        self.channel = channel
        self.requested_volume = 0.0

    def set_volume(self, value):
        self.requested_volume = value
        return self.channel.set_volume(value)

    def __getattr__(self, name):
        return getattr(self.channel, name)


class ShortBossScoreContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.quit()
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def tearDown(self):
        pygame.mixer.stop()

    def test_twelve_short_stereo_phrases_match_their_sources_credits_and_complete_periods(self):
        self.assertEqual(pygame.mixer.get_init(), (22050, -16, 2))
        manifest = json.loads((ROOT/"boss/manifest.json").read_text())
        self.assertEqual(manifest["files"], list(BOSS_RECORDINGS))
        self.assertEqual(manifest["target_rms"], .10)
        hashes = set()
        titles = set()
        for record in BOSS_RECORDINGS:
            with self.subTest(kind=record["kind"]):
                path = ROOT/SELECTED_BOSS_TRACKS[record["kind"]]
                sound = pygame.mixer.Sound(str(path))
                period = record["phrase_bars"] * record["beats_per_bar"] * 60 / record["phrase_bpm"]
                self.assertAlmostEqual(sound.get_length(), period, delta=2/22050)
                self.assertGreaterEqual(sound.get_length(), 20)
                self.assertLessEqual(sound.get_length(), 45)
                self.assertAlmostEqual(sound.get_length(), record["duration_seconds"], places=4)
                self.assertEqual(record["crossfade_seconds"], .25)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), record["encoded_sha256"])
                self.assertEqual(record["license"], "CC BY 4.0")
                self.assertIn("250 ms", record["changes"])
                self.assertIn(record["composer"].split(" / ")[0], record["credit"])
                self.assertIn(record["source_url"], (ROOT/"boss/CREDITS.md").read_text())
                self.assertGreaterEqual(rms(sound), .06)
                self.assertLessEqual(rms(sound), .112)
                samples = array("h", sound.get_raw())
                self.assertNotEqual(samples[::2], samples[1::2])
                hashes.add(hashlib.sha256(sound.get_raw()).hexdigest())
                titles.add(record["title"])
        self.assertEqual(len(hashes), 12)
        self.assertEqual(len(titles), 12)

    def test_loop_seams_do_not_introduce_a_larger_jump_than_the_adjacent_music(self):
        # Compare the wrapped sample step with actual nearby high-frequency
        # steps. An absolute zero boundary would erase the recorded waveform.
        for record in BOSS_RECORDINGS:
            with self.subTest(kind=record["kind"]):
                samples = array("h", pygame.mixer.Sound(str(ROOT/record["file"])).get_raw())
                neighborhood = []
                for edge in (samples[:2206], samples[-2206:]):
                    neighborhood.extend(abs(b-a) for a,b in zip(edge[:-2], edge[2:]))
                neighborhood.sort()
                reference = neighborhood[round((len(neighborhood)-1)*.99)]
                seam = max(abs(samples[channel]-samples[-2+channel]) for channel in range(2))
                self.assertLessEqual(seam, reference*2)

    def test_drawing_score_rises_once_then_remains_audible_and_retries_softly(self):
        sounds = NotebookSounds()
        sounds.start_ambience(0)
        sounds.boss_channel = VolumeTrace(sounds.boss_channel)
        sounds.apply_settings({"master_volume": 1, "music_volume": 1, "sfx_volume": 1})
        sounds.set_combat(True, True, "moon_compass")
        start = sounds.boss_channel.requested_volume
        sounds.update(BOSS_REVEAL_RISE_SECONDS/2)
        middle = sounds.boss_channel.requested_volume
        sounds.set_combat(True, True, "moon_compass")
        sounds.update(BOSS_REVEAL_RISE_SECONDS/2)
        settled = sounds.boss_channel.requested_volume
        self.assertGreater(middle, start)
        self.assertGreater(settled, middle)
        self.assertAlmostEqual(start/settled, .45, delta=.025)
        self.assertLessEqual(settled, BOSS_MUSIC_BUS_GAIN)
        sounds.update(15)
        self.assertEqual(sounds.boss_channel.requested_volume, settled)
        sounds.set_combat(False)
        sounds.set_combat(True, True, "moon_compass")
        self.assertAlmostEqual(sounds.boss_channel.requested_volume, start, delta=.008)
        sounds.apply_settings({"master_volume": .8, "music_volume": .35, "sfx_volume": .85})
        sounds.update(3.2)
        self.assertGreater(rms(sounds.boss_scores["moon_compass"])*sounds.boss_channel.requested_volume, .012)

    def test_settled_warning_is_clearer_than_the_boss_score_and_survives_music_mute(self):
        sounds = NotebookSounds()
        sounds.start_ambience(0)
        sounds.boss_channel = VolumeTrace(sounds.boss_channel)
        sounds.apply_settings({"master_volume": .8, "music_volume": .35, "sfx_volume": .85})
        sounds.set_combat(True, True, "moon_compass")
        sounds.update(3.2)
        before = sounds.boss_channel.requested_volume
        score_level = rms(sounds.boss_scores["moon_compass"])*before
        with patch("pygame.time.get_ticks", return_value=1000):
            warning = sounds.play("enemy_telegraph_heavy", variant=0, cooldown_ms=0)
        self.assertIs(warning, sounds.warning_channel)
        self.assertGreater(rms(warning.get_sound())*warning.get_volume(), score_level)
        self.assertLess(sounds.boss_channel.requested_volume, before)
        sounds.apply_settings({"music_volume": 0})
        self.assertEqual(sounds.boss_channel.requested_volume, 0)
        self.assertGreater(sounds.warning_channel.get_volume(), 0)
        sounds.apply_settings({"master_volume": 0})
        self.assertEqual(sounds.warning_channel.get_volume(), 0)


if __name__ == "__main__":
    unittest.main()
