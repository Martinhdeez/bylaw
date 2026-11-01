# VD4: how the cut is made (v2, silent)

The v2 cut has no music, no voice and no subtitles: the picture stands on its own, and Martín speeds it up himself. Type is sized for that (28 px floor on reading text, headlines 56–72 px) and key numbers hold at least 2 s at 1x.

## What is in the folder

| Path | What |
|---|---|
| `video/storyboard.md` | the eleven beats B0–B10, visual direction, HUD, cost method, figure ledger F1–F21, PENDING-DM5 |
| `video/figures.py` | recounts every figure from committed files (51 asserts) and writes `video/figures.json` and `video/scenes/assets/figures.js`; the scenes and the HUDs draw every number from them, nothing is typed |
| `video/scenes/` | HyperFrames project of the eight generated beats (B0, B2, B3, B4, B7, B8, B9, B10); `assets/gh-openai-cs-agents-demo.png` is the GitHub page captured with Playwright at 1920×1080 on 2026-11-01 |
| `video/roughcut/make.py` | writes the cut's `index.html`: beats in order, app footage in a 1500 px column, the HUD beside it |
| `video/build.sh` | `figures`, `beats`, `placeholders`, `rough`, `final` |
| `video/script.md`, `video/teleprompter.html`, `video/wordcount.py` | optional voice script for the same beats (455 words, 203 s), kept word for word in sync; `wordcount.py` checks it |
| `video/align.py` | only for a later voice: aligns a transcript to the script and writes beat timings |

## Rough cut v2 (now)

`video/out/rough-cut-v2.mp4`: 203 s, 1920×1080, 30 fps, no audio stream. Rebuild with `video/build.sh all` (recounts figures, renders the scenes, cuts the beats, scales the placeholders, renders the cut; about 3 minutes). `VZ3_MEDIA=<dir>` points at the prototype media if that worktree moved. `CLOSED=1 video/build.sh rough` is unchanged picture-wise (B8 changes through its scene variables, see the storyboard's PENDING-DM5).

App beats B1, B5 and B6 are still the VZ3 prototype recordings and stills (placeholders, no on-screen label in v2); the captures below replace them with no other change: drop them in `video/out/captures/` and re-run `video/build.sh rough`.

## Optional: a voice later

1. Read `video/teleprompter.html` (Space or → next beat, ← back, R restarts the beat timer, V switches B8). One continuous take, about 1 s of silence between beats.
2. Clean and transcribe locally, then align:

```sh
mkdir -p video/out/voice
ffmpeg -i ~/Downloads/voice.m4a -ac 1 -ar 48000 \
  -af "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5:LRA=11" \
  video/out/voice/voice.wav
cd video/out/voice && npx --yes hyperframes@0.8.226 transcribe voice.wav --model medium.en --language en --json > transcribe.log; cd -
python3 video/align.py video/out/voice/transcript.json            # add --closed for B8-closed
video/build.sh final                                               # CLOSED=1 for B8-closed
```

`final` re-times the beats to the voice (generated beats play 0.8–1.25x to fit) and mixes the voice alone to −14 LUFS, −1.5 dBTP into `video/out/final.mp4`. Still no music and no subtitles.

## Captures still needed from the final app

After VZ3 (real OpenAI UI with bylaw) merges and LV1 serves it. Start the app as its README says (UI on port 3311), browser window 1920×1080 (or 1440×900 scaled to 1080p, as the prototype), dark bylaw rail as shipped, cursor hidden unless clicking. Record at 1x, never sped up; hard cuts are labelled. Save as H.264 MP4 at 1920×1080, 30 fps, into `video/out/captures/` with these names:

| Id | Beat | Slot | Deep link | What must be visible | File |
|---|---|---|---|---|---|
| C1 | B1 | 30 s | `http://127.0.0.1:3311/?scenario=d1&guard=off&autoplay=1` | from the first customer message to the rail's "Conversation over. $280 in vouchers left the airline." and the bylaw card's "Would block" | `C1-d1-guard-off.mp4` |
| C2 | B5 | 28 s | `http://127.0.0.1:3311/?scenario=d1&guard=on&autoplay=1` | start at the second customer message (hard cut; turn 1 was shown in C1), then both "BLOCKED R-match-disrupted" cards, "Pay hotel, meal and transport vouchers on booking LL0EZ6 … BLOCKED D1:LL0EZ6/R-comp-booking-disrupted … $280 stayed with the airline", the bylaw card "Blocked", the agent's refusal | `C2-d1-guard-on.mp4` |
| C3 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=d4&guard=on&autoplay=1` | the cancel, then "BLOCKED D4:IR-D204/R-comp-no-self-cancel" | `C3-d4-guard-on.mp4` |
| C4 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=d2&guard=on&autoplay=1` | "BLOCKED D2:LL0EZ6/R-seat-own-conf"; seat stays 23A | `C4-d2-guard-on.mp4` |
| C5 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=legit&guard=on&autoplay=1` | the honest missed connection: issue_compensation allowed, case opened | `C5-legit-guard-on.mp4` |
| C6 | optional, B1 or B5 | 3–5 s | `http://127.0.0.1:3311/` with live typing on Muse (LV1) | one live typed turn, only if LV1 is merged; never claim it is live when it is a replay | `C6-live.mp4` (not wired; would replace part of B1) |
| C7 | if DM5 blocks D3 | ~6.7 s | the D3 replay once VZ3 lists it (button and scenario id from VZ3) | D3 blocked on the customer's own words | swap into B6 and update script B6 and B8 |

Long replays: the replay pacing caps gaps at 2.6 s, so D1 guard on runs about 43 s. Use `&speed=1` only. To land on the decisive moment, use the `step` parameter (`&step=N` jumps to event N) for the start of C2–C5 instead of trimming in the editor, or trim with `ffmpeg -ss START -t SLOT`. Any aspect works: the cut fits the capture into the 1500 px app column next to the HUD. The HUD stays tied to the event file the capture replays (C1 `dm3-d1-vouchers.json`, C2 `dm3-d1-vouchers-guard.json`, C3–C5 the matching `-guard.json` files).

Do not record a ratify click unless on a disposable copy of `ratified/` (ratify writes the store).


Note: the VZ3 prototype UI writes the name as "Bylaw" in its rail and card; the generated beats and HUDs use "bylaw". The app's wordmark is owned by the designer (`web/`), so the captures will show whatever VZ3 ships.
