#!/usr/bin/env bash
# Render the Growth film into ../frontend/public/film: 120 frames, scrubbed by scroll in the "how it grows" scene -> growth/NNN.webp
# Needs: node, ffmpeg (with libwebp), and a Chrome/Chromium binary in $CH.
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

echo "done: $i growth frames in $OUT"
