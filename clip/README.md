# COF launch clip (motion graphics)

`index.html` (16:9) and `vertical.html` (9:16, for phones and Shorts) are the same 38-second animation driven by a single `render(t)` function: open it in a browser to watch it loop, or render it frame by frame to video (1920×1080, 30 fps) with Playwright and ffmpeg (`render.py`, which streams the frames into ffmpeg and adds the music with its fades).

Scenes (seconds): scattered pieces 0–5 · the file 5.4–8.6 · everything that makes Clara 8.6–14.2 · **an inner life** 14.2–18.8 (COF 1.2: Clara's psyche as the explorer draws it — a few of her real nodes, coloured by kind, hung under the memories they come from, with their *because*, *supports* and *conflicts* links) · presets and facets 18.8–24 · rights 24–28 · several characters 28–32.6 · outro 32.8–38. The music (38 s) is fixed: change a scene's length only by taking the time from another one, and keep `tools/readme-figures/render.py`'s clip times in step.

Images: Clara Mercier and Martien, fictional COF example characters (AI-generated, from `spec/examples/10` and `04`); the two memory thumbnails of the psyche scene come from Clara's memories (`spec/examples/10`, `elements/memories/ev1` and `ev2`). Fonts: Bricolage Grotesque and IBM Plex (SIL Open Font License, see `fonts/`).

## The 60-second recap (README hero, site video)

`docs/media/cof-clip.mp4` (the site's video, with sound) and `docs/img/cof-hero.webp` (the README's animation) are not this clip alone but the **61-second recap** (7 November 2026, Yann's cut): this clip **without** its psyche scene (0–14.2 s, then 18.8–32.0 s), the « New in 1.1: memories » chapter made for the 1.1 announcement (`Communication/2026.10 - 003 Annonce 1.1/scripts/video/v3_recap.py`, outside this repository; 32.0–55.55 s of the previous recap), then the psyche scene again as a chapter of its own, **« New in 1.2: Psyche, an inner life. »** (the scene of 14.2–18.8 s rendered with that title: `TEXT[3][2]` overridden before `render(t)`), and this clip's outro (32.6–38 s). The sound keeps each segment's own music (the recap's track for the first two parts, the clip's ending under the last two), joined with 0.25 s cross-fades:

```
ffmpeg -i cof-clip-previous.mp4 -i sceneD.mp4 -i clip-16x9-music.mp4 -filter_complex "
 [0:v]trim=0:14.2,setpts=PTS-STARTPTS[a];[0:v]trim=18.8:55.55,setpts=PTS-STARTPTS[b];[1:v]setpts=PTS-STARTPTS[d];[2:v]trim=32.6:38,setpts=PTS-STARTPTS[e];[a][b][d][e]concat=n=4:v=1:a=0[v];
 [0:a]atrim=0:14.325,asetpts=PTS-STARTPTS[aa];[0:a]atrim=18.675:55.675,asetpts=PTS-STARTPTS[ab];[2:a]atrim=27.875:38,asetpts=PTS-STARTPTS[ak];
 [aa][ab]acrossfade=d=0.25[a1];[a1][ak]acrossfade=d=0.25[aud]" -map "[v]" -map "[aud]" -c:v libx264 -pix_fmt yuv420p -crf 20 -preset slow -c:a aac -b:a 192k -movflags +faststart -shortest cof-clip.mp4
```

The hero is that video at 15 fps, 1280 px, as `render.py`'s `hero()` writes it (WebP lossy, kmin 3 / kmax 10, method 6; q80, 8.6 MB).

Titles keep their final period (« Everything that makes Clara. », « An inner life. ») on purpose: it is the house style of both the 1.1 chapter and this clip; changing it would mean re-rendering the 1.1 chapter outside this repository.
