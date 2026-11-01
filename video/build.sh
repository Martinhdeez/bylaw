#!/usr/bin/env bash
# VD4 build: generated beats, placeholder app footage, rough cut. Run from the repo root:
#   video/build.sh            # everything
#   video/build.sh beats      # render the scenes and cut one MP4 per generated beat
#   video/build.sh rough      # rough cut only (needs beats, placeholders and the music bed)
#   video/build.sh final      # final cut from the voice (see ASSEMBLY.md)
# Needs node 22+, ffmpeg. Outputs land in video/out/ (gitignored).
set -euo pipefail
cd "$(dirname "$0")"
OUT=out
VZ3=${VZ3_MEDIA:-/Users/apple/orca/projects/meta-hackathon/.claude/worktrees/agent-a7ba61357657be2b4/.scratch/after/vz3}
BG=0x0f1122
mkdir -p "$OUT/beats" "$OUT/placeholders" "$OUT/music"
enc=(-c:v libx264 -pix_fmt yuv420p -preset slow -crf 16 -r 30 -an -movflags +faststart)

beats() {
  (cd scenes && npx --yes hyperframes@0.8.226 render --quality delivery --output ../$OUT/scenes-all.mp4)
  # name start duration, as in scenes/index.html and storyboard.md
  while read -r name start dur; do
    ffmpeg -nostdin -v error -y -i "$OUT/scenes-all.mp4" -ss "$start" -t "$dur" "${enc[@]}" "$OUT/beats/$name.mp4"
  done <<'EOF'
B1-hook 0 12
B2-thesis 12 10
B4-how 22 30
B7-generality 52 18
B8-measured 70 20
B9-close 90 12
EOF
}

placeholders() {
  # VZ3 prototype recordings (1440x900, 25 fps), letterboxed onto the Bylaw ground; 1x, never sped up.
  local fit="scale=1728:1080:flags=lanczos,pad=1920:1080:96:0:color=$BG,fps=30"
  ffmpeg -v error -y -ss 1.8 -i "$VZ3/d1-guard-off.mp4" -t 30 -vf "$fit" "${enc[@]}" "$OUT/placeholders/B3-guard-off.mp4"
  ffmpeg -v error -y -ss 15.2 -i "$VZ3/d1-guard-on.mp4" -t 28 -vf "$fit" "${enc[@]}" "$OUT/placeholders/B5-guard-on.mp4"
  # B6: end frames of D4, D2 and the honest run, guard on (stills until VZ3 captures exist)
  local i=0
  for s in d4 d2 legit; do
    ffmpeg -v error -y -loop 1 -i "$VZ3/1920-$s-guard-on-end.png" -t 6.667 -vf "fps=30,format=yuv420p" "${enc[@]}" "$OUT/placeholders/B6-$i-$s.mp4"
    i=$((i + 1))
  done
}

rough() {
  test -f "$OUT/music/bed.wav" || { echo "missing $OUT/music/bed.wav: see ASSEMBLY.md, Music bed"; exit 1; }
  mkdir -p roughcut/assets
  rm -f roughcut/assets/C*.mp4
  cp "$OUT"/beats/*.mp4 "$OUT"/placeholders/*.mp4 roughcut/assets/
  cp "$OUT/music/bed.wav" roughcut/assets/bed.wav
  cp -R scenes/assets/fonts roughcut/assets/
  python3 roughcut/make.py
  (cd roughcut && npx --yes hyperframes@0.8.226 render --quality looks --output ../$OUT/rough-cut.mp4)
}

# Final cut, once the voice is in: VOICE (wav), TIMING (from align.py), captures in out/captures/.
# CLOSED=1 uses the B8-closed text (PENDING-DM5).
final() {
  local voice=${VOICE:-$OUT/voice/voice.wav} timing=${TIMING:-$OUT/voice/timing.json} dst=${FINAL:-$OUT/final.mp4}
  mkdir -p roughcut/assets
  rm -f roughcut/assets/C*.mp4
  cp "$OUT"/beats/*.mp4 "$OUT"/placeholders/*.mp4 roughcut/assets/
  if ls "$OUT"/captures/C*.mp4 >/dev/null 2>&1; then cp "$OUT"/captures/C*.mp4 roughcut/assets/; fi
  cp -R scenes/assets/fonts roughcut/assets/
  python3 roughcut/make.py --final --timing "$timing" ${CLOSED:+--closed} --srt "${dst%.mp4}.srt"
  (cd roughcut && npx --yes hyperframes@0.8.226 render --quality delivery --output "../$OUT/final-picture.mp4")
  local total fade
  total=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/final-picture.mp4")
  fade=$(python3 -c "print(max(0, $total - 3))")
  # bed at -10 dB, ducked about 12 dB more under the voice (sidechain), faded out on the end card; mix to -14 LUFS, -1.5 dBTP
  ffmpeg -nostdin -v error -y -i "$OUT/final-picture.mp4" -i "$voice" -i "$OUT/music/bed.wav" -filter_complex \
    "[1:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[vk][vm];\
     [2:a]aformat=sample_rates=48000:channel_layouts=stereo,volume=0.32,afade=t=out:st=$fade:d=3[bed];\
     [bed][vk]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=400[duck];\
     [duck][vm]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t "$total" -movflags +faststart "$dst"
  echo "wrote $dst ($total s)"
}

case "${1:-all}" in
  beats) beats ;;
  placeholders) placeholders ;;
  rough) rough ;;
  final) final ;;
  all) beats; placeholders; rough ;;
esac
