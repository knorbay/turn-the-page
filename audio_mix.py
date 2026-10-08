"""Condition tactile effects and reserve headroom for simultaneous voices."""
from array import array
import math

EFFECT_GAIN_BUDGET = 1.65
REPEATED_PEAK = .27
SIGNATURE_PEAK = .34
BOSS_MUSIC_RMS = .11
BOSS_MUSIC_PEAK = .74
# (body pitch, resting pitch, tail, shell pitch): a different material per page.
_BOSS_DRUMS = ((94, 54, .22, 220), (78, 49, .15, 290),
               (70, 36, .28, 110), (132, 80, .12, 340),
               (82, 42, .25, 174))


def boss_music_pcm(raw, rate=22050, channels=2, page=None):
    """Keep the original melody and add a bounded, dry boss-only pulse.

    The five restored boss recordings each contain sixteen beats. Material
    accents follow those beats without a second playback channel or a delay.
    Preparation happens at page load. Unknown/fallback pages get gain only.
    Original files, tempo and loop length are never edited.
    """
    source = array("h")
    source.frombytes(raw)
    if not source:
        return raw
    peak = max(abs(value) for value in source)
    if not peak:
        return raw
    rms = math.sqrt(sum(value * value for value in source) / len(source))
    gain = min(.09 * 32768 / rms,
               BOSS_MUSIC_PEAK * 32767 / peak)
    if page is None or not 0 <= page < len(_BOSS_DRUMS):
        return array("h", (round(value * gain) for value in source)).tobytes()
    frames = len(source) // channels
    body, resting, tail, shell = _BOSS_DRUMS[page]
    # Keep the familiar melody at its previous gain. Only the added drum uses
    # remaining peak headroom, so a stronger hit never pushes the score down.
    mixed = [value * gain for value in source]
    length = round(tail * rate)
    for beat in range(0, 16, 2):
        start = round(beat * frames / 16)
        strength = .42 if beat % 4 == 0 else .29
        for offset in range(min(length, frames - start)):
            t = offset / rate
            envelope = (1 - math.exp(-t * 1400)) * math.exp(-t * 12 / (tail / .22))
            phase = math.tau * (resting * t + (body - resting) * .025 * (1 - math.exp(-t / .025)))
            pulse = math.sin(phase) * envelope
            pulse += .20 * math.sin(math.tau * shell * t) * math.exp(-t * 65)
            pulse += .09 * math.sin(math.tau * 1700 * t) * math.exp(-t * 500)
            # A short end taper makes every accent settle before the next hit.
            pulse *= min(1.0, (length - 1 - offset) / max(1, round(rate * .006)))
            value = pulse * strength * 32767
            index = (start + offset) * channels
            available = min(BOSS_MUSIC_PEAK * 32767 - math.copysign(1, value) * mixed[index + c]
                            for c in range(channels))
            value = math.copysign(min(abs(value), max(0, available) * .96), value)
            for channel in range(channels):
                mixed[index + channel] += value
    mixed_peak = max(abs(value) for value in mixed)
    mixed_rms = math.sqrt(sum(value * value for value in mixed) / len(mixed))
    finish_gain = min(1.0, BOSS_MUSIC_PEAK * 32767 / mixed_peak,
                      BOSS_MUSIC_RMS * 32768 / mixed_rms)
    return array("h", (round(value * finish_gain) for value in mixed)).tobytes()


def condition_pcm(raw, rate, channels=1, signature=False):
    """Remove brittle highs/DC, match energy, and taper PCM boundaries.

    This processes the recordings and synthesized fallback equally. It never
    edits licensed source assets. The peak ceiling plus the voice gain budget
    leaves space for score, ambience, and protected boss/bell channels.
    """
    source = array("h")
    source.frombytes(raw)
    if not source:
        return raw
    cutoff = 3200 if signature else 2300
    coefficient = 1 - math.exp(-math.tau * cutoff / rate)
    first = [0.0] * channels
    second = [0.0] * channels
    filtered = []
    for i, sample in enumerate(source):
        channel = i % channels
        first[channel] += coefficient * (sample - first[channel])
        second[channel] += coefficient * (first[channel] - second[channel])
        filtered.append(second[channel])
    means = [sum(filtered[c::channels]) / max(1, len(filtered[c::channels]))
             for c in range(channels)]
    frames = len(source) // channels
    fade = max(1, round(rate * .003))
    for i in range(len(filtered)):
        frame = i // channels
        envelope = max(0, min(1.0, frame / fade, (frames - 1 - frame) / fade))
        filtered[i] = (filtered[i] - means[i % channels]) * envelope
    peak = max(abs(v) for v in filtered)
    rms = math.sqrt(sum(v*v for v in filtered) / len(filtered))
    ceiling = SIGNATURE_PEAK if signature else REPEATED_PEAK
    target = .08 if signature else .062
    gain = min(2.0, ceiling * 32767 / max(1, peak),
               target * 32767 / max(1, rms))
    return array("h", (round(v * gain) for v in filtered)).tobytes()


def voice_gains(requested):
    total = sum(max(0, v) for v in requested)
    scale = min(1.0, EFFECT_GAIN_BUDGET / max(.001, total))
    return [max(0, v) * scale for v in requested]
