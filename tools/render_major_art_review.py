"""Real page scenes and a material/pose contact sheet for the major art pass."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from camera import Camera
from page_arsenal import ORIGINAL, PAGE_TOOLS, draw_weapon, draw_weapon_icon
from player import Player
from settings import HEIGHT, WIDTH


def weapon_sheet(out):
    tools = [(page, weapon, profile) for page, entries in PAGE_TOOLS.items()
             for weapon, profile in entries.items()]
    specialized = {profile.silhouette for _, _, profile in tools}
    tools.extend((None, weapon, profile) for weapon, profile in ORIGINAL.items()
                 if weapon != "unarmed" and profile.silhouette not in specialized)
    width, row_height = 1200, 160
    sheet = pygame.Surface((width, ((len(tools)+3)//4)*row_height))
    sheet.fill((242, 236, 215))
    font = pygame.font.Font(pygame.font.match_font("arial,dejavusans"), 16)
    for index, (page, weapon, profile) in enumerate(tools):
        left, top = (index % 4)*300, (index//4)*row_height
        pygame.draw.line(sheet, (181,172,150), (left+14,top+145), (left+286,top+145))
        sheet.blit(font.render(profile.label, True, (45,43,45)), (left+15,top+12))
        draw_weapon(sheet, weapon, page, (left+93,top+69), -.11, 1.7)
        draw_weapon_icon(sheet, weapon, page, (left+250,top+83), 46)
    pygame.image.save(sheet, out/"weapon-materials.png")


def actor_sheet(out):
    width, panel_w, panel_h = 1200, 240, 350
    sheet = pygame.Surface((width, panel_h*2))
    sheet.fill((243, 237, 215))
    font = pygame.font.Font(pygame.font.match_font("arial,dejavusans"), 18)
    styles = ("ronin", "cowboy", "astronaut", "ink_agent", "bad_drawing")
    tools = ("pencil_blade", "ink_pistol", "eraser_cannon", "carbon_lance", "margin_maul")
    for page, (style, weapon) in enumerate(zip(styles, tools)):
        for pose in range(2):
            native = pygame.Surface((120,140))
            native.fill((243,237,215))
            player = Player(43,72)
            player.draw_amount = 1
            player.page_style = style
            player.arsenal_page = page
            player.current_weapon = weapon
            player.facing = 1 if not pose else -1
            player.aim_angle = 0 if not pose else 3.14
            player.anim_time = .75
            player.motion_speed = .65 if pose else 0
            player.stride_phase = 1.1 if pose else 0
            player.on_ground = True
            if pose and page in (1,2,3):
                player.weapon_reload_progress = .47
            elif pose:
                player.combat_swing = (2.64, 81, .9)
            player.draw(native, Camera(120))
            scaled = pygame.transform.scale(native, (panel_w,panel_h-70))
            px, py = page*panel_w, pose*panel_h
            sheet.blit(scaled, (px,py+40))
            sheet.blit(font.render(style.upper(),True,(45,43,45)), (px+15,py+12))
    pygame.image.save(sheet, out/"player-poses.png")


def game_scenes(out):
    from game import Game
    from page_arsenal import PAGE_ENTRY_TOOLS
    from page_flow import FLOW_SECTIONS
    screen = pygame.display.set_mode((WIDTH,HEIGHT))
    with tempfile.TemporaryDirectory(prefix="turn-the-page-art-") as folder:
        game = Game(screen, Path(folder)/"review.json")
        for page in range(5):
            game.level.load_chapter(page,"start",game.player,game.camera)
            game._attach_runtime()
            game.weapons.lend_drawn_tool(PAGE_ENTRY_TOOLS[page])
            game.player.current_weapon = game.weapons.current_id
            game.player.page_style = ("ronin", "cowboy", "astronaut", "ink_agent", "bad_drawing")[page]
            sections = FLOW_SECTIONS.get(page, ())
            position = sections[0][1][0] if sections else 500
            support = next((p for p in game.level.world.platforms
                            if p.collider_active and p.one_way and p.x1 <= position+12 <= p.x2), None)
            game.player.x = position
            game.player.y = (support.y_at(position+12) if support else 590)-game.player.HEIGHT
            game.player.draw_amount = 1
            game.player.on_ground = True
            game.player.release_all_locks()
            game.camera.x = max(0,position-WIDTH*.38)
            game.camera.offset_x = game.camera.offset_y = 0
            game.level.page_title_time = game.level.toast_time = 0
            game.weapon_reveal_time = 0
            game.state = "playing"
            game.time = 1.2
            for p in game.level.world.platforms:
                if p.draw_progress >= 1:
                    p.refresh_lifecycle([])
            frame = pygame.Surface((WIDTH,HEIGHT))
            game._draw_scene(frame)
            pygame.image.save(frame, out/f"page-{page+1}.png")


def main():
    out = Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/"work"/"major-visual"/"after"
    out.mkdir(parents=True, exist_ok=True)
    pygame.init()
    try:
        weapon_sheet(out)
        actor_sheet(out)
        game_scenes(out)
    finally:
        pygame.quit()
    print(out)


if __name__ == "__main__":
    main()
