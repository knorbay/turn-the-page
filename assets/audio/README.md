# Runtime audio bank

The compact WAV bank contains original deterministic renders from
`audio_composer.py`. The first three pages also use selected CC0
music and three recorded material sounds under `music/` and `recorded/`.
Their exact authors, licenses, source pages, and file mapping are recorded in
`THIRD_PARTY.md`.

Rebuild the complete canonical bank with:

```bash
python3 tools/build_audio_assets.py
```

`audio.py` caches decoded tracks, loads the chosen CC0 calm/action pairs, and
deliberately loads the separate locally authored boss WAV
for its named fights. It falls back to live composition if an asset is missing.
Pages 4–5 have their own included, locally composed calm/action/boss WAVs.

The school pass adds these original sounds, without additional recordings:

- `sfx_bell.wav`: two electromechanical school-bell bursts, 2.85 seconds,
  with an inharmonic metal-cup tail. This replaces the old melodic chime.
- `classroom_babble.wav`: a 24-second looping layer of four synthesized,
  distant, unintelligible voices. It contains no words, sampled people or
  actual classroom recording. Irregular syllable groups and room reflections
  evoke conversation under the music.
- `sfx_katana_draw.wav`, `sfx_katana_cut.wav`, `sfx_staple.wav`,
  `sfx_snip.wav`, `sfx_ink_burst.wav`, `sfx_compass_sweep.wav`, and
  `sfx_stamp.wav`: seven different material/attack cues.

The combat-polish bank adds 25 locally synthesized cue families and alternate
takes. Page-specific tools now have separate physical signatures: bowie and
field-knife cuts, an electronic ion slice, revolver and suppressed shots,
double-barrel and breach blasts, a null cannon, and an orbit pulse. Enemy cues
are grouped by readable action (telegraph, melee/ranged/charge attack) and by
paper, ink, or metal hit/death material. Bosses can punctuate a phase change,
vulnerability opening, or signature move with `boss_phase_shift`,
`boss_opening`, and `boss_signature`.

Repeated cues have deterministic `_v2`, `_v3`, and where useful `_v4` WAVs.
Runtime rotates those takes, applies a small bounded pitch cycle, and enforces
per-cue cooldowns so shotgun pellets and simultaneous enemy hits do not stack
into clipping. `NotebookSounds.play(name)` remains valid; optional callers can
also supply `variant`, `pitch`, `volume`, and `cooldown_ms`.

The bell uses the SFX and master sliders, with a 0.60 cue gain to sit beside
the strong combat impacts. Music falls to 40% during the ring
and returns smoothly over its final 650 ms. Music, ambient Foley, classroom
voices and the bell each use reserved channels, so combat bursts cannot
interrupt them. Classroom voices use the music and master sliders, are mixed
very quietly for each page's recording level, and recede sharply during combat
and boss encounters. Heavy attacks briefly make headroom in both music layers,
then release without stopping or restarting the score. Baby-Face's reveal,
stomps and hero sword are unchanged.
