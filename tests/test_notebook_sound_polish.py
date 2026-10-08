"""Contracts for the old notebook sound identity and the restrained polish."""
import hashlib
import math
from pathlib import Path
import unittest
import wave

from audio_composer import NotebookComposer, SFX_VARIANT_COUNTS
from desk_audio import desk_score


ROOT = Path(__file__).resolve().parents[1] / "assets" / "audio"
RATE = 22050
# PCM digests from the delivered 0.32 original calm desk tracks. Combat may
# change its accents; exploration must keep the sound the player preferred.
ORIGINAL_CALM = (
    "1d229b1fcb06e8cfb4e93fe6dccb4389eda65b1a4a2f1639de14697285132186",
    "d38744226a72d42af1dd8abad11c2fe43d178d9a4535483cc86bfd3e6aa538ff",
    "d6b963d439dc7f02616e6cdded944aaffd694340eb6f2b3591a0604f064e3858",
    "2c5aa4cfb86040e6804c0a8f5cfc90dde8f53b9b4f9757ee6c00e64afc321c9a",
    "79f4ddbc85fecfd3cc2e03f33853908ee9b8f645f52b2a6cef3a87562667136b",
)


def rms(samples):
    return math.sqrt(sum(value * value for value in samples) / max(1, len(samples)))


def shipped(path):
    with wave.open(str(path)) as source:
        return source.readframes(source.getnframes())


class NotebookSoundPolishTests(unittest.TestCase):
    def test_original_calm_tracks_are_preserved_in_shipped_game(self):
        for page, digest in enumerate(ORIGINAL_CALM):
            raw = shipped(ROOT / "desk" / f"page_{page}_calm.wav")
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest, page)

    def test_reload_has_two_readable_gestures_separated_by_a_pause(self):
        samples = NotebookComposer(RATE).sfx("reload")
        first = samples[:round(.07 * RATE)]
        pause = samples[round(.078 * RATE):round(.115 * RATE)]
        seated = samples[round(.125 * RATE):round(.213 * RATE)]
        self.assertGreater(rms(first), 500)
        self.assertGreater(rms(seated), rms(first))
        self.assertLess(rms(pause), min(rms(first), rms(seated)) * .05)

    def test_impacts_remain_short_and_steps_leave_feedback_headroom(self):
        composer = NotebookComposer(RATE)
        hit = composer.sfx("hit")
        block = composer.sfx("blocked")
        reload = composer.sfx("reload")
        step = composer.sfx("paper_step")
        self.assertLess(len(hit) / RATE, .10)
        self.assertLess(len(block) / RATE, .18)
        self.assertGreater(len(reload), len(block))
        self.assertLess(rms(step), rms(hit) * .5)
        for samples in (hit, block, reload, step):
            self.assertLess(max(map(abs, samples)), 32767 * .32)
            self.assertEqual(samples[0], 0)
            self.assertEqual(samples[-1], 0)

    def test_new_reload_takes_are_deterministic_and_shipped(self):
        composer = NotebookComposer(RATE)
        takes = []
        for variation in range(SFX_VARIANT_COUNTS["reload"]):
            raw = composer.sfx("reload", variation).tobytes()
            self.assertEqual(raw, composer.sfx("reload", variation).tobytes())
            suffix = "" if variation == 0 else f"_v{variation + 1}"
            self.assertEqual(shipped(ROOT / f"sfx_reload{suffix}.wav"), raw)
            takes.append(raw)
        self.assertEqual(len(set(takes)), 3)

    def test_action_and_boss_tracks_keep_page_tempo_and_shipped_recipes(self):
        composer = NotebookComposer(RATE)
        for page in range(5):
            lengths = set()
            signatures = set()
            for label, energy, boss in (("calm", 0, False), ("action", 1, False),
                                        ("boss", 1, True)):
                samples = desk_score(composer, page, energy, boss)
                self.assertEqual(shipped(ROOT / "desk" / f"page_{page}_{label}.wav"),
                                 samples.tobytes(), (page, label))
                lengths.add(len(samples))
                signatures.add(hashlib.sha256(samples).hexdigest())
                self.assertLess(max(map(abs, samples)), 32767 * .18)
            self.assertEqual(len(lengths), 1, page)
            self.assertEqual(len(signatures), 3, page)


if __name__ == "__main__":
    unittest.main()
