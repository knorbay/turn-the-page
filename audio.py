from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from pathlib import Path

import pygame

from audio_composer import NotebookComposer, SFX_NAMES, SFX_VARIANT_COUNTS


_RAW_BANKS: dict[int, dict] = {}
_SOUND_CACHE: dict[tuple[int, str], pygame.mixer.Sound] = {}
_PITCHED_CACHE: dict[tuple[int, str, int, int], pygame.mixer.Sound] = {}

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


@dataclass(frozen=True)
class CueProfile:
    """Mix policy for one semantic cue; synthesis stays in the composer."""

    volume: float = 1.0
    cooldown_ms: int = 0
    pitch_cycle: tuple[float, ...] = (1.0,)
    duck: float = 0.0
    duck_ms: int = 0
    priority: bool = False


SFX_PLAYBACK = {
    # Player tools keep their own weight and leave headroom for hit feedback.
    "blade": CueProfile(.74, 24, (.975, 1.015, .995), .05, 65),
    "katana_cut": CueProfile(.78, 28, (.97, 1.02, .99), .06, 75),
    "bowie_cut": CueProfile(.78, 28, (.965, 1.01, .99), .06, 75),
    "ion_slice": CueProfile(.70, 24, (.98, 1.025, 1.0), .05, 70),
    "field_knife": CueProfile(.72, 22, (.97, 1.02, .99), .04, 55),
    "pistol": CueProfile(.75, 32, (.98, 1.018, .995), .07, 75),
    "revolver": CueProfile(.84, 42, (.97, 1.012, .99), .10, 95),
    "suppressed_shot": CueProfile(.64, 26, (.985, 1.02, 1.0), .03, 45),
    "shotgun": CueProfile(.78, 65, (.965, 1.012, .985), .14, 125),
    "double_barrel": CueProfile(.85, 85, (.96, 1.01, .98), .18, 155),
    "breach_shotgun": CueProfile(.76, 65, (.975, 1.018, .99), .12, 115),
    "cannon": CueProfile(.81, 85, (.96, 1.01, .98), .18, 165),
    "null_cannon": CueProfile(.76, 80, (.97, 1.015, .99), .16, 150),
    "rubber": CueProfile(.72, 45, (.97, 1.03, .995), .04, 55),
    "orbit_pulse": CueProfile(.66, 38, (.98, 1.025, 1.0), .04, 55),
    # Common impacts get very short cooldowns: simultaneous pellets read as a
    # single hit while attacks a frame apart still receive feedback.
    "hit": CueProfile(.72, 28, (.96, 1.025, .99, 1.01), .05, 55),
    "heavy_hit": CueProfile(.80, 42, (.96, 1.02, .985), .11, 105),
    "blocked": CueProfile(.71, 55, (.975, 1.018, .99), .07, 75),
    "enemy_break": CueProfile(.78, 38, (.95, 1.025, .98, 1.01), .12, 130),
    "ink": CueProfile(.68, 36, (.97, 1.025, .99), .05, 55),
    "paper_step": CueProfile(.55, 34, (.96, 1.025, .99)),
    "staple": CueProfile(.72, 38, (.97, 1.02, .99), .05, 65),
    "snip": CueProfile(.72, 42, (.97, 1.02, .99), .05, 65),
    "ink_burst": CueProfile(.72, 45, (.96, 1.025, .985), .08, 85),
    # Semantic enemy and boss vocabulary for new actors.
    "enemy_telegraph": CueProfile(.59, 95, (.97, 1.02, .99)),
    "enemy_telegraph_ranged": CueProfile(.61, 120, (.97, 1.02, .99)),
    "enemy_telegraph_heavy": CueProfile(.68, 160, (.96, 1.015, .98), .05, 80),
    "enemy_telegraph_air": CueProfile(.57, 120, (.97, 1.025, .99)),
    "enemy_attack_melee": CueProfile(.68, 55, (.97, 1.02, .99), .05, 65),
    "enemy_attack_ranged": CueProfile(.66, 50, (.97, 1.025, .99), .05, 65),
    "enemy_attack_charge": CueProfile(.74, 95, (.96, 1.02, .985), .09, 100),
    "enemy_hit_paper": CueProfile(.68, 28, (.96, 1.025, .99, 1.01), .04, 50),
    "enemy_hit_ink": CueProfile(.67, 28, (.96, 1.025, .99, 1.01), .04, 50),
    "enemy_hit_metal": CueProfile(.65, 34, (.96, 1.025, .99, 1.01), .05, 60),
    "enemy_death_paper": CueProfile(.76, 55, (.96, 1.02, .985), .10, 115),
    "enemy_death_ink": CueProfile(.76, 55, (.96, 1.02, .985), .10, 115),
    "enemy_death_metal": CueProfile(.74, 65, (.96, 1.02, .985), .11, 125),
    "boss_reveal": CueProfile(.82, 450, (1.0,), .24, 310, True),
    "boss_phase_shift": CueProfile(.84, 420, (.96, 1.0, 1.035), .28, 360, True),
    "boss_opening": CueProfile(.75, 180, (.98, 1.02, 1.0), .16, 190, True),
    "boss_signature": CueProfile(.82, 240, (.97, 1.015, .99), .22, 260, True),
}


# A legacy weapon call becomes the material actually drawn on that page. This
# keeps old gameplay call sites and save files stable while making each page's
# starting weapon audibly distinct.
PAGE_SFX_OVERRIDES = {
    1: {
        "blade": "bowie_cut",
        "pistol": "revolver",
        "shotgun": "double_barrel",
    },
    2: {
        "blade": "ion_slice",
        "cannon": "null_cannon",
        "rubber": "orbit_pulse",
    },
    3: {
        "blade": "field_knife",
        "pistol": "suppressed_shot",
        "shotgun": "breach_shotgun",
    },
}


class NotebookSounds:
    """Page-aware original score and tactile paper-world sound system.

    Runtime WAVs are built from the included deterministic composer. Missing
    assets fall back to the same local synthesis. Calm and action scores share
    tempo/length, remain phase aligned, and crossfade with encounter pressure.
    """

    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.sound_variants = {}
        self.ambience = [None] * 5
        self.score_low = [None] * 5
        self.score_high = [None] * 5
        self.score_boss = [None] * 5
        self.ambient_channel = None
        self.score_channel = None
        self.combat_channel = None
        self.classroom_channel = None
        self.bell_channel = None
        self.cue_channel = None
        self.classroom_sound = None
        self.bell_duck_until = 0
        self.transient_duck_started = 0
        self.transient_duck_until = 0
        self.transient_duck_depth = 0.0
        self._bell_play_gain = 1.0
        self._cue_play_gain = 1.0
        self._last_played = {}
        self._variation_cursor = {}
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
            variants = []
            for variation in range(SFX_VARIANT_COUNTS.get(name, 1)):
                if variation == 0:
                    relative = RECORDED_SFX.get(name, f"sfx_{name}.wav")
                else:
                    relative = f"sfx_{name}_v{variation + 1}.wav"
                path = self.asset_root / relative
                if path.exists():
                    key = (self.sample_rate, str(path))
                    if key not in _SOUND_CACHE:
                        _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
                    sound = _SOUND_CACHE[key]
                else:
                    raw_key = (name, variation)
                    if raw_key not in cache["sfx"]:
                        cache["sfx"][raw_key] = self.composer.sfx(name, variation)
                    sound = pygame.mixer.Sound(buffer=cache["sfx"][raw_key])
                sound.set_volume(1.0)
                variants.append(sound)
            self.sound_variants[name] = tuple(variants)
            self.sounds[name] = variants[0]

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
        pygame.mixer.set_num_channels(max(20, pygame.mixer.get_num_channels()))
        # Score, classroom and the page-turn bell have protected channels:
        # a busy fight cannot cut a ring or replace the distant conversation.
        # One further channel protects authored boss punctuation.
        pygame.mixer.set_reserved(6)
        self.ambient_channel = pygame.mixer.Channel(0)
        self.score_channel = pygame.mixer.Channel(1)
        self.combat_channel = pygame.mixer.Channel(2)
        self.classroom_channel = pygame.mixer.Channel(3)
        self.bell_channel = pygame.mixer.Channel(4)
        self.cue_channel = pygame.mixer.Channel(5)

    def _bell_duck(self) -> float:
        remaining = self.bell_duck_until - pygame.time.get_ticks()
        if remaining <= 0:
            return 1.0
        return .40 + .60 * (1.0 - min(1.0, remaining / 650.0))

    def _transient_duck(self) -> float:
        now = pygame.time.get_ticks()
        remaining = self.transient_duck_until - now
        if remaining <= 0 or self.transient_duck_depth <= 0:
            return 1.0
        span = max(1, self.transient_duck_until - self.transient_duck_started)
        return 1.0 - self.transient_duck_depth * min(1.0, remaining / span)

    def _start_transient_duck(self, depth: float, duration_ms: int) -> None:
        if depth <= 0 or duration_ms <= 0:
            return
        now = pygame.time.get_ticks()
        if now >= self.transient_duck_until:
            self.transient_duck_started = now
            self.transient_duck_depth = depth
        else:
            self.transient_duck_depth = max(self.transient_duck_depth, depth)
        self.transient_duck_until = max(self.transient_duck_until,
                                        now + int(duration_ms))

    @staticmethod
    def _safe_unit(value, fallback=1.0) -> float:
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            value = fallback
        if not math.isfinite(value):
            value = fallback
        return max(0.0, min(1.0, value))

    def resolve_cue(self, name: str) -> str:
        """Return the page-specific material cue behind a legacy sound name."""
        page = max(0, min(4, self.ambient_chapter))
        resolved = PAGE_SFX_OVERRIDES.get(page, {}).get(name, name)
        return resolved if resolved in self.sound_variants else name

    def _pitched_sound(self, name: str, variation: int,
                       sound: pygame.mixer.Sound, pitch: float):
        """Resample a short cue for pitch variation without another library."""
        if abs(pitch - 1.0) < .002:
            return sound
        mixer = pygame.mixer.get_init()
        if mixer is None or abs(int(mixer[1])) != 16:
            return sound
        pitch_key = max(250, min(4000, round(pitch * 1000)))
        key = (self.sample_rate, name, variation, pitch_key)
        cached = _PITCHED_CACHE.get(key)
        if cached is not None:
            return cached
        channels = max(1, int(mixer[2]))
        source = array("h")
        source.frombytes(sound.get_raw())
        frames = len(source) // channels
        if frames < 2:
            return sound
        ratio = pitch_key / 1000.0
        output_frames = max(1, round(frames / ratio))
        output = array("h", [0]) * (output_frames * channels)
        for out_frame in range(output_frames):
            position = min(frames - 1, out_frame * ratio)
            left = int(position)
            right = min(frames - 1, left + 1)
            blend = position - left
            for channel_index in range(channels):
                a = source[left * channels + channel_index]
                b = source[right * channels + channel_index]
                output[out_frame * channels + channel_index] = round(
                    a + (b - a) * blend
                )
        pitched = pygame.mixer.Sound(buffer=output.tobytes())
        pitched.set_volume(1.0)
        _PITCHED_CACHE[key] = pitched
        return pitched

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

    def _mix_gain(self, base: float, transient=True) -> float:
        quiet_scale = .14 if self.quiet else 1.0
        transient_scale = self._transient_duck() if transient else 1.0
        return max(0.0, min(1.0,
                            self.master_volume * self.music_volume * base * quiet_scale
                            * self._bell_duck() * transient_scale))

    def _apply_mix(self) -> None:
        if not self.enabled:
            return
        if self.ambient_channel is not None:
            ambience = .19 * (1.0 - self.intensity * .28)
            self.ambient_channel.set_volume(self._mix_gain(ambience))
        if self.score_channel is not None:
            calm = .20 * (1.0 - self.intensity * .62)
            self.score_channel.set_volume(self._mix_gain(calm))
        if self.combat_channel is not None:
            action_ceiling = .255 if self.boss_active else .235
            action = action_ceiling * self.intensity if self.combat_active else 0.0
            self.combat_channel.set_volume(self._mix_gain(action))
        if self.classroom_channel is not None:
            # Keep the voices beneath each score, lower them again in combat.
            # Split gain across sound/channel for finer mixer steps at this
            # quiet level (SDL's individual volume knobs have 128 steps).
            page = max(0, min(4, self.ambient_chapter))
            combat_scale = .70 if self.combat_active else 1.0
            if self.boss_active:
                combat_scale *= .62
            self.classroom_channel.set_volume(
                self._mix_gain(.18 * CLASSROOM_PAGE_GAIN[page]
                               * combat_scale
                               * (1.0 - self.intensity * .82)))
        if self.bell_channel is not None:
            self.bell_channel.set_volume(
                max(0.0, min(1.0, self.master_volume * self.sfx_volume
                             * .60 * self._bell_play_gain)))
        if self.cue_channel is not None:
            self.cue_channel.set_volume(
                max(0.0, min(1.0, self.master_volume * self.sfx_volume
                             * self._cue_play_gain)))

    def update(self, dt=0.0):
        """Release bell and combat-cue ducking outside encounter updates."""
        if not self.enabled or not (self.bell_duck_until
                                    or self.transient_duck_until):
            return
        self._apply_mix()
        now = pygame.time.get_ticks()
        if now >= self.bell_duck_until:
            self.bell_duck_until = 0
        if now >= self.transient_duck_until:
            self.transient_duck_started = 0
            self.transient_duck_until = 0
            self.transient_duck_depth = 0.0

    def play(self, name, variant=None, *, pitch=None, volume=1.0,
             cooldown_ms=None):
        """Play a cue with deterministic variants and mix-safe defaults.

        The original ``play(name)`` API remains valid. New callers may select
        a zero-based variant, pitch ratio, per-call volume, or cooldown.
        """
        if self.enabled and name in self.sound_variants:
            resolved = self.resolve_cue(name)
            profile = SFX_PLAYBACK.get(resolved, SFX_PLAYBACK.get(name, CueProfile()))
            now = pygame.time.get_ticks()
            try:
                chosen_cooldown = (profile.cooldown_ms if cooldown_ms is None
                                   else max(0, int(cooldown_ms)))
            except (TypeError, ValueError, OverflowError):
                chosen_cooldown = profile.cooldown_ms
            last_played = self._last_played.get(resolved)
            if (last_played is not None and chosen_cooldown > 0
                    and 0 <= now - last_played < chosen_cooldown):
                return None

            bank = self.sound_variants[resolved]
            cursor = self._variation_cursor.get(resolved, 0)
            if variant is None:
                variation = cursor % len(bank)
            else:
                try:
                    variation = int(variant) % len(bank)
                except (TypeError, ValueError, OverflowError):
                    text = str(variant)
                    variation = sum((index + 1) * ord(char)
                                    for index, char in enumerate(text)) % len(bank)
            self._variation_cursor[resolved] = cursor + 1

            if pitch is None:
                pitch_ratio = profile.pitch_cycle[cursor % len(profile.pitch_cycle)]
            else:
                try:
                    pitch_ratio = float(pitch)
                except (TypeError, ValueError, OverflowError):
                    pitch_ratio = 1.0
                if not math.isfinite(pitch_ratio):
                    pitch_ratio = 1.0
                pitch_ratio = max(.25, min(4.0, pitch_ratio))
            sound = self._pitched_sound(resolved, variation, bank[variation], pitch_ratio)
            cue_gain = (self.master_volume * self.sfx_volume * profile.volume
                        * self._safe_unit(volume))
            cue_gain = max(0.0, min(1.0, cue_gain))

            if resolved == "bell":
                self._bell_play_gain = profile.volume * self._safe_unit(volume)
                self.bell_channel.play(sound)
                # Duck the music through the mechanical ring and release
                # smoothly through its tail; the SFX slider owns the bell.
                if self.master_volume * self.sfx_volume > 0:
                    self.bell_duck_until = (pygame.time.get_ticks()
                                            + round(sound.get_length() * 1000))
                self._apply_mix()
                channel = self.bell_channel
            elif profile.priority and self.cue_channel is not None:
                self._cue_play_gain = profile.volume * self._safe_unit(volume)
                self.cue_channel.play(sound)
                self._apply_mix()
                channel = self.cue_channel
            else:
                channel = sound.play()
                if channel is not None:
                    channel.set_volume(cue_gain)
            if channel is not None:
                self._last_played[resolved] = now
                self._start_transient_duck(profile.duck, profile.duck_ms)
                if profile.duck:
                    self._apply_mix()
            return channel
        return None

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
