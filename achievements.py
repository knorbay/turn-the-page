"""Small, persistent achievements earned from facts already recorded by the game."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Achievement:
    achievement_id: str
    title: str
    description: str
    hidden: bool = False


ACHIEVEMENTS = (
    Achievement("first_draft", "A SAFE FIRST DRAFT", "Cross out the opening practice drawing."),
    Achievement("heard_you", "I CAN HEAR YOU", "Reply to the Artist's margin note."),
    Achievement("conversation", "A SMALL CONVERSATION", "Reply to the Artist five times."),
    Achievement("first_revision", "A LINE OF YOUR OWN", "Solve a physical page puzzle."),
    Achievement("three_revisions", "REWRITE THE ROUTE", "Solve all three page route puzzles."),
    Achievement("bestiary", "FIELD NOTES", "Defeat twelve different enemy kinds."),
    Achievement("new_ink", "UNFAMILIAR INK", "Defeat a Fold Duelist, Margin Sniper and Split Lantern."),
    Achievement("full_sketchbook", "EVERY LOST LINE", "Collect all twelve Lost Sketches."),
    Achievement("six_signatures", "SIX SIGNATURES", "Defeat all six named bosses."),
    Achievement("ten_returns", "POST OFFICE", "Perfectly return ten incoming shots."),
    Achievement("twenty_rooms", "MARGIN EXPLORER", "Clear twenty encounters."),
    Achievement("first_crossout", "FIRST CROSS-OUT", "Defeat the first hostile doodle."),
    Achievement("margin_runner", "BRAVEMAN",
                "Reach a page turn while avoiding more than attacking.", True),
    Achievement("overdrawn", "THE AGGRO MAN",
                "Attack 90 times, mostly with the Pencil Blade.", True),
    Achievement("clean_copy", "NO RED MARKS", "Finish a page without taking damage.", True),
    Achievement("back_page_reader", "BACK-PAGE READER", "Clip three Lost Sketches into the back pages."),
    Achievement("toolbox", "TEMPORARY TOOLBOX", "Attack with every ordinary page weapon."),
    Achievement("fast_revision", "QUICK REVISION", "Clear a named boss in under 45 seconds."),
    Achievement("page_one", "TURN ONE OVER", "Finish the samurai page."),
    Achievement("three_worlds", "THREE BAD DRAFTS", "Finish the first three pages."),
    Achievement("king_arthur", "KING ARTHUR", "Pull the Artist's impossible sword from the page.", True),
    Achievement("final_proof", "FINAL PROOF", "Defeat the Final Editor's chosen revision."),
    Achievement("five_named", "FIVE NAMES CROSSED OUT", "Defeat the five original named bosses."),
    Achievement("open_page", "THE PAGE REMAINS OPEN", "Reach the blank page."),
    Achievement("five_pages", "FIVE PAGES LATER", "Finish all five pages."),
    Achievement("head_of_redaction", "CUT THAT OUT", "Defeat the Head of Redaction."),
    Achievement("mirror", "MIRROR", "Face the proof made from your clean play.", True),
    Achievement("return_to_sender", "RETURN TO SENDER", "Return three shots with a perfectly timed dash."),
)

ACHIEVEMENT_BY_ID = {item.achievement_id: item for item in ACHIEVEMENTS}


class AchievementTracker:
    """Evaluates the behavior ledger without adding a second gameplay score."""

    def __init__(self, save_system):
        self.save = save_system
        self.unlocked = set(save_system.data.get("achievements", ()))
        self.pending = deque()

    def unlock(self, achievement_id):
        if achievement_id in self.unlocked or achievement_id not in ACHIEVEMENT_BY_ID:
            return False
        self.unlocked.add(achievement_id)
        self.pending.append(ACHIEVEMENT_BY_ID[achievement_id])
        self.save.unlock_achievement(achievement_id)
        return True

    def evaluate(self, game):
        behavior = game.behavior
        data = behavior.data
        boss_times = data.get("boss_clear_seconds", {})
        enemy_defeats = data.get("enemy_defeats", {})
        weapon_uses = data.get("weapon_uses", {})
        rules = {
            "first_draft": behavior.count("practice_complete") >= 1,
            "heard_you": behavior.count("artist_reply") >= 1,
            "conversation": behavior.count("artist_reply") >= 5,
            "first_revision": len(set(data.get("puzzles_solved", ()))) >= 1,
            "three_revisions": {"first_page_draft", "wanted_perforation",
                                "satellite_relay"}.issubset(data.get("puzzles_solved", ())),
            "bestiary": sum(int(n) > 0 for n in enemy_defeats.values()) >= 12,
            "new_ink": all(int(enemy_defeats.get(k, 0)) > 0 for k in
                           ("fold_duelist", "margin_sniper", "split_lantern")),
            "full_sketchbook": len(set(game.save.data.get("secrets", ()))) >= 12,
            "six_signatures": {"moon_compass", "wanted_sketch", "railroad_stapler",
                               "orbital_mistake", "scissor_director", "final_editor"}.issubset(boss_times),
            "ten_returns": behavior.count("perfect_return") >= 10,
            "twenty_rooms": behavior.count("arena_clear") >= 20,
        }
        for key, earned in rules.items():
            if earned:
                self.unlock(key)
        if behavior.count("enemies_defeated") >= 1:
            self.unlock("first_crossout")
        if (behavior.count("pages_completed") >= 1
                and behavior.count("dashes") >= 30
                and behavior.count("dashes") > behavior.count("attacks") * .95):
            self.unlock("margin_runner")
        if (behavior.count("attacks") >= 90
                and int(weapon_uses.get("pencil_blade", 0)) >= 60):
            self.unlock("overdrawn")
        if behavior.count("pages_completed") >= 1 and behavior.count("damage_taken") == 0:
            self.unlock("clean_copy")
        if len(game.save.data.get("secrets", ())) >= 3:
            self.unlock("back_page_reader")
        ordinary_tools = {"pencil_blade", "ink_pistol", "marker_shotgun",
                          "eraser_cannon", "rubber_band"}
        if all(int(weapon_uses.get(tool, 0)) > 0 for tool in ordinary_tools):
            self.unlock("toolbox")
        def quick_clear(value):
            try:
                seconds = float(value)
            except (TypeError, ValueError, OverflowError):
                return False
            return 0 < seconds <= 45

        if any(quick_clear(seconds) for seconds in boss_times.values()):
            self.unlock("fast_revision")
        if behavior.count("pages_completed") >= 1:
            self.unlock("page_one")
        if behavior.count("pages_completed") >= 3:
            self.unlock("three_worlds")
        if (behavior.deaths_to("baby_face_giant") >= 2
                and "excalibur" in game.weapons.unlocked):
            self.unlock("king_arthur")
        if int(enemy_defeats.get("final_editor", 0)) >= 1:
            self.unlock("final_proof")
        real_bosses = {"moon_compass", "wanted_sketch", "railroad_stapler",
                       "orbital_mistake", "final_editor"}
        if real_bosses.issubset(set(boss_times)):
            self.unlock("five_named")
        if game.save.data.get("completed", False):
            self.unlock("open_page")
        if behavior.count("pages_completed") >= 5:
            self.unlock("five_pages")
        if "scissor_director" in boss_times:
            self.unlock("head_of_redaction")
        if data.get("final_scenario") == "precise":
            self.unlock("mirror")
        if behavior.count("perfect_return") >= 3:
            self.unlock("return_to_sender")

    @property
    def total(self):
        return len(ACHIEVEMENTS)

    @property
    def count(self):
        return sum(item.achievement_id in self.unlocked for item in ACHIEVEMENTS)


__all__ = ["Achievement", "AchievementTracker", "ACHIEVEMENTS", "ACHIEVEMENT_BY_ID"]
