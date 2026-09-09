"""Writable user files live outside the standalone application bundle."""
import os
import sys
from pathlib import Path

from settings import TITLE


def _user_data_root():
    if sys.platform == "darwin":
        return Path.home()/"Library"/"Application Support"
    if sys.platform == "win32":
        return Path(os.environ.get("APPDATA", Path.home()/"AppData"/"Roaming"))
    return Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local"/"share"))


def default_save_path():
    override = os.environ.get("PAPER_STORY_SAVE")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        return _user_data_root()/TITLE/"paper_story_save.json"
    return Path(__file__).with_name("paper_story_save.json")


def legacy_save_path():
    """The beta rename keeps progress from the previous macOS build."""
    if sys.platform == "darwin":
        return Path.home()/"Library"/"Application Support"/"Turn the Page"/"paper_story_save.json"
    return None


def resource_path(*parts):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root.joinpath(*parts)
