# Nova AI — Films

Remotion source for the film on the `/welcome` page (the hero is live code now, see `frontend/components/welcome/Hero.tsx`).
It is drawn in code from the brand palette and the stamp mark, so it stays on-brand when the identity changes.

| Composition | Size | What it is | Ships as |
|---|---|---|---|
| `Growth` | 1000×1000, 120 frames | The relationship growing around the stamp. Not played: the "how it grows" scene scrubs through its frames as you scroll. | `growth/000.webp` … `119.webp` |

## Render

```bash
cd film
npm install
npm run studio                     # live preview
CH=/path/to/chromium npm run render:all
```

`render:all` runs [`render.sh`](render.sh): it renders the Growth composition and converts its frames to WebP.
It needs `ffmpeg` with libwebp and a Chrome or Chromium binary in `CH`.

Outputs land in `../frontend/public/film/` and are committed, so the web app works without rendering.

## Licence

Remotion is free for individuals and teams of up to three; see <https://remotion.dev/license>.
