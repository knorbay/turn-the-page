from __future__ import annotations

from array import array
from dataclasses import dataclass
import math
from pathlib import Path

import pygame

from audio_composer import NotebookComposer, SFX_NAMES, SFX_VARIANT_COUNTS
from audio_mix import boss_music_pcm, condition_pcm, voice_gains
from scene_music import (SELECTED_PAGE_TRACKS, SELECTED_BOSS_TRACKS,
                         BOSS_ENTRANCE_TRACKS, BOSS_ENTRY_DELAYS, BOSS_PROFILES)


_RAW_BANKS: dict[int, dict] = {}
_SOUND_CACHE: dict[tuple[int, int, str], pygame.mixer.Sound] = {}
_PITCHED_CACHE: dict[tuple[int, int, str, int, int], pygame.mixer.Sound] = {}
_CONDITIONED_CACHE = {}
_BOSS_MUSIC_CACHE = {}

PAGE_DIP_SECONDS = .22
PAGE_RISE_SECONDS = .30
BOSS_MUSIC_BUS_GAIN = .65
BOSS_REVEAL_RISE_SECONDS = 2.8

RECORDED_SFX = {
    "pencil": "recorded/pencil_write.ogg",
    "erase": "recorded/pencil_erase.ogg",
    "blade": "recorded/blade_swing.wav",
}

# Keep distant classroom voices behind the page's original pencil score.
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
    "pencil": CueProfile(.54, 35),
    "paper_break": CueProfile(.66, 55),
    "redraw": CueProfile(.62, 80),
    "reload": CueProfile(.65, 95, (.985, 1.015, 1.0)),
    "giant_step": CueProfile(.62, 105),
    "giant_stomp": CueProfile(.72, 110, (1.0,), .12, 125),
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
    "enemy_telegraph": CueProfile(.59, 95, (.97, 1.02, .99), .06, 100),
    "enemy_telegraph_ranged": CueProfile(.61, 120, (.97, 1.02, .99), .07, 110),
    "enemy_telegraph_heavy": CueProfile(.68, 160, (.96, 1.015, .98), .05, 80),
    "enemy_telegraph_air": CueProfile(.57, 120, (.97, 1.025, .99), .06, 100),
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

# Readable attacks keep their short notebook cues even in a burst of impacts.
WARNING_RANK = {"enemy_telegraph": 1, "enemy_telegraph_air": 1,
                "enemy_telegraph_ranged": 2, "enemy_telegraph_heavy": 3}


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
    """Page-aware music and tactile paper-world sound system.

    The first released soundtrack supplies the page and boss recordings.
    Music scenes hand over through a short dip, while the familiar mix levels,
    protected warnings and established notebook effects remain independent.
    """

    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.sounds = {}
        self.sound_variants = {}
        self.ambience = [None] * 5
        self.score_low = [None] * 5
        self.score_high = [None] * 5
        self.score_boss = [None] * 5
        self.boss_scores = {}
        self.boss_entrances = {}
        self.ambient_channel = None
        self.score_channel = None
        self.combat_channel = None
        self.classroom_channel = None
        self.bell_channel = None
        self.cue_channel = None
        self.warning_channel = None
        self.music_intro_channel = None
        self.boss_channel = None
        self._pending_boss_score = None
        self._boss_intro_elapsed = 0.0
        self._boss_intro_duration = 0.0
        self._boss_downbeat_delay = 0.0
        self.boss_entry_elapsed = 0.0
        self._page_scene = "calm"
        self._page_scene_gain = 1.0
        self._pending_page_scene = None
        self._page_fade_elapsed = 0.0
        self._page_fade_from = 1.0
        self._page_attack_elapsed = None
        self._page_attack_duration = PAGE_RISE_SECONDS
        self._warning_rank = 0
        self._warning_play_gain = 1.0
        self.effect_channels = ()
        self._effect_started = [0] * 6
        self._effect_gains = [0.0] * 6
        self._effect_names = [None] * 6
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
        self.boss_kind = None
        self.intensity = 0.0
        self.quiet = False
        if not self.enabled:
            return

        self.sample_rate = int(pygame.mixer.get_init()[0])
        self.output_channels = int(pygame.mixer.get_init()[2])
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
                    key = (self.sample_rate, self.output_channels, str(path))
                    if key not in _SOUND_CACHE:
                        _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
                    sound = _SOUND_CACHE[key]
                else:
                    raw_key = (name, variation)
                    if raw_key not in cache["sfx"]:
                        cache["sfx"][raw_key] = self.composer.sfx(name, variation)
                    sound = self._mono_sound(cache["sfx"][raw_key])
                if abs(pygame.mixer.get_init()[1]) == 16:
                    channels = pygame.mixer.get_init()[2]
                    mix_key = (self.sample_rate, channels, name, variation, relative)
                    if mix_key not in _CONDITIONED_CACHE:
                        signature = name.startswith("boss_") or name in WARNING_RANK or name in ("bell", "hero_sword", "hero_reveal")
                        _CONDITIONED_CACHE[mix_key] = pygame.mixer.Sound(buffer=condition_pcm(
                            sound.get_raw(), self.sample_rate, channels, signature))
                    sound = _CONDITIONED_CACHE[mix_key]
                sound.set_volume(1.0)
                variants.append(sound)
            self.sound_variants[name] = tuple(variants)
            self.sounds[name] = variants[0]

        path = self.asset_root / "classroom_babble.wav"
        key = (self.sample_rate, self.output_channels, str(path))
        if key not in _SOUND_CACHE:
            if path.exists():
                _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
            else:
                cache.setdefault("classroom", self.composer.classroom())
                _SOUND_CACHE[key] = self._mono_sound(cache["classroom"])
        self.classroom_sound = _SOUND_CACHE[key]
        self.classroom_sound.set_volume(.25)
        pygame.mixer.set_num_channels(max(20, pygame.mixer.get_num_channels()))
        # Score, classroom and the page-turn bell have protected channels:
        # a busy fight cannot cut a ring or replace the distant conversation.
        # Boss punctuation and ordinary attack warnings have separate voices.
        pygame.mixer.set_reserved(15)
        self.ambient_channel = pygame.mixer.Channel(0)
        self.score_channel = pygame.mixer.Channel(1)
        self.combat_channel = pygame.mixer.Channel(2)
        self.classroom_channel = pygame.mixer.Channel(3)
        self.bell_channel = pygame.mixer.Channel(4)
        self.cue_channel = pygame.mixer.Channel(5)
        self.warning_channel = pygame.mixer.Channel(6)
        # Musical entrances must survive boss attacks, warnings and hit bursts.
        # Boss entrances and loops have their own protected music channels.
        self.music_intro_channel = pygame.mixer.Channel(13)
        self.boss_channel = pygame.mixer.Channel(14)
        # A small voice pool keeps clustered pellets and enemy deaths tactile
        # without summing a dozen sharp samples in the same audio frame.
        self.effect_channels = tuple(pygame.mixer.Channel(i) for i in range(7, 13))

    def _mono_sound(self, raw):
        if self.output_channels == 1:
            return pygame.mixer.Sound(buffer=raw)
        source = array("h")
        source.frombytes(raw)
        interleaved = array("h", (value for value in source
                                 for _ in range(self.output_channels)))
        return pygame.mixer.Sound(buffer=interleaved.tobytes())

    def _asset_sound(self, relative):
        path = self.asset_root / relative
        if not path.exists():
            return None
        key = (self.sample_rate, self.output_channels, str(path))
        if key not in _SOUND_CACHE:
            _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
        return _SOUND_CACHE[key]

    def _ensure_boss_audio(self, kind, page):
        key = kind if kind in SELECTED_BOSS_TRACKS else f"page:{page}"
        if key not in self.boss_scores:
            relative = SELECTED_BOSS_TRACKS.get(kind)
            source = self._asset_sound(relative) if relative else None
            # External recordings are already mastered stereo loops. Adding
            # the legacy synthesized beat here would change their timbre.
            self.boss_scores[key] = source if source is not None else self.score_boss[page]
        if key not in self.boss_entrances:
            relative = BOSS_ENTRANCE_TRACKS.get(kind)
            self.boss_entrances[key] = self._asset_sound(relative) if relative else None
        return self.boss_scores[key], self.boss_entrances[key]

    def _boss_music_sound(self, source, page):
        if abs(pygame.mixer.get_init()[1]) != 16:
            return source
        key = (self.sample_rate, self.output_channels, source, page)
        if key not in _BOSS_MUSIC_CACHE:
            _BOSS_MUSIC_CACHE[key] = pygame.mixer.Sound(
                buffer=boss_music_pcm(source.get_raw(), self.sample_rate,
                                      self.output_channels, page))
        return _BOSS_MUSIC_CACHE[key]

    def _cancel_boss_music(self):
        self._pending_boss_score = None
        self._boss_intro_elapsed = 0.0
        self._boss_intro_duration = 0.0
        self._boss_downbeat_delay = 0.0
        self.boss_entry_elapsed = 0.0
        if self.music_intro_channel is not None:
            self.music_intro_channel.stop()
            self.boss_channel.stop()

    def _start_page_scene(self, scene, rise=PAGE_RISE_SECONDS):
        page = max(0, min(4, self.ambient_chapter))
        self._ensure_page_audio(page)
        self.score_channel.stop()
        self.combat_channel.stop()
        channel, sound = ((self.score_channel, self.score_low[page]) if scene == "calm"
                          else (self.combat_channel, self.score_high[page]))
        channel.play(sound, loops=-1)
        self._page_scene = scene
        self._pending_page_scene = None
        self._page_attack_duration = max(.001, rise)
        self._page_attack_elapsed = 0.0
        self._page_scene_gain = 0.0

    def _request_page_scene(self, scene):
        if scene == self._pending_page_scene:
            return
        if scene == self._page_scene:
            if self._pending_page_scene is not None:
                self._pending_page_scene = None
                self._page_attack_duration = PAGE_RISE_SECONDS
                self._page_attack_elapsed = self._page_scene_gain * PAGE_RISE_SECONDS
            return
        self._pending_page_scene = scene
        self._page_fade_elapsed = 0.0
        self._page_fade_from = self._page_scene_gain

    def _update_page_music(self, dt):
        if self.boss_active:
            return
        if self._pending_page_scene is not None:
            self._page_fade_elapsed += dt
            if self._page_fade_elapsed < PAGE_DIP_SECONDS:
                self._page_scene_gain = self._page_fade_from * (1 - self._page_fade_elapsed / PAGE_DIP_SECONDS)
            else:
                remainder = self._page_fade_elapsed - PAGE_DIP_SECONDS
                self._start_page_scene(self._pending_page_scene)
                self._page_attack_elapsed = remainder
                self._page_scene_gain = min(1.0, remainder / PAGE_RISE_SECONDS)
        elif self._page_attack_elapsed is not None:
            self._page_attack_elapsed += dt
            self._page_scene_gain = min(1.0, self._page_attack_elapsed / self._page_attack_duration)
            if self._page_scene_gain >= 1.0:
                self._page_attack_elapsed = None
        self._apply_mix()

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
        key = (self.sample_rate, int(mixer[2]), name, variation, pitch_key)
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
                    collection[page] = self._boss_music_sound(self.score_high[page], page)
                    continue
                key = (self.sample_rate, self.output_channels, str(path))
                if key not in _SOUND_CACHE:
                    _SOUND_CACHE[key] = pygame.mixer.Sound(str(path))
                collection[page] = _SOUND_CACHE[key]
            else:
                if label not in page_cache:
                    page_cache[label] = factory()
                collection[page] = self._mono_sound(page_cache[label])
            if label == "boss":
                # Prepare once at page load; its first entrance only retrieves
                # the cached playback Sound and never scans a loop mid-frame.
                collection[page] = self._boss_music_sound(collection[page], page)
        # Decode each current-page guardian before its entrance. Switching
        # identities during an encounter retrieves the Sound without file I/O.
        for kind, profile in BOSS_PROFILES.items():
            if profile["page"] == page:
                self._ensure_boss_audio(kind, page)

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
            if self.boss_active:
                ambience *= .28
            self.ambient_channel.set_volume(self._mix_gain(ambience))
        # Original recordings keep their familiar level beneath notebook ink.
        page_gain = self._page_scene_gain if not self.boss_active else 0.0
        if self.score_channel is not None:
            calm = .20 * (1.0 - .62 * self.intensity) * page_gain if self._page_scene == "calm" else 0.0
            self.score_channel.set_volume(self._mix_gain(calm))
        if self.combat_channel is not None:
            action = .235 * self.intensity * page_gain if self._page_scene == "action" else 0.0
            self.combat_channel.set_volume(self._mix_gain(action))
        if self.boss_channel is not None:
            intro_share = 0.0
            if self._boss_intro_duration > self._boss_intro_elapsed:
                span = max(.01, self._boss_intro_duration - self._boss_downbeat_delay)
                intro_share = min(1.0, (self._boss_intro_duration - self._boss_intro_elapsed) / span)
            # The score grows through the short drawing reveal. Complete
            # recorded phrases retain their own dynamics during the fight;
            # the warning bus can still dip the music between those phrases.
            reveal_gain = .45 + .55 * min(1.0,
                self.boss_entry_elapsed / BOSS_REVEAL_RISE_SECONDS)
            boss_gain = (BOSS_MUSIC_BUS_GAIN * (.93 + .07 * self.intensity)
                         * reveal_gain if self.boss_active else 0.0)
            self.boss_channel.set_volume(self._mix_gain(boss_gain * (1.0 - intro_share)))
            self.music_intro_channel.set_volume(self._mix_gain(boss_gain * intro_share))
        if self.classroom_channel is not None:
            # Keep the voices beneath each score, lower them again in combat.
            # Split gain across sound/channel for finer mixer steps at this
            # quiet level (SDL's individual volume knobs have 128 steps).
            page = max(0, min(4, self.ambient_chapter))
            combat_scale = .70 if self.combat_active else 1.0
            if self.boss_active:
                combat_scale *= .24
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
        if self.warning_channel is not None:
            self.warning_channel.set_volume(
                max(0.0, min(1.0, self.master_volume * self.sfx_volume
                             * self._warning_play_gain)))

    def update(self, dt=0.0):
        """Release bell and combat-cue ducking outside encounter updates."""
        if not self.enabled:
            return
        dt = max(0.0, float(dt))
        self._update_page_music(dt)
        revealing_score = self.boss_active and self.boss_entry_elapsed < BOSS_REVEAL_RISE_SECONDS
        if self.boss_active:
            self.boss_entry_elapsed += dt
        intro_advancing = self._boss_intro_elapsed < self._boss_intro_duration
        if intro_advancing:
            self._boss_intro_elapsed += dt
            if self._pending_boss_score is not None and self._boss_intro_elapsed >= self._boss_downbeat_delay:
                self.boss_channel.play(self._pending_boss_score, loops=-1)
                self._pending_boss_score = None
        if intro_advancing or revealing_score:
            self._apply_mix()
        self._rebalance_effects()
        if not (self.bell_duck_until or self.transient_duck_until):
            return
        self._apply_mix()
        now = pygame.time.get_ticks()
        if now >= self.bell_duck_until:
            self.bell_duck_until = 0
        if now >= self.transient_duck_until:
            self.transient_duck_started = 0
            self.transient_duck_until = 0
            self.transient_duck_depth = 0.0

    def _rebalance_effects(self):
        requested = [gain * self.master_volume * self.sfx_volume
                     if channel.get_busy() else 0.0
                     for gain, channel in zip(self._effect_gains, self.effect_channels)]
        for channel, gain in zip(self.effect_channels, voice_gains(requested)):
            channel.set_volume(gain)

    def play(self, name, variant=None, *, pitch=None, volume=1.0,
             cooldown_ms=None):
        """Play a cue with deterministic variants and mix-safe defaults.

        The original ``play(name)`` API remains valid. New callers may select
        a zero-based variant, pitch ratio, per-call volume, or cooldown.
        """
        if self.enabled and name in self.sound_variants:
            resolved = self.resolve_cue(name)
            profile = SFX_PLAYBACK.get(resolved, SFX_PLAYBACK.get(name, CueProfile(.72, 35)))
            now = pygame.time.get_ticks()
            try:
                chosen_cooldown = (profile.cooldown_ms if cooldown_ms is None
                                   else max(0, int(cooldown_ms)))
            except (TypeError, ValueError, OverflowError):
                chosen_cooldown = profile.cooldown_ms
            last_played = self._last_played.get(resolved)
            if cooldown_ms is None:
                repeated = resolved in ("pencil", "paper_step", "hit", "blocked", "ink") or resolved.startswith("enemy_hit_")
                if repeated:
                    chosen_cooldown = max(chosen_cooldown, 90 if resolved == "pencil" else 55)
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
            elif resolved in WARNING_RANK and self.warning_channel is not None:
                rank = WARNING_RANK[resolved]
                if self.warning_channel.get_busy() and self._warning_rank > rank:
                    return None
                self._warning_rank = rank
                self._warning_play_gain = profile.volume * self._safe_unit(volume)
                self.warning_channel.play(sound)
                self._apply_mix()
                channel = self.warning_channel
            elif profile.priority and self.cue_channel is not None:
                self._cue_play_gain = profile.volume * self._safe_unit(volume)
                self.cue_channel.play(sound)
                self._apply_mix()
                channel = self.cue_channel
            else:
                free = next((index for index, voice in enumerate(self.effect_channels)
                             if not voice.get_busy()), None)
                index = (free if free is not None else
                         min(range(len(self.effect_channels)),
                             key=self._effect_started.__getitem__))
                channel = self.effect_channels[index]
                channel.play(sound)
                self._effect_started[index] = now
                self._effect_gains[index] = profile.volume * self._safe_unit(volume)
                self._effect_names[index] = resolved
                self._rebalance_effects()
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
        self._rebalance_effects()

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
        self._cancel_boss_music()
        self.combat_active = False
        self.boss_active = False
        self.boss_kind = None
        self.action_variant = "page"
        self.intensity = 0.0
        self.quiet = False
        self.ambient_channel.play(self.ambience[chapter], loops=-1, fade_ms=700)
        self._start_page_scene("calm", rise=.9)
        if not self.classroom_channel.get_busy():
            self.classroom_channel.play(self.classroom_sound, loops=-1, fade_ms=1400)
        self._apply_mix()

    def set_combat(self, active=True, boss=False, boss_kind=None):
        if not self.enabled or self.combat_channel is None:
            return
        active = bool(active)
        boss = bool(boss and active)
        kind = boss_kind if boss else None
        boss_entry = boss and (not self.combat_active or not self.boss_active
                              or kind != self.boss_kind)
        leaving_boss = self.boss_active and not boss
        self.combat_active = active
        self.boss_active = boss
        self.boss_kind = kind
        if active:
            page = max(0, min(len(self.score_high) - 1, self.ambient_chapter))
            self._ensure_page_audio(page)
            if boss_entry:
                self._cancel_boss_music()
                self._pending_page_scene = None
                self._page_attack_elapsed = None
                self._page_scene_gain = 1.0
                desired, entrance = self._ensure_boss_audio(kind, page)
                if entrance is not None:
                    self.music_intro_channel.play(entrance)
                    self._boss_intro_duration = entrance.get_length()
                    self._boss_downbeat_delay = min(self._boss_intro_duration,
                        max(0.0, BOSS_ENTRY_DELAYS.get(kind, self._boss_intro_duration - .12)))
                    self._pending_boss_score = desired
                else:
                    self.boss_channel.play(desired, loops=-1, fade_ms=120)
            elif not boss:
                self._cancel_boss_music()
                if leaving_boss:
                    self._start_page_scene("action")
                else:
                    self._request_page_scene("action")
            self.action_variant = f"boss:{kind or 'page'}" if boss else "page"
            self.intensity = max(self.intensity, .44 if not boss else .70)
        else:
            self._cancel_boss_music()
            self.action_variant = "page"
            self.intensity = 0.0
            if leaving_boss:
                self._start_page_scene("calm")
            else:
                self._request_page_scene("calm")
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
