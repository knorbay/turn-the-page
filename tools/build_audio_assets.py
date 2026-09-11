"""Build redistributable runtime WAV assets from the original synth source."""
from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audio_composer import (
    NotebookComposer,
    SFX_NAMES,
    SFX_VARIANT_COUNTS,
    write_wav,
)


def build(destination: Path, pages=range(5)) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    composer = NotebookComposer(22050)
    outputs: list[Path] = []
    for name in SFX_NAMES:
        for variation in range(SFX_VARIANT_COUNTS.get(name, 1)):
            suffix = "" if variation == 0 else f"_v{variation + 1}"
            path = destination / f"sfx_{name}{suffix}.wav"
            write_wav(
                str(path), composer.sfx(name, variation), composer.sample_rate,
            )
            outputs.append(path)
    classroom = destination / "classroom_babble.wav"
    write_wav(str(classroom), composer.classroom(), composer.sample_rate)
    outputs.append(classroom)
    for page in pages:
        variants = {
            "ambience": composer.ambience(page),
            "calm": composer.score(page, 0),
            "action": composer.score(page, 1),
            "boss": composer.score(page, 1, True),
        }
        for label, samples in variants.items():
            path = destination / f"page_{page}_{label}.wav"
            write_wav(str(path), samples, composer.sample_rate)
            outputs.append(path)
    return outputs


if __name__ == "__main__":
    for output in build(ROOT / "assets" / "audio"):
        print(output)
