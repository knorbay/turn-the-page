"""The notebook bank and its attack warnings stay coherent under real playback."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
from pathlib import Path
import hashlib,unittest,wave
from unittest.mock import patch
import pygame
from audio import NotebookSounds, RECORDED_SFX, SELECTED_PAGE_TRACKS, WARNING_RANK
from scene_music import BOSS_PROFILES, BOSS_RECORDINGS, SELECTED_BOSS_TRACKS
from audio_mix import condition_pcm
from audio_composer import SFX_VARIANT_COUNTS
ROOT=Path(__file__).resolve().parents[1]/'assets/audio'

class NotebookAudioRevisionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):pygame.mixer.pre_init(22050,-16,1,512);pygame.init()
    @classmethod
    def tearDownClass(cls):pygame.quit()
    def tearDown(self):pygame.mixer.stop()
    def test_runtime_uses_the_original_notebook_bank_not_imported_combat_recordings(self):
        sounds=NotebookSounds()
        for cue in ('pistol','revolver','suppressed_shot','shotgun','blocked','paper_step','enemy_hit_ink'):
            takes=sounds.sound_variants[cue]
            self.assertEqual(len(takes),SFX_VARIANT_COUNTS.get(cue,1))
            for i,sound in enumerate(takes):
                suffix='' if i==0 else f'_v{i+1}'
                with wave.open(str(ROOT/f'sfx_{cue}{suffix}.wav')) as f:raw=f.readframes(f.getnframes())
                self.assertEqual(sound.get_raw(),condition_pcm(raw,22050),cue)
        self.assertEqual(set(RECORDED_SFX),{'pencil','erase','blade'})
    def test_all_five_pages_use_distinct_recordings_with_exclusive_scene_handover(self):
        sounds=NotebookSounds();hashes=set()
        sounds.apply_settings({'master_volume':.8,'music_volume':.35})
        for page in range(5):
            sounds.start_ambience(page)
            sounds.update(1)
            calm=sounds.score_channel.get_sound();action=sounds.score_high[page]
            self.assertIs(calm,sounds.score_low[page])
            self.assertFalse(sounds.combat_channel.get_busy())
            self.assertGreater(calm.get_length(),1)
            self.assertGreater(action.get_length(),1)
            self.assertAlmostEqual(sounds.score_channel.get_volume(),.8*.35*.20,delta=.008)
            hashes.add(hashlib.sha256(calm.get_raw()).hexdigest())
            self.assertFalse(SELECTED_PAGE_TRACKS[page]['calm'].startswith('directed/'))
            sounds.set_combat(True);sounds.update(.53)
            self.assertIs(sounds.combat_channel.get_sound(),action)
            self.assertFalse(sounds.score_channel.get_busy())
            self.assertAlmostEqual(sounds.combat_channel.get_volume(),.8*.35*.235*sounds.intensity,delta=.008)
            sounds.set_combat(False)
            sounds.update(.53)
            self.assertFalse(sounds.combat_channel.get_busy())
            self.assertIs(sounds.score_channel.get_sound(),calm)
        self.assertEqual(len(hashes),5)
    def test_twelve_boss_identities_select_distinct_credited_recordings(self):
        sounds=NotebookSounds();scores=set()
        self.assertEqual(len(BOSS_PROFILES),12)
        self.assertEqual(set(SELECTED_BOSS_TRACKS),set(BOSS_PROFILES))
        self.assertEqual({item['kind'] for item in BOSS_RECORDINGS},set(BOSS_PROFILES))
        for kind,profile in BOSS_PROFILES.items():
            sounds.start_ambience(profile['page']);sounds.set_combat(False)
            sounds.set_combat(True,True,kind)
            self.assertEqual(sounds.action_variant,f'boss:{kind}')
            self.assertFalse(sounds.music_intro_channel.get_busy())
            self.assertTrue(sounds.boss_channel.get_busy())
            score=sounds.boss_channel.get_sound()
            self.assertIs(score,sounds.boss_scores[kind])
            self.assertIsNot(score,sounds.score_boss[profile['page']])
            self.assertTrue(SELECTED_BOSS_TRACKS[kind].startswith('boss/'))
            self.assertGreaterEqual(score.get_length(),20)
            self.assertLessEqual(score.get_length(),45)
            # The game plays the mastered recording unchanged; the old
            # synthesized percussion must not be overlaid on it.
            original=pygame.mixer.Sound(str(ROOT/SELECTED_BOSS_TRACKS[kind]))
            self.assertEqual(score.get_raw(),original.get_raw(),kind)
            scores.add(hashlib.sha256(score.get_raw()).hexdigest())
        self.assertEqual(len(scores),12)
    def test_page_load_prepares_its_boss_recordings_before_entrance(self):
        sounds=NotebookSounds()
        for page in range(5):
            sounds.start_ambience(page)
            kinds=[kind for kind,profile in BOSS_PROFILES.items() if profile['page']==page]
            self.assertTrue(all(kind in sounds.boss_scores for kind in kinds))
            # Entry must only select cached Sounds, without decoding files
            # or rebuilding the older page score on a combat frame.
            with patch.object(sounds,'_asset_sound',side_effect=AssertionError('late boss decode')):
                for kind in kinds:
                    sounds.set_combat(True,True,kind)
                    self.assertIs(sounds.boss_channel.get_sound(),sounds.boss_scores[kind])
            sounds.set_combat(False)
    def test_boss_score_starts_once_per_entry_and_restarts_on_retry_or_new_boss(self):
        class CountingChannel:
            def __init__(self,channel):self.channel=channel;self.calls=0
            def play(self,*args,**kwargs):self.calls+=1;return self.channel.play(*args,**kwargs)
            def __getattr__(self,name):return getattr(self.channel,name)
        sounds=NotebookSounds();sounds.start_ambience(0)
        sounds.music_intro_channel=CountingChannel(sounds.music_intro_channel)
        sounds.boss_channel=CountingChannel(sounds.boss_channel)
        sounds.set_combat(True,True,'moon_compass')
        for _ in range(60):sounds.set_combat(True,True,'moon_compass');sounds.update(1/60)
        self.assertEqual(sounds.music_intro_channel.calls,0);self.assertEqual(sounds.boss_channel.calls,1)
        sounds.set_combat(False);sounds.set_combat(True,True,'moon_compass');sounds.update(.2)
        self.assertEqual(sounds.music_intro_channel.calls,0);self.assertEqual(sounds.boss_channel.calls,2)
        sounds.set_combat(True,True,'cloud_kite');sounds.update(.2)
        self.assertEqual(sounds.music_intro_channel.calls,0);self.assertEqual(sounds.boss_channel.calls,3)
    def test_departure_stops_boss_music_without_a_delayed_restart(self):
        sounds=NotebookSounds();sounds.start_ambience(0)
        for exit_action in (lambda:sounds.set_combat(False),lambda:sounds.start_ambience(1)):
            sounds.set_combat(True,True,'cloud_kite');exit_action();sounds.update(4)
            self.assertIsNone(sounds._pending_boss_score)
            self.assertFalse(sounds.boss_channel.get_busy());self.assertFalse(sounds.music_intro_channel.get_busy())
            self.assertFalse(sounds.boss_active)
    def test_boss_score_is_protected_and_music_slider_owns_it(self):
        sounds=NotebookSounds();sounds.start_ambience(0)
        sounds.set_combat(True,True,'cloud_kite');score=sounds.boss_channel.get_sound()
        for _ in range(30):sounds.play('heavy_hit',cooldown_ms=0);sounds.play('boss_signature',cooldown_ms=0)
        self.assertIs(sounds.boss_channel.get_sound(),score)
        sounds.apply_settings({'master_volume':1,'sfx_volume':1,'music_volume':0})
        for channel in (sounds.score_channel,sounds.combat_channel,sounds.boss_channel,sounds.music_intro_channel):
            self.assertEqual(channel.get_volume(),0)
        self.assertGreater(sounds.cue_channel.get_volume(),0)
    def test_hit_burst_cannot_cut_a_regular_attack_warning(self):
        sounds=NotebookSounds();sounds.start_ambience(0)
        with patch('pygame.time.get_ticks',return_value=1000):
            warning=sounds.play('enemy_telegraph_heavy',pitch=1,variant=0,cooldown_ms=0)
            sample=warning.get_sound();self.assertIs(warning,sounds.warning_channel)
            for _ in range(25):sounds.play('heavy_hit',cooldown_ms=0)
            self.assertIs(warning.get_sound(),sample)
            weaker=sounds.play('enemy_telegraph_air',pitch=1,variant=0,cooldown_ms=0)
            self.assertIsNone(weaker);self.assertIs(warning.get_sound(),sample)
            boss=sounds.play('boss_phase_shift',cooldown_ms=0)
            self.assertIs(boss,sounds.cue_channel);self.assertIs(warning.get_sound(),sample)
    def test_warning_and_boss_cues_duck_music_and_honor_sliders(self):
        sounds=NotebookSounds();sounds.start_ambience(0)
        sounds.apply_settings({'master_volume':1,'music_volume':1,'sfx_volume':1})
        sounds.set_combat(True,True,'moon_compass');sounds.update(3)
        before=sounds.boss_channel.get_volume()
        with patch('pygame.time.get_ticks',return_value=2000):
            sounds.play('enemy_telegraph_ranged',cooldown_ms=0)
            self.assertLess(sounds.boss_channel.get_volume(),before)
            sounds.play('boss_phase_shift',cooldown_ms=0)
        sounds.apply_settings({'sfx_volume':0,'master_volume':1})
        self.assertEqual(sounds.warning_channel.get_volume(),0)
        self.assertEqual(sounds.cue_channel.get_volume(),0)
        sounds.apply_settings({'master_volume':0})
        self.assertEqual(sounds.boss_channel.get_volume(),0)
    def test_equal_or_urgent_warning_can_replace_finished_or_less_urgent_warning(self):
        sounds=NotebookSounds()
        with patch('pygame.time.get_ticks',return_value=3000):
            low=sounds.play('enemy_telegraph_air',cooldown_ms=0)
            high=sounds.play('enemy_telegraph_heavy',cooldown_ms=0)
            self.assertIs(low,high);self.assertEqual(sounds._warning_rank,WARNING_RANK['enemy_telegraph_heavy'])
            high.stop()
            ordinary=sounds.play('enemy_telegraph',cooldown_ms=0)
            self.assertIsNotNone(ordinary)
            self.assertEqual(sounds._warning_rank,WARNING_RANK['enemy_telegraph'])

if __name__=='__main__':unittest.main()
