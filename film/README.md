# Nova films

Remotion source for the landing page's opening shot (`Hero`, 1920×1080, 30 fps, 10 s, seamless loop).
Everything moves a whole number of cycles per loop, so the last frame meets the first.

```bash
npm install
npm run studio                       # preview
CH=/path/to/chrome npm run render    # → frames; then grade with ffmpeg (below)
```

The raw render is graded in ffmpeg (halation, a light chromatic split, vignette, grain). Grading is done in
RGB (`format=gbrp`) so the screen blend does not shift colour:

```bash
GRADE="[0:v]format=gbrp,split=2[a][b];[b]gblur=sigma=30,curves=all='0/0 0.6/0.12 1/1'[g];[a][g]blend=all_mode=screen:all_opacity=0.45[h];[h]rgbashift=rh=-2:bh=2,vignette=angle=PI/2.3,noise=alls=6:allf=t,eq=contrast=1.03:brightness=0.01:saturation=1.08"
ffmpeg -i hero-raw.mp4 -filter_complex "$GRADE,format=yuv420p" -c:v libx264 -preset slow -crf 24 -movflags +faststart -an ../frontend/public/film/hero.mp4
```

Outputs live in `../frontend/public/film/` (`hero.mp4`/`hero.webm`, `hero-sm.*` at 960×540, `hero-poster.jpg`).
Remotion is free for individuals and teams of up to three; see https://remotion.dev/license.
