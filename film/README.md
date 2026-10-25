# Nova AI — Films

Remotion source for the two films on the `/welcome` page. Both are drawn in code from the brand palette
and the stamp mark, so they stay on-brand when the identity changes.

| Composition | Size | What it is | Ships as |
|---|---|---|---|
| `Hero` | 1920×1080, 30 fps, 10 s | A day passing over one life: an orrery of days around the stamp. Everything moves a whole number of cycles, so the last frame meets the first (seamless loop). | `hero.mp4` / `hero.webm`, `hero-sm.*` (960×540, phones), `hero-poster.jpg` (reduced motion) |
| `Growth` | 1000×1000, 120 frames | The relationship growing around the stamp. Not played: the "how it grows" scene scrubs through its frames as you scroll. | `growth/000.webp` … `119.webp` |

## Render

```bash
cd film
npm install
npm run studio                     # live preview of both compositions
CH=/path/to/chromium npm run render:all
```

`render:all` runs [`render.sh`](render.sh): it renders both compositions, converts the Growth frames to WebP,
grades the Hero film in ffmpeg (halation, a light chromatic split, vignette, grain) and encodes MP4 and WebM.
It needs `ffmpeg` with libwebp and libvpx-vp9, and a Chrome or Chromium binary in `CH`.

Grading is done in RGB (`format=gbrp`) before the screen blend; in YUV the blend shifts colour.

Outputs land in `../frontend/public/film/` and are committed, so the web app works without rendering.

## Licence

Remotion is free for individuals and teams of up to three; see <https://remotion.dev/license>.
