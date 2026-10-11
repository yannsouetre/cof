---
name: accessible-color-palette
description: Build or fix a harmonious, accessible colour system for a website or app — OKLCH tonal scales, hue harmony, semantic tokens, WCAG 2.2 contrast checks, dark mode, forced colours and colour-blind safety. Use when the user asks for a palette, brand colours, a theme, dark mode, or says colours "clash", "look dull" or "fail contrast".
---
# Accessible colour palette

Answer in the user's language. Work from numbers, not taste: every colour you propose comes with its OKLCH value, its hex value and the contrast ratio of each pair it will be used in.

## 1. Gather the inputs (ask ONE question if something essential is missing)
- Existing brand colours (hex) or the mood to convey, and what must not change.
- Surfaces: light only, light + dark, print, data visualisation?
- Conformance target: WCAG 2.2 AA (default) or AAA.

## 2. Work in OKLCH, not HSL
HSL "lightness" lies: yellow and blue at the same HSL lightness have very different perceived brightness, so HSL scales give uneven steps and broken contrast. OKLCH (`oklch(L C H)`, CSS Color 4, supported by all current browsers) separates **L** perceived lightness (0–1), **C** chroma and **H** hue angle. Same L ≈ same perceived lightness across hues, which makes contrast predictable. Conversion formulas: `reference/color-math.md`.

## 3. Choose hues (harmony)
- Start from the brand hue. Add **at most one accent hue**, picked by a classic relation measured on the OKLCH hue circle: analogous (±30°), split-complementary (±150°), triadic (±120°) or complementary (180°).
- Neutrals are the brand hue at very low chroma (C ≈ 0.005–0.015): tinted greys feel related to the brand instead of dead.
- Proportions: about 60 % neutral surfaces, 30 % brand, 10 % accent. The accent is reserved for the single most important action, or it stops working.
- Semantic colours (danger ≈ red, warning ≈ amber, success ≈ green, info ≈ blue) must not collide with the accent. If the brand hue *is* a semantic hue (a green brand), reuse it for success and always pair the state with an icon and a word.

## 4. Build tonal scales
For each hue, 11 steps (50 … 950) with **fixed hue, evenly spaced L** (e.g. 0.975 → 0.22) and **chroma peaking mid-scale**, reduced towards both ends. Then **gamut-map**: lower C at constant L and H until the colour fits sRGB (each hue has its own maximum chroma; yellows peak light, blues peak dark). Never clip RGB channels — that shifts the hue.

## 5. Map to semantic tokens
Components never use raw steps. Define roles once, per scheme:
`--color-bg`, `--color-surface`, `--color-text`, `--color-text-muted`, `--color-border` (decorative), `--color-border-input`, `--color-link`, `--color-primary` + `--color-on-primary`, `--color-accent` + `--color-on-accent`, `--color-focus`, `--color-danger` / `-warning` / `-success` / `-info` (+ their `on-` pairs).
Dark mode = a second mapping of the same roles, not an inversion.

## 6. Check every pair (WCAG 2.2)
| Use | Minimum (AA) | AAA |
|---|---|---|
| Body text, icons that carry text meaning | 4.5:1 | 7:1 |
| Large text (≥ 24 px, or ≥ 18.66 px bold) | 3:1 | 4.5:1 |
| UI component boundaries needed to identify them (input borders, toggles), focus indicators, meaningful graphics — SC 1.4.11 | 3:1 against adjacent colours | — |
| Decorative dividers, disabled controls, logos | exempt | — |

- Compute ratios with the formula in `reference/color-math.md`; report them, never guess. Check text on **every** surface it can sit on (bg, surface, tinted cards), not just on white.
- **Colour is never the only signal** (SC 1.4.1): links in body text are underlined or otherwise marked, errors have an icon and a message, charts use labels or patterns.
- **Colour-vision deficiencies** (red-green affects roughly 1 man in 12 in populations of European descent): avoid red/green as the only distinction; check with Chrome DevTools → Rendering → *Emulate vision deficiencies*.
- APCA (candidate method for a future WCAG) can be used as a second, perceptual opinion; WCAG 2.2 ratios remain the conformance reference.

## 7. Dark mode
- Background: a very dark tinted neutral (L ≈ 0.18–0.24), not `#000`; text: off-white (L ≈ 0.93–0.96), not `#fff` — pure white on pure black causes halation for some readers (notably with astigmatism).
- Use lighter steps for brand colours (300–400 instead of 600–700) and lower their chroma slightly; saturated colours vibrate on dark grounds.
- Elevation = lighter surfaces, not shadows.
- Eco-design note: on OLED screens dark pixels draw less power; on LCD screens it changes nothing. Offer dark mode for comfort, never claim a fixed saving.

## 8. Deliver in CSS
```css
:root { color-scheme: light dark; }
:root { --color-bg: oklch(0.975 0.008 150); /* … */ }
@media (prefers-color-scheme: dark) { :root { --color-bg: oklch(0.22 0.008 150); /* … */ } }
@media (forced-colors: active) { .btn { border: 1px solid ButtonText; } }  /* Windows contrast themes */
```
Keep hex fallbacks only if old browsers matter. Fewer colours mean a lighter stylesheet and a calmer interface: remove any token nobody uses.

## Output format
1. Palette table: step, OKLCH, hex (one table per hue).
2. Token mapping, light and dark.
3. Contrast report: each pair, ratio, pass/fail, threshold.
4. The CSS block.
5. One sentence of rationale per choice — no theory dump.

Worked example (green eco brand, verified ratios): `examples/eco-green-palette.md`.
