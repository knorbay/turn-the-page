"""The Living Margins: playable guidance, quiet conversation and short retries."""
import pygame
from chapters import Checkpoint
from world import PaperNote
from settings import INK, INK_LIGHT, WIDTH


def polish_route(runtime):
    """Put every encounter behind a stable, reachable retry landing."""
    if runtime.index in (1, 2):
        from action_content import WeaponPickup
        runtime.entities.add(WeaponPickup(6480 if runtime.index == 1 else 5600,
                                          590, 'chalk_bomb', page_index=runtime.index))
    arenas = [e for e in runtime.entities.items if getattr(e, 'is_combat_arena', False)]
    known = {cp.checkpoint_id for cp in runtime.checkpoints}
    for arena in arenas:
        if 'before_' + arena.arena_id in known:
            continue
        x = arena.start_x - 130
        # This landing is before the gate, never inside the fight or over its exit.
        p = runtime.world.add(x - 90, arena.start_x + 12, 590, 14,
                              'retry_' + arena.arena_id, 9300 + len(runtime.checkpoints))
        p.appearance = 'margin_rule'
        runtime.checkpoints.append(Checkpoint('before_' + arena.arena_id, x, 542,
                                               trigger_x=x - 16, requires=tuple(e.arena_id for e in arenas
                                               if e.mandatory and e.end_x < arena.start_x)))
    from page_experiences import add_page_experiences
    add_page_experiences(runtime)
    from notebook_agency import NotebookAgency
    runtime.entities.add(NotebookAgency(runtime))
    runtime.checkpoints.sort(key=lambda cp: float(cp.trigger_x or cp.x))
    if runtime.index == 0:
        runtime.world.notes[:] = [note for note in runtime.world.notes
                                  if note.text not in {'A / D MOVE     SPACE JUMP',
                                                       'F / J CUT     SHIFT / K DASH'}]
        # A blank figure, three lines drawn ahead of it, then an actual tool.
        # Bind the attack annotation to a target drawn after that tool is kept.
        runtime.world.notes[:] = [note for note in runtime.world.notes
            if note.text not in {'THREE HEARTS / fresh ink at every new fight',
                                 'INK VILLAGE / keep the blade dry'}]
        runtime.world.notes.append(PaperNote(1455,345,'a red stroke warns; a blue gap invites','small',INK_LIGHT))
        runtime.world.notes.append(PaperNote(3640,438,'SHIFT / K  ->  leave the red line behind','small',INK_LIGHT))
        runtime.entities.add(PracticeDrawing())


class PracticeDrawing:
    """An optional first-screen target, using the real weapon collision path."""
    active = True
    mandatory = False
    layer = 0
    encounter_active = False
    def __init__(self, x=1415, ground=545):
        from advanced_enemies import AdvancedEnemy
        self.x, self.ground = x, ground
        self.target = AdvancedEnemy(x,ground)
        self.target.kind = 'practice_drawing'
        self.target.hp = self.target.max_hp = 2
        self.target.width, self.target.height = 48, 62
        self.enemies = [self.target]
        self.completed = False
        self.reveal = 0.0
        self.target.notebook_reveal = 0.0
        self.hand = None
    def update(self, dt, ctx, interact=False):
        from scripted_events import ArtistTool, artist_canvas_free
        from action_content import claim_artist_canvas,release_artist_canvas
        self.hand = None
        if ctx.player.health<=0:
            release_artist_canvas(ctx,self)
            return
        tool_ready = bool(getattr(ctx,'weapons',None) and ctx.weapons.unlocked)
        if (not self.completed and self.reveal<1 and tool_ready and (self.reveal>0 or abs(ctx.player.center_x-self.x)<420)
                and artist_canvas_free(ctx,self)):
            if not claim_artist_canvas(ctx,self):return
            if self.reveal == 0: ctx.sounds.play('pencil')
            next_reveal = min(1,self.reveal+dt/.48)
            occupied=self.target.rect.colliderect(ctx.player.rect.inflate(8,4))
            self.reveal=.98 if next_reveal>=1 and occupied else next_reveal
            self.target.notebook_reveal = self.reveal
            if self.reveal < 1:
                self.hand = ArtistTool('pencil',self.x,self.ground-62+62*self.reveal,True)
                ctx.director.tool = self.hand
            else:release_artist_canvas(ctx,self)
        self.encounter_active = (not self.completed and self.reveal >= 1
            and abs(ctx.player.center_x-self.x)<420 and not ctx.player.locked)
        self.target.vx = self.target.vy = 0
        self.target.x, self.target.y = self.x, self.ground
        self.target.hit_flash = max(0, self.target.hit_flash-dt)
        self.target.invulnerable = max(0, self.target.invulnerable-dt)
        if self.target.dead and not self.completed:
            self.completed = True
            release_artist_canvas(ctx,self)
            self.encounter_active = False
            self.enemies.clear()
            if ctx.game:
                ctx.game.behavior.record('practice_complete')
            ctx.level.toast = 'Out, then back. The fold remembers your hand.'
            ctx.level.toast_time = 3.5
    def draw(self, surface, camera, renderer):
        if self.completed or self.reveal <= 0:
            return
        x,y = camera.screen_x(self.x),round(self.ground+camera.offset_y)
        old=surface.get_clip()
        surface.set_clip(old.clip(pygame.Rect(x-29,y-65,58,round(65*self.reveal))))
        pygame.draw.line(surface, INK_LIGHT, (x,y-35), (x,y), 3)
        pygame.draw.circle(surface, (174,85,73), (x,y-40), 22, 3)
        pygame.draw.circle(surface, INK, (x,y-40), 10, 2)
        surface.set_clip(old)
        if self.reveal >= 1 and self.encounter_active:
            renderer.doodle_text(surface,'F / J  send it, then watch it return',
                (x-155,y-94),INK_LIGHT,renderer.font_small,-1)


class ArtistCompanion:
    """Short, optional exchanges that notice what the player actually changed."""
    TOOL_LINES = {
        'chalk_bomb': 'Throw this chalk over cover. Its little cloud buys space.',
        'carbon_lance': 'One straight carbon line can pass through a crowd. Then reload.',
        'folded_shuriken': 'The fold comes back. Catch it for a faster next throw.',
        'margin_maul': 'I made that pencil too heavy. Wind up before you swing.',
        'ink_pistol': 'This ink travels fast. Leave yourself time to reload.',
        'marker_shotgun': 'A broad marker stroke works best when you stand close.',
        'eraser_cannon': 'The eraser removes incoming marks as well as enemies.',
        'rubber_band': 'Bank that shot off a line. Straight ahead is not the only way.',
        'excalibur': 'I may have overdrawn the sword. Its reach is the point.',
    }

    def __init__(self):
        self.seen = set()
        self.queued = set()
        self.pending = []
        self.text = ''
        self.reply = ''
        self.timer = 0.0
        self.silence = 0.0
        self.page = None
        self.age = 0.0
        self.observed = False
        self.last_deaths = 0
        self.last_clears = 0
        self.last_health = None
        self.last_weapon = None
        self.last_unlocked = set()
        self.last_flags = set()
        self.last_help = 0
        self.last_requests = 0
        self.last_boss_redraw = 0

    def say(self, key, text, reply=''):
        if key in self.seen or self.timer > 0 or self.silence > 0:
            return False
        self.seen.add(key)
        self.text, self.reply, self.timer = text, reply, 6.5
        self.silence = 14.0
        return True

    def _queue(self, priority, key, text, reply='', lifetime=25):
        if key in self.seen or key in self.queued:
            return
        self.queued.add(key)
        self.pending.append((priority, key, text, reply, self.age + lifetime))
        # A single room should never accumulate a backlog of old commentary.
        self.pending.sort(key=lambda note: -note[0])
        for stale in self.pending[3:]:
            self.queued.discard(stale[1])
        del self.pending[3:]

    def _snapshot(self, game):
        self.last_deaths = game.behavior.count('deaths')
        self.last_clears = game.behavior.count('arena_clear')
        self.last_help = game.behavior.count('artist_mercy')
        self.last_requests = game.behavior.count('artist_request')
        self.last_boss_redraw = game.behavior.count('boss_redraw')
        self.last_health = game.player.health
        self.last_weapon = game.weapons.current_id
        self.last_unlocked = set(game.weapons.unlocked)
        self.last_flags = set(game.level.flags)
        self.observed = True

    @staticmethod
    def _active_fight(game):
        return any(getattr(entity, 'encounter_active', False)
                   and not getattr(entity, 'completed', False)
                   for entity in game.level.entities.items)

    @staticmethod
    def _other_artist_note(game):
        return any(getattr(entity, 'letter_time', 0) > 0
                   for entity in game.level.entities.items)

    def _notice_actions(self, game, page):
        """Record changes now, then deliver their notes in a quiet margin."""
        if not self.observed:
            self._snapshot(game)
            return
        deaths = game.behavior.count('deaths')
        died = deaths > self.last_deaths
        if died:
            cause = getattr(game.level, 'respawn_cause', '')
            if cause in ('fall', 'erased_floor', 'ink_hazard', 'ink_wall'):
                text, reply = ('I left that edge too faint. I have redrawn the landing.',
                               'I see it now. Leave the next line visible, please.')
            else:
                text, reply = ('That sketch came apart. I kept your place.',
                               'Draw me back crooked if you must. I am still here.')
            self._queue(9, ('retry', page), text, reply, 55)
        self.last_deaths = deaths

        current_unlocked = set(game.weapons.unlocked)
        newly_unlocked = current_unlocked - self.last_unlocked
        for weapon in sorted(newly_unlocked):
            self._queue(7, ('new_weapon', weapon),
                        self.TOOL_LINES.get(weapon, 'That tool began as a margin doodle. Try how it moves.'),
                        'I will. Keep drawing different answers.', 38)
        self.last_unlocked = current_unlocked

        current_weapon = game.weapons.current_id
        if current_weapon != self.last_weapon and current_weapon not in newly_unlocked:
            if current_weapon == 'pencil_blade':
                text = 'Back to a close line. Its timing matters more than its ink.'
            elif current_weapon == 'margin_maul':
                text = 'That pencil is slow. Start the swing before they close in.'
            elif current_weapon in ('eraser_cannon', 'marker_shotgun', 'chalk_bomb'):
                text = 'A wider mark. Make room before you draw the next one.'
            else:
                text = 'Different tool, different rhythm. Show me what this one can do.'
            self._queue(2, ('switch', page, current_weapon), text,
                        'Then watch the space it leaves behind.', 15)
        self.last_weapon = current_weapon

        clears = game.behavior.count('arena_clear')
        if clears > self.last_clears:
            # One ordinary room reaction per page leaves space for the boss.
            self._queue(4, ('first_clear', page),
                        'You changed that fight without my hand on the page.',
                        'I had to. You gave me room to move.', 28)
        self.last_clears = clears

        puzzle_ids = {getattr(entity, 'puzzle_id') for entity in game.level.entities.items
                      if getattr(entity, 'puzzle_id', None)}
        solved = (set(game.level.flags) - self.last_flags) & puzzle_ids
        if solved:
            puzzle = sorted(solved)[0]
            responses = {
                'first_page_draft': (
                    'You put that step where my first line failed.',
                    'Then leave space for my next answer.'),
                'wanted_perforation': (
                    'You tore the poster exactly where I left the paper weak.',
                    'You drew the seam. I chose when to hit it.'),
                'satellite_relay': (
                    'I drew the star. You carried it farther than I planned.',
                    'The next connection can be ours.'),
            }
            text, reply = responses.get(puzzle, (
                'You found an answer I did not draw in the margin.',
                'Leave the next one unfinished. I want to try.'))
            self._queue(6, ('puzzle', page, sorted(solved)[0]),
                        text, reply, 35)
        self.last_flags = set(game.level.flags)

        requests = game.behavior.count('artist_request')
        if requests > self.last_requests:
            self._queue(5, ('request', page),
                        'You asked me to change the page. That changes my plan too.',
                        'Good. Let me choose where the line goes next.', 38)
        self.last_requests = requests

        redraws = game.behavior.count('boss_redraw')
        if redraws > self.last_boss_redraw:
            self._queue(8, ('boss_redraw', page),
                        'I drew you a new foothold. The next move is yours.',
                        'I see it. Do not erase it yet.', 42)
        self.last_boss_redraw = redraws

        help_count = game.behavior.count('artist_mercy')
        if help_count > self.last_help:
            self._queue(5, ('mercy', page),
                        'I rubbed one out. You still have to cross this page.',
                        'I know. Thanks for the breath.', 32)
        self.last_help = help_count

        health = game.player.health
        if health < self.last_health and health > 0 and not died:
            self._queue(3, ('hurt', page),
                        'That mark was mine to warn you about. Watch its red outline.',
                        'I saw it late. I will move before it lands.', 18)
        self.last_health = health

    def update(self, dt, game, frame):
        self.timer = max(0, self.timer-dt)
        self.silence = max(0, self.silence-dt)
        page = game.level.chapter_index
        if self.page != page:
            self.page, self.age = page, 0
            self.timer = self.silence = 0
            self.pending.clear()
            self.queued.clear()
            # Page loadouts can switch the weapon without a player action.
            self._snapshot(game)
        self.age += dt
        self._notice_actions(game, page)
        if game.player.locked or game.level.respawn_timer > 0:
            return
        # Fight warnings, puzzle prompts and the Artist's drawn interventions
        # own this part of the sheet until the action settles.
        if self._active_fight(game):
            self.timer = 0
            return
        director=getattr(game.level,'director',None)
        if (getattr(director,'canvas_owner',None) is not None
                or getattr(getattr(director,'tool',None),'visible',False)
                or getattr(director,'blocks_combat',False)):
            return
        if (game.level.toast_time > 0 or game.achievement_time > 0
                or game.level.interaction_hint or self._other_artist_note(game)):
            return
        if frame.interact and self.timer > 0 and self.reply:
            self.text, self.reply = self.reply, ''
            self.timer, self.silence = 4.5, 12
            game.behavior.record('artist_reply')
            game.persist_behavior(write=True)
            return
        self.pending = [note for note in self.pending if note[4] > self.age]
        self.queued = {note[1] for note in self.pending}
        if self.timer > 0 or self.silence > 0:
            return
        if self.pending:
            _, key, text, reply, _ = self.pending.pop(0)
            self.queued.discard(key)
            self.say(key, text, reply)
        elif self.age > 2 and ('hello',page) not in self.seen:
            lines = [
                ('Oh. You can hear me? Try moving. I will keep drawing.',
                 'A small nod. That counts. The red circle is yours to cross out.'),
                ('I drew you a hat. The gun needs time to reload.',
                 'Six shots. Make a little space before the seventh.'),
                ('The stars were meant to stay still. Sorry.',
                 'Bank the pulse off a line. You can reach around a shield.'),
                ('Keep your head down. This page has very good aim.',
                 'When the long red line stops moving, leave it behind.'),
                ('You have changed how I draw. One more page?',
                 'All right. I will leave the last word to you.'),
            ]
            if 0 <= page < len(lines):
                self.say(('hello',page), *lines[page])
        elif page == 0 and game.player.x > 1000:
            self.say('combat', 'Three cuts, then breathe. Dash past the red warning.',
                     'The blue marks show a boss opening. Spend them carefully.')

    def draw(self, surface, renderer, controller=False):
        if self.timer<=0 or not self.text:return
        reply=('PAD-Y: nod back' if controller else 'E: nod back') if self.reply else ''
        renderer.notebook.artist_note(surface,self.text,reply)
