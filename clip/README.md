# COF launch clip (motion graphics)

`index.html` (16:9) and `vertical.html` (9:16, for phones and Shorts) are the same 38-second animation driven by a single `render(t)` function: open it in a browser to watch it loop, or render it frame by frame to video (1920×1080, 30 fps) with Playwright and ffmpeg (`render.py`, which streams the frames into ffmpeg and adds the music with its fades).

Scenes (seconds): scattered pieces 0–5 · the file 5.4–8.6 · everything that makes Clara 8.6–14.2 · **an inner life** 14.2–18.8 (COF 1.2: Clara's psyche as the explorer draws it — a few of her real nodes, coloured by kind, hung under the memories they come from, with their *because*, *supports* and *conflicts* links) · presets and facets 18.8–24 · rights 24–28 · several characters 28–32.6 · outro 32.8–38. The music (38 s) is fixed: change a scene's length only by taking the time from another one, and keep `tools/readme-figures/render.py`'s clip times in step.

Images: Clara Mercier and Martien, fictional COF example characters (AI-generated, from `spec/examples/10` and `04`); the two memory thumbnails of the psyche scene come from Clara's memories (`spec/examples/10`, `elements/memories/ev1` and `ev2`). Fonts: Bricolage Grotesque and IBM Plex (SIL Open Font License, see `fonts/`).

## The 60-second recap (README hero, site video)

`docs/media/cof-clip.mp4` (the site's video, with sound) and `docs/img/cof-hero.webp` (the README's animation) are not this clip alone but the **60-second recap** (7 November 2026, Yann's cut): this clip **without** its psyche scene (0–14.2 s, then 18.8–32.0 s), the « New in 1.1: memories » chapter made for the 1.1 announcement (`Communication/2026.10 - 003 Annonce 1.1/scripts/video/v3_recap.py`, outside this repository; 32.0–55.0 s of the 1.1 recap, faded to the stage colour over its last 0.45 s so that the 1.1 outro, which cross-fades in from 55.0 s, never shows), then the psyche scene again as a chapter of its own, **« New in 1.2: Psyche, an inner life. »** (the scene of 14.2–18.8 s rendered with that title: `TEXT[3][2]` overridden before `render(t)`), and this clip's outro (32.6 s on, cut to the length of the sound). The soundtrack is the 1.1 recap's (the music does not follow the scenes), with a 20 ms fade-in: the track starts on a non-zero sample and clicked when the video opened — put a fade-in of a few milliseconds on every exported soundtrack:

```
ffmpeg -i clip-16x9-music.mp4 -i cof-clip-1.1.mp4 -i sceneD.mp4 -filter_complex "
 [0:v]trim=0:14.2,setpts=PTS-STARTPTS[a];[0:v]trim=18.8:32.0,setpts=PTS-STARTPTS[b];[1:v]trim=32.0:55.0,setpts=PTS-STARTPTS,fade=t=out:st=22.55:d=0.45:color=0x0c1311[c];[2:v]setpts=PTS-STARTPTS[d];[0:v]trim=32.6:37.427,setpts=PTS-STARTPTS[e];
 [a][b][c][d][e]concat=n=5:v=1:a=0[v];[1:a]afade=t=in:d=0.02[aud]" -map "[v]" -map "[aud]" -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow -c:a aac -b:a 192k -movflags +faststart -shortest cof-clip.mp4
```

The hero is that video at 15 fps, 1280 px, as `render.py`'s `hero()` writes it (WebP lossy, kmin 3 / kmax 10, method 6; q80, under 10 MB).

Titles keep their final period (« Everything that makes Clara. », « An inner life. ») on purpose: it is the house style of both the 1.1 chapter and this clip; changing it would mean re-rendering the 1.1 chapter outside this repository.
