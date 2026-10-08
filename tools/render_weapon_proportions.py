"""Compare real held tools, hands and page scenery at the game's native scale.

Capture ``before`` before editing, then ``after``. User saves are never read.
The review board uses unscaled 360x148 crops from Game._draw_scene, alongside
separate nearest-neighbour enlargements for checking attachment details.
"""
from pathlib import Path
import argparse
import math
import os
import sys
import tempfile
import zipfile
from types import ModuleType

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame
from game import Game
from page_arsenal import PAGE_ENTRY_TOOLS, profile_for
from page_flow import FLOW_SECTIONS
from settings import WIDTH, HEIGHT
from player import Player
from weapons import WeaponSystem
from localization import set_language, translate


CASES = [(f"page-{page}", page, PAGE_ENTRY_TOOLS[page], "idle", "Bölüm " + str(page + 1))
         for page in range(5)] + [
    ("western-double", 1, "marker_shotgun", "idle", "Çift namlu / taşıma"),
    ("agent-rifle", 3, "carbon_lance", "idle", "Karbon tüfek / taşıma"),
    ("space-null", 2, "eraser_cannon", "idle", "Hiçlik topu / taşıma"),
    ("final-sword", 4, "excalibur", "idle", "Excalibur / taşıma"),
    ("western-capsule", 1, "chalk_bomb", "idle", "Tebeşir kapsülü / taşıma"),
    ("agent-up", 3, "ink_pistol", "up", "Ajan tabancası / yukarı nişan"),
    ("rifle-left", 3, "carbon_lance", "left", "Karbon tüfek / sol nişan"),
    ("double-reload", 1, "marker_shotgun", "reload", "Çift namlu / doldurma"),
    ("katana-cut", 0, "pencil_blade", "cut", "Katana / kesiş"),
    ("bowie-cut", 1, "pencil_blade", "cut", "Bowie / kesiş"),
    ("field-cut", 3, "pencil_blade", "cut", "Saha bıçağı / kesiş"),
    ("maul-cut", 4, "margin_maul", "cut", "Kalem tokmak / kesiş"),
]


def capture(out, stage):
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    target = out / stage
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ttp-weapons-") as temp:
        game = Game(screen, Path(temp) / "review.json")
        for name, page, weapon, pose, _label in CASES:
            game.level.load_chapter(page, "start", game.player, game.camera)
            game._attach_runtime()
            game.weapons.lend_drawn_tool(weapon)
            player = game.player
            player.current_weapon = weapon
            player.page_style = ("ronin", "cowboy", "astronaut", "ink_agent", "bad_drawing")[page]
            position = FLOW_SECTIONS[page][0][1][0]
            support = next((p for p in game.level.world.platforms
                            if p.collider_active and p.one_way and p.x1 <= position + 12 <= p.x2), None)
            player.x = position
            player.y = (support.y_at(position + 12) if support else 590) - player.HEIGHT
            player.draw_amount = 1
            player.on_ground = True
            player.release_all_locks()
            player.anim_time = .75
            player.motion_speed = 0
            player.stride_phase = 0
            player.weapon_reload_progress = None
            player.weapon_recoil = 0
            player.combat_swing = None
            player.facing = -1 if pose == "left" else 1
            player.aim_angle = math.pi if pose == "left" else -1.05 if pose == "up" else 0
            game.weapons.aim_direction = pygame.Vector2(math.cos(player.aim_angle), math.sin(player.aim_angle))
            if pose == "reload":
                player.weapon_reload_progress = .47
            elif pose == "cut":
                context = game.level.context(game.player, game.camera, game.particles, game.sounds)
                game.weapons.handle_input(fire_pressed=True, aim={"direction": (1, 0)}, ctx=context)
                swing = game.weapons.melee
                if swing:
                    swing.elapsed = swing.active_from + .025
                    # The real attack pose: the animation owns angle, physical
                    # reach remains the combat contract.
                    player.combat_swing = swing.pencil_pose()
            game.camera.x = max(0, position - WIDTH * .38)
            game.camera.offset_x = game.camera.offset_y = 0
            game.level.page_title_time = game.level.toast_time = 0
            game.weapon_reveal_time = 0
            game.state = "playing"
            game.time = 1.2
            frame = pygame.Surface((WIDTH, HEIGHT))
            game._draw_scene(frame)
            pygame.image.save(frame, target / (name + "-game.png"))
            crop = pygame.Rect(game.camera.screen_x(player.center_x) - 132,
                               round(player.y) - 56, 360, 148)
            native = frame.subsurface(crop).copy()
            pygame.image.save(native, target / (name + ".png"))
            pygame.image.save(pygame.transform.scale(native, (1080, 444)),
                              target / (name + "-detail.png"))
        pygame.mixer.stop()


def review(out, destination):
    set_language("tr")
    font = pygame.font.Font(pygame.font.match_font("arial,dejavusans"), 16)
    small = pygame.font.Font(pygame.font.match_font("arial,dejavusans"), 13)
    row_h = 236
    board = pygame.Surface((1190, 88 + row_h * len(CASES)))
    board.fill((242, 236, 216))
    board.blit(font.render("SİLAH ORANLARI · oyun içi ölçekte (1:1)", True, (45, 43, 45)), (24, 16))
    board.blit(small.render("Aynı karakter, kamera, sayfa ve poz. Solda / ortada gerçek ölçek; sağda yeni çizimin 2 kat detayı.", True, (80, 77, 69)), (24, 42))
    for x, title in ((24, "0.35 · önce · 1:1"), (404, "0.36 · sonra · 1:1"), (824, "0.36 · el / gövde detayı · 2:1")):
        board.blit(small.render(title, True, (90, 82, 73)), (x, 66))
    for index, (name, page, weapon, _pose, label) in enumerate(CASES):
        top = 88 + index * row_h
        title = label + " · " + translate(profile_for(page, weapon).label)
        board.blit(small.render(title, True, (45, 43, 45)), (24, top))
        for column, stage in enumerate(("before", "after")):
            image = pygame.image.load(out / stage / (name + ".png"))
            x = 24 + column * 380
            board.blit(image, (x, top + 26))
            if stage == "after":
                detail = image.subsurface((84, 19, 148, 102)).copy()
                board.blit(pygame.transform.scale(detail, (296, 204)), (824, top + 26))
        pygame.draw.line(board, (204, 195, 171), (24, top + row_h - 4), (1158, top + row_h - 4))
    destination.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(board, destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("before", "after", "review"))
    parser.add_argument("out", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--reference-source", type=Path,
                        help="For before, use original held drawing/muzzle from a saved release ZIP.")
    args = parser.parse_args()
    if args.reference_source:
        if args.stage != "before":
            parser.error("A reference source is only used for the before capture")
        with zipfile.ZipFile(args.reference_source) as archive:
            for filename, cls, method in (("player.py", Player, "_draw_weapon_and_hands"),
                                          ("weapons.py", WeaponSystem, "muzzle")):
                path = next(name for name in archive.namelist() if name.endswith("/" + filename))
                reference = ModuleType("reference_" + filename[:-3])
                sys.modules[reference.__name__] = reference
                namespace = reference.__dict__
                exec(compile(archive.read(path).decode("utf-8"), str(args.reference_source) + ":" + path, "exec"), namespace)
                setattr(cls, method, getattr(namespace[cls.__name__], method))
    pygame.init()
    try:
        if args.stage == "review":
            review(args.out, args.review or args.out / "review.png")
        else:
            capture(args.out, args.stage)
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
