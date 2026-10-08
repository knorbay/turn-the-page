"""Regenerate store media from the shipping game and temporary saves.

Screenshots and GIF frames are Game.draw output. Scene setup chooses an
authored checkpoint and an already-earned tool; actions, enemy reveals,
collision, boss camera zoom and warnings then run through Game.update.
Cover/banner are promotional compositions of the existing code-drawn brand
art and notebook materials, and are kept separate from gameplay screenshots.
"""
from __future__ import annotations

import argparse
import gc
import io
import json
import os
from pathlib import Path
import random
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER","dummy")
os.environ.setdefault("SDL_AUDIODRIVER","dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT","1")
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import pygame
from PIL import Image, ImageDraw, ImageFont

from afterword import Afterword
from combat import CombatArena
from game import Game
from input_state import InputFrame
from localization import set_language
from major_campaign import SecretPocket
from optional_encounters import OptionalGuardianPocket
from settings import HEIGHT, WIDTH, VERSION
from sketches import SKETCHES
from brand_art import hero_sprite, artist_sprite

DEFAULT_OUTPUT=ROOT.parents[1]/"outputs"/"itch-0.42"
FPS=12
GIF_SIZE=(800,500)


def pil(surface):
    return Image.frombytes("RGB",surface.get_size(),pygame.image.tobytes(surface,"RGB"))


def place(game,x,bottom=590):
    player=game.player
    player.x,player.y=x,bottom-player.HEIGHT
    player.vx=player.vy=0
    player.on_ground=player.was_grounded=True
    player.facing=1
    game.camera.x=game.camera.target_x=max(0,min(game.level.world.width-WIDTH,player.center_x-WIDTH*.39))
    game.camera.offset_x=0
    # Settle the real vertical follow before a still or the start of a clip.
    game.camera.vertical_offset=min(0,player.rect.centery-400)+max(0,player.rect.centery-540)
    game.camera.offset_y=round(-game.camera.vertical_offset)


def scene(screen,directory,page,checkpoint,tool,name):
    game=Game(screen,directory/f"{name}.json")
    game.save.data["settings"]["language"]="en"
    set_language("en")
    game.state="playing"
    game.level.load_chapter(page,checkpoint,game.player,game.camera)
    game._attach_runtime()
    game.save.checkpoint(page,checkpoint)
    game.player.release_all_locks()
    game.player.draw_amount=1
    game.player.page_style=("ronin","cowboy","astronaut","ink_agent","bad_drawing")[page]
    game.weapons.lend_drawn_tool(tool)
    game._visual_weapon_id=tool
    game.level.page_title_time=game.level.toast_time=0
    game.weapon_reveal_time=game.achievement_time=0
    game.time=8
    game.last_input_device="keyboard"
    return game


def tick(game,frame=None):
    game.update(1/60,frame or InputFrame())
    if game.player.health<=0 or game.level.respawn_timer>0:
        raise RuntimeError(f"Capture interrupted by a real defeat at {game.player.x:.1f}")


def settle(game,frames=20):
    for _ in range(frames):tick(game)


def walk(game,target,limit=260):
    for _ in range(limit):
        distance=target-game.player.center_x
        if abs(distance)<=9 and abs(game.player.vx)<12:return
        tick(game,InputFrame(left=distance < -9,right=distance > 9))
    raise RuntimeError(f"Could not walk to live target {target}")


def arena_scene(screen,directory,page,room,tool,name):
    game=scene(screen,directory,page,"before_"+room,tool,name)
    arena=next(e for e in game.level.entities.items
               if isinstance(e,CombatArena) and e.arena_id==room)
    # The last room is wider than a viewport. Begin at its authored central
    # floor so the real hero and rejected draft share the eventual camera.
    place(game,arena.start_x+(950 if page==4 else 145))
    for _ in range(700):
        tick(game)
        if arena.encounter_active:
            if arena.boss and game.boss_cinematic.active:break
            if not arena.boss and all(getattr(e,"notebook_reveal",1)>=1
                                      and getattr(e,"artist_still",0)<=0 for e in arena.enemies):break
    else:raise RuntimeError(f"Authored arena did not activate: {room}")
    if arena.boss:
        for _ in range(205):tick(game)
    return game,arena


def pocket_scene(screen,directory,page,kind,tool,name):
    checkpoint="after_practice_crossouts" if page==0 else (
        "after_safe_pocket_counterattack" if page==2 else "before_scissor_office")
    game=scene(screen,directory,page,checkpoint,tool,name)
    pocket=next(e for e in game.level.entities.items
                if isinstance(e,(SecretPocket,OptionalGuardianPocket)) and e.kind==kind)
    place(game,pocket.base+48)
    settle(game,180)
    walk(game,pocket.base+60)
    tick(game,InputFrame(interact=True))
    for _ in range(120):
        tick(game)
        if pocket.entrance_progress>=1:break
    if pocket.entrance_progress<1:raise RuntimeError("E did not reveal the real pocket steps")
    for index,landing in enumerate(pocket.steps):
        target=(landing.x1+landing.x2)/2 if index<4 else pocket.bounds[0]+60
        tick(game,InputFrame(jump_pressed=True,jump_held=True,
                            left=target<game.player.center_x,right=target>game.player.center_x))
        for _ in range(230):
            distance=target-game.player.center_x
            tick(game,InputFrame(left=distance < -9,right=distance > 9,jump_held=True))
            if game.player.on_ground and abs(game.player.rect.bottom-landing.y)<=2:break
        else:raise RuntimeError(f"Could not climb the live {kind} route: {landing.name}")
    walk(game,pocket.bounds[0]+60)
    settle(game,24)
    if pocket.encounter_active:raise RuntimeError("Optional boss started before its E interaction")
    return game,pocket


def combat_input(index,game,room):
    live=[e for e in room.enemies if not e.dead]
    enemy=min(live,key=lambda e:abs(e.rect.centerx-game.player.center_x),default=None)
    if enemy is None:return InputFrame()
    distance=enemy.rect.centerx-game.player.center_x
    melee=game.weapons.current_id in ("pencil_blade","margin_maul")
    # Deliberate button presses, real aim and defensive hops. No health,
    # invulnerability, enemy health or warning state is modified for footage.
    approach=melee and abs(distance)>105 and not game.boss_cinematic.active
    warning="warn" in getattr(enemy,"state","") or "telegraph" in getattr(enemy,"state","")
    jump=warning and index%70==20
    return InputFrame(right=approach and distance>0,left=approach and distance<0,
                      jump_pressed=jump,jump_held=jump or index%70 in range(21,28),
                      jump_released=index%70==29,
                      attack_pressed=index%25==0,attack_held=not melee,
                      aim_x=enemy.rect.centerx,aim_y=enemy.rect.centery-10)


def record(game,count,driver,size=GIF_SIZE):
    frames=[];metadata=[]
    for index in range(count):
        tick(game,driver(index,game))
        if index%(60//FPS)==0:
            game.draw()
            frames.append(pil(game.screen).resize(size,Image.Resampling.LANCZOS))
            afterword=game.afterword if game.state=="ending" and game.ending_time>3.3 else None
            actor=afterword.player if afterword else game.player
            camera=afterword.camera if afterword else game.camera
            event={"tick":index,"player":[round(actor.x,2),round(actor.y,2)],
                "health":actor.health,"boss_zoom":round(camera.zoom,3),
                "weapon":actor.current_weapon if afterword else game.weapons.current_id,
                "attack_visible":bool(game.weapons.melee and game.weapons.melee.active) or bool(game.weapons.projectiles),
                "enemies":[{"kind":e.kind,"state":getattr(e,"state",""),"hp":round(e.hp,2),
                            "screen_x":game.camera.screen_x(e.rect.centerx)}
                    for owner in game.level.entities.items if getattr(owner,"encounter_active",False)
                    for e in getattr(owner,"enemies",()) if not e.dead]}
            if afterword:
                event["memories"]=[{"key":m.key,"progress":round(m.progress,3),"completed":m.completed}
                                   for m in afterword.memories]
                event["signature_progress"]=round(afterword.seal_progress,3)
            metadata.append(event)
    return frames,metadata


def snapshot(game,path):
    game.draw();pil(game.screen).save(path,optimize=True)
    return {"path":path.name,"dimensions":[WIDTH,HEIGHT],"bytes":path.stat().st_size,
            "chapter":game.level.chapter_index,"weapon":game.weapons.current_id,
            "state":game.state,"health":game.player.health}


def encode_gif(frames,path):
    sample=Image.new("RGB",(200*6,125*4))
    for i in range(24):
        frame=frames[round(i*(len(frames)-1)/23)]
        sample.paste(frame.resize((200,125),Image.Resampling.BILINEAR),((i%6)*200,(i//6)*125))
    duration=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(len(frames))]
    for width,colors in ((800,128),(768,128),(720,128),(720,96),(640,96)):
        palette=sample.quantize(colors=colors,method=Image.Quantize.MEDIANCUT)
        indexed=[frame.resize((width,round(width*HEIGHT/WIDTH)),Image.Resampling.LANCZOS)
                 .quantize(palette=palette,dither=Image.Dither.NONE) for frame in frames]
        buffer=io.BytesIO()
        indexed[0].save(buffer,format="GIF",save_all=True,append_images=indexed[1:],
                        duration=duration,loop=0,disposal=2,optimize=True)
        data=buffer.getvalue()
        if len(data)<=6_000_000:break
    if len(data)>6_000_000:raise RuntimeError("GIF exceeds the store's 6 MB target")
    path.write_bytes(data)
    with Image.open(path) as check:
        milliseconds=0
        for i in range(check.n_frames):
            check.seek(i);milliseconds+=check.info.get("duration",0)
        return {"path":path.name,"bytes":len(data),"dimensions":list(check.size),
                "encoded_frames":check.n_frames,"capture_fps":FPS,"duration_seconds":milliseconds/1000,
                "colors":colors,"loop":0}


def contact_sheet(frames,labels,path,columns=4,tile=(420,263)):
    rows=(len(frames)+columns-1)//columns
    canvas=Image.new("RGB",(tile[0]*columns,(tile[1]+25)*rows),(232,222,196))
    draw=ImageDraw.Draw(canvas)
    for i,(frame,label) in enumerate(zip(frames,labels)):
        x=(i%columns)*tile[0];y=(i//columns)*(tile[1]+25)
        draw.text((x+9,y+6),label,fill=(43,42,39))
        canvas.paste(frame.resize(tile,Image.Resampling.LANCZOS),(x,y+25))
    canvas.save(path)


def font(size,condensed=True):
    choices=(Path("/System/Library/Fonts/Avenir Next Condensed.ttc") if condensed else
             Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
             Path("/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"))
    return next((ImageFont.truetype(str(p),size) for p in choices if p.exists()),ImageFont.load_default())


def brand_art(size,paper):
    """Store key art: existing authored hero/Artist on the real paper material."""
    width,height=size
    poster=Image.new("RGBA",size,(42,41,44,255))
    inset=14
    page=paper.resize((width-inset*2,height-inset*2),Image.Resampling.LANCZOS).convert("RGBA")
    poster.alpha_composite(page,(inset,inset))
    draw=ImageDraw.Draw(poster)
    for y in range(round(height*.38),height-25,round(height*.105)):
        draw.line((inset,y,width-inset,y),fill=(183,206,207,255),width=1)
    draw.line((48,14,48,height-14),fill=(195,124,112,255),width=2)
    hero=hero_sprite()
    ratio=min(width*.42/hero.width,height*.56/hero.height)
    hero=hero.resize((round(hero.width*ratio),round(hero.height*ratio)),Image.Resampling.LANCZOS)
    poster.alpha_composite(hero,(round(width*.54),round(height*.385)))
    hand=artist_sprite()
    ratio=min(width*.31/hand.width,height*.36/hand.height)
    hand=hand.resize((round(hand.width*ratio),round(hand.height*ratio)),Image.Resampling.LANCZOS)
    poster.alpha_composite(hand,(width-hand.width+11,-12))
    title=font(round(height*.124),False)
    big=font(round(height*.216),False)
    tx=round(width*.095);ty=round(height*.083)
    draw.text((tx,ty),"TURN THE",font=title,fill=(42,41,44,255))
    draw.text((tx-4,ty+round(height*.108)),"PAGE",font=big,fill=(42,41,44,255))
    line_y=ty+round(height*.352)
    draw.line((tx,line_y,tx+round(width*.36),line_y-5),fill=(148,61,56,255),width=5)
    small=font(round(height*.052))
    draw.text((tx,round(height*.805)),"A notebook that fights back.",font=small,fill=(91,70,58,255))
    # A lifted corner closes the composition without inventing game content.
    draw.polygon([(width-67,height-14),(width-14,height-70),(width-14,height-14)],fill=(226,214,186,255))
    draw.line([(width-67,height-14),(width-14,height-70)],fill=(134,116,99,255),width=2)
    return poster.convert("RGB")


def main(out):
    random.seed(420)
    out.mkdir(parents=True,exist_ok=True)
    review=out/"review";review.mkdir(exist_ok=True)
    pygame.mixer.pre_init(22050,-16,2,512)
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    manifest={"version":VERSION,"language":"en","screenshot_source":"shipping Game.draw",
              "save_policy":"all saves isolated in an automatically removed temporary directory",
              "screenshots":[],"gifs":[],"cover_source":"existing code-authored hero and Artist; runtime notebook paper"}
    screenshots=[];gif_samples=[];gif_labels=[]
    with tempfile.TemporaryDirectory(prefix="turn-store-042-") as folder:
        temp=Path(folder)
        specs=((0,"practice_crossouts","pencil_blade","01-ronin-ink-katana"),
               (1,"coffee_crossfire","marker_shotgun","02-western-double-barrel"),
               (3,"carbon_crossfire","fold_crossbow","04-agent-fold-crossbow"),
               (4,"final_margin_revision","margin_maul","05-final-draft"))
        combat_clips=[]
        for page,room,tool,name in specs:
            print(f"capturing {name}",flush=True)
            game,arena=arena_scene(screen,temp,page,room,tool,name)
            frames,events=record(game,180,lambda index,g:combat_input(index,g,arena),size=(WIDTH,HEIGHT))
            # Prefer an actual attack frame with the crowd drawn and on screen.
            candidates=[i for i,event in enumerate(events) if i>=8 and event["health"]>0]
            def composition_score(index):
                event=events[index]
                visible=[e for e in event["enemies"] if 100<e["screen_x"]<WIDTH-100]
                action=event["attack_visible"]
                return (bool(visible),action,len(visible),-abs(index-len(events)*.6))
            selected=max(candidates,key=composition_score)
            path=out/(name+".png")
            frames[selected].save(path,optimize=True)
            meta={"path":path.name,"dimensions":[WIDTH,HEIGHT],"bytes":path.stat().st_size,
                  "chapter":page,"weapon":tool,"room":room,"actions":"real approach, aim, attack and defensive hops",
                  "event":events[selected]}
            manifest["screenshots"].append(meta);screenshots.append(frames[selected])
            if page in (0,1):combat_clips.append((frames,events))
            if page==4:paper=pil(game.renderer.pages[0])
            game.sounds.quiet_ambience(True)

        clips=[frame.resize(GIF_SIZE,Image.Resampling.LANCZOS)
               for clip,_ in combat_clips for frame in clip]
        meta=encode_gif(clips,out/"01-ink-and-outlaw-combat.gif")
        meta.update({"actions":"3s real ronin katana encounter followed by 3s real Western double-barrel encounter",
                     "events":[event for _,events in combat_clips for event in events]})
        manifest["gifs"].append(meta)
        for i in (0,15,30,35,48,61,71):gif_samples.append(clips[i]);gif_labels.append(f"combat / frame {i}")
        del clips,combat_clips;gc.collect()

        print("capturing live optional Orbit Crab E entrance",flush=True)
        game,pocket=pocket_scene(screen,temp,2,"orbit_crab","orbit_saw","orbit-crab")
        frames,events=record(game,360,lambda i,g:InputFrame(interact=i==0) if i<195
                            else combat_input(i-195,g,pocket),size=(WIDTH,HEIGHT))
        if not any(event["boss_zoom"]>1.3 for event in events):raise RuntimeError("Boss zoom was not captured")
        for state,index in (("03-orbit-crab-warning",59),("06-drawn-boss-entrance",24)):
            path=out/(state+".png")
            frames[index].save(path,optimize=True)
            screenshots.append(Image.open(path).copy())
            manifest["screenshots"].append({"path":path.name,"dimensions":[WIDTH,HEIGHT],
                "bytes":path.stat().st_size,"chapter":2,"boss":"orbit_crab","actions":"E opens a fully drawn optional deck; real camera entrance and first warning","event":events[index]})
        meta=encode_gif(frames,out/"02-boss-drawing-and-dodge.gif")
        meta.update({"actions":"E challenge after opening and climbing the real route; protected camera zoom, pencil reveal, first ring warning","events":events})
        manifest["gifs"].append(meta)
        for i in (0,8,18,27,39,55,71):gif_samples.append(frames[i]);gif_labels.append(f"boss draw / frame {i}")
        game.sounds.quiet_ambience(True)
        del frames;gc.collect()

        print("capturing the playable last page",flush=True)
        game=scene(screen,temp,4,"after_final_margin_revision","margin_maul","afterword")
        game.save.data["secrets"]=["shrine_roof","water_tower","agent_badge","cloud_heart"]
        game._start_ending()
        for _ in range(204):tick(game)
        last=game.afterword.memories[2]
        game.afterword.player.x=last.x-game.afterword.player.WIDTH/2
        game.afterword.camera.x=last.x-WIDTH/2
        game.afterword.camera.target_x=game.afterword.camera.x
        frames,events=record(game,360,lambda i,g:InputFrame(interact=i==0,right=245<=i<325),size=(WIDTH,HEIGHT))
        path=out/"07-your-last-page.png"
        frames[49].save(path,optimize=True)
        screenshots.append(Image.open(path).copy())
        manifest["screenshots"].append({"path":path.name,"dimensions":[WIDTH,HEIGHT],"bytes":path.stat().st_size,
            "chapter":4,"state":"ending","actions":"player presses E to draw a personal figure with actually collected rune motifs"})
        meta=encode_gif(frames,out/"03-draw-your-last-page.gif")
        meta.update({"actions":"manual E begins a 3.6s authored drawing; movement resumes after the stroke; collection motifs come from temporary saved progress","events":events})
        manifest["gifs"].append(meta)
        for i in (0,8,18,27,39,55,71):gif_samples.append(frames[i]);gif_labels.append(f"last page / frame {i}")
        game.save.data["secrets"]=[sketch.secret_id for sketch in SKETCHES]
        game.state="back_pages";game.sketch_page=1
        path=out/"08-techniques-worth-keeping.png"
        manifest["screenshots"].append(snapshot(game,path))
        screenshots.append(Image.open(path).copy())

    # Cover/banner use promotional key art; gallery pictures remain untouched
    # runtime output and carry no added marketing/debug captions.
    brand_art((630,500),paper).save(out/"cover-630x500.png",optimize=True)
    brand_art((960,360),paper).save(out/"banner-960x360.png",optimize=True)
    manifest["cover"]={"path":"cover-630x500.png","dimensions":[630,500],
        "bytes":(out/"cover-630x500.png").stat().st_size}
    manifest["banner"]={"path":"banner-960x360.png","dimensions":[960,360],
        "bytes":(out/"banner-960x360.png").stat().st_size}
    order=sorted(zip(manifest["screenshots"],screenshots),key=lambda pair:pair[0]["path"])
    manifest["screenshots"]=[meta for meta,_ in order]
    contact_sheet([im for _,im in order],[meta["path"] for meta,_ in order],review/"screenshots-sheet.png")
    contact_sheet(gif_samples,gif_labels,review/"gif-frames-sheet.png",columns=7,tile=(320,200))
    (out/"asset-manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    pygame.quit()
    print(json.dumps({"output":str(out),"screenshots":len(manifest["screenshots"]),
                      "gifs":[{k:gif[k] for k in ("path","bytes","duration_seconds","dimensions")} for gif in manifest["gifs"]]},ensure_ascii=False),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=DEFAULT_OUTPUT)
    args=parser.parse_args()
    main(args.output.resolve())
