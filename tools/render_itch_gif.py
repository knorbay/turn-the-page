"""Record a compact 0.20 itch GIF from the shipping game renderer.

The clips are controlled in-game situations, not painted mockups: each frame
is produced by Game.update()/Game.draw(), including collision, camera motion,
the Artist, weapon effects, and the live paper scenery.  Independent scenes
are edited together so the short loop can show all five pages.
"""

from __future__ import annotations

import argparse
import io
import os
from pathlib import Path
import sys
import tempfile

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PIL import Image
import pygame

from combat import CombatArena
from game import Game
from input_state import InputFrame
from route_puzzles import DraftBridgePuzzle, PerforatedPosterPuzzle, SatelliteRelayPuzzle
from settings import HEIGHT, WIDTH


DEFAULT_OUTPUT = ROOT / "store" / "Turn-the-Page-0.20-Gameplay.gif"
FPS = 10


def _scene(screen, savedir: Path, chapter: int, name: str,
           checkpoint: str) -> Game:
    game = Game(screen, savedir / f"{name}.json")
    game.state = "playing"
    game.level.load_chapter(chapter, checkpoint, game.player, game.camera)
    game._apply_page_identity()
    game.player.release_all_locks()
    game.player.draw_amount = 1
    game.player.page_style = ("ronin", "cowboy", "astronaut", "ink_agent", "bad_drawing")[chapter]
    game.player.on_ground = True
    game.level.page_title_time = 0
    game.level.toast_time = 0
    game.achievement_time = 0
    game.weapon_reveal_time = 0
    game.time = 8
    return game


def _place(game: Game, x: float, bottom: float) -> None:
    player = game.player
    player.x, player.y = x, bottom - player.HEIGHT
    player.vx = player.vy = 0
    player.on_ground = player.was_grounded = True
    player.facing = 1
    game.camera.x = game.camera.target_x = max(0, player.center_x - WIDTH * .38)
    game.camera.offset_x = game.camera.offset_y = 0


def _capture(game: Game, count: int, input_for_frame, size=(640, 400)) -> list[Image.Image]:
    frames = []
    for index in range(count):
        game.update(1 / 60, input_for_frame(index, game))
        if index % (60 // FPS) == 0:
            game.draw()
            frame = Image.frombytes("RGB", game.screen.get_size(),
                                    pygame.image.tobytes(game.screen, "RGB"))
            frames.append(frame.resize(size, Image.Resampling.LANCZOS))
    return frames


def _bridge(screen, savedir, size):
    game = _scene(screen, savedir, 0, "bridge", "bridge")
    puzzle = next(entity for entity in game.level.entities.items
                  if isinstance(entity, DraftBridgePuzzle))
    _place(game, puzzle.marks[0][0] - game.player.WIDTH / 2, 590)
    game.camera.x = game.camera.target_x = 2790

    def drive(tick, _game):
        # A real E press draws a physical ledge; run toward it while the pencil
        # finishes the stroke, then jump onto the new line.
        return InputFrame(interact=tick == 0,
                          right=12 <= tick < 110,
                          jump_pressed=tick == 42,
                          jump_held=42 <= tick < 51,
                          attack_pressed=tick in (74, 92))

    return _capture(game, 104, drive, size)


def _poster(screen, savedir, size):
    game = _scene(screen, savedir, 1, "poster", "after_marker_margin_trial")
    puzzle = next(entity for entity in game.level.entities.items
                  if isinstance(entity, PerforatedPosterPuzzle))
    _place(game, puzzle.gate.x1 - 127, puzzle.ledge.y)
    game.camera.x = game.camera.target_x = puzzle.gate.x1 - 690

    def drive(tick, _game):
        return InputFrame(right=tick < 60,
                          dash_pressed=tick == 21)

    frames = _capture(game, 66, drive, size)
    if not puzzle.completed:
        raise RuntimeError("Poster clip did not tear the live puzzle gate")
    return frames


def _relay(screen, savedir, size):
    game = _scene(screen, savedir, 2, "relay", "after_orbital_debris")
    puzzle = next(entity for entity in game.level.entities.items
                  if isinstance(entity, SatelliteRelayPuzzle))
    _place(game, puzzle.source[0] - game.player.WIDTH / 2, puzzle.source[1])
    game.camera.x = game.camera.target_x = puzzle.start_x - 360

    def charge(tick, _game):
        return InputFrame(interact=tick == 0, right=tick > 16)

    frames = _capture(game, 42, charge, size)
    if puzzle.phase != "carrying":
        raise RuntimeError("Star did not charge at the source pad")

    # The loop cuts to the upper step, as a short trailer would.  Its charged
    # state comes from the actual source interaction above; the second press
    # connects the star while the player is standing on the real receiver.
    _place(game, puzzle.receiver[0] - 116, puzzle.receiver[1])
    game.camera.x = game.camera.target_x = puzzle.start_x + 150

    def connect(tick, _game):
        return InputFrame(right=tick < 35,
                          interact=tick >= 35 and tick < 43)

    frames += _capture(game, 66, connect, size)
    if not puzzle.completed:
        raise RuntimeError("Star clip did not open the live airlock")
    return frames


def _dossier(screen, savedir, size):
    game = _scene(screen, savedir, 3, "dossier", "after_agent_checkpoint")
    _place(game, 2250, 590)
    game.camera.x = game.camera.target_x = 1980
    game.weapons.active_loadout = None
    game.weapons.unlock("field_knife")
    game.weapons.select("field_knife")

    def drive(tick, _game):
        return InputFrame(right=tick < 68,
                          attack_pressed=tick in (17, 35, 55),
                          aim_x=game.player.center_x + 135,
                          aim_y=game.player.rect.centery)

    return _capture(game, 78, drive, size)


def _editor(screen, savedir, size):
    game = _scene(screen, savedir, 4, "editor", "before_final_margin_revision")
    arena = next(entity for entity in game.level.entities.items
                 if isinstance(entity, CombatArena)
                 and entity.arena_id == "final_margin_revision")
    ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
    arena.encounter_active = True
    arena.wave = max(spec["wave"] for spec in arena.enemy_specs)
    arena._spawn_wave(ctx, arena.wave)
    arena.entrance_gate.enabled = True
    boss = next(enemy for enemy in arena.enemies if getattr(enemy, "is_boss", False))
    _place(game, boss.x - 235, 590)
    game.camera.x = game.camera.target_x = boss.x - 635
    game.player.invulnerable = 99
    game.weapons.active_loadout = None
    game.weapons.unlock("eraser_cannon")
    game.weapons.select("eraser_cannon")
    # Start at an authored attack warning rather than spending the storefront
    # clip on the encounter's arrival. The full attack cycle still updates
    # through the game's normal arena and weapon simulation.
    boss.scenario = "precise"
    game.behavior.data["final_scenario"] = "precise"
    boss.notebook_reveal = 1
    boss.artist_still = 0
    boss._start_pattern(ctx)
    arena.boss_intro_time = 0
    game.level.toast = "THE REJECTED HERO / READ THE DRAFT"
    game.level.toast_time = 2.1

    def drive(tick, _game):
        # This is the normal attack input/weapon simulation, with invulnerability
        # only to keep a short storefront capture from being interrupted by death.
        return InputFrame(right=tick < 18,
                          left=40 <= tick < 55,
                          attack_pressed=tick in (7, 86, 142),
                          aim_x=boss.rect.centerx,
                          aim_y=boss.rect.centery - 20)

    return _capture(game, 156, drive, size)


def _palette(frames: list[Image.Image], colors: int) -> Image.Image:
    # One shared palette prevents the notebook paper from changing hue at an
    # edit cut.  Sample every clip, not just the first ronin frame.
    sample = Image.new("RGB", (160 * 8, 100 * 5))
    picks = [frames[round(i * (len(frames) - 1) / 39)] for i in range(40)]
    for index, frame in enumerate(picks):
        sample.paste(frame.resize((160, 100), Image.Resampling.BILINEAR),
                     ((index % 8) * 160, (index // 8) * 100))
    return sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)


def _encode(frames: list[Image.Image], *, width: int, colors: int,
            stride: int) -> bytes:
    selected = frames[::stride]
    height = round(width * HEIGHT / WIDTH)
    palette = _palette(selected, colors)
    quantized = [frame.resize((width, height), Image.Resampling.LANCZOS)
                 .quantize(palette=palette, dither=Image.Dither.NONE)
                 for frame in selected]
    buffer = io.BytesIO()
    quantized[0].save(buffer, format="GIF", save_all=True,
                      append_images=quantized[1:], optimize=True,
                      duration=100 * stride, loop=0, disposal=2)
    return buffer.getvalue()


def main(output: Path) -> None:
    pygame.mixer.pre_init(22050, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    try:
        with tempfile.TemporaryDirectory(prefix="turn-020-gif-") as temp:
            directory = Path(temp)
            size = (640, 400)
            clips = [
                _bridge(screen, directory, size),
                _poster(screen, directory, size),
                _relay(screen, directory, size),
                _dossier(screen, directory, size),
                _editor(screen, directory, size),
            ]
        frames = [frame for clip in clips for frame in clip]
        candidates = ((640, 128, 1), (620, 128, 1), (600, 128, 1),
                      (580, 128, 1), (560, 128, 1), (560, 96, 1), (520, 96, 1),
                      (500, 80, 1), (480, 80, 1), (448, 64, 1),
                      (448, 64, 2))
        best = None
        for width, colors, stride in candidates:
            data = _encode(frames, width=width, colors=colors, stride=stride)
            best = (data, width, colors, stride)
            if len(data) <= 3_000_000:
                break
        data, width, colors, stride = best
        if len(data) > 3_000_000:
            raise RuntimeError(f"GIF remains above 3 MB: {len(data):,} bytes")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(data)
        with Image.open(output) as check:
            print(f"{output}: {len(data):,} bytes, {check.n_frames} frames, "
                  f"{check.size[0]}x{check.size[1]}, {colors} colors, "
                  f"{len(frames) / FPS:.1f}s of gameplay")
    finally:
        pygame.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    main(args.output)
