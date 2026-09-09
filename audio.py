from __future__ import annotations

import math
from pathlib import Path

import pygame

from audio_composer import NotebookComposer, SFX_NAMES


_RAW_BANKS: dict[int, dict] = {}
_SOUND_CACHE: dict[tuple[int, str], pygame.mixer.Sound] = {}

SELECTED_PAGE_TRACKS = {
    0: {"calm": "music/page_0_calm.ogg", "action": "music/page_0_action.ogg"},
    1: {"calm": "music/page_1_calm.mp3", "action": "music/page_1_action.mp3"},
    2: {"calm": "music/page_2_calm.mp3", "action": "music/page_2_action.mp3"},
}

RECORDED_SFX = {
    "pencil": "recorded/pencil_write.ogg",
    "erase": "recorded/pencil_erase.ogg",
    "blade": "recorded/blade_swing.wav",
}

# The selected sci-fi recording is intentionally quiet. Keep the classroom
# behind each page's own score instead of letting it dominate that page.
CLASSROOM_PAGE_GAIN = (.72, 1.0, .20, .58, .58)


class NotebookSounds:
    """Page-aware original score and tactile paper-world sound system.

    Runtime WAVs are built from the included deterministic composer. Missing
    assets fall back to the same local synthesis. Calm and action scores share
    tempo/length, remain phase aligned, and crossfade with encounter pressure.
    """

    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.ambience = [None] * 5
        self.score_low = [None] * 5
        self.score_high = [None] * 5
        self.score_boss = [None] * 5
        self.ambient_channel = None
        self.score_channel = None
        self.combat_channel = None
        self.classroom_channel = None
        self.bell_channel = None
        self.classroom_sound = None
        self.bell_duck_until = 0
        self.ambient_chapter = -1
        self.master_volume = .8
        self.sfx_volume = .85
        self.music_volume = .55
        self.combat_active = False
        self.boss_active = False
        self.action_variant = "page"
        self.intensity = 0.0
        self.quiet = False
        if not self.enabled:
            return

        self.sample_rate = int(pygame.mixer.get_init()[0])
        self.composer = NotebookComposer(self.sample_rate)
        self.asset_root = Path(__file__).resolve().parent / "assets" / "audio"
        cache = _RAW_BANKS.setdefault(self.sample_rate, {"sfx": {}, "pages": {}})
        for name in SFX_NAMES:
            path = self.asset_root / RECORDED_SFX.get(name, f"sfx_{name}.wav")
            if path.exists():
                key = (self.sample_rate, str(path))
                if key not in _SOUND_CACHE:
                    _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
                self.sounds[name] = _SOUND_CACHE[key]
            else:
                if name not in cache["sfx"]:
                    cache["sfx"][name] = self.composer.sfx(name)
                self.sounds[name] = pygame.mixer.Sound(buffer=cache["sfx"][name])

        path = self.asset_root / "classroom_babble.wav"
        key = (self.sample_rate, str(path))
        if key not in _SOUND_CACHE:
            if path.exists():
                _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
            else:
                cache.setdefault("classroom", self.composer.classroom())
                _SOUND_CACHE[key] = pygame.mixer.Sound(buffer=cache["classroom"])
        self.classroom_sound = _SOUND_CACHE[key]
        self.classroom_sound.set_volume(.25)
        pygame.mixer.set_num_channels(max(16, pygame.mixer.get_num_channels()))
        # Score, classroom and the page-turn bell have protected channels:
        # a busy fight cannot cut a ring or replace the distant conversation.
        pygame.mixer.set_reserved(5)
        self.ambient_channel = pygame.mixer.Channel(0)
        self.score_channel = pygame.mixer.Channel(1)
        self.combat_channel = pygame.mixer.Channel(2)
        self.classroom_channel = pygame.mixer.Channel(3)
        self.bell_channel = pygame.mixer.Channel(4)

    def _bell_duck(self) -> float:
        remaining = self.bell_duck_until - pygame.time.get_ticks()
        if remaining <= 0:
            return 1.0
        return .40 + .60 * (1.0 - min(1.0, remaining / 650.0))

    def _ensure_page_audio(self, page: int) -> None:
        if self.ambience[page] is not None:
            return
        labels = {
            "ambience": (self.ambience, lambda: self.composer.ambience(page)),
            "calm": (self.score_low, lambda: self.composer.score(page, 0)),
            "action": (self.score_high, lambda: self.composer.score(page, 1)),
            "boss": (self.score_boss, lambda: self.composer.score(page, 1, True)),
        }
        cache = _RAW_BANKS[self.sample_rate]["pages"]
        page_cache = cache.setdefault(page, {})
        for label, (collection, factory) in labels.items():
            selected = SELECTED_PAGE_TRACKS.get(page, {}).get(label)
            path = (self.asset_root / selected if selected
                    else self.asset_root / f"page_{page}_{label}.wav")
            if path.exists():
                if label == "boss" and selected == SELECTED_PAGE_TRACKS.get(page, {}).get("action") \
                        and self.score_high[page] is not None:
                    collection[page] = self.score_high[page]
                    continue
                key = (self.sample_rate, str(path))
                if key not in _SOUND_CACHE:
                    _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
                collection[page] = _SOUND_CACHE[key]
            else:
                if label not in page_cache:
                    page_cache[label] = factory()
                collection[page] = pygame.mixer.Sound(buffer=page_cache[label])

    def _mix_gain(self, base: float) -> float:
        quiet_scale = .14 if self.quiet else 1.0
        return max(0.0, min(1.0,
                            self.master_volume * self.music_volume * base * quiet_scale
                            * self._bell_duck()))

    def _apply_mix(self) -> None:
        if not self.enabled:
            return
        if self.ambient_channel is not None:
            self.ambient_channel.set_volume(self._mix_gain(.19))
        if self.score_channel is not None:
            calm = .20 * (1.0 - self.intensity * .36)
            self.score_channel.set_volume(self._mix_gain(calm))
        if self.combat_channel is not None:
            action = .27 * self.intensity if self.combat_active else 0.0
            self.combat_channel.set_volume(self._mix_gain(action))
        if self.classroom_channel is not None:
            # Keep the voices beneath each score, lower them again in combat.
            # Split gain across sound/channel for finer mixer steps at this
            # quiet level (SDL's individual volume knobs have 128 steps).
            page = max(0, min(4, self.ambient_chapter))
            self.classroom_channel.set_volume(
                self._mix_gain(.18 * CLASSROOM_PAGE_GAIN[page]
                               * (1.0 - self.intensity * .35)))
        if self.bell_channel is not None:
            self.bell_channel.set_volume(
                max(0.0, min(1.0, self.master_volume * self.sfx_volume * .60)))

    def update(self, dt=0.0):
        """Release the bell duck even while walking outside an encounter."""
        if not self.enabled or not self.bell_duck_until:
            return
        self._apply_mix()
        if pygame.time.get_ticks() >= self.bell_duck_until:
            self.bell_duck_until = 0

    def play(self, name):
        if self.enabled and name in self.sounds:
            if name == "bell":
                self.sounds[name].set_volume(1.0)
                self.bell_channel.play(self.sounds[name])
                # Duck the music through the mechanical ring and release
                # smoothly through its tail; the SFX slider owns the bell.
                if self.master_volume * self.sfx_volume > 0:
                    self.bell_duck_until = (pygame.time.get_ticks()
                                            + round(self.sounds[name].get_length() * 1000))
                self._apply_mix()
                return
            self.sounds[name].set_volume(
                max(0, min(1, self.master_volume * self.sfx_volume))
            )
            self.sounds[name].play()

    def apply_settings(self, settings):
        def safe_gain(key, fallback):
            try:
                value = float(settings.get(key, fallback))
            except (TypeError, ValueError, OverflowError):
                value = fallback
            if not math.isfinite(value):
                value = fallback
            return max(0.0, min(1.0, value))

        self.master_volume = safe_gain("master_volume", .8)
        self.sfx_volume = safe_gain("sfx_volume", .85)
        self.music_volume = safe_gain("music_volume", .55)
        self._apply_mix()

    def start_ambience(self, chapter=0):
        if not self.enabled or self.ambient_channel is None:
            return
        chapter = max(0, min(len(self.ambience) - 1, int(chapter)))
        self._ensure_page_audio(chapter)
        same_page = chapter == self.ambient_chapter
        if same_page and self.ambient_channel.get_busy():
            self.quiet = False
            self._apply_mix()
            return
        self.ambient_chapter = chapter
        self.combat_active = False
        self.boss_active = False
        self.action_variant = "page"
        self.intensity = 0.0
        self.quiet = False
        self.ambient_channel.play(self.ambience[chapter], loops=-1, fade_ms=700)
        self.score_channel.play(self.score_low[chapter], loops=-1, fade_ms=900)
        # Both score interpretations start together. The action layer is kept
        # silent until the first red arena stroke closes.
        self.combat_channel.play(self.score_high[chapter], loops=-1, fade_ms=80)
        if not self.classroom_channel.get_busy():
            self.classroom_channel.play(self.classroom_sound, loops=-1, fade_ms=1400)
        self._apply_mix()

    def set_combat(self, active=True, boss=False):
        if not self.enabled or self.combat_channel is None:
            return
        active = bool(active)
        boss = bool(boss and active)
        self.combat_active = active
        self.boss_active = boss
        if active:
            page = max(0, min(len(self.score_high) - 1, self.ambient_chapter))
            desired = self.score_boss[page] if boss else self.score_high[page]
            variant = "boss" if boss else "page"
            # A boss cue intentionally restarts on its entrance; ordinary
            # combat remains phase-aligned with the calm page score.
            if boss or variant != self.action_variant or not self.combat_channel.get_busy():
                self.combat_channel.play(desired, loops=-1, fade_ms=240)
            self.action_variant = variant
            self.intensity = max(self.intensity, .44 if not boss else .70)
        else:
            self.intensity = 0.0
            self.combat_channel.fadeout(360)
        self._apply_mix()

    def set_intensity(self, value: float, boss: bool = False):
        """React to current encounter pressure without changing composition."""
        if not self.enabled:
            return
        value = max(0.0, min(1.0, float(value)))
        if boss:
            value = max(.66, value)
        # Smooth enough to avoid audible pumping while still answering play
        # within roughly a second, like a live accompanist watching the page.
        self.intensity += (value - self.intensity) * .18
        self._apply_mix()

    def quiet_ambience(self, quiet=True):
        self.quiet = bool(quiet)
        self._apply_mix()
