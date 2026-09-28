# TURN THE PAGE — 0.20.0 · Living Pages

The five-page notebook now has three mandatory, physical route revisions:
draw a bridge and erase its margin in Page I, jump to tear a Wanted poster's
raised seam in Page II, and carry a fading star up the satellite ledges in
Page III. The Artist comments on each solution. The established page themes,
boss identities, save format and combat systems remain in place.

Twenty-eight location-specific graphite landmarks make the pages more distinct.
Melee weapons draw different live attack marks, and defeated figures linger as
rubbed-out sketches before disappearing. Two new route achievements bring the
total to 28. See [the 0.20 notes](BUYUK_GUNCELLEME_020_TR.md) for this release.

## Previous update

The page now changes visibly while you play. Each world has new, location-specific
notebook sketches; ground lines are less repetitive; held tools have distinct
shapes and firing or reload poses. Switching tools shows a brief larger drawing.
The Artist reacts to pickups, injuries, revisions and the first solved puzzle,
with optional replies. Page I has a physical three-mark drawing puzzle:
trace a ledge, jump onto it, then erase the blocking margin. See
[the 0.14 notes](CANLI_CIZIMLER_014_TR.md) for details.

Pages IV and V each have a new mandatory room and a playable approach to their boss. Five new enemy drawings follow their page themes, a two-shot Chalk Capsule gives Pages II and III a short-range crowd tool, and a death visibly breaks the player's drawing before the Artist redraws it. The sound mixer limits overlapping effects. See [the 0.13 notes](GENISLETILMIS_SURUM_013.md) for the previous release.

A hand-drawn notebook action game in which an Artist outside the page can redraw the player, lend tools, revise the arena, and react to how you fight.

This build contains five playable pages, 25 required encounters, 27 ordinary enemy types on the main route, six named bosses, a separate three-attempt Lost Expedition interlude, and four behavior-selected final configurations. The 105 authored enemy spawns include the bosses and interlude. Main-route length is 69,150 world units.

TURN THE PAGE ties combat tools to each page: a katana for the Ronin, a Bowie knife, six-shooter and double barrel in the West, energy tools in orbit, and a field knife, suppressed pistol and breach shotgun for the Agent. Their reach, rhythm, recoil, reloads, grouping and projectile behavior differ. The inventory grows only as drawings are collected. The same silhouette appears in the pickup, the character's hands and the inventory.

Twelve Lost Sketches teach persistent, optional techniques. Thirty handwritten school notes and all in-game text are in English. The two-burst school bell, quiet classroom babble, distinct boss rules and Lost Expedition reversal remain part of the game.

The latest combat pass adds three readable enemy variants: Gutter Lantern locks a falling ink column, Rake Cactus fires three ankle-height shots, and Ember Hound leaves a short-lived spark trail. Starting melee tools now have unique actions: katana launcher, same-target Bowie combo, piercing Ion Edge wave, wounded-target Field Knife execution, and a delayed redraw stroke.

All six named bosses escalate through distinct performances: the Moon Ronin's blade arc, four-poster crossfire, an express train return pass, expanding orbital shields and impact shards, the Head of Redaction's temporary floor cuts and marked attacks, and the Rejected Hero's response to your fighting style. The Lost Expedition keeps its signature sequence. Weapon sounds use page-specific cues, subtle variations and short mix ducking; enemy warnings and boss openings have dedicated cues.

The previous animation pass added planted running and clearer jump, landing, dash, and blade poses. Small marks on nearby enemies explain the Bowie's same-target chain and the Field Knife's wounded-target finish. Directional armour now reads a projectile's approach side, so a banked rear hit behaves correctly; blocked attacks no longer display successful cut marks. The title screen and native archive names identify the current revision.

Living Margins adds optional replies to the Artist, a harmless opening practice target, a shorter initial drawing, and pre-encounter retry landings throughout the campaign. Fold Duelists commit to two cuts, Margin Snipers freeze a visible sightline, and Split Lanterns draw two columns around a safe pocket. Fractional weapon damage is preserved; shotgun pellets no longer round up to one damage each. The Agent pistol and Redraw echoes have lower sustained damage. Named bosses require more openings, shorten later-phase recovery, and the Final Editor accepts one scratch per successful hit. There are 28 achievements across two pages.

## Run

Python 3.10+ and Pygame 2.5–2.x are required.

```sh
python3 -m pip install -r requirements.txt
python3 main.py
```

On macOS, double-click `run_paper_story.command`.

For direct practice against any of the six named bosses, double-click `bosslari_dene.command`. It uses a temporary save and skips the room's guard wave.

To try a particular page without changing your campaign save, double-click `bolum_testi.command`, or use:

```sh
python3 practice.py --page 4
python3 practice.py --page 4 --room scissor_office
python3 practice.py --page 5 --room final_margin_revision
python3 practice.py --page 2 --room marker_margin_trial --boss
```

Practice uses a temporary save. Ordinary play saves beside `main.py`; `PAPER_STORY_SAVE` may override its location. A completed save from the old three-page release continues at the new Agent page.

## Controls

| Action | Keyboard / mouse |
| --- | --- |
| Move | A/D or arrows |
| Jump | Space; release for a shorter jump |
| Attack | F, J or left click |
| Dash | Shift, K or right click |
| Drop through an elevated platform | S + Space / Down + jump |
| Perfect return | Dash into an incoming shot at the last moment |
| Reload | R |
| Change weapon | Q or mouse wheel; acquired tools only |
| Examine a Lost Sketch | E |
| Pause | Esc |
| Fullscreen | F11 |

The perfect return is active during the first 80 ms of a dash and returns at most one shot per dash. Normal dash protection remains available outside that timing window. Returned shots obey enemy armor and boss openings.

Common controllers, resizable windows, mouse aiming, audio sliders, achievements and Back Pages remain supported.

## Five pages

| Page | Identity | Encounters / named bosses |
| --- | --- | --- |
| I — Ink of the Ronin | Katana, washi, bamboo, folded shrine | 4 / Moon Ronin |
| II — Dust & Bad Decisions | Bowie knife, six-shooter, double barrel, ledger desert | 4 / Wanted Sketch, Railroad Stapler |
| III — A Very Wrong Future | Ion Edge, Orbit Pulse, Null Cannon, Meteor Chalk, orbital chart | 5 / Orbital Sentinel; Lost Expedition is an interlude |
| IV — The Carbon Agent | Field knife, suppressed pistol, breach shotgun, carbon city | 6 / Head of Redaction |
| V — The Last Draft | Redraw Pencil, mixed enemy roles, revised platforms, schoolwork | 6 / Rejected Hero |

The Lost Expedition remains a staged reversal: two authored one-hit defeats, an attempted pressure-seal repair, then a sword-drawing/pulling sequence and your winning strike. The real finale is on Page V.

The final encounter uses four attack scripts and different physical platform layouts: THE AGGRO MAN, BRAVEMAN, MIRROR and MIXED REVISION. Its selection considers recorded attacks, damage, actual retreat, time spent close to enemies, and boss clear times. The choice is remembered across retries.

## Three hearts and learned techniques

Health has a fixed maximum of three. A new arena starts at full health; a named boss also restores all three marks after its guard wave. Clearing an ordinary wave or entering another phase of the same boss does not heal. The three hearts remain visible between encounters. A lethal hit always completes its redraw; crossing a trigger cannot revive a defeated figure.

Lost Sketches preview their benefit before collection. They improve specific techniques: late edge jumps, air control, blade-finisher reach, dash recovery, sidearm handling and piercing, scattergun control, elastic ricochets and eraser reloads. Back Pages explains every learned effect and shows whether its weapon is available on this page. Existing collected sketches automatically receive their effects when an old save is loaded; retries never stack the bonuses.

## Physical notebook rules

A continuous dark top stroke supports your feet. Thin platforms can be jumped through from below; heavy vertical arena strokes still block passage. Erased intervals change both the drawing and collision. Arena landings are drawn before enemies engage. Traversal scenes queue until combat ends; extra landings and terrain revisions use cleared-wave breaks. A platform supporting the player is retained. The final boss still permits deliberate live revisions, shown with local pencil tips and previews. Lower margins catch missed floor edits and provide a route back up.

Hits now pause appropriate enemy attack timelines. Already committed contact attacks resist light-hit cancellation; heavy reactions can interrupt briefly. Pressure coordination covers the Agent and flying enemy states, so a third waiting enemy cannot begin another warning when two attacks are already being prepared or executed.

## Verification

```sh
python3 -m unittest discover -s tests -q
python3 tools/render_beta_review.py
```

Automated tests cover an informed new-game-to-ending pilot through all five pages, including the two scripted Lost Expedition defeats. This is automated progression verification; human completion time and first-play difficulty require playtesting.

Additional checks cover physical platforms, checkpoints, projectile returns, actual stagger, all four final layouts, save migration, shootable decoys, train rear vulnerability, orbital armour and protected audio channels. The Final Editor now locks and draws its aim before firing and converts leftover projectiles to harmless graphite when its clip opens. All six direct boss practice entries were opened and rendered using the runtime.

Gameplay-specific contracts check three-heart resets and lethal-hit ordering, all twelve sketch effects, era-specific weapon handling, preserved selected tools and magazine counts, and safe Artist staging. `python3 tools/render_gameplay_pass.py` renders the actual HUD, five page scenes and Back Pages for inspection in `work/gameplay_review/`.

Rendered QA images are written to `work/beta_review/`. Audio for all five pages is included. Existing CC0 recording/music provenance remains in `assets/audio/THIRD_PARTY.md`; the two new pages use the included deterministic notebook composer.

See `BETA_NOTLARI_TR.md` for Turkish release notes and focused playtest suggestions.

`python3 tools/render_identity_pass.py` creates controlled animation reviews in `work/identity_pass_review/`, using actual actor update/draw methods. Handwriting uses an installed matching font when available, with a system fallback; no system font is redistributed.
