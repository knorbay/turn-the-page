"""Original procedural score and tactile notebook foley.

The composer is deliberately independent from pygame.  Runtime audio and the
QA renderer consume the same PCM, so the files we audition are the sounds the
game actually plays.  No downloaded or copyrighted samples are required.
"""
from __future__ import annotations

from array import array
import math
import random
import wave


TAU = math.tau

SFX_NAMES = (
    "pencil", "erase", "page", "fold", "tear", "paper_step", "ink",
    "doodle", "dash", "hit", "heavy_hit", "enemy_break", "pistol",
    "shotgun", "cannon", "rubber", "brush", "reload", "pickup",
    "paper_break", "redraw", "giant_step", "giant_stomp",
    "hero_reveal", "hero_sword", "bell", "blade", "blocked",
    "arena_lock", "arena_clear", "boss_reveal", "heart",
    "katana_draw", "katana_cut", "staple", "snip", "ink_burst",
    "compass_sweep", "stamp",
    # Page-specific player tools. Runtime redirects the legacy weapon cue to
    # one of these without requiring callers to know which page is active.
    "bowie_cut", "ion_slice", "field_knife", "revolver",
    "suppressed_shot", "double_barrel", "breach_shotgun",
    "null_cannon", "orbit_pulse",
    # Semantic combat cues are intentionally broader than an enemy class.
    # New actors can ask for a material and role while old calls keep working.
    "enemy_telegraph", "enemy_telegraph_ranged",
    "enemy_telegraph_heavy", "enemy_telegraph_air",
    "enemy_attack_melee", "enemy_attack_ranged", "enemy_attack_charge",
    "enemy_hit_paper", "enemy_hit_ink", "enemy_hit_metal",
    "enemy_death_paper", "enemy_death_ink", "enemy_death_metal",
    "boss_phase_shift", "boss_opening", "boss_signature",
)

# Repeated combat cues receive deterministic alternate renders. The first
# render remains the canonical ``sfx_<name>.wav`` for compatibility; further
# takes are written as ``_v2``, ``_v3`` and so on by the asset builder.
SFX_VARIANT_COUNTS = {
    "blade": 3, "katana_cut": 3, "pistol": 4, "shotgun": 3,
    "cannon": 3, "rubber": 3, "hit": 4, "heavy_hit": 3,
    "enemy_break": 4, "blocked": 3, "ink": 3, "paper_step": 3,
    "staple": 3, "snip": 3, "ink_burst": 3,
    "bowie_cut": 3, "ion_slice": 3, "field_knife": 3,
    "revolver": 4, "suppressed_shot": 4, "double_barrel": 3,
    "breach_shotgun": 3, "null_cannon": 3, "orbit_pulse": 3,
    "enemy_telegraph": 3, "enemy_telegraph_ranged": 3,
    "enemy_telegraph_heavy": 3, "enemy_telegraph_air": 3,
    "enemy_attack_melee": 3, "enemy_attack_ranged": 3,
    "enemy_attack_charge": 3, "enemy_hit_paper": 4,
    "enemy_hit_ink": 4, "enemy_hit_metal": 4,
    "enemy_death_paper": 3, "enemy_death_ink": 3,
    "enemy_death_metal": 3, "boss_phase_shift": 3,
    "boss_opening": 3, "boss_signature": 3,
}


def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _pcm(values) -> array:
    return array("h", (round(_clip(value) * 32767) for value in values))


def mix_pcm(*layers: tuple[array, float], length: int | None = None) -> array:
    """Mix signed 16-bit mono layers without changing their timing."""
    if not layers:
        return array("h")
    size = length if length is not None else max(len(samples) for samples, _ in layers)
    mixed = [0.0] * size
    for samples, gain in layers:
        scale = float(gain) / 32767.0
        for index, sample in enumerate(samples[:size]):
            mixed[index] += sample * scale
    return _pcm(mixed)


def sequence_pcm(parts: list[tuple[array, float]], sample_rate: int,
                 gap: float = .18) -> array:
    """Place preview cues in sequence with a short, audible separation."""
    gap_samples = array("h", [0]) * int(sample_rate * gap)
    output = array("h")
    for samples, gain in parts:
        output.extend(mix_pcm((samples, gain)))
        output.extend(gap_samples)
    return output


def write_wav(path: str, samples: array, sample_rate: int) -> None:
    with wave.open(path, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(samples.tobytes())


class NotebookComposer:
    """Small deterministic synthesizer for page-aware music and paper Foley."""

    PAGE_BPM = (76, 108, 68, 66, 76)
    PAGE_ROOT = (50, 55, 46, 45, 52)

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = int(sample_rate)

    @staticmethod
    def midi(note: float) -> float:
        return 440.0 * 2 ** ((float(note) - 69.0) / 12.0)

    def silence(self, duration: float) -> list[float]:
        return [0.0] * max(1, int(self.sample_rate * duration))

    def _add_note(self, target: list[float], start: float, duration: float,
                  frequency: float, gain: float, instrument: str = "pencil") -> None:
        begin = max(0, round(start * self.sample_rate))
        count = max(1, round(duration * self.sample_rate))
        end = min(len(target), begin + count)
        if begin >= len(target):
            return
        for index in range(begin, end):
            age = (index - begin) / self.sample_rate
            t = age / max(.001, duration)
            attack = min(1.0, age / (.008 if instrument != "air" else .12))
            release = max(0.0, 1.0 - t)
            if instrument == "toy":
                envelope = attack * release ** 2.4
                wave_value = (
                    math.sin(TAU * frequency * age) * .64
                    + math.sin(TAU * frequency * 2.01 * age) * .22
                    + math.sin(TAU * frequency * 3.98 * age) * .10
                )
            elif instrument == "ink":
                envelope = attack * release ** 1.55
                wave_value = (
                    math.sin(TAU * frequency * age)
                    + .25 * math.sin(TAU * frequency * 3 * age)
                    + .12 * math.sin(TAU * frequency * 5 * age)
                ) * .72
            elif instrument == "bass":
                envelope = attack * release ** 1.15
                fall = frequency * (1.0 - .055 * min(1, age / .14))
                wave_value = math.sin(TAU * fall * age) * .82
            elif instrument == "air":
                envelope = attack * math.sin(math.pi * min(1, t)) ** .55
                wave_value = (
                    math.sin(TAU * frequency * age) * .55
                    + math.sin(TAU * frequency * 1.5 * age) * .18
                )
            else:  # graphite/pencil pluck
                envelope = attack * math.exp(-age * 6.5) * release
                wave_value = (
                    math.sin(TAU * frequency * age) * .72
                    + math.sin(TAU * frequency * 2 * age) * .18
                    + math.sin(TAU * frequency * 4.08 * age) * .08
                )
            target[index] += wave_value * envelope * gain

    def _add_noise(self, target: list[float], start: float, duration: float,
                   gain: float, seed: int, texture: str = "paper") -> None:
        begin = max(0, round(start * self.sample_rate))
        count = max(1, round(duration * self.sample_rate))
        end = min(len(target), begin + count)
        rng = random.Random(seed)
        smooth = 0.0
        previous = 0.0
        for index in range(begin, end):
            age = (index - begin) / self.sample_rate
            t = age / max(.001, duration)
            white = rng.uniform(-1.0, 1.0)
            smooth += (white - smooth) * (.08 if texture == "room" else .32)
            high = white - previous
            previous = white
            if texture == "scratch":
                pulse = .35 + .65 * abs(math.sin(TAU * 19 * age))
                sample = high * .52 + white * .22
                envelope = math.sin(math.pi * min(1, t)) ** .4 * pulse
            elif texture == "rub":
                pulse = .45 + .55 * abs(math.sin(TAU * 7.5 * age))
                sample = smooth * .95 + white * .12
                envelope = math.sin(math.pi * min(1, t)) ** .32 * pulse
            elif texture == "tear":
                sample = high * .72 + white * .12
                envelope = (1.0 - t) ** .42 * (.45 + .55 * abs(math.sin(TAU * 31 * age)))
            elif texture == "room":
                sample = smooth
                envelope = .75 + .25 * math.sin(TAU * .11 * age + seed)
            else:
                sample = white * .58 + smooth * .42
                envelope = math.sin(math.pi * min(1, t)) ** .48
            target[index] += sample * envelope * gain

    def _add_impact(self, target: list[float], start: float, frequency: float,
                    gain: float, duration: float = .28, seed: int = 1) -> None:
        self._add_note(target, start, duration, frequency, gain, "bass")
        self._add_noise(target, start, min(.12, duration), gain * .42,
                        seed, "tear")

    def _add_chirp(self, target: list[float], start: float, duration: float,
                   start_frequency: float, end_frequency: float,
                   gain: float, seed: int = 1) -> None:
        """Add a short pitched gesture with a paper-soft attack and tail."""
        begin = max(0, round(start * self.sample_rate))
        count = max(1, round(duration * self.sample_rate))
        end = min(len(target), begin + count)
        rng = random.Random(seed)
        phase = 0.0
        for index in range(begin, end):
            age = (index - begin) / self.sample_rate
            progress = age / max(.001, duration)
            frequency = start_frequency + (end_frequency - start_frequency) * progress
            phase += TAU * frequency / self.sample_rate
            edge = math.sin(math.pi * min(1.0, progress)) ** .62
            flutter = 1.0 + rng.uniform(-.012, .012)
            target[index] += (
                math.sin(phase) * .72 + math.sin(phase * 2.01) * .18
            ) * edge * gain * flutter

    def ambience(self, page: int, duration: float | None = None) -> array:
        page = max(0, min(4, int(page)))
        duration = float(duration or (16 * 60 / self.PAGE_BPM[page]))
        target = self.silence(duration)
        self._add_noise(target, 0, duration, .040, 1701 + page * 401, "room")
        # Sparse diegetic events keep the room alive without becoming a looped beat.
        if page == 0:
            for beat, pitch in ((1.2, 1120), (4.2, 920), (7.0, 1260), (9.7, 870)):
                if beat < duration:
                    self._add_noise(target, beat, .28, .035, 40 + round(beat * 10), "scratch")
                    self._add_note(target, beat + .03, .06, pitch, .012, "pencil")
            for tick in (1.5, 3.0, 6.0, 9.0):
                if tick < duration:
                    self._add_note(target, tick, .055, 1480, .018, "toy")
        elif page == 1:
            for beat in (1.1, 3.6, 6.2, 8.4):
                if beat < duration:
                    self._add_note(target, beat, .05, 530, .022, "ink")
                    self._add_noise(target, beat + .08, .34, .026, 700 + round(beat * 20), "rub")
        elif page == 2:
            for beat in (1.6, 5.0, 8.3, 11.2):
                if beat < duration:
                    self._add_noise(target, beat, .52, .034, 1100 + round(beat * 30), "rub")
            for beat in (3.2, 9.1):
                if beat < duration:
                    self._add_impact(target, beat, 38, .035, .45, 1200 + round(beat * 10))
        elif page == 3:
            for beat in (2.0, 5.3, 8.8):
                if beat < duration:
                    self._add_noise(target, beat, .75, .025, 1600 + round(beat), "paper")
        return _pcm(target)

    def classroom(self, duration: float = 24.0) -> array:
        """Original, deliberately unintelligible distant conversational babble.

        Four independent vowel/formant voices use irregular syllable and breath
        rhythms. There is no text, speech model, recording, or sampled person.
        The runtime places this below the score, never in the foreground.
        """
        target = self.silence(duration)
        vowels = ((430, 1120), (570, 1380), (350, 1570), (640, 1010))
        for voice, pitch in enumerate((111, 143, 184, 223)):
            rng = random.Random(71243 + voice * 137)
            at = .18 + voice * .39
            while at < duration - .5:
                for syllable in range(rng.randint(3, 7)):
                    span = rng.uniform(.10, .25)
                    frequency = pitch * rng.uniform(.92, 1.08)
                    formants = rng.choice(vowels)
                    harmonics = []
                    for partial in range(1, 14):
                        hz = frequency * partial
                        if hz > 1900:
                            break
                        # Two broad vowel resonances, rolled off by classroom
                        # distance. Random phrase endings prevent a metronome.
                        weight = sum(math.exp(-((hz - f) / 180) ** 2)
                                     for f in formants)
                        harmonics.append((hz, (weight + .06) / partial ** .55))
                    gain = .051 * rng.uniform(.65, 1.0)
                    begin = round(at * self.sample_rate)
                    end = min(len(target), begin + round(span * self.sample_rate))
                    for index in range(begin, end):
                        age = (index - begin) / self.sample_rate
                        envelope = math.sin(math.pi * min(1, age / span)) ** .65
                        glide = age + .006 * age * age / span
                        voiced = sum(math.sin(TAU * hz * glide) * weight
                                     for hz, weight in harmonics)
                        target[index] += voiced * envelope * gain
                    at += span + rng.uniform(.018, .065)
                    if at >= duration - .4:
                        break
                at += rng.uniform(.35, 1.15)
        # Soft room reflections smear the syllables; the loop has a short
        # seamless floor of air and no intelligible dialogue.
        dry = target[:]
        for delay, gain in ((.043, .24), (.081, .15), (.127, .08)):
            offset = round(delay * self.sample_rate)
            for index in range(offset, len(target)):
                target[index] += dry[index - offset] * gain
        self._add_noise(target, 0, duration, .012, 81023, "room")
        for index in range(len(target)):
            edge = min(index, len(target) - 1 - index) / self.sample_rate
            target[index] *= min(1.0, edge / .12)
        return _pcm(target)

    def _school_bell(self) -> array:
        """Two electromechanical school-bell bursts with an inharmonic tail."""
        duration = 2.85
        target = self.silence(duration)
        # Hammer strikes excite a metal cup, rather than a three-note chime.
        strikes = [start + hit / 27.0 for start in (0.0, 1.04)
                   for hit in range(19)]
        for at in strikes:
            begin = round(at * self.sample_rate)
            count = min(len(target) - begin, round(.91 * self.sample_rate))
            for offset in range(count):
                age = offset / self.sample_rate
                # Cup modes are intentionally non-harmonic.
                metal = (math.sin(TAU * 648 * age) * math.exp(-age * 5.2)
                         + .56 * math.sin(TAU * 1103 * age) * math.exp(-age * 7.0)
                         + .34 * math.sin(TAU * 1717 * age) * math.exp(-age * 9.0)
                         + .19 * math.sin(TAU * 2543 * age) * math.exp(-age * 12.0))
                target[begin + offset] += metal * .11 * min(1.0, age / .001)
            self._add_noise(target, at, .007, .07, 3600 + begin, "tear")
        peak = max(abs(value) for value in target)
        return _pcm(value * .74 / max(.74, peak) for value in target)

    def score(self, page: int, energy: float = 0.0, boss: bool = False) -> array:
        """Compose a loop from shared Artist and Stickman motifs.

        Low and high energy calls use the same tempo and length.  Runtime can
        therefore keep both playing in phase and crossfade immediately.
        """
        page = max(0, min(4, int(page)))
        bpm = self.PAGE_BPM[page]
        beat = 60.0 / bpm
        beats = 16
        duration = beats * beat
        target = self.silence(duration)
        root = self.PAGE_ROOT[page]
        energy = max(0.0, min(1.0, float(energy)))

        if boss:
            # Each world's named drawings get an authored phrase instead of
            # simply restarting the normal action file.
            phrases = {
                0: ((12, 19, 13, 20, 15, 22), "pluck"),
                1: ((12, 15, 17, 18, 22, 20), "ink"),
                2: ((12, 13, 19, 18, 15, 12), "toy"),
            }
            proof, instrument = phrases.get(page, ((12, 16, 14, 19, 16, 12), "toy"))
            for index, interval in enumerate(proof):
                at = index * 2 * beat
                self._add_note(target, at, beat * 1.55,
                               self.midi(root + interval), .115, instrument)
            for index in range(beats):
                at = index * beat
                if index % 2 == 0:
                    self._add_impact(target, at, 39 if index % 4 else 32,
                                     .16, .34, 6000 + index)
                if index in (3, 7, 11, 15):
                    self._add_noise(target, at, .22, .055, 6200 + index, "tear")
            # The shared Artist motif remains audible: the creator is still in the room.
            for index, interval in enumerate((0, 7, 3)):
                self._add_note(target, (8 + index) * beat,
                               beat * .72, self.midi(root + interval), .082, "ink")
            return _pcm(target)

        chords = {
            0: ((0, 3, 7), (-2, 3, 7), (0, 5, 9), (-2, 2, 7)),
            1: ((0, 4, 7), (-2, 2, 7), (0, 5, 9), (2, 5, 9)),
            2: ((0, 3, 7), (-1, 3, 7), (-3, 2, 7), (-2, 3, 8)),
            3: ((0, 2, 7), (-2, 3, 7), (0, 5, 9), (-3, 2, 7)),
            4: ((0, 4, 7), (2, 5, 9), (-2, 2, 7), (0, 5, 9)),
        }[page]
        pad_instrument = "air" if page in (3, 4) else "pencil"
        for bar, chord in enumerate(chords):
            at = bar * 4 * beat
            for interval in chord:
                self._add_note(target, at, 3.65 * beat,
                               self.midi(root + interval), .028, pad_instrument)

        # Artist: three deliberate marks. Stickman: a four-note answer that keeps moving.
        artist_motif = (0, 7, 3)
        stickman_motif = (0, 2, 7, 5)
        lead = "toy" if page in (0, 2) else "ink"
        for phrase in (0, 8):
            for index, interval in enumerate(artist_motif):
                self._add_note(target, (phrase + index) * beat,
                               beat * .72, self.midi(root + 12 + interval), .080, lead)
            for index, interval in enumerate(stickman_motif):
                self._add_note(target, (phrase + 3.5 + index * .75) * beat,
                               beat * .46, self.midi(root + 12 + interval), .065, "pencil")

        if energy > .05:
            for index in range(beats):
                at = index * beat
                bass_note = root - 12 + chords[index // 4][0]
                self._add_note(target, at, beat * .72,
                               self.midi(bass_note), .075 * energy, "bass")
                if index % 2 == 0:
                    self._add_impact(target, at, 72 if page == 1 else 58,
                                     .055 * energy, .18, 3000 + page * 100 + index)
                else:
                    self._add_noise(target, at, .09, .030 * energy,
                                    3500 + page * 100 + index, "scratch")
            # Combat variation writes over the motif, rather than replacing it.
            for index, interval in enumerate((7, 5, 3, 2, 0, -2, 0, 3)):
                self._add_note(target, (7 + index * .5) * beat, beat * .28,
                               self.midi(root + 12 + interval), .055 * energy, "ink")
        return _pcm(target)

    def sfx(self, name: str, variation: int = 0) -> array:
        """Render one deterministic take of a cue.

        ``variation=0`` preserves the original canonical render. Alternate
        takes change oscillator pitch, material noise and tiny layer timings;
        they never depend on global random state.
        """
        specs = {
            "pencil": (.24, "scratch", 930),
            "erase": (.34, "rub", 290),
            "page": (.62, "page", 120),
            "fold": (.48, "paper", 180),
            "tear": (.34, "tear", 145),
            "paper_step": (.08, "tap", 520),
            "ink": (.17, "ink", 185),
            "doodle": (.13, "pencil", 720),
            "dash": (.13, "swish", 670),
            "hit": (.09, "hit", 260),
            "heavy_hit": (.18, "heavy", 110),
            "enemy_break": (.28, "break", 84),
            "pistol": (.10, "snap", 830),
            "shotgun": (.22, "marker", 105),
            "cannon": (.30, "heavy", 58),
            "rubber": (.15, "rubber", 910),
            "brush": (.26, "brush", 170),
            "reload": (.18, "cap", 460),
            "pickup": (.42, "pickup", 740),
            "paper_break": (.38, "tear", 92),
            "redraw": (.82, "redraw", 1040),
            "giant_step": (.34, "giant", 42),
            "giant_stomp": (.56, "giant", 31),
            "hero_reveal": (1.45, "hero", 523),
            "hero_sword": (.55, "sword", 118),
            "bell": (2.85, "bell", 648),
            "blade": (.19, "swish", 740),
            "blocked": (.16, "blocked", 640),
            "arena_lock": (.38, "arena_lock", 76),
            "arena_clear": (.56, "arena_clear", 620),
            "boss_reveal": (.72, "boss_reveal", 44),
            "heart": (.34, "heart", 660),
            "katana_draw": (.47, "katana_draw", 1480),
            "katana_cut": (.29, "katana_cut", 920),
            "staple": (.24, "staple", 280),
            "snip": (.31, "snip", 1370),
            "ink_burst": (.27, "ink_burst", 160),
            "compass_sweep": (.63, "compass_sweep", 790),
            "stamp": (.29, "stamp", 84),
            "bowie_cut": (.24, "bowie_cut", 680),
            "ion_slice": (.31, "ion_slice", 420),
            "field_knife": (.18, "field_knife", 760),
            "revolver": (.19, "revolver", 118),
            "suppressed_shot": (.14, "suppressed_shot", 155),
            "double_barrel": (.34, "double_barrel", 76),
            "breach_shotgun": (.27, "breach_shotgun", 96),
            "null_cannon": (.46, "null_cannon", 52),
            "orbit_pulse": (.32, "orbit_pulse", 510),
            "enemy_telegraph": (.25, "enemy_telegraph", 780),
            "enemy_telegraph_ranged": (.37, "enemy_telegraph_ranged", 410),
            "enemy_telegraph_heavy": (.51, "enemy_telegraph_heavy", 66),
            "enemy_telegraph_air": (.42, "enemy_telegraph_air", 930),
            "enemy_attack_melee": (.22, "enemy_attack_melee", 610),
            "enemy_attack_ranged": (.25, "enemy_attack_ranged", 205),
            "enemy_attack_charge": (.39, "enemy_attack_charge", 74),
            "enemy_hit_paper": (.16, "enemy_hit_paper", 180),
            "enemy_hit_ink": (.16, "enemy_hit_ink", 235),
            "enemy_hit_metal": (.18, "enemy_hit_metal", 720),
            "enemy_death_paper": (.39, "enemy_death_paper", 112),
            "enemy_death_ink": (.44, "enemy_death_ink", 94),
            "enemy_death_metal": (.48, "enemy_death_metal", 145),
            "boss_phase_shift": (.86, "boss_phase_shift", 58),
            "boss_opening": (.54, "boss_opening", 118),
            "boss_signature": (.72, "boss_signature", 46),
        }
        duration, kind, frequency = specs.get(name, (.16, "hit", 330))
        target = self.silence(duration)
        variation = max(0, int(variation))
        seed = (sum((index + 1) * ord(char) for index, char in enumerate(name))
                + variation * 7919)
        if variation:
            frequency *= (1.0, .955, 1.038, .982)[variation % 4]
        if kind in ("scratch", "pencil"):
            self._add_noise(target, 0, duration, .25, seed, "scratch")
            self._add_note(target, .01, min(.13, duration), frequency, .07, "pencil")
        elif kind in ("rub", "brush"):
            self._add_noise(target, 0, duration, .31, seed, "rub")
            self._add_note(target, .03, duration * .7, frequency, .035, "air")
        elif kind in ("page", "paper"):
            self._add_noise(target, 0, duration, .32, seed, "paper")
            self._add_noise(target, duration * .58, duration * .34, .24, seed + 1, "tear")
        elif kind in ("tear", "break"):
            self._add_noise(target, 0, duration, .38, seed, "tear")
            self._add_impact(target, duration * .42, frequency, .13, .18, seed + 2)
        elif kind in ("heavy", "giant"):
            self._add_impact(target, 0, frequency, .47 if kind == "giant" else .34,
                             duration, seed)
            self._add_noise(target, .015, min(.22, duration), .17, seed + 1, "tear")
        elif kind in ("ink", "marker"):
            self._add_note(target, 0, duration, frequency, .18, "ink")
            self._add_noise(target, .01, duration, .20, seed, "rub")
        elif kind in ("snap", "tap", "cap"):
            self._add_impact(target, 0, frequency, .24, duration, seed)
        elif kind == "swish":
            self._add_noise(target, 0, duration, .29, seed, "tear")
            for index in range(len(target)):
                t = index / max(1, len(target) - 1)
                target[index] *= math.sin(math.pi * t)
        elif kind == "rubber":
            self._add_note(target, 0, duration, frequency, .16, "toy")
            self._add_note(target, .035, duration * .75, frequency * .61, .09, "ink")
        elif kind == "pickup":
            for index, interval in enumerate((0, 4, 7)):
                self._add_note(target, index * .08, .28,
                               frequency * 2 ** (interval / 12), .12, "toy")
        elif kind == "redraw":
            for index in range(5):
                self._add_noise(target, index * .135, .19, .21, seed + index, "scratch")
                self._add_note(target, index * .135, .12,
                               frequency * (1 + index * .035), .035, "pencil")
        elif kind == "bell":
            return self._school_bell()
        elif kind == "hero":
            intervals = (0, 7, 12, 16)
            for index, interval in enumerate(intervals):
                self._add_note(target, index * (.16 if kind == "hero" else .05),
                               duration - index * .1,
                               frequency * 2 ** (interval / 12), .13, "toy")
            if kind == "hero":
                self._add_impact(target, .62, 54, .18, .45, seed + 5)
        elif kind == "sword":
            self._add_impact(target, 0, frequency, .34, duration, seed)
            self._add_note(target, .03, duration, 1046, .12, "toy")
            self._add_noise(target, .04, .22, .13, seed + 1, "scratch")
        elif kind == "blocked":
            self._add_impact(target, 0, frequency, .25, .12, seed)
            self._add_note(target, .015, .13, frequency * 2.34, .12, "toy")
        elif kind == "arena_lock":
            self._add_impact(target, 0, frequency, .30, .26, seed)
            self._add_impact(target, .12, frequency * .82, .24, .24, seed + 1)
            self._add_noise(target, .03, .28, .12, seed + 2, "scratch")
        elif kind == "arena_clear":
            self._add_noise(target, 0, .26, .18, seed, "rub")
            for index, interval in enumerate((0, 4, 9)):
                self._add_note(target, .08 + index * .08, .32,
                               frequency * 2 ** (interval / 12), .10, "toy")
        elif kind == "boss_reveal":
            self._add_impact(target, 0, frequency, .40, .58, seed)
            self._add_noise(target, .04, .62, .22, seed + 1, "tear")
            self._add_note(target, .12, .54, 92, .13, "ink")
        elif kind == "heart":
            self._add_note(target, 0, .24, frequency, .13, "toy")
            self._add_note(target, .09, .25, frequency * 1.5, .12, "toy")
        elif kind == "katana_draw":
            self._add_noise(target, 0, .31, .16, seed, "scratch")
            self._add_note(target, .11, .35, frequency, .13, "toy")
            self._add_note(target, .13, .27, frequency * 1.43, .048, "toy")
            self._add_impact(target, .018, 350, .13, .055, seed + 1)
        elif kind == "katana_cut":
            self._add_noise(target, 0, .18, .40, seed, "tear")
            self._add_note(target, .075, .19, frequency, .10, "toy")
            self._add_impact(target, .105, 150, .21, .12, seed + 1)
        elif kind == "staple":
            self._add_impact(target, 0, 390, .30, .05, seed)
            self._add_impact(target, .052, 180, .34, .08, seed + 1)
            self._add_note(target, .069, .15, 1610, .06, "toy")
            self._add_noise(target, .12, .06, .12, seed + 2, "scratch")
        elif kind == "snip":
            self._add_noise(target, 0, .16, .19, seed, "scratch")
            self._add_impact(target, .105, 560, .24, .07, seed + 1)
            self._add_note(target, .11, .17, frequency, .09, "toy")
            self._add_note(target, .12, .16, frequency * 1.61, .038, "toy")
        elif kind == "ink_burst":
            for index in range(3):
                at = index * .039
                self._add_note(target, at, .12, frequency * (1 - index * .14), .21, "bass")
                self._add_noise(target, at + .015, .10, .16, seed + index, "rub")
            self._add_noise(target, .09, .15, .12, seed + 4, "paper")
        elif kind == "compass_sweep":
            self._add_impact(target, 0, 420, .12, .075, seed)
            self._add_noise(target, .05, .49, .21, seed + 1, "scratch")
            self._add_note(target, .34, .28, frequency, .055, "toy")
        elif kind == "stamp":
            self._add_impact(target, .012, frequency, .45, .17, seed)
            self._add_noise(target, 0, .07, .29, seed + 1, "paper")
            self._add_noise(target, .11, .13, .12, seed + 2, "rub")
        elif kind == "bowie_cut":
            self._add_noise(target, 0, .17, .31, seed, "tear")
            self._add_impact(target, .035, frequency * .42, .17, .07, seed + 1)
            self._add_note(target, .052, .16, frequency * 1.9, .055, "toy")
        elif kind == "ion_slice":
            self._add_chirp(target, 0, .22, frequency * .72,
                            frequency * 2.25, .20, seed)
            self._add_noise(target, .035, .17, .13, seed + 1, "paper")
            self._add_note(target, .105, .18, frequency * 2.62, .055, "air")
        elif kind == "field_knife":
            self._add_noise(target, 0, .12, .27, seed, "scratch")
            self._add_impact(target, .062, frequency * .31, .17, .065, seed + 1)
        elif kind == "revolver":
            self._add_impact(target, 0, frequency, .42, .16, seed)
            self._add_noise(target, 0, .045, .34, seed + 1, "tear")
            self._add_note(target, .018, .16, 1280 * frequency / 118, .07, "toy")
            self._add_impact(target, .102, frequency * 1.7, .09, .05, seed + 2)
        elif kind == "suppressed_shot":
            self._add_impact(target, 0, frequency, .19, .095, seed)
            self._add_noise(target, 0, .065, .15, seed + 1, "rub")
            self._add_note(target, .012, .09, frequency * 5.4, .045, "pencil")
        elif kind == "double_barrel":
            self._add_impact(target, 0, frequency, .47, .28, seed)
            self._add_noise(target, 0, .16, .31, seed + 1, "tear")
            self._add_impact(target, .035, frequency * .83, .28, .24, seed + 2)
            self._add_noise(target, .17, .14, .12, seed + 3, "paper")
        elif kind == "breach_shotgun":
            self._add_impact(target, 0, frequency, .40, .21, seed)
            self._add_noise(target, .004, .085, .25, seed + 1, "tear")
            self._add_note(target, .024, .17, frequency * 6.1, .045, "toy")
        elif kind == "null_cannon":
            self._add_chirp(target, 0, .36, frequency * 2.4,
                            frequency * .68, .30, seed)
            self._add_noise(target, .025, .38, .22, seed + 1, "rub")
            self._add_impact(target, .06, frequency, .31, .33, seed + 2)
        elif kind == "orbit_pulse":
            self._add_note(target, 0, .24, frequency, .16, "toy")
            self._add_note(target, .038, .25, frequency * 1.5, .12, "ink")
            self._add_chirp(target, .08, .18, frequency * .7,
                            frequency * 1.18, .09, seed)
        elif kind == "enemy_telegraph":
            for index, ratio in enumerate((1.0, 1.18, 1.42)):
                self._add_note(target, index * .057, .16, frequency * ratio,
                               .09, "pencil")
            self._add_noise(target, 0, .21, .08, seed, "scratch")
        elif kind == "enemy_telegraph_ranged":
            self._add_chirp(target, 0, .28, frequency * .72,
                            frequency * 1.38, .16, seed)
            self._add_noise(target, .045, .24, .12, seed + 1, "rub")
            self._add_note(target, .19, .14, frequency * 1.8, .07, "ink")
        elif kind == "enemy_telegraph_heavy":
            self._add_impact(target, 0, frequency, .25, .31, seed)
            self._add_impact(target, .21, frequency * .82, .18, .24, seed + 1)
            self._add_noise(target, .06, .39, .13, seed + 2, "scratch")
        elif kind == "enemy_telegraph_air":
            self._add_noise(target, 0, .33, .22, seed, "paper")
            self._add_chirp(target, .04, .31, frequency * .78,
                            frequency * 1.31, .075, seed + 1)
        elif kind == "enemy_attack_melee":
            self._add_noise(target, 0, .16, .33, seed, "tear")
            self._add_impact(target, .08, frequency * .27, .18, .12, seed + 1)
        elif kind == "enemy_attack_ranged":
            self._add_note(target, 0, .19, frequency, .18, "ink")
            self._add_noise(target, .012, .13, .18, seed, "rub")
            self._add_impact(target, .025, frequency * .55, .10, .08, seed + 1)
        elif kind == "enemy_attack_charge":
            self._add_chirp(target, 0, .31, frequency * 1.35,
                            frequency * .63, .14, seed)
            self._add_noise(target, .02, .34, .24, seed + 1, "tear")
            self._add_impact(target, .22, frequency, .24, .16, seed + 2)
        elif kind == "enemy_hit_paper":
            self._add_noise(target, 0, .13, .30, seed, "paper")
            self._add_impact(target, .018, frequency, .19, .10, seed + 1)
        elif kind == "enemy_hit_ink":
            self._add_note(target, 0, .14, frequency, .19, "ink")
            self._add_noise(target, .01, .12, .19, seed, "rub")
            self._add_impact(target, .035, frequency * .52, .12, .09, seed + 1)
        elif kind == "enemy_hit_metal":
            self._add_impact(target, 0, frequency * .32, .20, .11, seed)
            self._add_note(target, .012, .16, frequency, .13, "toy")
            self._add_note(target, .018, .14, frequency * 1.57, .06, "toy")
        elif kind == "enemy_death_paper":
            self._add_noise(target, 0, .34, .36, seed, "tear")
            self._add_impact(target, .13, frequency, .21, .20, seed + 1)
            self._add_noise(target, .24, .12, .10, seed + 2, "paper")
        elif kind == "enemy_death_ink":
            for index in range(3):
                at = index * .055
                self._add_note(target, at, .22, frequency * (1 - index * .16),
                               .18, "ink")
                self._add_noise(target, at, .15, .14, seed + index, "rub")
            self._add_impact(target, .20, frequency * .52, .15, .18, seed + 4)
        elif kind == "enemy_death_metal":
            self._add_impact(target, 0, frequency, .31, .24, seed)
            for index, ratio in enumerate((3.8, 5.1, 6.7)):
                self._add_note(target, .035 + index * .046, .33,
                               frequency * ratio, .075 / (1 + index * .2), "toy")
            self._add_noise(target, .20, .22, .11, seed + 3, "paper")
        elif kind == "boss_phase_shift":
            self._add_impact(target, 0, frequency, .38, .61, seed)
            self._add_chirp(target, .06, .56, frequency * 1.7,
                            frequency * 5.2, .13, seed + 1)
            for index, ratio in enumerate((1.0, 1.5, 2.0)):
                self._add_note(target, .24 + index * .095, .42,
                               frequency * ratio, .10, "ink")
            self._add_noise(target, .08, .66, .14, seed + 4, "tear")
        elif kind == "boss_opening":
            self._add_impact(target, 0, frequency, .28, .36, seed)
            self._add_noise(target, .035, .42, .18, seed + 1, "paper")
            for index, ratio in enumerate((3.0, 4.0, 5.5)):
                self._add_note(target, .10 + index * .06, .31,
                               frequency * ratio, .075, "toy")
        elif kind == "boss_signature":
            self._add_impact(target, 0, frequency, .42, .58, seed)
            self._add_noise(target, .025, .54, .23, seed + 1, "tear")
            self._add_chirp(target, .08, .48, frequency * 2.1,
                            frequency * .92, .14, seed + 2)
            self._add_note(target, .31, .35, frequency * 4.0, .09, "ink")
        else:
            self._add_impact(target, 0, frequency, .25, duration, seed)
        return _pcm(target)

    def build_bank(self) -> dict:
        ambience = [self.ambience(page) for page in range(5)]
        low = [self.score(page, 0) for page in range(5)]
        high = [self.score(page, 1) for page in range(5)]
        boss = [self.score(page, 1, True) for page in range(5)]
        return {
            "sfx": {name: self.sfx(name) for name in SFX_NAMES},
            "ambience": ambience,
            "score_low": low,
            "score_high": high,
            "score_boss": boss,
            "classroom": self.classroom(),
        }
