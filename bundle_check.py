"""Opt-in packaged-runtime verification; normal launches never enter here."""
import hashlib
import json
import math
from array import array
import sys
import tempfile
from pathlib import Path
import pygame
from game import Game
from input_state import InputFrame
from runtime_paths import default_save_path
from settings import WIDTH, HEIGHT, VERSION


def verify(output):
    pygame.mixer.pre_init(22050,-16,2,512)
    pygame.init()
    screen=pygame.display.set_mode((WIDTH,HEIGHT))
    pages=[]
    air_exits=[]
    with tempfile.TemporaryDirectory(prefix="ttp-check-") as directory:
        game=Game(screen,Path(directory)/"save.json")
        for page in range(5):
            game.level.load_chapter(page,"start",game.player,game.camera)
            game._apply_page_identity()
            game.sounds.start_ambience(page)
            game.state="playing"
            for _ in range(10):
                game.update(1/60,InputFrame())
                game.draw()
                game._present()
                pygame.display.flip()
            game.draw()
            assert game.player.max_health==3
            assert game.screen.get_at((WIDTH-20,100)).r > 100, "Paper canvas was covered"
            pages.append(game.level.title)
        # Exercise the reported final-jump bug in the frozen executable as
        # well as in source tests, using genuine final checkpoint snapshots.
        last_checkpoints=("after_moon_gate_duel", "after_midnight_train",
                          "after_baby_face_interlude", "after_scissor_office",
                          "after_final_margin_revision")
        for page, checkpoint in enumerate(last_checkpoints):
            game.reset()
            game.level.load_chapter(page,checkpoint,game.player,game.camera)
            game._attach_runtime()
            jumped=False
            for _ in range(360):
                jump=not jumped and game.player.on_ground and game.player.x>=game.level.runtime.end_x-55
                jumped=jumped or jump
                game.update(1/60,InputFrame(right=True,jump_pressed=jump,jump_held=True))
                if game.transition_active or game.state=="ending":
                    break
            assert jumped and game.level.chapter_complete, f"Air exit failed on page {page+1}"
            assert game.behavior.count("deaths")==0, f"Air exit caused a fall on page {page+1}"
            assert not game.player.on_ground, "Exit regression did not cross the edge in the air"
            if page<4:
                for _ in range(180):
                    game.update(1/60,InputFrame())
                assert game.level.chapter_index==page+1 and not game.transition_active
                assert "page_transition" not in game.player.control_locks
            else:
                assert game.state=="ending" and game.save.data["completed"]
            air_exits.append(page+1)
        from sketches import SKETCHES
        from chapters import build_chapter
        from localization import translate, set_language, SUPPORTED_LANGUAGES
        from tutorial import TrainingLesson
        assert TrainingLesson.MIN_SECONDS >= 60
        from tools.training_pilot import lesson_input
        original_save = dict(game.save.data)
        game.start_training()
        lesson = game.level.runtime.training
        for lesson_tick in range(12000):
            game.update(1/60, lesson_input(game))
            if game.state == "title":
                break
        assert lesson.completed and game.state == "title", "Packaged tutorial stalled"
        assert lesson.elapsed >= 75 and lesson.dodges >= 3
        assert all(target.completed for target in lesson.targets)
        assert lesson.bridge_requested and lesson.read_seal
        assert game.save.data["chapter"] == original_save["chapter"]
        actual_training_seconds = round(lesson_tick/60, 2)
        assert len(SKETCHES) == 19
        pockets = [e.kind for page in range(5) for e in build_chapter(page).entities.items
                   if getattr(e, "is_secret_pocket", False)]
        assert sorted(pockets) == ["carbon", "cloud", "fold"]
        from route_expeditions import RouteExpedition
        heart_routes = [sum(isinstance(e, RouteExpedition) for e in build_chapter(page).entities.items)
                        for page in range(5)]
        assert heart_routes == [1, 1, 1, 1, 1], "Repeated recovery routes returned in the bundle"
        # Automatic gifts are completed physical drawings. A gift must leave
        # the current weapon and magazine intact, including after a reload.
        from notebook_agency import NotebookAgency
        from page_arsenal import PAGE_ENTRY_TOOLS
        automatic_tools = []
        for page in range(5):
            game.reset()
            game.level.load_chapter(page, "start", game.player, game.camera)
            game._attach_runtime()
            game.save.checkpoint(page, "start")
            game.player.release_all_locks()
            agency = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
            agency._restore(ctx)
            held = PAGE_ENTRY_TOOLS[page]
            game.weapons.unlock(held)
            game.weapons.select(held)
            ammo = game.weapons.current.ammo
            agency.first.completed = True
            game.player.x = agency.first.end_x+30
            assert not agency.choose("tool", ctx), "Artist still accepts requests"
            agency.update(.01, ctx)
            assert agency.operation == "support_tool"
            expected = agency.selected_weapon
            for _ in range(75):
                agency.update(1/60, ctx)
                agency.draw(game.screen, game.camera, game.renderer)
            assert expected in game.weapons.available_ids
            assert game.weapons.current_id == held and game.weapons.current.ammo == ammo
            game.continue_game()
            restored = next(e for e in game.level.entities.items if isinstance(e, NotebookAgency))
            restored.update(0, game.level.context(game.player, game.camera, game.particles, game.sounds))
            assert expected in game.weapons.available_ids, "Artist gift lost on reload"
            assert game.weapons.current_id == held and game.weapons.current.ammo == ammo
            automatic_tools.append({"page":page+1,"gift":expected,"held":held})
        from audio import SELECTED_PAGE_TRACKS, RECORDED_SFX
        from scene_music import (BOSS_PROFILES, BOSS_ENTRY_DELAYS, MUSIC_CREDITS,
                                 SELECTED_BOSS_TRACKS, BOSS_ENTRANCE_TRACKS, SCORE_MANIFEST, BOSS_SCORE_MANIFEST)
        from audio_composer import SFX_VARIANT_COUNTS
        manifest = json.loads((game.sounds.asset_root / SCORE_MANIFEST).read_text(encoding='utf8'))
        selected_music = {tracks[label] for tracks in SELECTED_PAGE_TRACKS.values()
                          for label in ('calm', 'action')}
        selected_music.update(SELECTED_BOSS_TRACKS.values())
        selected_music.update(BOSS_ENTRANCE_TRACKS.values())
        original_files = {item['file']: item for item in manifest['files']}
        boss_manifest = json.loads((game.sounds.asset_root / BOSS_SCORE_MANIFEST).read_text(encoding='utf8'))
        boss_files = {item['file']: item for item in boss_manifest['files']}
        assert len(selected_music) == 22
        assert len(BOSS_PROFILES) == len(boss_files) == len(set(SELECTED_BOSS_TRACKS.values())) == 12
        assert manifest['score_id'] == 'original-first-version'
        assert boss_manifest['score_id'] == 'contrasting-boss-phrases-0.41'
        assert not BOSS_ENTRANCE_TRACKS and not BOSS_ENTRY_DELAYS
        assert len(MUSIC_CREDITS) == 18 and len({item['title'] for item in MUSIC_CREDITS}) == 18
        for credit in MUSIC_CREDITS:
            assert credit['composer'] and credit['credit']
            assert credit['license'] in {'CC0 1.0', 'CC BY 4.0'}
            assert credit['source_url'].startswith('https://') and credit['license_url'].startswith('https://creativecommons.org/')
        # The existing exploration tracks and their archived fallback score retain their hashes.
        for relative, item in original_files.items():
            path = game.sounds.asset_root / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            assert digest == item['encoded_sha256']
            assert item['historical_proofs'] and all(
                proof['matches_current'] and proof['encoded_sha256'] == digest
                for proof in item['historical_proofs'])
        for relative, item in boss_files.items():
            assert hashlib.sha256((game.sounds.asset_root/relative).read_bytes()).hexdigest() == item['encoded_sha256']
            assert item['license'] == 'CC BY 4.0' and item['changes'] and item['license_evidence']
        from optional_encounters import OptionalGuardianPocket, OPTIONAL_DUELS
        from margin_guardians import GUARDIAN_CLASSES
        optional_guardians = []
        for spec in OPTIONAL_DUELS:
            runtime = build_chapter(spec.page)
            pocket = next(e for e in runtime.entities.items if isinstance(e, OptionalGuardianPocket))
            assert pocket.kind == spec.kind and not pocket.mandatory
            actor = GUARDIAN_CLASSES[pocket.kind](pocket.bounds[0]+200, pocket.ground)
            assert actor.is_boss and actor.max_hp == 10
            optional_guardians.append({'page':spec.page+1,'kind':pocket.kind,'reward':spec.rune})
        boss_scores = {}
        page_scores = {}
        for page in range(5):
            game.sounds.start_ambience(page)
            game.sounds.set_combat(False)
            game.sounds.update(1)
            calm = game.sounds.score_channel.get_sound()
            assert calm is game.sounds.score_low[page]
            assert game.sounds.score_channel.get_volume() > 0
            assert game.sounds.combat_channel.get_volume() == 0
            assert calm.get_length() > 8
            game.sounds.set_combat(True)
            game.sounds.update(1)
            action = game.sounds.combat_channel.get_sound()
            assert action is game.sounds.score_high[page]
            assert action.get_length() > 8 and action is not calm
            assert game.sounds.combat_channel.get_volume() > 0
            assert game.sounds.score_channel.get_volume() == 0, 'Different page recordings overlapped'
            page_scores[str(page+1)] = {'calm_seconds':round(calm.get_length(),2),
                                       'action_seconds':round(action.get_length(),2)}
        for kind, profile in BOSS_PROFILES.items():
            game.sounds.start_ambience(profile['page'])
            game.sounds.set_combat(False)
            game.sounds.set_combat(True, True, kind)
            assert game.sounds.music_intro_channel.get_sound() is None
            score = game.sounds.boss_channel.get_sound()
            assert score is game.sounds.boss_scores[kind] and 20 <= score.get_length() <= 45
            samples = array('h', score.get_raw())
            boss_rms = math.sqrt(sum(value*value for value in samples)/len(samples))/32768
            boss_peak = max(abs(value) for value in samples)/32768
            assert .045 <= boss_rms <= .115 and boss_peak <= .62, 'Boss playback gain missing in native bundle'
            game.sounds.update(.1)
            for _ in range(10):
                game.sounds.set_combat(True, True, kind)
            assert abs(game.sounds.boss_entry_elapsed-.1) < .00001, 'Repeated combat updates restarted the entrance'
            assert game.sounds.boss_channel.get_sound() is score
            assert game.sounds.action_variant == f'boss:{kind}'
            game.sounds.update(3)
            game.sounds.apply_settings({'master_volume':.8,'sfx_volume':.85,'music_volume':0})
            assert game.sounds.boss_channel.get_volume() == 0
            assert game.sounds.music_intro_channel.get_volume() == 0
            game.sounds.apply_settings({'master_volume':.8,'sfx_volume':.85,'music_volume':.35})
            boss_scores[kind] = {'score_seconds':round(score.get_length(),2),
                                 'entrance_seconds':0,
                                 'recording':SELECTED_BOSS_TRACKS[kind],
                                 'runtime_rms':round(boss_rms,5),
                                 'runtime_peak':round(boss_peak,5)}
        assert pygame.mixer.get_init()[2] == 2
        for cue in ('pistol','revolver','shotgun','reload','enemy_hit_ink'):
            assert len(game.sounds.sound_variants[cue]) == SFX_VARIANT_COUNTS.get(cue,1)
        warning = game.sounds.play('enemy_telegraph_heavy', cooldown_ms=0)
        assert warning is game.sounds.warning_channel
        sample = warning.get_sound()
        for _ in range(20):game.sounds.play('heavy_hit', cooldown_ms=0)
        assert warning.get_sound() is sample, 'Hit burst stole attack warning'
        regular_waves = set()
        normal_wave_sizes = {}
        main_bosses = []
        for page in range(5):
            for room in build_chapter(page).entities.items:
                if not getattr(room, 'is_combat_arena', False):continue
                if room.boss and room.arena_id != 'baby_face_interlude':
                    assert len(room.wave_ids) == 1 and len(room.enemy_specs) == 1
                    assert room.end_x-room.start_x >= 2300
                    main_bosses.append(room.arena_id)
                elif not room.boss and room.arena_id != 'baby_face_interlude':
                    regular_waves.add(len(room.wave_ids))
                    sizes = {wave:sum(int(spec.get('count',1)) for spec in room.enemy_specs
                                     if int(spec.get('wave',0)) == wave)
                             for wave in room.wave_ids}
                    assert set(sizes.values()) <= {2,3,4,5}, room.arena_id
                    normal_wave_sizes[room.arena_id] = sizes
        assert {size for sizes in normal_wave_sizes.values() for size in sizes.values()} == {2,3,4,5}
        assert regular_waves == {1,2,3}
        assert len(normal_wave_sizes) == 18
        game.reset()
        pocket = next(e for e in game.level.entities.items if getattr(e, "is_secret_pocket", False))
        assert not pocket.entrance_open and all(not p.enabled for p in pocket.steps)
        game.player.release_all_locks()
        ctx = game.level.context(game.player, game.camera, game.particles, game.sounds)
        game.player.x, game.player.y = pocket.base+48, 542
        pocket.update(.01, ctx, True)
        for _ in range(50):pocket.update(1/60, ctx)
        assert pocket.entrance_progress == 1 and all(p.enabled for p in pocket.steps)
        game.player.x, game.player.y = pocket.bounds[0]+35, pocket.ground-48
        pocket.update(.01, ctx, True)
        guardian = pocket.enemies[0]
        assert guardian.kind == "cloud_kite" and guardian.max_hp == 8
        pocket.draw(game.screen, game.camera, game.renderer)
        game.state = 'playing'
        assert game.boss_cinematic.maybe_begin(), 'Real boss drawing did not start'
        frozen_positions = (game.player.x, game.player.y, guardian.x, guardian.y)
        for _ in range(120):
            game.update(1/60, InputFrame(right=True, attack_pressed=True))
        assert game.boss_cinematic.active and game.camera.zoom > 1.6
        assert 0 < guardian.notebook_reveal < 1
        assert frozen_positions == (game.player.x, game.player.y, guardian.x, guardian.y)
        for _ in range(73):
            game.update(1/60, InputFrame())
        assert not game.boss_cinematic.active and game.camera.zoom == 1
        assert guardian.notebook_reveal == 1 and 'boss_cinematic' not in game.player.control_locks
        game.camera.script_target = 20000
        for _ in range(90):
            game.camera.update(1/60, game.player.center_x, game.level.world.width,
                               0, game.player.y, player_locked=False)
        assert game.camera.script_target is None
        assert abs(game.camera.screen_x(game.player.center_x)-WIDTH/2) <= 1
        assert game.camera.offset_y > 100
        game.save.discover('cloud_heart')
        game.save.mark_complete(game.session_seconds)
        game._open_replay_pages()
        game.replay_page_index = 5
        game._activate_replay_page()
        word = game.afterword
        before = word.player.x
        for _ in range(60):game.update(1/60, InputFrame(right=True))
        assert word.player.x > before+100 and not word.complete
        for memory in word.memories:
            word.player.x, word.player.y = memory.x-12, word.GROUND_Y-48
            word.player.vx = word.player.vy = 0
            game.update(1/60, InputFrame(interact=True))
            for _ in range(220):game.update(1/60, InputFrame())
            assert memory.completed, 'Packaged afterword drawing stalled'
        word.player.x, word.player.y = word.SEAL_X-12, word.GROUND_Y-48
        word.player.vx = word.player.vy = 0
        game.update(1/60, InputFrame(interact=True))
        for _ in range(195):game.update(1/60, InputFrame())
        assert word.complete and word.completed_memories == 3
        word.menu_index = 0
        game._activate_afterword_action()
        assert game.state == 'replay_pages'
        game.replay_page_index = 3
        game._activate_replay_page()
        assert game.level.chapter_index == 3 and game.save.data['completed']
        assert 'cloud_heart' in game.save.data['secrets']
        from weapons import WEAPON_ORDER
        assert {'fold_crossbow', 'orbit_saw'} <= set(WEAPON_ORDER)
        for language in SUPPORTED_LANGUAGES:
            set_language(language)
            game.save.data["settings"]["language"] = language
            assert translate("NEW GAME")
            if language != "en":
                assert translate("NEW GAME") != "NEW GAME", f"Menu translation missing: {language}"
            for menu in ("title", "settings", "controls", "pause", "back_pages", "achievements", "credits", "replay_pages", "ending"):
                game.state = menu
                game.draw()
                game._present()
        game.state = "playing"
        for key in (pygame.K_SPACE, pygame.K_w, pygame.K_UP):
            game.pending_input = InputFrame()
            game._key_down(key)
            assert game.pending_input.jump_pressed
        game.save.write()
        game.save.load()
        assert game.save.path.exists()
        report={"version":VERSION,"frozen":bool(getattr(sys,"frozen",False)),"pages":pages,
                "jumping_exits":air_exits, "languages":list(SUPPORTED_LANGUAGES),
                "tutorial_min_seconds":TrainingLesson.MIN_SECONDS, "sketch_count":len(SKETCHES),
                "actual_training_seconds":actual_training_seconds,
                "chapter_lengths":[build_chapter(i).end_x for i in range(5)],
                "secret_pockets":pockets,"optional_guardians":optional_guardians,"heart_routes_per_page":heart_routes,
                "artist_automatic_tools":automatic_tools,"new_weapons":["fold_crossbow","orbit_saw"],
                "afterword":{"interactive":True,"memories":3,"manual_signature":True},"postgame_page_replay":True,
                "boss_scores":boss_scores,"page_scores":page_scores,
                "main_boss_rooms":main_bosses,
                "normal_wave_counts":sorted(regular_waves),
                "normal_wave_sizes":normal_wave_sizes,
                "audio_identity":"12 cinematic boss recordings, original page music and notebook effects",
                "selected_music_cues":len(selected_music),"music_credit_count":len(MUSIC_CREDITS),
                "music_license":"CC BY 4.0 / CC0 1.0 / original compositions","exclusive_page_music_scenes":True,
                "music_channels":2,"distinct_recorded_boss_loops":True,"boss_drawing_seconds":3.2,"protected_boss_drawing":True,
                "protected_attack_warnings":True,
                "retained_recordings":sorted(RECORDED_SFX),
                "cloud_guardian":{"kind":guardian.kind,"hp":guardian.max_hp},
                "hidden_cloud_entrance":True,"player_follow_camera":True,
                "save_path":str(default_save_path()),"audio":game.sounds.enabled,
                "asset_root":str(game.sounds.asset_root)}
    pygame.quit()
    Path(output).write_text(json.dumps(report,indent=2),encoding="utf8")
