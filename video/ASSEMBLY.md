# VD4: how the final cut is made

Everything runs from the repo root on macOS with node 22+, ffmpeg and python 3; no Muse calls, no keys. Heavy files live in `video/out/` (gitignored). Tested end to end on 2026-11-01 with a stand-in voice (macOS `say`): transcribe, align, final picture, mix (`video/out/voice-test/`).

## What is in the folder

| Path | What |
|---|---|
| `video/storyboard.md` | beats, timings, screens, figure ledger, PENDING-DM5 |
| `video/script.md`, `video/teleprompter.html` | the voice text; the teleprompter (open the file in a browser, offline) |
| `video/wordcount.py` | words per beat; checks the teleprompter matches the script |
| `video/figures.py` | recounts every figure from committed files |
| `video/scenes/` | HyperFrames project: the six generated beats (`compositions/*.html`) |
| `video/roughcut/make.py` | writes `video/roughcut/index.html`: the rough cut, or the final picture |
| `video/align.py` | aligns the voice transcript to the beats |
| `video/build.sh` | `beats`, `placeholders`, `rough`, `final` |
| `video/musicgen.py` | how the music bed was made |

## 1. Recording the voice (Martín)

1. Open `video/teleprompter.html`. Space or → next beat, ← back, R restarts the beat timer, V switches B8 (open / closed). The timer turns amber 3 s before the beat's target and red after it.
2. Quiet room, phone or USB mic 15–20 cm away, slightly off-axis. Record **one continuous take** (WAV or M4A, 48 kHz if possible). Leave about 1 s of silence between beats; do not restart a beat in the middle: if a beat goes wrong, stop, wait 2 s, and read that whole beat again. Keep the best whole take of each beat.
3. Read B8-open unless DM5 has merged with D3 blocked (then B8-closed; tell me which).
4. Target: 180 s or less in total. The rough cut (`video/out/rough-cut.mp4`) shows each beat's slot and the subtitles at the planned pace; rehearse against it.
5. Send the file. Name it `voice.<ext>`.

## 2. From the voice file to timings

```sh
mkdir -p video/out/voice
ffmpeg -i ~/Downloads/voice.m4a -ac 1 -ar 48000 \
  -af "highpass=f=80,afftdn=nf=-25,acompressor=threshold=-20dB:ratio=3:attack=5:release=120,loudnorm=I=-16:TP=-1.5:LRA=11" \
  video/out/voice/voice.wav
```

If a beat was read twice, cut the bad take out first (Audacity, or `ffmpeg -ss/-to` plus `concat`), so the file holds each beat once and in order.

Transcribe locally (whisper.cpp through the HyperFrames CLI, free, nothing leaves the machine). `medium.en` handles a non-native accent better than the default:

```sh
cd video/out/voice && npx --yes hyperframes@0.8.226 transcribe voice.wav --model medium.en --language en --json > transcribe.log; cd -
python3 video/align.py video/out/voice/transcript.json            # add --closed for B8-closed
```

`align.py` matches the script to the transcript word by word (difflib, so misheard words do not break it), then prints each beat's slot: it starts 0.25 s before the beat's first word and runs to the next beat's start; the end card keeps 2.5 s after the last word. It writes `video/out/voice/timing.json` and warns if the total is over 180 s. If it is over: shorten the silences between beats in the voice file, or re-read the longest beat; do not speed the voice up.

## 3. Picture follows the voice

```sh
video/build.sh final            # CLOSED=1 video/build.sh final for B8-closed
```

What it does:

1. Copies the generated beats, the placeholders and every real capture in `video/out/captures/` into `video/roughcut/assets/`. A capture replaces its placeholder when present (names in section 5); missing ones are listed.
2. `make.py --final --timing ...` builds the picture on the voice's slots:
   - **generated beats** play at `planned / slot` speed, clamped to 0.8–1.25x, so their reveals stay on the words. A beat whose voice is off by more than 25 % should be re-timed in its scene file instead (the anchor times are the numbers in its `tl.fromTo(..., t)` calls; the comments in `video/scenes/index.html` give the beat order), then `video/build.sh beats`;
   - **app captures** play at 1x from their first frame for the slot length; trim each capture so it starts at the right moment and lasts at least its slot (B6 splits its slot evenly over the three captures);
   - subtitles are burned only on the app-capture beats (the generated beats carry their words on screen) and timed from the transcript; `video/out/final.srt` gets every line as a caption sidecar to upload with the video.
3. Renders the picture (`video/out/final-picture.mp4`, HyperFrames, delivery quality).
4. Mixes with ffmpeg: the voice at full level; the bed at about −10 dB, ducked a further ~12 dB by a sidechain compressor keyed on the voice (threshold 0.02, ratio 8, attack 20 ms, release 400 ms), faded out over the last 3 s; then `loudnorm` to −14 LUFS integrated, −1.5 dBTP. Output: `video/out/final.mp4`.

Check before uploading:

```sh
ffprobe -v error -show_entries format=duration -of csv=p=0 video/out/final.mp4      # <= 180
ffmpeg -i video/out/final.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E 'I:|Peak:' | tail -2
python3 video/figures.py                                                             # all figures still match
```

Then watch it once with sound. Nobody has listened to the mix yet: levels were measured, not heard.

## 4. Music bed

`video/out/music/bed.wav`, 181 s, generated locally with MusicGen (`facebook/musicgen-small`, the media-use engine's local recipe) because HyperFrames/HeyGen was not signed in. No copyrighted material; note that the musicgen-small weights are CC-BY-NC 4.0, fine for a non-commercial hackathon entry. Prompt: "calm minimal ambient electronic underscore, soft warm synth pads, gentle muted plucked arpeggio, steady slow pulse 92 bpm, confident and clear, no drums, no vocals, background music for a narrated tech demo". It is a 28 s seed crossfade-looped to length; −16 LUFS, −1 dBTP. Measured, not heard: listen to it before the final mix.

To regenerate (about 3 min, installs torch into a throwaway venv, not the project):

```sh
uv venv /tmp/bgm && uv pip install --python /tmp/bgm/bin/python torch transformers soundfile numpy
/tmp/bgm/bin/python video/musicgen.py "<prompt>" video/out/music/bed.wav 181
```

Better option if wanted: sign in (`npx hyperframes auth login`, free) and pick a track from HeyGen's music catalog through `/media-use`; replace `bed.wav` and re-run `video/build.sh final`.

## 5. Captures still needed from the final app

After VZ3 (real OpenAI UI with Bylaw) merges and LV1 serves it. Start the app as its README says (UI on port 3311), browser window 1920×1080 (or 1440×900 scaled to 1080p, as the prototype), dark Bylaw rail as shipped, cursor hidden unless clicking. Record at 1x, never sped up; hard cuts are labelled. Save as H.264 MP4 at 1920×1080, 30 fps, into `video/out/captures/` with these names:

| Id | Beat | Slot | Deep link | What must be visible | File |
|---|---|---|---|---|---|
| C1 | B3 | 30 s | `http://127.0.0.1:3311/?scenario=d1&guard=off&autoplay=1` | from the first customer message to the rail's "Conversation over. $280 in vouchers left the airline." and the Bylaw card's "Would block" | `C1-d1-guard-off.mp4` |
| C2 | B5 | 28 s | `http://127.0.0.1:3311/?scenario=d1&guard=on&autoplay=1` | start at the second customer message (hard cut; turn 1 was shown in C1), then both "BLOCKED R-match-disrupted" cards, "Pay hotel, meal and transport vouchers on booking LL0EZ6 … BLOCKED D1:LL0EZ6/R-comp-booking-disrupted … $280 stayed with the airline", the Bylaw card "Blocked", the agent's refusal | `C2-d1-guard-on.mp4` |
| C3 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=d4&guard=on&autoplay=1` | the cancel, then "BLOCKED D4:IR-D204/R-comp-no-self-cancel" | `C3-d4-guard-on.mp4` |
| C4 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=d2&guard=on&autoplay=1` | "BLOCKED D2:LL0EZ6/R-seat-own-conf"; seat stays 23A | `C4-d2-guard-on.mp4` |
| C5 | B6 | ~6.7 s | `http://127.0.0.1:3311/?scenario=legit&guard=on&autoplay=1` | the honest missed connection: issue_compensation allowed, case opened | `C5-legit-guard-on.mp4` |
| C6 | optional, B3 or B5 | 3–5 s | `http://127.0.0.1:3311/` with live typing on Muse (LV1) | one live typed turn, only if LV1 is merged; never claim it is live when it is a replay | `C6-live.mp4` (not wired; would replace part of B3) |
| C7 | if DM5 blocks D3 | ~6.7 s | the D3 replay once VZ3 lists it (button and scenario id from VZ3) | D3 blocked on the customer's own words | swap into B6 and update script B6 and B8 |

Long replays: the replay pacing caps gaps at 2.6 s, so D1 guard on runs about 43 s. Use `&speed=1` only. To land on the decisive moment, use the `step` parameter (`&step=N` jumps to event N) for the start of C2–C5 instead of trimming in the editor, or trim with `ffmpeg -ss START -t SLOT`. Convert a 1440×900 recording the same way as the placeholders: `scale=1728:1080,pad=1920:1080:96:0:color=0x0f1122,fps=30`.

Do not record a ratify click unless on a disposable copy of `ratified/` (ratify writes the store).

## 6. Rough cut (now)

`video/out/rough-cut.mp4` (180 s): generated beats, the VZ3 prototype recordings and stills as placeholders for B3, B5 and B6 (amber label "PLACEHOLDER"), a beat label on every beat, the script as subtitles at the planned pace, the music bed at a rehearsal level. Rebuild with `video/build.sh all` (renders the scenes, cuts the beats, makes the placeholders, renders the rough cut; about 3 minutes). `VZ3_MEDIA=<dir>` points at the prototype media if the worktree moved.
