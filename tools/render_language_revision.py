"""Review all four renderer languages with disposable saves and no native window."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT','1')
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from advanced_enemies import create_enemy
from game import Game
from localization import SUPPORTED_LANGUAGES, set_language, translate
from settings import WIDTH, HEIGHT


class AuditFont:
    def __init__(self,font,log):
        self.font,self.log=font,log
    def render(self,text,*args,**kwargs):
        self.log.append(translate(str(text)))
        return self.font.render(text,*args,**kwargs)
    def __getattr__(self,name):
        return getattr(self.font,name)


def capture(game,out,name,log):
    old_small,old_font=game.renderer.font_small,game.renderer.font
    game.renderer.font_small=AuditFont(old_small,log)
    game.renderer.font=AuditFont(old_font,log)
    try:
        game.draw()
        pygame.image.save(game.screen,out/(name+'.png'))
    finally:
        game.renderer.font_small,game.renderer.font=old_small,old_font


def choose_language(game,language):
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f'Unsupported review language: {language}')
    while game.save.data['settings']['language']!=language:
        game.settings_index=5
        game._change_setting(1)
    set_language(language)


def main():
    out=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'work'/'language-review'
    out.mkdir(parents=True,exist_ok=True)
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    labels={}
    with tempfile.TemporaryDirectory() as tmp:
        game=Game(screen,Path(tmp)/'review.json')
        for page,aid,kind in ((0,'moon_gate_duel','moon_compass'),
                (1,'midnight_train','railroad_stapler'),(2,'zero_garden','orbital_mistake'),
                (3,'scissor_office','scissor_director'),(4,'final_margin_revision','final_editor')):
            game.level.load_chapter(page,'start',game.player,game.camera)
            game._attach_runtime()
            arena=next(e for e in game.level.entities.items if getattr(e,'arena_id',None)==aid)
            game.player.x=arena.start_x+180
            game.player.y=542
            game.player.draw_amount=1
            game.player.on_ground=True
            game.player.release_all_locks()
            game.camera.x=arena.start_x-90
            game.camera.offset_y=game.camera.offset_x=0
            arena.enemies=[create_enemy(kind,arena.start_x+740)]
            arena.encounter_active=True
            arena.wave=len(arena.wave_ids)-1
            arena.boss_intro_time=2
            game.level.page_title_time=game.level.toast_time=0
            game.weapon_reveal_time=game.achievement_time=0
            game.level.interaction_hint=''
            lesson=getattr(game.level.runtime,'training',None)
            if lesson:lesson.completed=True
            game.weapons.lend_drawn_tool(('folded_shuriken','ink_pistol','rubber_band',
                                         'ink_pistol','pencil_blade')[page])
            game.state='playing'
            for language in SUPPORTED_LANGUAGES:
                choose_language(game,language)
                name=f'{language}-boss-page-{page+1}'
                log=[]
                capture(game,out,name,log)
                labels[name]=sorted(set(log))
        game.level.load_chapter(0,'start',game.player,game.camera)
        game._attach_runtime()
        game.level.runtime.training.completed=True
        game.player.x=1050
        game.player.y=542
        game.player.draw_amount=1
        game.player.release_all_locks()
        game.player.dash_cooldown=.35
        game.camera.x=600
        game.camera.offset_x=game.camera.offset_y=0
        game.level.page_title_time=game.level.toast_time=0
        game.level.interaction_hint=''
        game.weapon_reveal_time=game.achievement_time=0
        game.weapons.lend_drawn_tool('folded_shuriken')
        game.artist_companion.text='I left that edge too faint. I have redrawn the landing.'
        game.artist_companion.reply='I see it now. Leave the next line visible, please.'
        game.artist_companion.timer=6.5
        for language in SUPPORTED_LANGUAGES:
            choose_language(game,language)
            log=[]
            name=f'{language}-compact-dialogue-dash'
            capture(game,out,name,log)
            labels[name]=sorted(set(log))
        (out/'rendered-language-labels.json').write_text(
            json.dumps(labels,ensure_ascii=False,indent=2))
    pygame.quit()
    print(out)


if __name__=='__main__':main()
