# COF launch clip (motion graphics)

`index.html` (16:9) and `vertical.html` (9:16, for phones and Shorts) are the same 38-second animation driven by a single `render(t)` function: open it in a browser to watch it loop, or render it frame by frame to video (1920×1080, 30 fps) with Playwright and ffmpeg (`render.py`, which streams the frames into ffmpeg and adds the music with its fades).

Scenes (seconds): scattered pieces 0–5 · the file 5.4–8.6 · everything that makes Clara 8.6–14.2 · **an inner life** 14.2–18.8 (COF 1.2: Clara's psyche as the explorer draws it — a few of her real nodes, coloured by kind, hung under the memories they come from, with their *because*, *supports* and *conflicts* links) · presets and facets 18.8–24 · rights 24–28 · several characters 28–32.6 · outro 32.8–38. The music (38 s) is fixed: change a scene's length only by taking the time from another one, and keep `tools/readme-figures/render.py`'s clip times in step.

Images: Clara Mercier and Martien, fictional COF example characters (AI-generated, from `spec/examples/10` and `04`); the two memory thumbnails of the psyche scene come from Clara's memories (`spec/examples/10`, `elements/memories/ev1` and `ev2`). Fonts: Bricolage Grotesque and IBM Plex (SIL Open Font License, see `fonts/`).

## The 60-second recap (README hero, site video)

`docs/media/cof-clip.mp4` (the site's video, with sound) and `docs/img/cof-hero.webp` (the README's animation) are not this clip alone but the **60-second recap**: this clip up to 32.0 s, then the « New in 1.1: memories » chapter made for the 1.1 announcement (`Communication/2026.10 - 003 Annonce 1.1/scripts/video/v3_recap.py`, outside this repository), on the clip's music prolonged. For 1.2 the recap was rebuilt by swapping its first 32 s for this clip (the two are identical from 28 s, the several-characters scene, so the cut is invisible), keeping the 1.1 recap's sound:

```
ffmpeg -i clip-16x9-music.mp4 -i cof-clip-1.1.mp4 -filter_complex "[0:v]trim=end=32,setpts=PTS-STARTPTS[a];[1:v]trim=start=32,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]" \
  -map "[v]" -map 1:a -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow -c:a copy -movflags +faststart cof-clip.mp4
```

The hero is that video at 15 fps, 1280 px, as `render.py`'s `hero()` writes it (WebP lossy, kmin 3 / kmax 10, method 6; q80 for the 1.2 recap, to stay under 10 MB).
