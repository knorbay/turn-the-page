"""Render all six shipped boss cycles and the actual pencil combo.

The actor montage is a controlled animation review, not a playthrough.
Bosses use their real update/draw methods on their real page geometry.
Baby Face remains in its separate signature-beat review.
"""
import os
os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
import math
import sys
import tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import pygame
from PIL import Image
from game import Game
from combat import CombatArena
from weapons import MeleeSwing
from settings import WIDTH,HEIGHT


BOSS_CONFIGS = (
    (0, "moon_gate_duel", "MOON COMPASS", "JUMP THE ARC / PINNED HINGE"),
    (1, "marker_margin_trial", "WANTED SKETCH", "FIND THE WET POSTER"),
    (1, "midnight_train", "RAILROAD STAPLER", "THREE FALLING LANES"),
    (2, "zero_garden", "ORBITAL MISTAKE", "LET THE MOONS GO"),
    (3, "scissor_office", "SCISSOR DIRECTOR", "JUMP THE LOW CUT"),
    (4, "final_margin_revision", "FINAL EDITOR", "PRECISE / PROOF VOLLEY"),
)

MONTAGE_SIZE = (1680, 746)
TILE_SIZE = (552, 345)
CYCLE_FRAMES = 105
SNAPSHOT_FRAME = 12


def pil(surface):
    return Image.frombytes("RGB",surface.get_size(),pygame.image.tobytes(surface,"RGB"))


def stage_boss(enemy, ctx, bounds):
    """Restart one deterministic showcase cycle at its signature warning."""
    enemy._restore_temporary_erases(force=True)
    enemy.projectiles.clear()
    enemy.dead = False
    enemy.hp = enemy.max_hp
    enemy.hit_flash = enemy.hit_stun = enemy.attack_suppressed = 0
    enemy.invulnerable = 0
    enemy.time = 0
    enemy.x, enemy.y = enemy.review_origin
    enemy.vx = enemy.vy = 0
    ctx.player.invulnerable = 999

    if enemy.kind == "moon_compass":
        enemy.facing = 1 if ctx.player.center_x > enemy.x else -1
        enemy.anchor_x = enemy.x
        enemy.angle = .08 if enemy.facing > 0 else math.pi - .08
        enemy._set_state("sweep_telegraph", .94)
    elif enemy.kind == "wanted_sketch":
        enemy.combat_targets.clear()
        enemy.shuffle_index = 0
        enemy._shuffle(ctx, bounds)
    elif enemy.kind == "railroad_stapler":
        enemy.facing = 1 if ctx.player.center_x > enemy.x else -1
        enemy.lanes.clear()
        enemy.lane_index = 0
        enemy._brake(ctx, bounds)
    elif enemy.kind == "orbital_mistake":
        enemy.y = enemy.ground_y - 95
        enemy.orbiters = [0, 1, 2]
        enemy.orbit_angle = .2
        enemy.shot_target = (ctx.player.center_x, ctx.player.rect.centery)
        enemy._set_state("moon_release_warn", 1.0)
    elif enemy.kind == "scissor_director":
        enemy.facing = 1 if ctx.player.center_x > enemy.x else -1
        enemy.target_x = max(bounds[0] + 90,
                             min(bounds[1] - 90, ctx.player.center_x))
        enemy.pattern_index = 1
        enemy._set_state("cut_warn", .94)
    elif enemy.kind == "final_editor":
        # Phase three shows the complete precise script, while the explicit
        # remembered value prevents the behavior ledger choosing a fallback.
        ctx.game.behavior.data["final_scenario"] = "precise"
        enemy.scenario = "precise"
        enemy.phase = 3
        enemy.hp = 3
        enemy.pattern_cursor = -1
        enemy._start_pattern(ctx)
        enemy.mirror_weapon = "pencil_blade"


def titled_tile(screen, title_font, cue_font, title, cue):
    tile = pygame.transform.smoothscale(screen, TILE_SIZE)
    footer = pygame.Surface((TILE_SIZE[0], 31), pygame.SRCALPHA)
    footer.fill((25, 25, 27, 208))
    tile.blit(footer, (0, TILE_SIZE[1] - footer.get_height()))
    tile.blit(cue_font.render(cue, True, (233, 221, 190)),
              (9, TILE_SIZE[1] - 25))
    return tile, title_font.render(title, True, (242, 236, 216))


def main():
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    out=ROOT/"work"/"identity_pass_review"
    out.mkdir(parents=True,exist_ok=True)
    font=pygame.font.Font(None,25)
    cue_font=pygame.font.Font(None,21)
    games=[]
    with tempfile.TemporaryDirectory() as temp:
        for i,(page,room,title,cue) in enumerate(BOSS_CONFIGS):
            g=Game(screen,Path(temp)/f"review-{i}.json")
            g.level.load_chapter(page,"start",g.player,g.camera)
            g._apply_page_identity()
            a=next(a for a in g.level.entities.items if isinstance(a,CombatArena) and a.arena_id==room)
            for p in g.level.world.platforms:
                if p.thickness<=40:p.draw_progress=1
            ctx=g.level.context(g.player,g.camera,g.particles,g.sounds)
            a.encounter_active=True
            wave=max(s["wave"] for s in a.enemy_specs)
            a.wave=wave;a._spawn_wave(ctx,wave);a.boss_intro_time=0
            g.player.release_all_locks();g.player.x=a.start_x+360;g.player.y=542
            g.player.draw_amount=1;g.player.invulnerable=999
            g.camera.x=a.start_x+max(0,(a.end_x-a.start_x-WIDTH)/2)
            g.camera.offset_x=g.camera.offset_y=0
            g.level.page_title_time=g.level.toast_time=0
            boss=next(enemy for enemy in a.enemies
                      if getattr(enemy,"is_boss",False))
            boss.review_origin=(boss.x,boss.y)
            games.append((g,a,ctx,boss,title,cue))
        frames=[]
        for frame in range(210):
            montage=pygame.Surface(MONTAGE_SIZE);montage.fill((39,39,38))
            for i,(g,a,ctx,boss,title,cue) in enumerate(games):
                bounds=(a.start_x-45,a.end_x-35)
                if frame%CYCLE_FRAMES==0:
                    g.particles.items.clear()
                    stage_boss(boss,ctx,bounds)
                g.time=frame/30
                boss.update(1/30,ctx,bounds)
                g.particles.update(1/30)
                g.camera.offset_x=g.camera.offset_y=0
                g._draw_scene(g.screen)
                tile,title_surface=titled_tile(g.screen,font,cue_font,title,cue)
                x=(i%3)*560+4;y=(i//3)*373+24
                montage.blit(tile,(x,y))
                montage.blit(title_surface,(x,y-23))
                if frame==SNAPSHOT_FRAME:
                    pygame.image.save(g.screen,out/f"boss-{i+1}.png")
            if frame==SNAPSHOT_FRAME:
                pygame.image.save(montage,out/"Bosslar-ve-Ders-Notlari.png")
            if frame%2==0:
                frames.append(pil(pygame.transform.smoothscale(montage,(1344,597))))
        frames[0].save(out/"Boss-Davranislari.gif",save_all=True,
                        append_images=frames[1:],duration=67,loop=0)
        # Three different combat strokes, with actual pose and ribbon code.
        g=games[0][0]
        g.player.x=160;g.player.y=218;g.player.on_ground=True
        g.player.invulnerable=0;g.player.page_style="ronin"
        g.player.current_weapon="pencil_blade"
        g.camera.x=0;g.camera.offset_x=g.camera.offset_y=0
        combo=[]
        for frame in range(72):
            t=frame/30
            panel=pygame.Surface((840,315));panel.fill((242,235,211))
            for i,duration in enumerate((.25,.28,.46)):
                g.player.x=100+i*280
                swing=MeleeSwing(i+1,pygame.Vector2(1,0),duration,.045,
                    .16 if i<2 else .25,1, (61,67,91)[i],100,.1)
                local=t%.8
                swing.elapsed=min(duration,local)
                g.weapons.melee=swing if local<duration else None
                g.player.combat_swing=swing.pencil_pose() if local<duration else None
                g.player.anim_time=t;g.player.vx=0
                if g.weapons.melee:g.weapons._draw_melee(panel,g.camera)
                g.player.draw(panel,g.camera)
                pygame.draw.line(panel,(112,99,76),(20+i*280,267),(260+i*280,267),1)
                panel.blit(font.render(("01 / KESİŞ","02 / TERS KESİŞ","03 / BİTİRİCİ")[i],
                                       True,(58,58,57)),(30+i*280,30))
            combo.append(pil(panel))
        combo[0].save(out/"Katana-Hareketleri.gif",save_all=True,
                       append_images=combo[1:],duration=33,loop=0)
        notes=pygame.Surface((1020,825));notes.fill((242,235,211))
        for page in range(5):
            for i in range(2):
                notes.blit(g.renderer.notebook_notes.sheets[page][i],(i*510,page*165))
        pygame.image.save(notes,out/"ders-notlari.png")
    pygame.quit()
    print(out)


if __name__=="__main__":main()
