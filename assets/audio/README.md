# Runtime audio bank — 0.41

The 10 existing calm/action page cues remain unchanged. Twelve different
CC BY 4.0 recorded boss loops under `boss/` replace the shared synthesized
boss score. `scene_music.py` selects 22 active music assets. The 15 historical
page assets, including unused fallback boss WAVs, remain archived and hashed
in `original/manifest.json`.

`boss/manifest.json` records original source URLs, composer/license evidence,
source and delivered hashes, excerpt boundaries, modifications, decoded
runtime duration/RMS/peak and the boss/page assignment. See `boss/CREDITS.md`
and `THIRD_PARTY.md` for attribution. In-game credits show all 18 recording
credits across three pages with source and license URLs and modification notice.

The new boss files are 22050 Hz stereo Vorbis. Composer-provided PeriTune
loops retain their authored phrase boundaries. Full-mix excerpts use a short
crossfade to loop without a silent trailer ending. Clips are 27–38 seconds, with earlier phrase development and preserved dynamics.
The boss bus is 0.65 and rises from 45% to full gain over the 2.8-second drawing entrance.
Levels are mastered offline;
runtime plays the stored stereo recording directly with no added synthetic beat.
Loops decode at page load so entering a fight does not perform disk I/O.
Boss channels remain exclusive of calm/action music and respect pause, mute,
retry, return-to-title and page transitions. Short warnings have protected channels.

Recorded pencil/erase/blade sounds and the original notebook effects are
unchanged. Rebuild original effects and fallback desk music with:

```sh
python3 tools/build_audio_assets.py
```

Do not regenerate the archival exploration recordings; their original manifest
verifies unchanged hashes. Legacy import/score preparation scripts describe
older releases and are not part of this release's playback or build path.
