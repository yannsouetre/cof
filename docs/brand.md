# COF visual identity

One look for the format, its tools and its communication. It comes from the launch clip (`clip/`) and is already used by the explorer. The [French version](brand.fr.md) holds the same rules.

## Colours

The main palette is dark: a deep green-black background, light text and one accent, teal.

| Token | Dark (main) | Light | Use |
|---|---|---|---|
| `--bg` | `#0d1312` | `#f3f4f2` | page background |
| `--panel` | `#18201f` | `#ffffff` | cards, panels, chips |
| `--line` | `#2a3533` | `#dde1de` | borders, separators |
| `--ink` | `#eef3f1` | `#1a1e1d` | text |
| `--muted` | `#93a39e` | `#5f6764` | secondary text, captions |
| `--accent` (teal) | `#4cc2a8` | `#0f6b5c` | links, buttons, the active choice, "allowed" |
| `--accent-deep` | `#0f6b5c` | `#0f6b5c` | the file icon's gradient end, filled buttons on light |
| `--mint` | `#bfeee2` | `#d9ece7` | the file's folded corner, soft highlights |
| `--offer` (violet) | `#a98ae8` | `#6a45b8` | what a preset offers without applying it; LoRA and weights |
| `--no` (coral) | `#f07a72` | `#a8231d` | "not allowed", errors |
| `--warn` (amber) | `#e0a54a` | `#9a5b00` | warnings |

Rules:
- One accent per screen: teal. Violet and coral carry a meaning (offered, refused); they are never decoration.
- Text on teal is `#05201b`, never white.
- Large surfaces stay neutral; colour goes to small things (a button, a pill, a tick).

## Typefaces

All three are free (SIL Open Font License) and come with the clip in `clip/fonts/`.

| Role | Typeface | Weights |
|---|---|---|
| Titles, the "COF" word, big numbers | **Bricolage Grotesque** | 700, 500 |
| Text, labels, buttons | **IBM Plex Sans** | 400, 500 |
| File names, formats, code, values | **IBM Plex Mono** | 500 |

- Titles are tight: letter spacing −0.02 em, line height about 1.0.
- File names and formats are always in the monospace: `photos (.jpeg)`, `LoRA (.safetensors)`.

## Shapes

- Rounded corners: 14 px for chips and thumbnails, 22–28 px for cards and the file icon.
- **The file icon**: a teal document (gradient `#4cc2a8` → `#0f6b5c`), folded top-right corner in mint, the word `.cof` in Bricolage 700, `character` above it in Plex Mono. It stands for the format in diagrams and in the clip.
- **The bust mark** (`builder/icon/`): the application icon of the builder and the explorer.
- Pills for choices (language, age, style): fully rounded, outlined when off, filled in teal when on.

## Pictures

- The examples' characters (Clara Mercier, Martien…) on a white background, in rounded cards, with a soft shadow.
- Diagrams: few boxes, short labels, thin teal connectors, the file icon at the centre.
- Every image published for COF shows fictional characters only, and says that its images are AI-generated.

## Files

- Figures of the README: `docs/img/` (built from `tools/readme-figures/`).
- Clip: `clip/index.html` (source), `docs/media/cof-clip.mp4` (with music).
- Fonts: `clip/fonts/` (with their licences).
