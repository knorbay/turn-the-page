from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import wave

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from advanced_enemies import BabyFaceGiant, PaperWasp, RulerGuard
from audio_composer import NotebookComposer, mix_pcm, write_wav
from camera import Camera
from combat import DoodleEnemy
from paper_renderer import PaperRenderer
from settings import PAPER


ROOT = Path(__file__).resolve().parents[1]


class ArtAudioDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def test_calm_and_action_arrangements_are_phase_compatible(self):
        composer = NotebookComposer(22050)
        for page in range(5):
            calm = composer.score(page, 0)
            action = composer.score(page, 1)
            self.assertEqual(len(calm), len(action))
            self.assertNotEqual(hashlib.sha256(calm).digest(),
                                hashlib.sha256(action).digest())

    def test_boss_arrangement_is_not_a_relabelled_action_loop(self):
        composer = NotebookComposer(22050)
        action = composer.score(2, 1)
        boss = composer.score(2, 1, True)
        self.assertEqual(len(action), len(boss))
        self.assertNotEqual(hashlib.sha256(action).digest(),
                            hashlib.sha256(boss).digest())
        for page in range(3):
            action_path = ROOT / "assets" / "audio" / f"page_{page}_action.wav"
            boss_path = ROOT / "assets" / "audio" / f"page_{page}_boss.wav"
            self.assertNotEqual(hashlib.sha256(action_path.read_bytes()).digest(),
                                hashlib.sha256(boss_path.read_bytes()).digest())

    def test_runtime_mix_exports_valid_pcm_wave(self):
        composer = NotebookComposer(22050)
        score = composer.score(1, 1)
        ambience = composer.ambience(1, len(score) / composer.sample_rate)
        mixed = mix_pcm((score, .9), (ambience, .6))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "review.wav"
            write_wav(str(path), mixed, composer.sample_rate)
            with wave.open(str(path), "rb") as rendered:
                self.assertEqual(rendered.getnchannels(), 1)
                self.assertEqual(rendered.getframerate(), 22050)
                self.assertEqual(rendered.getnframes(), len(score))

    def test_canonical_material_roster_has_distinct_render_signatures(self):
        renderer = PaperRenderer()
        camera = Camera(360)
        actors = (
            DoodleEnemy("crawler", 170, 350, 11),
            DoodleEnemy("hopper", 170, 350, 12),
            DoodleEnemy("spitter", 170, 350, 13),
            RulerGuard(170, 350, 14),
            PaperWasp(170, 350, 15),
            BabyFaceGiant(170, 350, 16),
        )
        signatures = set()
        for actor in actors:
            actor.state = "idle"
            surface = pygame.Surface((360, 400))
            surface.fill(PAPER)
            actor.draw(surface, camera, renderer)
            signatures.add(hashlib.sha256(
                pygame.image.tobytes(surface, "RGB")
            ).hexdigest())
        self.assertEqual(len(signatures), len(actors))

    def test_release_assets_do_not_contain_generated_character_rasters(self):
        assets = ROOT / "assets"
        raster_assets = [path for path in assets.rglob("*")
                         if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
        self.assertEqual(raster_assets, [])


if __name__ == "__main__":
    unittest.main()
