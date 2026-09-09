"""Small, explicit player-behaviour ledger used by the Artist.

The ledger records facts, not a hidden personality score.  Reactions can be
authored from these facts later without committing the game to a procedural
"personality AI" or exposing bars to the player.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy


DEFAULT_BEHAVIOR = {
    "counts": {
        "attacks": 0,
        "dashes": 0,
        "damage_taken": 0,
        "deaths": 0,
        "enemies_hit": 0,
        "enemies_defeated": 0,
        "artist_help": 0,
        "artist_help_ignored": 0,
        "lost_sketches": 0,
        "pages_completed": 0,
    },
    "deaths_by_cause": {},
    "weapon_uses": {},
    "enemy_hits": {},
    "enemy_defeats": {},
    "boss_clear_seconds": {},
    "page_clear_seconds": {},
    "final_scenario": "",
    "combat_motion": {"seconds": 0.0, "close_seconds": 0.0,
                      "retreat_seconds": 0.0, "distance": 0.0},
    "recent": [],
}


class BehaviorLedger:
    """JSON-safe event ledger with a deliberately tiny query surface."""

    def __init__(self, snapshot=None):
        self.data = deepcopy(DEFAULT_BEHAVIOR)
        if isinstance(snapshot, dict):
            self._merge(snapshot)
        self._recent_lines = deque(maxlen=4)

    def _merge(self, snapshot):
        for key in ("counts", "deaths_by_cause", "weapon_uses", "enemy_hits",
                    "enemy_defeats", "boss_clear_seconds", "page_clear_seconds", "combat_motion"):
            value = snapshot.get(key)
            if isinstance(value, dict):
                self.data[key].update(value)
        recent = snapshot.get("recent", [])
        if isinstance(recent, list):
            self.data["recent"] = [entry for entry in recent[-16:] if isinstance(entry, dict)]
        scenario = snapshot.get("final_scenario", "")
        if isinstance(scenario, str):
            self.data["final_scenario"] = scenario

    @staticmethod
    def _key(value, fallback="unknown"):
        # Numeric page zero is a valid key, not a missing value.
        text = str(fallback if value is None else value).strip().lower().replace(" ", "_")
        return text or fallback

    def record(self, event, **details):
        event = self._key(event)
        counts = self.data["counts"]
        count_key = {
            "death": "deaths",
            "attack": "attacks",
            "dash": "dashes",
            "damage": "damage_taken",
            "enemy_hit": "enemies_hit",
            "enemy_defeated": "enemies_defeated",
            "lost_sketch": "lost_sketches",
            "page_complete": "pages_completed",
        }.get(event, event)
        counts[count_key] = int(counts.get(count_key, 0)) + 1
        if event == "death":
            cause = self._key(details.get("cause"))
            table = self.data["deaths_by_cause"]
            table[cause] = int(table.get(cause, 0)) + 1
        elif event == "attack":
            weapon = self._key(details.get("weapon"))
            table = self.data["weapon_uses"]
            table[weapon] = int(table.get(weapon, 0)) + 1
        elif event in ("enemy_hit", "enemy_defeated"):
            kind = self._key(details.get("kind"))
            table_name = "enemy_hits" if event == "enemy_hit" else "enemy_defeats"
            table = self.data[table_name]
            table[kind] = int(table.get(kind, 0)) + 1
        elif event == "page_complete":
            page = self._key(details.get("page"))
            try:
                seconds = round(float(details.get("seconds", 0)), 2)
            except (TypeError, ValueError):
                seconds = 0
            self.data["page_clear_seconds"][page] = seconds
        elif event == "boss_clear":
            boss = self._key(details.get("kind"))
            try:
                seconds = round(float(details.get("seconds", 0)), 2)
            except (TypeError, ValueError):
                seconds = 0
            self.data["boss_clear_seconds"][boss] = seconds
        elif event == "final_scenario":
            self.data["final_scenario"] = self._key(details.get("kind"), "unreadable")

        entry = {"event": event}
        for key, value in details.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                entry[str(key)] = value
        self.data["recent"].append(entry)
        self.data["recent"] = self.data["recent"][-16:]

    def count(self, event):
        return int(self.data["counts"].get(self._key(event), 0))

    def deaths_to(self, cause):
        return int(self.data["deaths_by_cause"].get(self._key(cause), 0))

    def snapshot(self):
        return deepcopy(self.data)

    def observe_combat(self, dt, player, enemies):
        live = [e for e in enemies if not getattr(e, "dead", False)]
        if not live or player.locked:
            return
        target = min(live, key=lambda e: abs(e.x-player.center_x))
        dx = target.x-player.center_x
        motion = self.data["combat_motion"]
        motion["seconds"] += dt
        motion["distance"] += abs(player.vx)*dt
        if abs(dx) < 180:
            motion["close_seconds"] += dt
        if player.vx*dx < 0 and abs(player.vx) > 90:
            motion["retreat_seconds"] += dt

    def broad_tendency(self):
        """A private authoring hint; never rendered as a player-facing meter."""
        attacks = self.count("attacks")
        defeats = self.count("enemies_defeated")
        dashes = self.count("dashes")
        damage = self.count("damage_taken")
        motion = self.data["combat_motion"]
        seconds = motion.get("seconds", 0)
        if seconds >= 20:
            if motion["retreat_seconds"] / seconds > .36:
                return "avoidant"
            boss_times = [float(t) for t in self.data["boss_clear_seconds"].values()
                          if isinstance(t, (int, float)) and t > 0]
            if defeats >= 20 and damage / max(1, seconds / 60) < .7 and boss_times and min(boss_times) < 75:
                return "precise"
            if attacks > 80 and motion["close_seconds"] / seconds > .45:
                return "aggressive"
            return "unreadable"
        if dashes >= 30 and dashes > attacks * .95:
            return "avoidant"
        if damage <= 2 and defeats >= 8:
            return "precise"
        if attacks > 55 and defeats > 14:
            return "aggressive"
        return "unreadable"

    def death_reaction(self, cause, weapon=None, arena=None):
        """Choose a short contextual line without repeating the last few."""
        total = self.count("deaths")
        cause = self._key(cause)
        arena = self._key(arena, "")
        weapon = self._key(weapon, "")
        if cause == "baby_face_giant" or arena == "baby_face_giant":
            candidates = ["...that was excessive.", "Hold still. I have an idea.",
                          "Fine. I am fixing his face."]
        elif cause in ("fall", "erased_floor"):
            candidates = ["The line was there a second ago.", "Feet first this time.",
                          "I should draw railings. I won't."]
        elif cause in ("ink_hazard", "ink_wall"):
            candidates = ["Still wet.", "That stain is not a doorway.",
                          "I wrote CAREFUL quite clearly."]
        elif "boss" in arena or cause in (
            "artist_mistake", "failed_sketch", "moon_compass",
            "wanted_sketch", "railroad_stapler", "orbital_mistake",
        ):
            candidates = ["Again. I can redraw faster than it can hit.",
                          "It remembers you now.", "One more clean attempt."]
        elif total <= 1:
            candidates = ["Oh. You come apart.", "Wait. Don't move."]
        elif total >= 5:
            candidates = ["I know the shape by heart now.", "Quicker lines. Same hero.",
                          "Please try to keep this version."]
        elif weapon and weapon != "pencil_blade":
            candidates = ["I drew you that tool.", "The weapon survived. Convenient.",
                          "Let's pretend that was practice."]
        else:
            candidates = ["Again, then.", "Almost neat this time.", "Back on the line."]
        for line in candidates:
            if line not in self._recent_lines:
                self._recent_lines.append(line)
                return line
        line = candidates[total % len(candidates)]
        self._recent_lines.append(line)
        return line

    def redraw_variant(self):
        """Cosmetic only: death never rolls a hidden gameplay punishment."""
        variants = ("clean", "crooked_head", "long_arm", "long_leg", "rushed")
        return variants[self.count("deaths") % len(variants)]
