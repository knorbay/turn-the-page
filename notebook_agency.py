"""The Artist observes play and draws help without a request menu."""
import math
import pygame
from scripted_events import ArtistDirector, ArtistTool, artist_canvas_free
from page_arsenal import draw_weapon_icon
from weapon_delivery import next_delivery


class NotebookAgency:
    active = True
    mandatory = False
    layer = 0
    # Only used to restore legacy 0.32 save IDs, never shown as offers.
    TOOL_OFFERS = {0:('margin_maul','chalk_bomb'), 1:('chalk_bomb','marker_shotgun'),
        2:('eraser_cannon','chalk_bomb'), 3:('folded_shuriken','marker_shotgun'),
        4:('rubber_band','eraser_cannon')}

    def __init__(self, runtime):
        self.runtime, self.page = runtime, runtime.index
        self.arenas = [e for e in runtime.entities.items if getattr(e,'is_combat_arena',False)]
        self.first = self.arenas[0] if self.arenas else None
        self.offer_x = 5100 if self.page == 0 else self.first.start_x-700 if self.first else 400
        self.choice = ''
        self.restored = False
        self.timer = 0.0
        self.operation = None
        self.platforms = []
        self.used_patches = set()
        self.used_tools = set()
        self.boss_phases = set()
        self.noticed = set()
        self.hand = ArtistDirector()
        self.letter = ''
        self.letter_time = 0
        self.target = None
        self.last_scratch = -1
        self.selected_weapon = ''
        self.gift_x, self.gift_y = 0, 0
        self.gift_reason = ''
        self.gift_page_done = False
        self.gift_cooldown = 0.0

    def choose(self, choice, ctx):
        return False

    def weapon_for_choice(self, choice):
        return self.TOOL_OFFERS[self.page][choice == 'tool2']

    def _policy(self, ctx):
        game = getattr(ctx, 'game', None)
        return getattr(game, 'artist_director', None)

    def _platform(self, ctx, x, y, width, name):
        existing = ctx.world.platform_named(name)
        if existing is not None:
            if existing not in self.platforms:self.platforms.append(existing)
            return existing
        x = max(12,min(ctx.world.width-width-12,x))
        p = ctx.world.add(x,x+width,y,10,name,8700+len(self.platforms))
        p.appearance='handwriting';p.begin_drawing()
        self.platforms.append(p)
        return p

    def _route(self, ctx):
        if self.platforms:return
        if self.page == 0:
            self._platform(ctx,self.offer_x+180,520,300,'requested_road_a')
            self._platform(ctx,self.offer_x+505,465,270,'requested_road_b')
        elif self.first:
            self._platform(ctx,self.first.start_x+115,510,190,'requested_road_a')
            self._platform(ctx,self.first.start_x+350,445,180,'requested_road_b')

    def _give_tool(self, ctx):
        if not ctx.weapons:return
        held = ctx.weapons.current_id
        if ctx.weapons.active_loadout is not None:ctx.weapons.active_loadout.add(self.selected_weapon)
        ctx.weapons.unlock(self.selected_weapon)
        if held == 'unarmed':ctx.weapons.select(self.selected_weapon)
        if ctx.game:
            snapshot=ctx.weapons.snapshot()
            ctx.game.save.update_combat(snapshot['unlocked'],snapshot['current_id'],snapshot['ammo'])

    def _restore(self, ctx):
        self.restored = True
        raw = ctx.game.save.data.get('notebook_choices',{}) if ctx.game else {}
        self.choice = raw.get(str(self.page),'') if isinstance(raw,dict) else ''
        if self.choice in ('tool','tool2'):
            saved = ctx.game.save.data.get('notebook_tools',{})
            self.selected_weapon = saved.get(str(self.page),'margin_maul')
            from weapons import WEAPON_ORDER
            if self.selected_weapon not in WEAPON_ORDER:self.selected_weapon=self.weapon_for_choice(self.choice)
            self._give_tool(ctx)
        elif self.choice == 'road':
            self._route(ctx)
            for p in self.platforms:p.draw_progress=1
        policy = self._policy(ctx)
        if policy:
            self.gift_page_done = bool(policy.gifts_for(self.page))
            for weapon in policy.gifts_for(self.page):
                self.selected_weapon = weapon
                self._give_tool(ctx)

    def _begin_tool(self, ctx, weapon, reason):
        if not weapon or weapon in ctx.weapons.unlocked:return False
        if not artist_canvas_free(ctx,self,allow_in_combat=True) or not ctx.director.claim_canvas(self,allow_in_combat=True):return False
        self.selected_weapon = weapon
        self.gift_x, self.gift_y = ctx.player.center_x+65, ctx.player.y-70
        self.gift_reason = reason
        self.operation = 'support_tool';self.timer=0;self.last_scratch=-1
        self.letter = ('New drawing. Q to try it.'
            if reason == 'chapter_progression' else
            'I saw you struggle with this drawing. Here is a stronger tool. Q tries it; your weapon stays.'
            if reason == 'repeated_defeat' else
            'I watched your last fight. Here is another range to try. Q changes tools; your weapon stays.')
        self.letter_time = 2.8 if reason == 'chapter_progression' else 6
        ctx.sounds.play('pencil')
        return True

    def _quiet_tool_window(self, ctx, interact=False):
        """Automatic loans yield to the player's drawings and pending notices.

        Their earned availability has no expiry. Wait for a real quiet stretch
        instead of occupying the hand while somebody collects, shoots a clue,
        starts an optional fight, or still reads the tool just picked up.
        """
        if interact or self.gift_cooldown > 0 or self.letter_time > 0:
            return False
        if getattr(ctx.level, 'toast_time', 0) > 0 or getattr(ctx.level, 'interaction_hint', ''):
            return False
        weapons = getattr(ctx, 'weapons', None)
        if (weapons is None or weapons.melee is not None or weapons.projectiles
                or weapons.fire_buffer > 0):
            return False
        game = getattr(ctx, 'game', None)
        if game is not None and (getattr(game, 'weapon_reveal_time', 0) > 0
                or getattr(game, 'achievement_time', 0) > 0
                or getattr(getattr(game, 'achievements', None), 'pending', ())):
            return False
        from action_content import WeaponPickup
        for entity in ctx.level.entities.items:
            if entity is self or getattr(entity, 'layer', ctx.world.active_layer) != ctx.world.active_layer:
                continue
            if (getattr(entity, 'letter_time', 0) > 0 or
                    getattr(entity, 'encounter_active', False) and not getattr(entity, 'completed', False)):
                return False
            sketch = getattr(entity, 'sketch', None)
            if (sketch is not None and not getattr(sketch, 'discovered', False)
                    and abs(ctx.player.center_x-sketch.x) < 230
                    and abs(ctx.player.rect.bottom-sketch.y) < 125):
                return False
            pickup = entity if isinstance(entity, WeaponPickup) else getattr(entity, 'tool_gift', None)
            if (pickup is not None and not pickup.collected
                    and pickup.weapon_id not in weapons.unlocked
                    and abs(ctx.player.center_x-pickup.x) < 390
                    and abs(ctx.player.rect.bottom-pickup.y) < 150):
                return False
        return True

    def _begin_patch(self, ctx, arena):
        if arena.arena_id in self.used_patches or ctx.player.health >= ctx.player.max_health:return False
        if not ctx.director.claim_canvas(self,allow_in_combat=True):return False
        self.used_patches.add(arena.arena_id)
        self.operation='patch_player';self.timer=0;self.last_scratch=-1
        self.letter='Your ink is almost gone. I will redraw one heart. Keep reading the red lines.'
        self.letter_time=4.5
        ctx.sounds.play('pencil')
        return True

    def update(self, dt, ctx, interact=False):
        if not self.restored:self._restore(ctx)
        self.letter_time=max(0,self.letter_time-dt)
        self.gift_cooldown=max(0,self.gift_cooldown-dt)
        self.hand.tool.visible=False
        if ctx.player.health<=0:
            ctx.director.release_canvas(self);self.operation=None
            return
        if (self.operation == 'support_tool' and self.gift_reason != 'repeated_defeat'
                and (interact or any(getattr(e, 'encounter_active', False)
                    and not getattr(e, 'completed', False) for e in ctx.level.entities.items))):
            # A deliberate drawing or a newly entered fight owns the hand.
            # Unfinished automatic gifts remain earned for the next quiet gap.
            if self.gift_reason == 'alternate_range':self.gift_page_done = False
            self.operation = None
            self.letter_time = 0
            self.gift_cooldown = 3.2
            ctx.director.release_canvas(self)
        active=next((a for a in self.arenas if a.encounter_active and not a.completed),None)
        policy=self._policy(ctx)
        if active and policy:
            policy.ensure_attempt(active,ctx)
            if active.arena_id not in self.noticed and getattr(active,'artist_notice',''):
                self.noticed.add(active.arena_id)
                self.letter=active.artist_notice;self.letter_time=4
        if self.operation is None and not ctx.player.locked and policy:
            if active and active.arena_id != 'baby_face_interlude':
                if (ctx.player.health<=1 and active.arena_id not in self.used_patches
                        and active.encounter_time>=2 and any(not e.dead for e in active.enemies)):
                    self._begin_patch(ctx,active)
                elif (getattr(active,'artist_mode','standard')=='support'
                        and policy.room(self.page,active).get('deaths',0)>=3
                        and active.arena_id not in self.used_tools and active.encounter_time>=3):
                    weapon=policy.gift_for(self.page,ctx.weapons,rescue=True)
                    if self._begin_tool(ctx,weapon,'repeated_defeat'):self.used_tools.add(active.arena_id)
            elif (not active and self._quiet_tool_window(ctx, interact)
                    and self.first and self.first.completed and not self.gift_page_done
                    and ctx.weapons.unlocked and ctx.weapons.current_id != 'unarmed'
                    and self.first.end_x-80 < ctx.player.center_x):
                weapon=policy.gift_for(self.page,ctx.weapons)
                if weapon is None:self.gift_page_done=True
                elif self._begin_tool(ctx,weapon,'alternate_range'):self.gift_page_done=True
            elif not active and self.gift_page_done and self._quiet_tool_window(ctx, interact):
                weapon = next_delivery(self.page,self.arenas,ctx.player,ctx.weapons)
                if weapon:self._begin_tool(ctx,weapon,'chapter_progression')
        if active and self.operation is None:
            for boss in active.enemies:
                if not getattr(boss,'is_boss',False) or boss.kind=='baby_face_giant':continue
                phase=getattr(boss,'phase',1);key=(active.arena_id,phase)
                if phase>=2 and key not in self.boss_phases:
                    if not ctx.director.claim_canvas(self,allow_in_combat=True):break
                    self.boss_phases.add(key)
                    side=-1 if ctx.player.center_x<boss.x else 1
                    x=max(active.start_x+45,min(active.end_x-225,ctx.player.center_x+side*110))
                    self.target=self._platform(ctx,x,500,165,'artist_boss_step_'+active.arena_id+'_'+str(phase))
                    self.operation='boss_road';self.timer=0;self.last_scratch=-1
                    self.letter='He changed the rules. So can we. Use this line.';self.letter_time=4
                    ctx.sounds.play('pencil')
                    if ctx.game:ctx.game.behavior.record('boss_redraw',kind=boss.kind,phase=phase)
                    break
        if self.operation:
            self.timer+=dt
            p=min(1,self.timer/1.15)
            if self.operation=='support_tool':
                self.hand.tool=ArtistTool('pencil',self.gift_x-45+p*90,self.gift_y,True)
                if p>=1:
                    self._give_tool(ctx)
                    if policy:policy.remember_gift(self.page,self.selected_weapon,ctx)
                    if ctx.game:
                        ctx.game.behavior.record('artist_help',kind=self.gift_reason,page=self.page,weapon=self.selected_weapon)
                        ctx.game.persist_behavior(write=True)
                    ctx.sounds.play('pickup');self.operation=None
                    self.gift_cooldown=3.2
            elif self.operation=='patch_player':
                self.hand.tool=ArtistTool('pencil',ctx.player.center_x+math.sin(p*12)*17,ctx.player.y+10+28*p,True,-.65)
                if p>=1:
                    ctx.player.health=min(ctx.player.max_health,ctx.player.health+1)
                    ctx.player.invulnerable=max(ctx.player.invulnerable,.8)
                    ctx.particles.paper_puff(ctx.player.center_x,ctx.player.y+16,10)
                    ctx.sounds.play('heart')
                    if ctx.game:
                        ctx.game.behavior.record('artist_help',kind='observed_low_ink',page=self.page)
                        ctx.game.persist_behavior(write=True)
                    self.operation=None
            elif self.operation=='boss_road':
                self.target.draw_progress=p
                self.hand.tool=ArtistTool('pencil',self.target.visible_x2,self.target.y,True)
                if p>=1:self.operation=None
            tick=int(self.timer*5)
            if tick!=self.last_scratch:
                self.last_scratch=tick;ctx.sounds.play('pencil')
            if self.operation is None:ctx.director.release_canvas(self)
        elif active and ctx.director.canvas_owner is None and not ctx.director.tool.visible:
            drawing=next((e for e in active.enemies if getattr(e,'notebook_reveal',1)<1),None)
            if drawing is not None:
                p=drawing.notebook_reveal
                self.hand.tool=ArtistTool('pencil',drawing.x+math.sin(p*30)*15,drawing.rect.top+drawing.rect.height*p,True)
        if self.hand.tool.visible:ctx.player.look_target=(self.hand.tool.x,self.hand.tool.y)

    def draw(self, surface, camera, renderer):
        if self.operation=='support_tool':
            sx=camera.screen_x(self.gift_x);sy=self.gift_y+camera.offset_y
            rect=pygame.Rect(sx-55,sy-55,110,116)
            old=surface.get_clip();reveal=rect.copy()
            reveal.width=round(rect.width*min(1,self.timer/1.15))
            surface.set_clip(old.clip(reveal))
            draw_weapon_icon(surface,self.selected_weapon,self.page,(sx,sy),size=86)
            surface.set_clip(old)

    def draw_overlay(self, surface, camera, renderer):
        self.hand.draw(surface,camera,renderer)
        if self.letter_time>0:renderer.notebook.artist_note(surface,self.letter)
