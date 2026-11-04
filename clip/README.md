# COF launch clip (motion graphics)

`index.html` (16:9) and `vertical.html` (9:16, for phones and Shorts) are the same 38-second animation driven by a single `render(t)` function: open it in a browser to watch it loop, or render it frame by frame to video (1920×1080, 30 fps) with Playwright and ffmpeg (`render.py`, which streams the frames into ffmpeg and adds the music with its fades).

Scenes (seconds): scattered pieces 0–5 · the file 5.4–8.6 · everything that makes Clara 8.6–14.2 · **an inner life** 14.2–18.8 (COF 1.2: Clara's psyche as the explorer draws it — a few of her real nodes, coloured by kind, hung under the memories they come from, with their *because*, *supports* and *conflicts* links) · presets and facets 18.8–24 · rights 24–28 · several characters 28–32.6 · outro 32.8–38. The music (38 s) is fixed: change a scene's length only by taking the time from another one, and keep `tools/readme-figures/render.py`'s clip times in step.

Images: Clara Mercier and Martien, fictional COF example characters (AI-generated, from `spec/examples/10` and `04`); the two memory thumbnails of the psyche scene come from Clara's memories (`spec/examples/10`, `elements/memories/ev1` and `ev2`). Fonts: Bricolage Grotesque and IBM Plex (SIL Open Font License, see `fonts/`).
