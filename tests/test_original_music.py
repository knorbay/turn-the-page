"""The original soundtrack stays byte-identical and scene playback stays safe."""
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

from audio import NotebookSounds, PAGE_DIP_SECONDS, PAGE_RISE_SECONDS
from audio_mix import BOSS_MUSIC_PEAK, BOSS_MUSIC_RMS
from scene_music import (BOSS_ENTRANCE_TRACKS, BOSS_ENTRY_DELAYS, BOSS_PROFILES,
                         MUSIC_CREDITS, MUSIC_PROFILES, SCORE_MANIFEST, BOSS_SCORE_MANIFEST,
                         SELECTED_BOSS_TRACKS, SELECTED_PAGE_TRACKS)

ROOT = Path(__file__).resolve().parents[1] / "assets/audio"


class CountingChannel:
    def __init__(self, channel):
        self.channel = channel
        self.plays = []

    def play(self, sound, *args, **kwargs):
        self.plays.append(sound)
        return self.channel.play(sound, *args, **kwargs)

    def set_volume(self, value):
        self.requested_volume = value
        return self.channel.set_volume(value)

    def __getattr__(self, name):
        return getattr(self.channel, name)


class OriginalRecordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # pre_init cannot replace a mono device left by another fixture.
        pygame.mixer.quit()
        pygame.mixer.pre_init(22050, -16, 2, 512)
        pygame.init()
        cls.manifest = json.loads((ROOT / SCORE_MANIFEST).read_text())

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_selection_has_only_the_fifteen_original_assets_and_no_new_entrances(self):
        expected = {tracks[role] for tracks in SELECTED_PAGE_TRACKS.values()
                    for role in ("calm", "action", "boss")}
        self.assertEqual(len(expected), 15)
        self.assertEqual({item["file"] for item in self.manifest["files"]}, expected)
        self.assertEqual(BOSS_ENTRANCE_TRACKS, {})
        self.assertEqual(BOSS_ENTRY_DELAYS, {})
        self.assertEqual(self.manifest["entrance_tracks"], {})
        self.assertEqual(self.manifest["score_id"], "original-first-version")
        self.assertEqual(len(MUSIC_PROFILES), 5)
        self.assertFalse(any("directed/" in relative or "score/" in relative for relative in expected))

    def test_each_selected_file_matches_its_first_native_release_byte_for_byte(self):
        for item in self.manifest["files"]:
            with self.subTest(asset=item["file"]):
                raw = (ROOT / item["file"]).read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                self.assertEqual(len(raw), item["bytes"])
                self.assertEqual(digest, item["encoded_sha256"])
                self.assertTrue(item["historical_proofs"])
                for proof in item["historical_proofs"]:
                    self.assertTrue(proof["matches_current"])
                    self.assertEqual(proof["encoded_sha256"], digest)
                    self.assertTrue(proof["member"])
                    self.assertEqual(len(proof["bundle_sha256"]), 64)

    def test_original_recordings_decode_in_the_real_stereo_game_mixer(self):
        self.assertEqual(pygame.mixer.get_init(), (22050, -16, 2))
        hashes = set()
        for item in self.manifest["files"]:
            with self.subTest(asset=item["file"]):
                sound = pygame.mixer.Sound(str(ROOT / item["file"]))
                self.assertGreater(sound.get_length(), 1)
                self.assertAlmostEqual(sound.get_length(), item["duration_seconds"], delta=.25)
                raw = sound.get_raw()
                samples = array("h", raw)
                self.assertEqual(len(samples) % 2, 0)
                self.assertGreater(max(abs(min(samples)), abs(max(samples))), 0)
                hashes.add(hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(hashes), 15)

    def test_original_cc0_credits_and_procedural_cues_keep_their_provenance(self):
        recordings = [item for item in self.manifest["files"] if item["source_kind"] == "cc0_recording"]
        procedural = [item for item in self.manifest["files"] if item["source_kind"] == "original_procedural"]
        self.assertEqual(len(recordings), 6)
        self.assertEqual(len(procedural), 9)
        credit_titles = {item["title"] for item in MUSIC_CREDITS}
        for item in recordings:
            self.assertIn(item["title"], credit_titles)
            self.assertTrue(item["composer"])
            self.assertIn("CC0", item["license"])
            self.assertTrue(item["license_url"])
            self.assertTrue(item["source_url"])
        for item in procedural:
            self.assertTrue(item["composer"])
            self.assertNotIn("Kevin MacLeod", item["composer"])

    def test_twelve_boss_identities_have_distinct_credited_recordings(self):
        manifest = json.loads((ROOT / BOSS_SCORE_MANIFEST).read_text())
        self.assertEqual(len(BOSS_PROFILES), 12)
        self.assertEqual(set(SELECTED_BOSS_TRACKS), set(BOSS_PROFILES))
        self.assertEqual(len(set(SELECTED_BOSS_TRACKS.values())), 12)
        self.assertEqual(len({item["encoded_sha256"] for item in manifest["files"]}), 12)
        self.assertEqual(len(MUSIC_CREDITS), 18)
        for item in manifest["files"]:
            with self.subTest(kind=item["kind"]):
                self.assertEqual(item["file"], SELECTED_BOSS_TRACKS[item["kind"]])
                self.assertEqual(item["page"], BOSS_PROFILES[item["kind"]]["page"])
                self.assertEqual(hashlib.sha256((ROOT/item["file"]).read_bytes()).hexdigest(), item["encoded_sha256"])
                self.assertEqual(item["license"], "CC BY 4.0")
                self.assertTrue(item["source_url"].startswith("https://"))
                self.assertTrue(item["license_evidence"].startswith("https://"))
                self.assertTrue(item["composer"] and item["credit"] and item["changes"])

    def test_recorded_boss_playback_preserves_the_mastered_stereo_and_page_music(self):
        sounds = NotebookSounds()
        for kind, profile in BOSS_PROFILES.items():
            page = profile["page"]
            with self.subTest(kind=kind):
                sounds.start_ambience(page)
                sounds.set_combat(True, True, kind)
                recorded = pygame.mixer.Sound(str(ROOT / SELECTED_BOSS_TRACKS[kind]))
                played = sounds.boss_scores[kind]
                self.assertEqual(played.get_raw(), recorded.get_raw())
                self.assertGreaterEqual(played.get_length(), 20)
                self.assertLessEqual(played.get_length(), 45)
                samples = array("h", played.get_raw())
                rms = math.sqrt(sum(sample*sample for sample in samples)/len(samples))/32768
                self.assertGreater(rms, .06)
                self.assertLess(rms, .112)
                self.assertLessEqual(max(abs(sample) for sample in samples)/32768, .62)
                # Stereo remains genuinely different, rather than duplicating a synth oscillator.
                self.assertNotEqual(samples[::2], samples[1::2])
                self.assertIsNot(played, sounds.score_boss[page])
                for label, sound in (("calm", sounds.score_low[page]), ("action", sounds.score_high[page])):
                    original = pygame.mixer.Sound(str(ROOT / SELECTED_PAGE_TRACKS[page][label]))
                    self.assertEqual(sound.get_raw(), original.get_raw())

    def test_boss_accent_preserves_the_original_stereo_difference(self):
        from audio_mix import boss_music_pcm
        source = array('h')
        rate = 8000
        for frame in range(rate * 4):
            source.extend((round(4000 * math.sin(math.tau * 261.63 * frame / rate)),
                           round(2000 * math.sin(math.tau * 329.63 * frame / rate))))
        raw = source.tobytes()
        played = array('h', boss_music_pcm(raw, rate, 2, 3))
        old_difference = [a - b for a, b in zip(source[::2], source[1::2])]
        new_difference = [a - b for a, b in zip(played[::2], played[1::2])]
        gain = sum(a * b for a, b in zip(old_difference, new_difference)) / sum(a * a for a in old_difference)
        self.assertLess(max(abs(b - a * gain) for a, b in zip(old_difference, new_difference)), 1.05)
        self.assertEqual(source.tobytes(), raw)

    def test_boss_pages_have_distinct_repeatable_accent_materials(self):
        from audio_mix import boss_music_pcm
        rate = 8000
        source = array('h', (round(3500 * math.sin(math.tau * 220 * frame / rate))
                             for frame in range(rate * 4))).tobytes()
        rendered = [boss_music_pcm(source, rate, 1, page) for page in range(5)]
        self.assertEqual(len(set(rendered)), 5)
        for page, raw in enumerate(rendered):
            self.assertEqual(len(raw), len(source))
            self.assertEqual(raw, boss_music_pcm(source, rate, 1, page))
            self.assertLessEqual(max(abs(value) for value in array('h', raw)) / 32768,
                                 BOSS_MUSIC_PEAK)


class OriginalScenePlaybackTests(unittest.TestCase):
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

    def sounds(self, page=0):
        sounds = NotebookSounds()
        sounds.score_channel = CountingChannel(sounds.score_channel)
        sounds.combat_channel = CountingChannel(sounds.combat_channel)
        sounds.music_intro_channel = CountingChannel(sounds.music_intro_channel)
        sounds.boss_channel = CountingChannel(sounds.boss_channel)
        sounds.start_ambience(page)
        sounds.update(1)
        return sounds

    def assert_exclusive_page_recording(self, sounds):
        self.assertFalse(sounds.score_channel.get_busy() and sounds.combat_channel.get_busy())
        self.assertFalse(sounds.score_channel.get_volume() > 0 and sounds.combat_channel.get_volume() > 0)

    def test_repeated_encounter_updates_hand_over_once_and_never_layer_unrelated_tracks(self):
        sounds = self.sounds()
        original_gain = sounds.score_channel.get_volume()
        for tick in range(60):
            sounds.set_combat(True)
            sounds.update(1 / 60)
            self.assert_exclusive_page_recording(sounds)
            if tick == 5:
                self.assertLess(sounds.score_channel.get_volume(), original_gain)
                self.assertEqual(sounds.combat_channel.get_volume(), 0)
        self.assertEqual(sounds.combat_channel.plays, [sounds.score_high[0]])
        self.assertGreater(sounds.combat_channel.get_volume(), 0)
        for _ in range(60):
            sounds.set_combat(False)
            sounds.update(1 / 60)
            self.assert_exclusive_page_recording(sounds)
        self.assertEqual(sounds.score_channel.plays, [sounds.score_low[0], sounds.score_low[0]])
        self.assertGreater(sounds.score_channel.get_volume(), 0)

    def test_departure_during_calm_dip_cancels_the_action_cue(self):
        sounds = self.sounds()
        sounds.set_combat(True)
        sounds.update(PAGE_DIP_SECONDS / 2)
        lowered = sounds.score_channel.get_volume()
        sounds.set_combat(False)
        sounds.update(PAGE_RISE_SECONDS + .01)
        self.assertEqual(sounds.combat_channel.plays, [])
        self.assertEqual(len(sounds.score_channel.plays), 1)
        self.assertGreater(sounds.score_channel.get_volume(), lowered)
        self.assert_exclusive_page_recording(sounds)

    def test_returning_to_combat_during_action_dip_cancels_calm_restart(self):
        sounds = self.sounds()
        sounds.set_combat(True)
        sounds.update(PAGE_DIP_SECONDS + PAGE_RISE_SECONDS + .01)
        sounds.set_combat(False)
        sounds.update(PAGE_DIP_SECONDS / 2)
        sounds.set_combat(True)
        sounds.update(PAGE_RISE_SECONDS + .01)
        self.assertEqual(len(sounds.score_channel.plays), 1)
        self.assertEqual(sounds.combat_channel.plays, [sounds.score_high[0]])
        self.assertGreater(sounds.combat_channel.get_volume(), 0)
        self.assert_exclusive_page_recording(sounds)

    def test_page_turn_cancels_a_pending_old_page_action_cue(self):
        sounds = self.sounds()
        sounds.set_combat(True)
        sounds.update(PAGE_DIP_SECONDS / 2)
        sounds.start_ambience(2)
        sounds.update(2)
        self.assertIs(sounds.score_channel.get_sound(), sounds.score_low[2])
        self.assertEqual(sounds.combat_channel.plays, [])
        self.assertFalse(sounds.combat_active)
        self.assert_exclusive_page_recording(sounds)

    def test_boss_entry_cancels_page_transition_and_uses_the_original_bed_directly(self):
        sounds = self.sounds()
        sounds.set_combat(True)
        sounds.update(PAGE_DIP_SECONDS / 2)
        sounds.set_combat(True, True, "moon_compass")
        self.assertEqual(sounds.score_channel.get_volume(), 0)
        self.assertEqual(sounds.combat_channel.get_volume(), 0)
        self.assertEqual(sounds.combat_channel.plays, [])
        self.assertEqual(sounds.music_intro_channel.plays, [])
        self.assertEqual(sounds.boss_channel.plays, [sounds.boss_scores["moon_compass"]])
        sounds.update(.3)
        self.assertGreater(sounds.boss_channel.get_volume(), 0)
        self.assertEqual(sounds.music_intro_channel.get_volume(), 0)
        for _ in range(60):
            sounds.set_combat(True, True, "moon_compass")
            sounds.update(1 / 60)
        self.assertEqual(len(sounds.boss_channel.plays), 1)
        sounds.set_combat(False)
        sounds.update(1)
        self.assertFalse(sounds.boss_channel.get_busy())
        self.assertEqual(sounds.combat_channel.plays, [])
        self.assertGreater(sounds.score_channel.get_volume(), 0)

    def test_retry_restarts_the_original_loop_without_an_entrance_or_late_restart(self):
        sounds = self.sounds()
        sounds.set_combat(True, True, "moon_compass")
        sounds.update(.5)
        sounds.set_combat(False)
        sounds.update(4)
        self.assertEqual(len(sounds.boss_channel.plays), 1)
        self.assertFalse(sounds.boss_channel.get_busy())
        sounds.set_combat(True, True, "moon_compass")
        sounds.set_combat(True, True, "cloud_kite")
        self.assertEqual(sounds.music_intro_channel.plays, [])
        self.assertEqual(len(sounds.boss_channel.plays), 3)
        self.assertIs(sounds.boss_channel.get_sound(), sounds.boss_scores["cloud_kite"])
        for _ in range(20):
            sounds.set_combat(True, True, "cloud_kite")
            sounds.update(.1)
        self.assertEqual(len(sounds.boss_channel.plays), 3)

    def test_default_boss_is_audible_but_normal_page_returns_at_its_familiar_level(self):
        sounds = self.sounds()
        sounds.apply_settings({"master_volume": .8, "music_volume": .35, "sfx_volume": .85})
        normal_volume = sounds.score_channel.requested_volume
        sounds.set_combat(True, True, "moon_compass")
        # The drawing begins at a softer level; test foreground audibility
        # after the reveal rather than requiring a full-volume first frame.
        sounds.update(3.2)
        samples = array("h", sounds.boss_scores["moon_compass"].get_raw())
        rms = math.sqrt(sum(sample * sample for sample in samples) / len(samples)) / 32768
        self.assertGreater(rms * sounds.boss_channel.requested_volume, .012)
        self.assertLess(sounds.boss_channel.requested_volume, .23)
        sounds.set_combat(False)
        sounds.update(1)
        self.assertAlmostEqual(sounds.score_channel.requested_volume, normal_volume)
        self.assertEqual(sounds.boss_channel.requested_volume, 0)

    def test_boss_entrance_reuses_pcm_prepared_at_page_load(self):
        sounds = self.sounds()
        prepared = {kind: sounds.boss_scores[kind] for kind in ("moon_compass", "cloud_kite")}
        self.assertIsNot(prepared["moon_compass"], prepared["cloud_kite"])
        with patch("audio.boss_music_pcm", side_effect=AssertionError("synthesis at boss entrance")), \
                patch.object(sounds, "_asset_sound", side_effect=AssertionError("file decoding at boss entrance")):
            sounds.set_combat(True, True, "moon_compass")
            self.assertIs(sounds.boss_scores["moon_compass"], prepared["moon_compass"])
            sounds.set_combat(True, True, "cloud_kite")
            self.assertIs(sounds.boss_scores["cloud_kite"], prepared["cloud_kite"])

    def test_music_mute_and_master_mute_apply_during_every_scene_phase(self):
        for phase in ("calm", "action", "boss"):
            with self.subTest(phase=phase):
                sounds = self.sounds()
                if phase == "action":
                    sounds.set_combat(True)
                    sounds.update(.53)
                elif phase == "boss":
                    sounds.set_combat(True, True, "moon_compass")
                    sounds.update(.3)
                music_channels = (sounds.ambient_channel, sounds.classroom_channel, sounds.score_channel,
                                  sounds.combat_channel, sounds.music_intro_channel, sounds.boss_channel)
                sounds.apply_settings({"master_volume": .8, "sfx_volume": .85, "music_volume": 0})
                self.assertTrue(all(channel.get_volume() == 0 for channel in music_channels))
                self.assertGreater(sounds.cue_channel.get_volume(), 0)
                sounds.apply_settings({"master_volume": .8, "sfx_volume": .85, "music_volume": .55})
                active = {"calm": sounds.score_channel, "action": sounds.combat_channel,
                          "boss": sounds.boss_channel}[phase]
                self.assertGreater(active.get_volume(), 0)
                sounds.apply_settings({"master_volume": 0, "sfx_volume": .85, "music_volume": .55})
                self.assertTrue(all(channel.get_volume() == 0 for channel in music_channels))
                self.assertEqual(sounds.cue_channel.get_volume(), 0)
                pygame.mixer.stop()

    def test_unavailable_mixer_keeps_game_audio_calls_safe_without_loading_assets(self):
        with patch("pygame.mixer.get_init", return_value=None), patch("pygame.mixer.Sound") as load:
            sounds = NotebookSounds()
            self.assertFalse(sounds.enabled)
            sounds.start_ambience(2)
            sounds.set_combat(True, True, "orbital_mistake")
            sounds.set_intensity(1, boss=True)
            sounds.update(5)
            sounds.quiet_ambience()
            sounds.apply_settings({"master_volume": 0, "music_volume": 0})
            self.assertIsNone(sounds.play("boss_phase_shift"))
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
