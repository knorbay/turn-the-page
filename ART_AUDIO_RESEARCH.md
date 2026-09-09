# Turn the Page — Art & Audio Research / Production Direction

## Decision

The shipping build will not use generative raster character art. Three early
generated concept sheets were rejected because their uniform cross-hatching,
detail density and polished imperfection made them look synthetic. They are
stored only under `work/rejected_ai_concepts/`, which is excluded from release
packages.

The game art is drawn at runtime from a restricted vocabulary of deterministic
marks. The target is not “beautiful sketch art.” The target is a drawing whose
material, construction mistake and attack function can be read immediately.

The initial procedural score remains as a fallback and for small notebook
cues. The shipping route now bundles a reviewed CC0 calm/action pair for each
world plus real pencil, eraser, and blade-swing recordings. Exact provenance
is kept in `assets/audio/THIRD_PARTY.md`.

## Research set and what we take from it

### Creator / drawing relationship

- [Animator vs. Animation — Alan Becker](https://www.youtube.com/watch?v=npTC6b5-yvM): the creator's cursor and tools are physical actors. The relationship remains understandable without dialogue. **Turn the Page rule:** the pencil endpoint must touch the line currently being created, and the line must change gameplay state.
- [Crayon Physics Deluxe — official site](https://www.crayonphysics.com/): a drawn shape becomes a physical object rather than visual decoration. **Rule:** notebook marks are platforms, cover, gates, hazards or tools.
- [Draw a Stickman: EPIC — Nintendo](https://www.nintendo.com/US/store/products/draw-a-stickman-epic-switch/): different pencils have different verbs. **Rule:** weapon identity comes from the drawing tool and page, not a permanent generic arsenal.
- [West of Loathing developer interview](https://www.gamedeveloper.com/business/road-to-the-igf-asymmetric-s-i-west-of-loathing-i-): extremely simple stick figures can carry visual depth and humor through pose. **Rule:** readable pose and timing beat rendered detail.

### Real notebook evidence

- [Blue Hill Academy trigonometry notebook, 1850–1900](https://digitalmaine.com/blue_hill_documents/23/) is listed as No Copyright–United States. It shows that a working notebook accumulates calculation, correction and variable spacing rather than evenly distributed “vintage texture.”
- [Joseph Worley's 1842 exercise book — Ohio Memory](https://ohiomemory.ohiohistory.org/archives/2837) mixes arithmetic, geometry and physics on the same page. **Rule:** diagrams are local clusters with a reason; background marks do not cover every empty area.

These scans are research references only. They are not copied into the build.

### Music and sound

- [Untitled Goose Game — Panic Podcast transcript](https://podcast.panic.com/episodes/s01e01/transcript/): high- and low-energy performances are split into short compatible fragments, allowing the music to answer play within about a second. **Turn the Page rule:** calm and combat arrangements share tempo, key and loop length and run in phase; pressure crossfades them.
- [Composing for Chicory — Lena Raine](https://medium.com/@kuraine/composing-for-chicory-motifs-memories-9d7351555694): two character motifs are established early and gain meaning through context and instrumentation. **Rule:** Artist and Stickman each have a small interval motif; page identity re-orchestrates them instead of replacing the score with unrelated tracks.
- [Neverhood Songs — Terry Scott Taylor](https://terrytaylor.bandcamp.com/album/neverhood-songs-deluxe): the official description frames the music as another shape-shifting character commenting on scenes. **Rule:** comic audio should comment through timing and timbre, not comedy stingers after every joke.
- [World of Goo soundtrack notes — Kyle Gabler](https://kylegabler.com/WorldOfGooSoundtrack): live warmth was added to computer instruments; chair and cardboard-box percussion became part of the score. **Rule:** desk taps, paper tears, pencil scratches and cap clicks are percussion, not a separate decorative SFX layer.
- [OpenGameArt](https://opengameart.org/) CC0 music and recording packs were
  auditioned as a legal, redistributable production source. Six world tracks
  and three tactile recordings were selected; the project carries its own
  source ledger rather than relying on a web page remaining unchanged.

## Runtime line rules

1. One enemy uses at most three dominant mark types.
2. A material is anatomy, not surface decoration.
3. Construction ghosts are sparse and belong to a rejected attempt.
4. Red correction marks identify a real mistake or attack lane.
5. Perfect circles/rectangles appear only when a compass/ruler is part of the creature.
6. Wobble is deterministic. Shapes do not shimmer randomly every frame.
7. Telegraph red is never used as ordinary shading.
8. Collision remains stable even when anatomy is deliberately wrong.
9. Small-scale silhouette is checked before facial detail.
10. No enemy is produced by recoloring a common body skeleton.

## Canonical enemy drawing recipes

| Enemy | Construction | Material limit | Readable combat promise |
| --- | --- | --- | --- |
| Wax crawler | Five unequal pressure rings, open jaw, two antenna strokes | Wax crayon + graphite | Low horizontal bite/lunge |
| Compass hopper | Two compass legs, three pivots, exposed spring | Ruler/compass graphite + blue construction pencil | Vertical launch/drop |
| Ink spitter | Transparent squat bottle, moving ink line, four wire legs, nib | Glass outline + violet ink + metal nib | Ranged ballistic shot |
| Ruler guard | Ruler is shield/body; pencil spear lives on open side | Wood pencil + graphite ticks | Front blocks; back is vulnerable |
| Paper wasp | Two torn wings, one folded body, two staples | Paper + graphite + staples | Air pressure and committed dive |
| Eraser brute | One worn pink block with soft-side annotation | Eraser pigment + rubbed graphite dust | Removes floor; punish recovery |
| Crumpled one | Dense paper ball with only two eye holes | Compressed graphite/paper | Horizontal charge; wall stun |
| Doodle turret | Boxed note base, ink core, line-of-fire annotation | Graphite box + ink | Controls standing space |
| Baby-Face Giant | Wrong torso polygon, five hatch lines, one single-stroke arm, one ruler-joint arm, boot plus peg leg, tiny baby head | Graphite + red repair stitches + paper | Huge stomp/sweep; moustache changes no stats |
| Ink Samurai | Wide sleeves, split hakama, top-knot, one horizontal katana | Graphite + warm paper + red hilt | Closes distance, sheath telegraph, long draw-cut |
| Origami Drone | Four folded planes, scan eye, two vibrating rotors | Pale paper + graphite + one red sensor | Aimed needle, then overheats and droops into blade range |
| Goblin Scribble | Huge ears, grin, squat limbs, stolen crooked club | Graphite + dirty paper + brown pencil | Snicker telegraph into long pounce |
| Ink Outlaw | Hat wider than torso, poncho trapezoid, tiny sidearm | Graphite + sand paper + red neckerchief | Keeps duel distance and announces quickdraw |
| Tumbleweed Thing | Seven rotating dry loops around two tiny eyes | Brown pencil + graphite | Rustle telegraph into committed roll |
| Star Scout | Elliptical saucer, crossing orbital rings, lock eye | Blue-grey pencil + graphite + red sensor | Floats, locks, fires from a changing lane |
| Moon Bot | Helmet dome, box chassis, asymmetric ram arm | Blue-grey pencil + graphite + red sensor | Closes space, rams, and fires through arena-gate cheese |
| Lantern Yokai | Ribbed paper lamp, hanging flame, single handle stroke | Warm paper + graphite + vermilion | Fires a three-flame fan, then sinks into blade range |
| Cactus Gunner | Rooted trunk, mismatched arms, cowboy hat, visible needles | Green pencil + graphite | Announces a three-needle fan that reaches arena corners |
| Comet Hound | Low quadruped, diamond head, long blue star tail | Blue pencil + graphite + red eye | Telegraphs and commits to a full horizontal lane rush |

## Five boss rules

| Boss | World read | Counter-play rule |
| --- | --- | --- |
| Moon Compass | Red moon behind a giant compass needle | Dodge the full arc; only the stuck needle takes two hits per opening |
| Wanted Sketch | Rejected construction figure wearing a badly added cowboy hat | Read charge, ink rain, or slam; attack only while its lines unravel |
| Railroad Stapler | Stapler converted into a tiny locomotive with wheels/chimney | Escape the long snap; punish the mechanical reload |
| Orbital Mistake | Crossed-out anatomy trapped inside incompatible orbit rings | Survive phase chains; erase two loose marks per opening |
| Final Editor | Walking proof sheet, binder clip, red margin and visible scenario tool | Read the chosen scenario; attack only when the binder opens |

## Page production identities

### Page 1 — Ink of the Ronin

- Pale fibrous washi sheet with an oversized red sun, bamboo clusters, torii marks, and intentional empty breaths.
- Platforms: brush roads, torn temple steps, ruler-straight drone field, moon-gate underline.
- Cast: ronin player; samurai, lantern and ruler core; origami drone/goblin violate the era; Moon Compass closes the page.
- Palette: graphite, warm paper, muted bamboo green, one vermilion sun/hilt accent.
- Music: 76 BPM; dry plucks and restrained wood/desk pulse.

### Page 2 — Dust & Bad Decisions

- Warm ledger sheet becomes a desert horizon with cacti, dry riverbed, canyon steps, railroad ties, and midnight-train finish.
- Platforms: torn riverbank, long annotated dust road, canyon paper scraps, ruler-straight rail line.
- Cast: cowboy-hat player; outlaw/tumbleweed/cactus core; paper wasp and crumpled paper break the western logic; Wanted Sketch and Railroad Stapler provide different boss rules.
- Palette: graphite, ochre ledger paper, dry brown, one faded red bandanna/telegraph accent.
- Music: 108 BPM; clipped scratch percussion and train-like desk pulse, phase-aligned with calm travel.

### Page 3 — A Very Wrong Future

- Pale engineering chart replaces the horizon with orbital arcs, constellations, coordinates, and a continuous station deck.
- Platforms: ghost-line deck, satellite construction scraps, equation-box moon surface, comet marks.
- Cast: astronaut player; Star Scout/Moon Bot/Comet Hound core; clone, turret, eraser, recycled drone and inexplicable goblin reveal the Artist's bad research; Orbital Mistake, the uncounted Baby-Face interlude, and Final Editor close the arc.
- Palette: graphite, cold blue-grey, correction red; gold appears only for Excalibur.
- Music: 68 BPM; fragile toy motif over eraser rub and distant desk weight.
- Boss layer: innocent three-note music-box phrase against low stomp impacts.

## Motif system

- **Artist motif:** root → fifth → minor third. Three deliberate marks.
- **Stickman motif:** root → second → fifth → fourth. A phrase that moves away and returns.
- Both motifs appear on every canonical page in different materials.
- Calm/action layers share 16 beats, page BPM and root, so combat pressure can crossfade without a new song starting.
- Boss music preserves the Artist motif while a clipped proofing phrase and desk impacts occupy the foreground.
- Excalibur uses a separate four-note rising reveal only once; it is not looped.

## Adaptive score mapping

| Game observation | Audio response |
| --- | --- |
| Traversal / quiet page | Ambience + low-energy motif |
| Arena border closes | High layer fades in at minimum 44% intensity |
| More live roles | Bass and desk-percussion layer rises |
| Telegraph/committed attacks | Intensity rises further |
| Low player health | Small additional rise; no panic siren |
| Empty wave gap | Action layer falls to a low breath |
| Boss entrance | Named-boss proof/impact arrangement restarts deliberately |
| Arena clear | Action layer fades; calm page remains |
| Page turn | All layers duck, paper turn speaks, next page settles before ambience returns |

## Foley construction recipes

Every cue uses a short combination of onset, material body and decay.

| Cue | Onset | Body | Tail |
| --- | --- | --- | --- |
| Pencil draw | Graphite click | Pulsed high scratch | Short wooden pitch |
| Redraw | Five separate scratch gestures | Rising graphite pitch | Final body stroke |
| Eraser | Soft contact | Low filtered rubbing | Paper dust falloff |
| Page turn | Air/noise swell | Paper friction | Edge snap |
| Marker | Cap-like impact | Wet odd-harmonic tone | Short rub |
| Damage | Paper crack | Low body hit | Minimal tail for readability |
| Giant step | Sharp paper break | 32–42 Hz desk/body impact | Dust/noise decay |
| Hero reveal | Four rising toy partials | Low desk impact at midpoint | Bell decay |

## Implemented

- Generated visual concepts removed from the release path.
- `sketch_marks.py`: deterministic rough circles, wax rings, pivots, staples,
  torn paper and correction marks.
- Shipping samurai, drone, goblin, outlaw, tumbleweed, wasp, scout, moon-bot,
  and Baby-Face drawings use separate silhouettes and restricted recipes.
- `audio_composer.py`: original fallback motifs, ambience and 32 semantic
  notebook cues, including separate block, arena-lock, arena-clear,
  boss-reveal and heart-redraw feedback.
- `assets/audio/music/`: selected CC0 Japanese, western, and science-fiction
  calm/action pairs used by the three shipping worlds.
- `assets/audio/recorded/`: CC0 pencil, eraser, and blade-swing recordings.
- `assets/audio/`: pre-rendered canonical WAV bank from that same source; the
  measured headless startup dropped from about 4.17 seconds to 0.17 seconds.
- `audio.py`: synchronized calm/action channels, boss arrangement and
  pressure-driven mixing.
- `CombatArena` sends live enemy count, telegraph pressure and player health to
  the score.
- `tools/render_audio_qa.py` exports the exact runtime synthesis for review.

## Production boundary

The procedural Foley is now authored and identifiable, but a final commercial
mix should replace selected paper, pencil and eraser bodies with recordings
captured from the actual notebook, pencil, eraser, ruler and desk chosen for
the game. The onset timing and runtime layer architecture can remain unchanged.
