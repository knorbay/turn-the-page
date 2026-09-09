from __future__ import annotations

import json
import math
import os
from pathlib import Path

from settings import HEIGHT, WIDTH
from runtime_paths import default_save_path, legacy_save_path


DEFAULT_PROGRESS = {
    "version": 6,
    "campaign_revision": 2,
    "chapter": 0,
    "checkpoint": "start",
    "secrets": [],
    "completed": False,
    "achievements": [],
    "play_seconds": 0,
    "weapons": ["pencil_blade"],
    "current_weapon": "pencil_blade",
    "weapon_ammo": {},
    # Facts the Artist can react to.  These are deliberately counters and
    # recent events rather than an exposed morality/personality score.
    "behavior": {},
    "settings": {
        "master_volume": 0.8,
        "sfx_volume": 0.85,
        "music_volume": 0.35,
        "fullscreen": False,
        "window_width": WIDTH,
        "window_height": HEIGHT,
    },
}


class SaveSystem:
    """Small human-readable local save with conservative schema repair."""

    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else default_save_path()
        self.read_path = self.path
        if path is None and not self.path.exists():
            legacy = legacy_save_path()
            if legacy is not None and legacy.exists():
                self.read_path = legacy
        self.data = self._fresh()
        self.load()

    @staticmethod
    def _fresh():
        return json.loads(json.dumps(DEFAULT_PROGRESS))

    @property
    def can_continue(self):
        return self.path.exists() and (self.data["chapter"] > 0 or self.data["checkpoint"] != "start" or self.data["completed"])

    def load(self):
        source = self.read_path if self.read_path.exists() else self.path
        if not source.exists():
            return self.data
        try:
            raw = json.loads(source.read_text(encoding="utf8"))
        except (OSError, ValueError, TypeError):
            return self.data
        for key in ("chapter", "checkpoint", "secrets", "completed", "achievements", "play_seconds",
                    "weapons", "current_weapon", "weapon_ammo", "behavior"):
            if key in raw:
                self.data[key] = raw[key]
        if isinstance(raw.get("settings"), dict):
            self.data["settings"].update(raw["settings"])
        self._repair_settings()
        self.data["chapter"] = max(0, min(4, int(self.data["chapter"])))
        self.data["secrets"] = sorted(set(str(s) for s in self.data["secrets"]))
        if not isinstance(self.data.get("achievements"), list):
            self.data["achievements"] = []
        self.data["achievements"] = sorted(set(str(item)
                                                   for item in self.data["achievements"]))
        if not isinstance(self.data.get("weapons"), list):
            self.data["weapons"] = ["pencil_blade"]
        self.data["weapons"] = sorted(set(str(w) for w in self.data["weapons"]) | {"pencil_blade"})
        if self.data.get("current_weapon") not in self.data["weapons"]:
            self.data["current_weapon"] = "pencil_blade"
        if not isinstance(self.data.get("weapon_ammo"), dict):
            self.data["weapon_ammo"] = {}
        if not isinstance(self.data.get("behavior"), dict):
            self.data["behavior"] = {}
        if raw.get("campaign_revision", 1) < 2 and self.data["chapter"] == 2 and (
                self.data.get("completed") or self.data["checkpoint"] == "after_final_margin_revision"):
            # Continue an old completed three-page run at the new Agent page.
            # Achievements and collected sketches remain earned.
            self.data.update(chapter=3, checkpoint="start", completed=False,
                             weapons=["pencil_blade"], current_weapon="pencil_blade",
                             weapon_ammo={})
            self.data["behavior"]["final_scenario"] = ""
        if source != self.path:
            self.write()
            self.read_path = self.path
        return self.data

    @staticmethod
    def _finite_volume(value, fallback):
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError):
            value = float(fallback)
        if not math.isfinite(value):
            value = float(fallback)
        return max(0.0, min(1.0, value))

    @staticmethod
    def _window_dimension(value, fallback, minimum, maximum):
        try:
            value = int(float(value))
        except (TypeError, ValueError, OverflowError):
            value = int(fallback)
        return max(minimum, min(maximum, value))

    def _repair_settings(self):
        """Keep old or hand-edited saves from breaking the settings screen."""
        settings = self.data["settings"]
        defaults = DEFAULT_PROGRESS["settings"]
        for key in ("master_volume", "sfx_volume", "music_volume"):
            settings[key] = self._finite_volume(settings.get(key), defaults[key])
        fullscreen = settings.get("fullscreen", False)
        if isinstance(fullscreen, str):
            fullscreen = fullscreen.strip().lower() in ("1", "true", "yes", "on")
        settings["fullscreen"] = bool(fullscreen)
        settings["window_width"] = self._window_dimension(
            settings.get("window_width"), WIDTH, 800, 7680,
        )
        settings["window_height"] = self._window_dimension(
            settings.get("window_height"), HEIGHT, 500, 4320,
        )

    def write(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(json.dumps(self.data, indent=2, sort_keys=True), encoding="utf8")
        temporary.replace(self.path)

    def new_game(self):
        settings = dict(self.data.get("settings", {}))
        achievements = list(self.data.get("achievements", ()))
        self.data = self._fresh()
        self.data["settings"].update(settings)
        self.data["achievements"] = achievements
        self._repair_settings()
        self.write()

    def checkpoint(self, chapter: int, checkpoint: str, seconds: float = 0):
        self.data["chapter"] = chapter
        self.data["checkpoint"] = checkpoint
        self.data["play_seconds"] = max(float(self.data.get("play_seconds", 0)), float(seconds))
        self.write()

    def discover(self, secret_id: str):
        if secret_id not in self.data["secrets"]:
            self.data["secrets"].append(secret_id)
            self.data["secrets"].sort()
            self.write()
            return True
        return False

    def unlock_achievement(self, achievement_id: str):
        achievement_id = str(achievement_id)
        if achievement_id in self.data["achievements"]:
            return False
        self.data["achievements"].append(achievement_id)
        self.data["achievements"].sort()
        self.write()
        return True

    def update_settings(self, settings: dict, write=True):
        self.data["settings"].update(settings)
        self._repair_settings()
        if write:
            self.write()

    def mark_complete(self, seconds: float):
        self.data["completed"] = True
        self.data["play_seconds"] = float(seconds)
        self.write()

    def update_combat(self, weapons, current_weapon, ammo=None):
        self.data["weapons"] = sorted(set(str(item) for item in weapons) | {"pencil_blade"})
        self.data["current_weapon"] = (str(current_weapon)
                                       if str(current_weapon) in self.data["weapons"]
                                       else "pencil_blade")
        if isinstance(ammo, dict):
            self.data["weapon_ammo"] = {str(key): max(0, int(value))
                                        for key, value in ammo.items()}
        self.write()

    def update_behavior(self, snapshot, write=False):
        """Store the Artist ledger; callers choose durable save boundaries."""
        self.data["behavior"] = dict(snapshot) if isinstance(snapshot, dict) else {}
        if write:
            self.write()
