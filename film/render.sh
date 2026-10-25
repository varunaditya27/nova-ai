#!/usr/bin/env bash
# Render both films and grade them into ../frontend/public/film.
#   Growth: 120 frames, scrubbed by scroll in the "how it grows" scene  -> growth/NNN.webp
#   Hero:   the 10 s seamless opening shot                              -> hero.{mp4,webm}, hero-sm.*, hero-poster.jpg
# Needs: node, ffmpeg (with libwebp and libvpx-vp9), and a Chrome/Chromium binary in $CH.
set -euo pipefail
cd "$(dirname "$0")"
: "${CH:?set CH to a Chrome/Chromium executable, e.g. CH=/usr/bin/chromium}"
OUT=../frontend/public/film
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT/growth"

npx remotion render src/index.ts Growth "$TMP/g" --sequence --image-format=png --browser-executable="$CH" --concurrency=4
i=0
for f in $(ls "$TMP"/g/*.png | sort); do
  ffmpeg -y -loglevel error -i "$f" -vf "eq=saturation=1.25,scale=800:800" -c:v libwebp -quality 78 "$OUT/growth/$(printf '%03d' $i).webp"
  i=$((i + 1))
done

npx remotion render src/index.ts Hero "$TMP/hero.mp4" --browser-executable="$CH" --crf=14 --concurrency=4

# Grade in RGB (format=gbrp) so the screen blend does not shift colour.
GRADE="[0:v]format=gbrp,split=2[a][b];[b]gblur=sigma=30,curves=all='0/0 0.6/0.12 1/1'[g];[a][g]blend=all_mode=screen:all_opacity=0.45[h];[h]rgbashift=rh=-2:bh=2,vignette=angle=PI/2.3,noise=alls=6:allf=t,eq=contrast=1.05:brightness=0.01:saturation=1.3"
SMALL="scale=960:540"
ffmpeg -y -loglevel error -i "$TMP/hero.mp4" -filter_complex "$GRADE,format=yuv420p" -c:v libx264 -preset slow -crf 24 -movflags +faststart -an "$OUT/hero.mp4"
ffmpeg -y -loglevel error -i "$TMP/hero.mp4" -filter_complex "$GRADE,$SMALL,format=yuv420p" -c:v libx264 -preset slow -crf 25 -movflags +faststart -an "$OUT/hero-sm.mp4"
ffmpeg -y -loglevel error -i "$TMP/hero.mp4" -filter_complex "$GRADE,format=yuv420p" -c:v libvpx-vp9 -b:v 0 -crf 33 -row-mt 1 -an "$OUT/hero.webm"
ffmpeg -y -loglevel error -i "$TMP/hero.mp4" -filter_complex "$GRADE,$SMALL,format=yuv420p" -c:v libvpx-vp9 -b:v 0 -crf 36 -row-mt 1 -an "$OUT/hero-sm.webm"
ffmpeg -y -loglevel error -i "$TMP/hero.mp4" -ss 2.5 -frames:v 1 -filter_complex "$GRADE" -q:v 3 "$OUT/hero-poster.jpg"
echo "done: $i growth frames and the hero film in $OUT"
