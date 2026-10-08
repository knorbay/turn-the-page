"""Capture isolated arena scenes and scale diagrams, never a user's save."""
from __future__ import annotations
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
from pathlib import Path
import sys
import tempfile
import pygame

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chapters import build_chapter
from encounter_revision import ROOM_LAYOUTS
from game import Game
from input_state import InputFrame
from localization import set_language
from settings import WIDTH, HEIGHT

OUT = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'work/encounter-review'


def scene(page, arena_id):
    screen = pygame.display.get_surface()
    with tempfile.TemporaryDirectory() as directory:
        game = Game(screen, Path(directory)/'review.json')
        game.state = 'playing'
        game.level.load_chapter(page, 'before_'+arena_id, game.player, game.camera)
        game._attach_runtime()
        arena = next(e for e in game.level.entities.items if getattr(e,'arena_id','')==arena_id)
        # Enter using the same walk controller as gameplay. Invulnerability
        # lets the automated photographer wait for the ink to finish safely.
        game.player.invulnerable = 999
        for _ in range(250):
            game.update(1/60, InputFrame(right=not arena.encounter_active))
            if arena.encounter_active and arena.enemies and all(
                    getattr(e,'notebook_reveal',1)==1 for e in arena.enemies):
                break
        game.level.page_title_time=game.level.toast_time=0
        game.level.interaction_hint=''
        game.time=8
        game.camera.x=game.camera.target_x=arena.start_x-140
        game._draw_scene(screen)
        pygame.image.save(screen, OUT/(arena_id+'-entry.png'))
        # A world-wide renderer frame verifies that the extra floor and gates
        # belong to this room, not an overlapping extension into the next one.
        panorama=pygame.Surface((int(arena.end_x-arena.start_x)+240, HEIGHT))
        arena.boss_intro_time=0
        # The paper texture is a native1120px canvas; stitch fixed-size
        # frames rather than inventing a larger unsupported game viewport.
        for left in range(0, panorama.get_width(), WIDTH):
            game.camera.x=game.camera.target_x=arena.start_x-120+left
            game._draw_scene(screen)
            panorama.blit(screen,(left,0))
        pygame.image.save(panorama, OUT/(arena_id+'-full-room.png'))
        return arena.end_x-arena.start_x


def route_chart():
    surface = pygame.Surface((1450, 1420))
    surface.fill((241,235,214))
    title=pygame.font.SysFont('Arial',27,bold=True)
    font=pygame.font.SysFont('Arial',17)
    surface.blit(title.render('Combat rooms / physical scale and wave rhythm',True,(49,47,44)),(35,25))
    y=80
    for page in range(5):
        runtime=build_chapter(page)
        surface.blit(title.render(f'PAGE {page+1} / {int(runtime.end_x)} world units',True,(128,67,65)),(35,y))
        y+=42
        for arena in (e for e in runtime.entities.items if getattr(e,'is_combat_arena',False)):
            span=arena.end_x-arena.start_x
            text=f'{arena.arena_id}  /  {int(span)}  /  '+('single boss duel' if arena.boss else f'{len(arena.wave_ids)} wave(s)')
            surface.blit(font.render(text,True,(49,47,44)),(35,y))
            left=570
            pygame.draw.rect(surface,(174,165,139),(left,y+3,round(span*.275),13),1)
            pygame.draw.rect(surface,(133,64,60) if arena.boss else (74,106,117),(left,y+3,round(span*.275),13))
            if not arena.boss:
                for n in range(1,len(arena.wave_ids)):
                    px=left+round(span*.275*n/len(arena.wave_ids))
                    pygame.draw.line(surface,(241,235,214),(px,y+3),(px,y+16),2)
            y+=31
        y+=20
    pygame.image.save(surface,OUT/'room-scale-and-rhythm.png')


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    pygame.mixer.pre_init(22050,-16,1,512)
    pygame.init();pygame.display.set_mode((WIDTH,HEIGHT));set_language('tr')
    for page,arena in ((0,'first_crossout'),(0,'bamboo_static'),
                       (0,'moon_gate_duel'),(3,'scissor_office'),(4,'final_margin_revision')):
        scene(page,arena)
    route_chart()
    pygame.quit()
    print(OUT)


if __name__=='__main__':main()
