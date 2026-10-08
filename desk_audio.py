"""Original, phase-aligned desk score: taps, scribbles and pencil plucks.

Calm keeps the familiar sparse desk rhythm. Combat accents breathe between
strokes, and each page's boss writes a different short phrase on that rhythm.
"""
from audio_composer import _pcm


# The same desk materials carry all five worlds. These are rhythmic gestures,
# rather than five unrelated genre tracks competing with the paper setting.
PAGE_BOSS_MARKS = (
    (0, 6, 14, 20, 28),        # Deliberate long brush strokes.
    (0, 3, 11, 16, 19, 27),  # Short Western call and response.
    (0, 5, 10, 18, 25),      # Uneven orbital pulses.
    (0, 2, 15, 17, 30),      # A pair of covert carbon marks.
    (0, 7, 12, 20, 27),      # The editor interrupts the familiar pulse.
)


def desk_score(composer, page, energy=0, boss=False):
    page = max(0, min(4, int(page)))
    energy = max(0.0, min(1.0, float(energy)))
    beat = 60 / (76 + page * 4)
    target = composer.silence(32 * beat)
    root = (62, 57, 65, 60, 62)[page]
    accents = (.90, .58, .75, .52)
    for i in range(32):
        at = i * beat
        # Quiet keeps the original tap and phrase; action uses hand-like
        # accents instead of giving every quarter note identical weight.
        if i % 4 == 0 or energy:
            composer._add_impact(
                target, at, 125 + page * 13,
                .028 + energy * .075 * accents[i % 4],
                .06, 902 + i + page * 91,
            )
        if energy and i % 2:
            composer._add_noise(target, at + beat * .5, .13,
                                .040 * energy, 600 + i, "scratch")
        if i in (0, 7, 16, 23):
            interval = (0, 3, 7, 2)[(i // 7) % 4]
            composer._add_note(target, at, .8,
                               composer.midi(root + interval), .055, "pencil")
        if boss and i in PAGE_BOSS_MARKS[page]:
            composer._add_impact(target, at + beat * .5,
                                 74 + page * 5, .085, .16, 100 + i)
            composer._add_noise(target, at + beat * .73, .10,
                                .038, 300 + i, "paper")
            composer._add_note(target, at + beat * .56, .16,
                               composer.midi(root - 5 + i % 3),
                               .027, "pencil")
        elif energy and i % 8 == 6:
            composer._add_noise(target, at, .32, .030 * energy,
                                500 + i, "rub")
    return _pcm(target)
