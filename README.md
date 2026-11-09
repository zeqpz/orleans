# Voodoo on Bourbon

A New Orleans voodoo reskin of the Smukiez slot for [Stake Engine](https://stake-engine.com): Bourbon Street at
night, drawn in a Rick and Morty cartoon style. It starts from the newest engine.io build of
[zeqpz/slotsgame](https://github.com/zeqpz/slotsgame) (`main` b8a6f8d: front end, `engine/games/smukiez_v5` and math v5
with Bonus Boost). The old `beta/` and `live-pull/` folders were left out. **The math is unchanged:** a 7x7 board with
cluster pays, tumbles, Multis, FS / XFS scatters and the Bonus Boost mode, RTP 96.5-96.7%, max 10,000x.

## What changed

| Part | Now |
|---|---|
| Symbols | H1 Mardi Gras mask, H2 voodoo doll, H3 jazz trumpet, H4 candle skull, H5 gris-gris bag, H6 bayou gator, H7 beignets; L1-L10 fleur-de-lis, beads, crawfish, king cake, candle, skeleton key, doubloon, tarot card, bone, gas lamp; **M** voodoo potion; **BS = "FS"** (gold Mardi Gras lettering), **ES = "XFS"** (dripping voodoo-green lettering) |
| Character | **Doc**, an original top-hatted voodoo showman with a skull cane: 10 Blender clips (idle, enter, exit, anticipation, win, big win, lose, cane twirl, hat tip, conjure), 8 faces |
| Background | Bourbon Street as a static 4K plate, with live layers on top (`frontend/bgscene.js`): gas lamps that flicker, neon signs that buzz, a breathing moon, reflections that follow the lamps, 170 twinkling, slowly drifting stars, and three bands of drifting green and violet fog |
| Multi | No pop. The potion is hexed away: it burns from the rim inward along a voodoo-green edge, its spirit (a ghost of the XFS skull) rises, and green smoke and motes curl up (`hexIcon`). Its value condenses out of spirit wisps (`voodooReveal`); values evaporate rather than pop |
| Board | An opaque midnight-velvet backing with a fleur-de-lis damask, cut to the iron frame's exact opening (`tools/nola/board_back.py`). The board is sized so the whole frame and the HUD fit on screen |
| UI | Iron-lace frame and panels, Mardi Gras gold digits and headlines, a VOODOO ON BOURBON wordmark, Fredoka throughout |
| Music | A Bourbon Street brass band: bucket drums, sax, trombone, trumpet and sousaphone (Lyria 3 Pro). Base F, menu C, intro B-flat, bonus G minor, total B-flat; all five are seamless loops |
| Sounds | Every sound except the HUD buttons, 52 sets: bucket-drum spin, gourd rattle, streetcar bells, brass stings, sad trombone, bead and doubloon showers, a landing sound for each symbol's material, Doc's cane, hat and magic |

## Pipeline (all scripts in `tools/nola/` unless noted)

The OpenRouter key is read from `%USERPROFILE%\Documents\gamdevkey.txt`; scripts never print it. Run everything
with the art venv `ClaudeRoblox/smukiez-slot/.venv`.

1. **Art** (`orimg.py`, gpt-image-2.5): `gen_symbols.py` (H1 is the style anchor), `gen_ui.py gen`, `gen_faces.py`.
   Prompts are in `art/nola-src/prompts/` and `symbols.json`, and every call is logged in `art/nola-src/log.jsonl`.
2. **4K pass**: `upscale4k.py all` runs clean_alpha, then Real-ESRGAN x4 (anime model; alpha upscaled as its own grey
   image so the edges stay smooth), writing masters to `art/nola-src/4k/`: symbols at 4096², the background at
   3840x2160, the character at 2731x4096, and the UI at 4x. `gen_ui.py fit` sizes the UI from those masters.
3. **Background**: `bg_layers.py` aligns the lit painting to the lights-off plate and splits the lights into
   additive layers (hand-placed regions). `bg_export.py` writes the 4K plate, the layers, the fog bands and the star
   field (`frontend/assets/bg/`).
4. **Character layers**: `doc_layers.py` cuts out the cane and palm wisp, aligns and composites each face, then
   upscales to 4K (`art/nola-src/doc/`).
5. **Blender** (5.2.3; builds run live through the MCP or in the background):
   - `blender/symanim.py <ID>` builds each symbol's scene: idle, land, hit and multi clips on a bone-bent mesh plus
     effect sprites from `make_fx_sprites.py`. `blender/render_all.sh` renders all 20, 5 at a time (about 5 minutes).
   - `blender/doc.py` is Doc's rig (bones roll-aligned to the camera, the cane kept plumb, face swaps) and his 10
     clips.
   - QA: `qa_sym.py all` and `qa_char.py` check loop seams, the hand-back to the rest pose and alpha at the frame
     edge. All currently pass.
   - Packing: `tools/blender/pack_frames.py all` (14-unit frame) and `tools/blender/pack_chars.py doc`.
6. **Front end**: `reskin_frontend.py` applies every edit to `frontend/index.html` and `rules.js` as exact
   replacements, so a changed base fails loudly. Run it on a fresh base copy.
7. **Music**: `tools/music/lyria.py <cue> --takes 2`. Pick takes by key, copy them to `art/music-src/`, then
   `tools/music/build.py --wav ...` and paste the printed `MUSIC` table.
8. **Sounds**: `tools/sfx/nola.py all` (prompts in `nola_spec.py`), `tools/sfx/nola_textures.py` for the reels rattle
   and the doubloon rain, then `node tools/sfx/encode_new.js <.tools/pw/node_modules/playwright> %TEMP%/nola_sfx/written.txt`.

Browser tests (headless Playwright, with the mock RGS running): `node tools/nola/qa_browser.js` checks the live
layers, the character and the console; `node tools/nola/qa_replay.js` replays a round with a Multi and captures the hex-away.

## Run it locally

```
smukiez-slot/.venv/Scripts/python.exe frontend/mock_rgs.py
```
Open http://localhost:8755/index.html?sessionID=test&rgs_url=http://localhost:8755&lang=en&device=desktop. The
first run decompresses the books, which takes about 30 s. The Claude preview launch config is `orleans-game`.

## Notes

- Doc is an original character in the "voodoo showman" archetype: top hat, plum tailcoat, skull cane, green magic.
  He is not a copy of any film character.
- The upload set for Stake is unchanged: `math-sdk/games/smukiez_tag_run/library/publish_files/` plus the front end.
