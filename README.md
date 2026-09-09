# TURN THE PAGE — Beta 0.9.0

A hand-drawn notebook action game in which an Artist outside the page can redraw the player, lend tools, revise the arena, and react to how you fight.

This build contains five playable pages, 23 required encounters, 17 ordinary enemy types, six named bosses, a separate three-attempt Baby-Face interlude, and four behavior-selected final configurations. The 97 authored enemy spawns include the bosses and interlude. Main-route length is 62,350 world units.

TURN THE PAGE ties combat tools to each page: a katana for the Ronin, a Bowie knife, six-shooter and double barrel in the West, energy tools in orbit, and a field knife, suppressed pistol and breach shotgun for the Agent. Their reach, rhythm, recoil, reloads, grouping and projectile behavior differ. The inventory grows only as drawings are collected. The same silhouette appears in the pickup, the character's hands and the inventory.

Twelve Lost Sketches now teach persistent, optional techniques. Twenty handwritten school notes and all in-game text are in English. The two-burst school bell, quiet classroom babble, distinct boss rules and Baby-Face reversal remain part of the game.

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
| I — Ink of the Ronin | Katana, washi, bamboo, folded shrine | 4 / Moon Compass |
| II — Dust & Bad Decisions | Bowie knife, six-shooter, double barrel, ledger desert | 4 / Wanted Sketch, Railroad Stapler |
| III — A Very Wrong Future | Ion Edge, Orbit Pulse, Null Cannon, orbital chart | 5 / Orbital Mistake; Baby-Face is an interlude |
| IV — The Carbon Agent | Field knife, suppressed pistol, breach shotgun, carbon city | 5 / Head of Redaction |
| V — The Last Draft | Mixed enemy roles, revised platforms, schoolwork | 5 / Final Editor |

Baby-Face remains a staged comedy reversal: two authored one-hit defeats, the moustache and “It's more fair now.”, then a locked sword-drawing/pulling sequence and your winning strike. The real finale is on Page V.

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

115 tests pass, including an informed new-game-to-ending pilot through all five pages with only the two scripted Baby-Face defeats. This is automated progression verification; human completion time and first-play difficulty require playtesting.

Additional checks cover physical platforms, checkpoints, projectile returns, actual stagger, all four final layouts, save migration, shootable decoys, train rear vulnerability, orbital armour and protected audio channels. The Final Editor now locks and draws its aim before firing and converts leftover projectiles to harmless graphite when its clip opens. All six direct boss practice entries were opened and rendered using the runtime.

Gameplay-specific contracts check three-heart resets and lethal-hit ordering, all twelve sketch effects, era-specific weapon handling, preserved selected tools and magazine counts, and safe Artist staging. `python3 tools/render_gameplay_pass.py` renders the actual HUD, five page scenes and Back Pages for inspection in `work/gameplay_review/`.

Rendered QA images are written to `work/beta_review/`. Audio for all five pages is included. Existing CC0 recording/music provenance remains in `assets/audio/THIRD_PARTY.md`; the two new pages use the included deterministic notebook composer.

See `BETA_NOTLARI_TR.md` for Turkish release notes and focused playtest suggestions.

`python3 tools/render_identity_pass.py` creates controlled animation reviews in `work/identity_pass_review/`, using actual actor update/draw methods. Handwriting uses an installed matching font when available, with a system fallback; no system font is redistributed.
