"""Opt-in packaged-runtime verification; normal launches never enter here."""
import json
import sys
import tempfile
from pathlib import Path
import pygame
from game import Game
from input_state import InputFrame
from runtime_paths import default_save_path
from settings import WIDTH, HEIGHT, VERSION


def verify(output):
    pygame.mixer.pre_init(22050,-16,1,512)
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    pages=[]
    with tempfile.TemporaryDirectory(prefix="ttp-check-") as directory:
        game=Game(screen,Path(directory)/"save.json")
        for page in range(5):
            game.level.load_chapter(page,"start",game.player,game.camera)
            game._apply_page_identity()
            game.sounds.start_ambience(page)
            game.state="playing"
            for _ in range(3):game.update(1/60,InputFrame())
            game.draw()
            assert game.player.max_health==3
            pages.append(game.level.title)
        game.save.write()
        game.save.load()
        assert game.save.path.exists()
        report={"version":VERSION,"frozen":bool(getattr(sys,"frozen",False)),"pages":pages,
                "save_path":str(default_save_path()),"audio":game.sounds.enabled,
                "asset_root":str(game.sounds.asset_root)}
    pygame.quit()
    Path(output).write_text(json.dumps(report,indent=2),encoding="utf8")
