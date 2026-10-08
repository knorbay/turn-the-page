"""The Artist responds to recent fights between drawings, never to requests."""
from copy import deepcopy

from encounter_variety import MAX_ADAPTED_ENEMIES

RANGED_TOOLS = {'ink_pistol', 'marker_shotgun', 'eraser_cannon', 'rubber_band',
                'carbon_lance', 'chalk_bomb', 'folded_shuriken',
                'fold_crossbow', 'orbit_saw'}
CLOSE_TOOLS = {0:'pencil_blade', 1:'pencil_blade', 2:'pencil_blade',
               3:'pencil_blade', 4:'margin_maul'}
DISTANCE_TOOLS = {0:'folded_shuriken', 1:'ink_pistol', 2:'rubber_band',
                  3:'ink_pistol', 4:'rubber_band'}
SUPPORT_TOOLS = {0:'margin_maul', 1:'marker_shotgun', 2:'eraser_cannon',
                 3:'marker_shotgun', 4:'eraser_cannon'}
CHALLENGE_CAST = {0:'goblin_scribble', 1:'tumbleweed_thing', 2:'comet_hound',
                  3:'folder_glider', 4:'fold_duelist'}
CHALLENGE_ALTERNATES = {0:('fold_duelist','gutter_lantern','ruler_guard'),
    1:('ticket_vulture','cactus_gunner','tumbleweed_thing'),
    2:('comet_hound','crumpled_one','doodle_turret'),
    3:('file_runner','carbon_stamper','ruler_guard'),
    4:('goblin_scribble','gutter_lantern','moon_bot')}


class AdaptiveArtist:
    def __init__(self, saved=None):
        raw = saved if isinstance(saved, dict) else {}
        self.data = {'rooms':deepcopy(raw.get('rooms', {})) if isinstance(raw.get('rooms'), dict) else {},
                     'recent':deepcopy(raw.get('recent', []))[-6:] if isinstance(raw.get('recent'), list) else [],
                     'gifts':deepcopy(raw.get('gifts', {})) if isinstance(raw.get('gifts'), dict) else {}}
        self.attempts = {}

    @staticmethod
    def key(page, arena):
        return f'{page}:{arena.arena_id}'

    def snapshot(self):
        return deepcopy(self.data)

    def persist(self, ctx, write=False):
        game = getattr(ctx, 'game', None)
        if game is not None:
            game.save.data['artist_adaptation'] = self.snapshot()
            if write:game.save.write()

    def room(self, page, arena):
        key = self.key(page, arena)
        raw = self.data['rooms'].get(key)
        if not isinstance(raw, dict):
            raw = {'deaths':0, 'clears':0}
            self.data['rooms'][key] = raw
        for field in ('deaths', 'clears'):
            value = raw.get(field, 0)
            raw[field] = max(0, int(value)) if isinstance(value, (int, float)) else 0
        return raw

    def mode_for(self, page, arena):
        # The expedition's two losses are authored story beats, not failures.
        if arena.arena_id == 'baby_face_interlude':return 'standard'
        if self.room(page, arena).get('deaths', 0) >= 2:return 'support'
        recent = [r for r in self.data['recent'] if isinstance(r, dict)][-3:]
        if sum(r.get('result') == 'death' for r in recent) >= 2:return 'support'
        last = recent[-2:]
        if (len(last) == 2 and all(r.get('result') == 'clear'
                and isinstance(r.get('damage'), (int, float)) and r['damage'] <= 1
                and isinstance(r.get('seconds'), (int, float))
                and r['seconds'] <= (80 if r.get('boss') else 45) for r in last)):
            return 'challenge'
        return 'standard'

    def prepare_encounter(self, arena, ctx):
        key = self.key(ctx.level.chapter_index, arena)
        mode = self.mode_for(ctx.level.chapter_index, arena)
        self.attempts[key] = {'damage':0, 'finished':False, 'mode':mode}
        arena.artist_mode = mode
        arena.artist_notice = ''
        if not hasattr(arena, '_artist_original_specs'):
            arena._artist_original_specs = deepcopy(arena.enemy_specs)
        arena.enemy_specs = deepcopy(arena._artist_original_specs)
        # Skill pressure adds a fully telegraphed regular opponent. It never
        # speeds up warnings, inflates health, or adds a guard to a boss room.
        if mode == 'challenge' and not arena.boss and getattr(arena, 'mandatory', False):
            wave = max((int(s.get('wave', 0)) for s in arena.enemy_specs), default=0)
            count = sum(int(s.get('count', 1)) for s in arena.enemy_specs
                        if int(s.get('wave', 0)) == wave)
            ceiling = min(MAX_ADAPTED_ENEMIES,
                          int(getattr(arena, 'adapted_max_enemies', MAX_ADAPTED_ENEMIES)))
            if count < ceiling:
                page = ctx.level.chapter_index
                existing = {s.get('kind') for s in arena.enemy_specs if int(s.get('wave', 0)) == wave}
                candidates = (CHALLENGE_CAST[page], *CHALLENGE_ALTERNATES[page])
                kind = next((candidate for candidate in candidates if candidate not in existing),
                            CHALLENGE_CAST[page])
                arena.enemy_specs.append({'wave':wave, 'kind':kind,
                    'offset':(arena.end_x-arena.start_x)*.74, 'artist_challenge':True})
                arena.artist_notice = 'You crossed the last drawings easily. I am adding one more opponent.'
        elif mode == 'support':
            arena.artist_notice = 'That drawing caught you twice. I will watch your ink more closely.'
        arena.wave_ids = sorted({int(s.get('wave', 0)) for s in arena.enemy_specs})
        self.persist(ctx)

    def ensure_attempt(self, arena, ctx):
        if self.key(ctx.level.chapter_index, arena) not in self.attempts:
            self.prepare_encounter(arena, ctx)

    def record_damage(self, game):
        for arena in game.level.entities.items:
            if getattr(arena, 'is_combat_arena', False) and arena.encounter_active and not arena.completed:
                key = self.key(game.level.chapter_index, arena)
                attempt = self.attempts.get(key)
                if attempt is not None:attempt['damage'] += 1
                return

    def observe_death(self, arena, ctx, cause=''):
        if arena is None or arena.arena_id == 'baby_face_interlude' or cause == 'baby_face_giant':return
        key = self.key(ctx.level.chapter_index, arena)
        attempt = self.attempts.get(key, {'damage':0, 'finished':False})
        if attempt.get('finished'):return
        attempt['finished'] = True
        self.room(ctx.level.chapter_index, arena)['deaths'] += 1
        self.data['recent'].append({'result':'death', 'page':ctx.level.chapter_index,
            'arena':arena.arena_id, 'damage':attempt.get('damage', 0)})
        self.data['recent'] = self.data['recent'][-6:]
        self.attempts.pop(key, None)
        self.persist(ctx)

    def complete_encounter(self, arena, ctx):
        if arena.arena_id == 'baby_face_interlude':return
        key = self.key(ctx.level.chapter_index, arena)
        attempt = self.attempts.get(key, {'damage':0, 'finished':False})
        if attempt.get('finished'):return
        attempt['finished'] = True
        self.room(ctx.level.chapter_index, arena)['clears'] += 1
        self.data['recent'].append({'result':'clear', 'page':ctx.level.chapter_index,
            'arena':arena.arena_id, 'damage':attempt.get('damage', 0),
            'seconds':round(arena.encounter_time, 2), 'boss':bool(arena.boss)})
        self.data['recent'] = self.data['recent'][-6:]
        self.persist(ctx)

    def gift_for(self, page, weapons, rescue=False):
        candidate = SUPPORT_TOOLS[page] if rescue else (
            CLOSE_TOOLS[page] if weapons.current_id in RANGED_TOOLS else DISTANCE_TOOLS[page])
        return candidate if candidate not in weapons.unlocked else None

    def remember_gift(self, page, weapon, ctx):
        gifts = self.data['gifts'].setdefault(str(page), [])
        if not isinstance(gifts, list):
            gifts = self.data['gifts'][str(page)] = []
        if weapon not in gifts:gifts.append(weapon)
        self.persist(ctx)

    def gifts_for(self, page):
        from weapons import WEAPON_ORDER
        raw = self.data['gifts'].get(str(page), [])
        return tuple(w for w in raw if w in WEAPON_ORDER) if isinstance(raw, list) else ()
