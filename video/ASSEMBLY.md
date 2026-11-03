# VD4: how the cut is made (v3, silent)

The cut has no music, no voice and no subtitles: the picture stands on its own, and Martín speeds it up himself. Type is sized for that (28 px floor on reading text, headlines 56–72 px) and key numbers hold at least 2 s at 1x.

## What is in the folder

| Path | What |
|---|---|
| `video/storyboard.md` | the twelve beats B0–B10 with B5b, visual direction, HUD, cost method, figure ledger F1–F22 |
| `video/figures.py` | recounts every figure from committed files (59 asserts) and writes `video/figures.json` and `video/scenes/assets/figures.js`; the scenes and the HUDs draw every number from them, nothing is typed |
| `video/vd4-live-d1.usage.json` | the API's own token counter (`GET /api/live/status` `tokens_used`) before and after the live session of B5b; the session export (`reports/live/vd4-live-d1.json`) carries no usage |
| `video/scenes/` | HyperFrames project of the generated beats (B0, B2, B3, B4, B7, B8, B9, B10) |
| `video/capture/` | `capture.js` (replays C1–C5), `live.js` (the live session C6), `trim.py` (cuts the raw captures into their slots) |
| `video/roughcut/make.py` | writes the cut's `index.html`: beats in order, app footage in a 1500 px column, the HUD beside it |
| `video/build.sh` | `figures`, `beats`, `placeholders`, `rough`, `silent`, `final` |
| `video/script.md`, `video/teleprompter.html`, `video/wordcount.py` | optional voice script for the same beats (474 words, 226 s), kept word for word in sync; `wordcount.py` checks it |
| `video/align.py` | only for a later voice: aligns a transcript to the script and writes beat timings |

## Final silent cut (now)

`video/out/final-silent.mp4`: 226 s, 1920×1080, 30 fps, H.264, no audio stream. Every app beat is a real capture of the merged app (bylaw/build at 1ffca89). The only slot still holding a fallback is C8, the user's Ratify click (below).

Rebuild: `video/build.sh beats && video/build.sh placeholders && video/build.sh silent` (about 4 minutes). `video/build.sh rough` gives a quicker look-quality render, `out/rough-cut.mp4`.

## Captures (recorded 2026-11-03)

Recorded with Playwright (`video/capture/`) at 1920×1080 from the production build of `targets/cs_demo/ui` (`BYLAW_API_URL` set at build time, `npm start`) against `uv run uvicorn bylaw.api:app`. Raw WebM in `video/out/raw/`, cut by `python3 video/capture/trim.py video` into `video/out/captures/` (H.264, 30 fps, 1x, never sped up). Every visible "bylaw" is lower case.

| Id | Beat | Slot | Deep link (UI on its port) | Event file of the HUD | File |
|---|---|---|---|---|---|
| C1 | B1 | 30 s | `/?scenario=d1&guard=off&autoplay=1&tour=0` | `dm3-d1-vouchers.json` | `C1-d1-guard-off.mp4` (whole replay, last frame held 3.6 s) |
| C2 | B5 | 28 s | `/?scenario=d1&guard=on&autoplay=1&tour=0` | `dm3-d1-vouchers-guard.json` | `C2-d1-guard-on.mp4` (last 28 s) |
| C3 | B6 | 6.7 s | `/?scenario=d4&guard=on&autoplay=1&tour=0` | `dm3-d4-cancel-then-comp-guard.json` | `C3-d4-guard-on.mp4` |
| C4 | B6 | 6.7 s | `/?scenario=d2&guard=on&autoplay=1&tour=0` | `dm3-d2-other-seat-guard.json` | `C4-d2-guard-on.mp4` |
| C5 | B6 | 6.7 s | `/?scenario=legit&guard=on&autoplay=1&tour=0` | `dm3-l-disrupted-comp-guard.json` | `C5-legit-guard-on.mp4` |
| C6 | B5b | 7 s + 10 s | `/?tour=0`, the two turns of `scripts/live/dm3-d1-vouchers.json` typed into the composer, guard on, live on `muse-spark-1.3` | `reports/live/vd4-live-d1.json` | `C6a-live-d1-typing.mp4` (typing and sending turn 2), hard cut over 23.2 s of waiting (said in the HUD), `C6b-live-d1-block.mp4` (the answer lands, `issue_compensation` blocked) |
| C8 | B4 | 6 s | the ratify setup below | none | `C8-user-ratifies.mp4`, **to record** |

C7 (D3 closed) is not a capture: the cs_demo UI has no D3 scenario. B8 shows the guarded D3 run from its event file instead (storyboard F10).

The live session (C6) was one take: session 93eff1516e74, 2026-11-03 19:10:56 UTC, 20,728 Muse tokens. bylaw denied `issue_compensation` at 41.043 s by `D1:LL0EZ6/R-comp-booking-disrupted`; no vouchers were paid. To redo it: start the API with live on (it needs the Muse key, which `bylaw.llm` loads itself), build and start the UI, then `PW=<ui>/node_modules/playwright-core node video/capture/live.js video/out/raw <ui url> <api url> scripts/live/dm3-d1-vouchers.json`; copy `C6-export.json` to `reports/live/vd4-live-d1.json` and the counters in `C6-meta.json` to `video/vd4-live-d1.usage.json`, then rerun `figures.py`.

## C8: the user ratifies, on camera

The rules in `ratified/csdemo.json` were ratified by agents calling `bylaw.ratified.ratify`, not by a person, and the video says so (B4's store frame). C8 is the place for Martín's own click. It is never faked: until C8 exists, the 6 s slot holds B4's store frame with that honest note.

The setup runs the web app (`web/`, served by the API) against a **temporary copy** of the store, so the click never touches `ratified/`:

- Store: `.scratch/vd4-ratify/csdemo.json` in the VD4 worktree (gitignored), a copy of `ratified/csdemo.json` without A6, so A6 shows its Ratify button. `csdemo.pristine.json` beside it is the same copy, for a reset.
- Server: `uvicorn bylaw.api:app` on 127.0.0.1:8766 with `BYLAW_RATIFIED_DIR=<worktree>/.scratch/vd4-ratify` and `BYLAW_LIVE=0` (no Muse calls).
- Deep link: **http://127.0.0.1:8766/#/csdemo/holes/D1%3ALL0EZ6/amendment** ("Amendment A6 for H6", with "Ratify this amendment" and its Ratify button on the right).

Steps:

1. Open the deep link in a browser window of 1920×1080 (or full screen on a 1080p display). Start the screen recorder (QuickTime: File → New Screen Recording, or `Cmd+Shift+5`), whole screen.
2. Hold 1 s on the amendment, move the pointer to **Ratify**, click it, and hold 3 s on the result.
3. Stop the recording. Trim it to 6 s around the click and save it as `video/out/captures/C8-user-ratifies.mp4` (H.264, 1920×1080, 30 fps; `ffmpeg -ss START -i in.mov -t 6 -vf fps=30 -c:v libx264 -pix_fmt yuv420p -crf 16 -an video/out/captures/C8-user-ratifies.mp4`).
4. `video/build.sh silent` puts it in the slot.
5. To take it again, reset the store: `cp .scratch/vd4-ratify/csdemo.pristine.json .scratch/vd4-ratify/csdemo.json` and reload the page.

The click writes A6 with the click's own `ratified_at` into the temporary store only. If the click is used in the video, the B4 store frame that follows it still shows the committed store's entry (2026-10-29, ratified by the DM2 builder agent); both are true.

To start the setup again after a reboot, from the VD4 worktree: `BYLAW_LIVE=0 BYLAW_RATIFIED_DIR=$PWD/.scratch/vd4-ratify uv run uvicorn bylaw.api:app --host 127.0.0.1 --port 8766` (with `web/dist` built).

## Optional: a voice later

1. Read `video/teleprompter.html` (Space or → next beat, ← back, R restarts the beat timer). One continuous take, about 1 s of silence between beats.
2. Clean and transcribe locally, then align:

```sh
mkdir -p video/out/voice
ffmpeg -i ~/Downloads/voice.m4a -ac 1 -ar 48000 \
  -af "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5:LRA=11" \
  video/out/voice/voice.wav
cd video/out/voice && npx --yes hyperframes@0.8.226 transcribe voice.wav --model medium.en --language en --json > transcribe.log; cd -
python3 video/align.py video/out/voice/transcript.json
video/build.sh final
```

`final` re-times the beats to the voice (generated beats play 0.8–1.25x to fit) and mixes the voice alone to −14 LUFS, −1.5 dBTP into `video/out/final.mp4`. Still no music and no subtitles.
