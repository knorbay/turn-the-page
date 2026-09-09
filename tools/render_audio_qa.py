"""Render the exact runtime synthesis as listenable WAV review files."""
from __future__ import annotations

import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from audio_composer import NotebookComposer, mix_pcm, sequence_pcm, write_wav


def render(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    composer = NotebookComposer(22050)
    renders = []

    page_specs = (
        ("01_ronin_washi_calm.wav", 0, 0.0, False, .76, .88),
        ("02_wild_west_combat.wav", 1, 1.0, False, .58, .92),
        ("03_wrong_future_boss.wav", 2, 1.0, True, .42, .95),
    )
    for filename, page, energy, boss, ambience_gain, score_gain in page_specs:
        score = composer.score(page, energy, boss)
        ambience = composer.ambience(page, len(score) / composer.sample_rate)
        mix = mix_pcm((ambience, ambience_gain), (score, score_gain))
        path = output_dir / filename
        write_wav(str(path), mix, composer.sample_rate)
        renders.append(path)

    cue_names = (
        "pencil", "redraw", "erase", "page", "pistol", "shotgun",
        "heavy_hit", "enemy_break", "giant_step", "giant_stomp",
        "hero_reveal", "hero_sword",
    )
    cue_reel = sequence_pcm(
        [(composer.sfx(name), .88) for name in cue_names],
        composer.sample_rate, .22,
    )
    cue_path = output_dir / "04_paper_foley_reel.wav"
    write_wav(str(cue_path), cue_reel, composer.sample_rate)
    renders.append(cue_path)
    return renders


if __name__ == "__main__":
    destination = Path(os.environ.get(
        "TURN_PAGE_AUDIO_QA",
        ROOT / "work" / "audio_qa",
    ))
    for result in render(destination):
        print(result)
