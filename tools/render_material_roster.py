"""Render a large review sheet from the actual runtime enemy draw methods."""
from __future__ import annotations

import math
import os
from pathlib import Path
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame

from advanced_enemies import (BabyFaceGiant, CactusGunner, CometHound,
                              CrumpledOne, DoodleTurret, EraserBrute,
                              FinalEditorBoss, GoblinScribble, InkClone, InkOutlaw, InkSamurai,
                              LanternYokai, MoonBot, MoonCompassBoss,
                              OrbitalMistakeBoss, OrigamiDrone, PaperWasp,
                              RailroadStaplerBoss, RulerGuard, StarScout,
                              TumbleweedThing, WantedSketchBoss)
from camera import Camera
from paper_renderer import PaperRenderer


INK = (42, 41, 39)
MUTED = (164, 157, 143)
BACK = (35, 34, 32)


def render(path: Path) -> Path:
    pygame.init()
    renderer = PaperRenderer()
    canvas = pygame.Surface((1440, 2050))
    canvas.fill(BACK)
    title_font = pygame.font.Font(None, 48)
    label_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 21)
    canvas.blit(title_font.render("TURN THE PAGE — ACTUAL RUNTIME MARKS", True,
                                  (237, 232, 214)), (40, 28))
    canvas.blit(small_font.render(
        "No generated character raster. Every tile calls the in-game draw method.",
        True, MUTED), (42, 77))

    entries = (
        ("INK SAMURAI", "wide sleeves + hakama + sheathed katana", 0,
         InkSamurai(220, 245, 11)),
        ("ORIGAMI DRONE", "folded aircraft + scan eye + overheat droop", 0,
         OrigamiDrone(220, 245, 12)),
        ("GOBLIN SCRIBBLE", "ears + grin + stolen club / deliberate mismatch", 0,
         GoblinScribble(220, 245, 13)),
        ("LANTERN YOKAI", "paper lamp + flame fan / descends after firing", 0,
         LanternYokai(220, 245, 20)),
        ("RULER GUARD", "ruler shield + pencil spear / back opening", 0,
         RulerGuard(220, 245, 21)),
        ("INK OUTLAW", "cowboy hat + poncho + quickdraw silhouette", 1,
         InkOutlaw(220, 245, 14)),
        ("TUMBLEWEED THING", "rotating dry loops + tiny hidden face", 1,
         TumbleweedThing(220, 245, 15)),
        ("PAPER WASP", "torn folds + staples / wrong western visitor", 1,
         PaperWasp(220, 245, 16)),
        ("CACTUS GUNNER", "rooted arms + hat / three-needle space control", 1,
         CactusGunner(220, 245, 22)),
        ("CRUMPLED ONE", "compressed paper loops / wall-stun charge", 1,
         CrumpledOne(220, 245, 23)),
        ("STAR SCOUT", "saucer body + orbital rings + lock eye", 2,
         StarScout(220, 245, 17)),
        ("MOON BOT", "helmet dome + box chassis + ram arm", 2,
         MoonBot(220, 245, 18)),
        ("COMET HOUND", "four legs + long star tail / lane rush", 2,
         CometHound(220, 245, 24)),
        ("INK CLONE", "mirrored stick anatomy / copies then cheats", 2,
         InkClone(220, 245, 25)),
        ("DOODLE TURRET", "folded note + ink core + ruler nib", 2,
         DoodleTurret(220, 245, 26)),
        ("ERASER BRUTE", "worn rubber block / temporarily cuts the floor", 2,
         EraserBrute(220, 245, 27)),
        ("BABY-FACE ACCIDENT", "three-attempt gag / not one of the five bosses", 2,
         BabyFaceGiant(220, 285, 28)),
    )

    tile_w, tile_h = 440, 255
    for index, (name, description, page, actor) in enumerate(entries):
        col, row = index % 3, index // 3
        tile = pygame.Surface((tile_w, tile_h))
        renderer.background(tile, page)
        camera = Camera(tile_w)
        actor.state = "idle"
        if isinstance(actor, (LanternYokai, OrigamiDrone, PaperWasp, StarScout)):
            actor.y = 180
            if hasattr(actor, "hover_y"):
                actor.hover_y = 180
        if isinstance(actor, BabyFaceGiant):
            actor.empowered = True
            actor.moustache_progress = 1
        actor.draw(tile, camera, renderer)
        x = 40 + col * 470
        y = 116 + row * 320
        canvas.blit(tile, (x, y))
        pygame.draw.rect(canvas, (91, 86, 78), (x, y, tile_w, tile_h), 1)
        canvas.blit(label_font.render(name, True, (238, 232, 211)),
                    (x + 4, y + tile_h + 5))
        canvas.blit(small_font.render(description, True, MUTED),
                    (x + 4, y + tile_h + 31))

    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, path)
    pygame.quit()
    return path


def render_bosses(path: Path) -> Path:
    pygame.init()
    renderer = PaperRenderer()
    canvas = pygame.Surface((1440, 790))
    canvas.fill(BACK)
    title_font = pygame.font.Font(None, 48)
    label_font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 21)
    canvas.blit(title_font.render("TURN THE PAGE — FIVE BOSSES / FIVE RULES", True,
                                  (237, 232, 214)), (40, 28))
    canvas.blit(small_font.render(
        "Themed wrappers keep tested counter-play while changing silhouette and page context.",
        True, MUTED), (42, 77))

    bosses = [
        ("THE MOON COMPASS", "dodge the arc / hit the stuck needle", 0,
         MoonCompassBoss(220, 260, 31), "stuck"),
        ("WANTED SKETCH", "read charge/rain/slam / punish loose lines", 1,
         WantedSketchBoss(220, 260, 32), "unravel"),
        ("RAILROAD STAPLER", "escape the snap / attack during reload", 1,
         RailroadStaplerBoss(220, 260, 33), "reload"),
        ("ORBITAL MISTAKE", "survive phase chains / erase the unravel", 2,
         OrbitalMistakeBoss(220, 260, 34), "unravel"),
        ("THE FINAL EDITOR", "four scenarios / punish the open binder", 2,
         FinalEditorBoss(220, 285, 35), "proof_window"),
    ]
    tile_w, tile_h = 440, 255
    for index, (name, description, page, actor, state) in enumerate(bosses):
        col, row = index % 3, index // 3
        tile = pygame.Surface((tile_w, tile_h))
        renderer.background(tile, page)
        camera = Camera(tile_w)
        actor.state = state
        actor.state_time = .45
        if isinstance(actor, MoonCompassBoss):
            actor.angle = math.pi / 2
        if isinstance(actor, OrbitalMistakeBoss):
            actor.phase = 3
        if isinstance(actor, FinalEditorBoss):
            actor.scenario = "aggressive"
        actor.draw(tile, camera, renderer)
        x = 40 + col * 470
        y = 116 + row * 320
        canvas.blit(tile, (x, y))
        pygame.draw.rect(canvas, (91, 86, 78), (x, y, tile_w, tile_h), 1)
        canvas.blit(label_font.render(name, True, (238, 232, 211)),
                    (x + 4, y + tile_h + 5))
        canvas.blit(small_font.render(description, True, MUTED),
                    (x + 4, y + tile_h + 31))
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, path)
    pygame.quit()
    return path


if __name__ == "__main__":
    print(render(ROOT / "work" / "visual_qa" /
                 "turn_the_page_material_roster.png"))
    print(render_bosses(ROOT / "work" / "visual_qa" /
                        "turn_the_page_five_bosses.png"))
