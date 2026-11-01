#!/usr/bin/env bash
# VD4 build (v2, silent): generated beats, placeholder app footage, rough cut. Run from the repo root:
#   video/build.sh            # everything
#   video/build.sh figures    # recount every figure and rewrite figures.json / scenes/assets/figures.js
#   video/build.sh beats      # render the scenes and cut one MP4 per generated beat
#   video/build.sh rough      # silent rough cut, out/rough-cut-v2.mp4 (needs beats and placeholders)
#   video/build.sh final      # optional: same picture timed to a recorded voice, with the voice mixed (ASSEMBLY.md)
# Needs node 22+, ffmpeg. Outputs land in video/out/ (gitignored).
set -euo pipefail
cd "$(dirname "$0")"
OUT=out
VZ3=${VZ3_MEDIA:-/Users/apple/orca/projects/meta-hackathon/.claude/worktrees/agent-a7ba61357657be2b4/.scratch/after/vz3}
mkdir -p "$OUT/beats" "$OUT/placeholders"
enc=(-c:v libx264 -pix_fmt yuv420p -preset slow -crf 16 -r 30 -an -movflags +faststart)

figures() { python3 figures.py; }

beats() {
  figures
  (cd scenes && npx --yes hyperframes@0.8.226 render --quality delivery --output ../$OUT/scenes-all.mp4)
  # name start duration, as in scenes/index.html and storyboard.md
  while read -r name start dur; do
    ffmpeg -nostdin -v error -y -i "$OUT/scenes-all.mp4" -ss "$start" -t "$dur" "${enc[@]}" "$OUT/beats/$name.mp4"
  done <<'EOF'
B0-opening 0 7
B2-what-happened 7 12
B3-thesis 19 14
B4-how 33 30
B7-generality 63 16
B8-measured 79 18
B9-trace 97 20
B10-close 117 8
EOF
}

placeholders() {
  # VZ3 prototype recordings (1440x900, 25 fps), scaled to the 1500 px app column of the cut; 1x, never sped up.
  local fit="scale=1500:-2:flags=lanczos,fps=30"
  ffmpeg -nostdin -v error -y -ss 1.8 -i "$VZ3/d1-guard-off.mp4" -t 30 -vf "$fit" "${enc[@]}" "$OUT/placeholders/B1-guard-off.mp4"
  ffmpeg -nostdin -v error -y -ss 15.2 -i "$VZ3/d1-guard-on.mp4" -t 28 -vf "$fit" "${enc[@]}" "$OUT/placeholders/B5-guard-on.mp4"
  # B6: end frames of D4, D2 and the honest run, guard on (stills until VZ3 captures exist)
  local i=0
  for s in d4 d2 legit; do
    ffmpeg -nostdin -v error -y -loop 1 -i "$VZ3/1920-$s-guard-on-end.png" -t 6.667 -vf "scale=1500:-2:flags=lanczos,fps=30,format=yuv420p" "${enc[@]}" "$OUT/placeholders/B6-$i-$s.mp4"
    i=$((i + 1))
  done
}

stage() {
  mkdir -p roughcut/assets
  rm -f roughcut/assets/*.mp4
  cp "$OUT"/beats/*.mp4 "$OUT"/placeholders/*.mp4 roughcut/assets/
  if ls "$OUT"/captures/C*.mp4 >/dev/null 2>&1; then cp "$OUT"/captures/C*.mp4 roughcut/assets/; fi
  cp -R scenes/assets/fonts roughcut/assets/
}

rough() {
  stage
  python3 roughcut/make.py ${CLOSED:+--closed}
  (cd roughcut && npx --yes hyperframes@0.8.226 render --quality looks --output ../$OUT/rough-cut-v2.mp4)
}

# Optional, once a voice is recorded: VOICE (wav), TIMING (from align.py). CLOSED=1 uses the B8-closed text.
final() {
  local voice=${VOICE:-$OUT/voice/voice.wav} timing=${TIMING:-$OUT/voice/timing.json} dst=${FINAL:-$OUT/final.mp4}
  stage
  python3 roughcut/make.py --final --timing "$timing" ${CLOSED:+--closed}
  (cd roughcut && npx --yes hyperframes@0.8.226 render --quality delivery --output "../$OUT/final-picture.mp4")
  # voice only, to -14 LUFS, -1.5 dBTP
  ffmpeg -nostdin -v error -y -i "$OUT/final-picture.mp4" -i "$voice" -filter_complex \
    "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart "$dst"
  echo "wrote $dst"
}

case "${1:-all}" in
  figures) figures ;;
  beats) beats ;;
  placeholders) placeholders ;;
  rough) rough ;;
  final) final ;;
  all) beats; placeholders; rough ;;
esac
