"""Jump into a beta page or room using a disposable practice save."""
import argparse
import tempfile
from pathlib import Path
import pygame
from action_content import WeaponPickup
from combat import CombatArena
from game import Game
from settings import WIDTH,HEIGHT


def main():
    parser=argparse.ArgumentParser(description='Turn the Page — separate chapter practice')
    parser.add_argument('--page',type=int,choices=range(1,6),default=1)
    parser.add_argument('--room',help='Optional encounter id; see BETA_NOTLARI_TR.md')
    parser.add_argument('--boss',action='store_true',help='Start at the named boss wave in --room')
    args=parser.parse_args()
    if args.boss and not args.room:
        parser.error('--boss requires --room')
    pygame.mixer.pre_init(22050,-16,1,512)
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT),pygame.RESIZABLE)
    with tempfile.TemporaryDirectory(prefix='turn-the-page-practice-') as directory:
        game=Game(screen,Path(directory)/'practice.json')
        game.reset(True)
        page=args.page-1
        game.level.load_chapter(page,'start',game.player,game.camera)
        if args.room:
            arenas={a.arena_id:a for a in game.level.entities.items if isinstance(a,CombatArena)}
            if args.room not in arenas:
                parser.error('This page has: '+', '.join(arenas))
            arena=arenas[args.room]
            cp=max((cp for cp in game.level.runtime.checkpoints if cp.x<arena.start_x),key=lambda cp:cp.x)
            game.level.load_chapter(page,cp.checkpoint_id,game.player,game.camera)
            game.player.x=arena.start_x-150
        game._apply_page_identity()
        for gift in sorted((e for e in game.level.entities.items if isinstance(e,WeaponPickup)),key=lambda e:e.x):
            if gift.x<=game.player.x:
                game.weapons.unlock(gift.weapon_id)
                game.weapons.select(gift.weapon_id)
        game.state='playing'
        game.level.toast='CHAPTER PRACTICE / your campaign save is safe'
        game.level.toast_time=5
        game.sounds.start_ambience(page)
        if args.boss:
            arena=next(a for a in game.level.entities.items
                       if isinstance(a,CombatArena) and a.arena_id==args.room)
            if not arena.boss:
                parser.error('This room does not have a named boss')
            ctx=game.level.context(game.player,game.camera,game.particles,game.sounds)
            arena.encounter_active=True
            arena.wave=len(arena.wave_ids)-1
            arena._spawn_wave(ctx,arena.wave_ids[-1])
            arena.entrance_gate.enabled=True
            game.player.x=arena.start_x+80
            game.player.y=542
            game.player.release_all_locks()
            game.player.draw_amount=1
            game.camera.x=max(0,arena.start_x-30)
        pygame.display.set_caption('TURN THE PAGE — Chapter Practice')
        game.run()
    pygame.quit()

if __name__=='__main__':main()
