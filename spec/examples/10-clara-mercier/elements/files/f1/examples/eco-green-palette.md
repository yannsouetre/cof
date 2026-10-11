# Worked example — green eco-design studio

**Brief:** a responsible web-design studio; brand green from the founder's work jacket; calm, trustworthy, light and dark modes; WCAG 2.2 AA.

## Hues
- Brand: H 150 (green). Accent: H 300 (plum) — split-complementary (150 + 150°), far from every semantic hue, used only for the main call to action.
- Neutrals: H 150 at C 0.008 (green-tinted greys). Success reuses the brand green, always with an icon and a word.

## Scales (L fixed per step, chroma peaking mid-scale, gamut-mapped to sRGB)
| Step | Brand | Accent | Neutral |
|---|---|---|---|
| 50 | oklch(0.975 0.033 150) `#e8fdec` | oklch(0.975 0.014 300) `#f8f5ff` | oklch(0.975 0.008 150) `#f3f8f4` |
| 100 | oklch(0.940 0.042 150) `#d8f4dd` | oklch(0.940 0.034 300) `#eee7ff` | oklch(0.940 0.008 150) `#e8ede8` |
| 200 | oklch(0.885 0.056 150) `#c0e4c6` | oklch(0.885 0.060 300) `#dfd1fc` | oklch(0.885 0.008 150) `#d6dbd6` |
| 300 | oklch(0.800 0.078 150) `#9acca3` | oklch(0.800 0.084 300) `#c6b2ec` | oklch(0.800 0.008 150) `#babfbb` |
| 400 | oklch(0.710 0.101 150) `#72b380` | oklch(0.710 0.109 300) `#ac92dc` | oklch(0.710 0.008 150) `#9ea39f` |
| 500 | oklch(0.620 0.125 150) `#469b5c` | oklch(0.620 0.134 300) `#9371ca` | oklch(0.620 0.008 150) `#838884` |
| 600 | oklch(0.530 0.112 150) `#337d48` | oklch(0.530 0.120 300) `#775aa6` | oklch(0.530 0.008 150) `#696d69` |
| 700 | oklch(0.450 0.091 150) `#2a6339` | oklch(0.450 0.098 300) `#5e4783` | oklch(0.450 0.008 150) `#525753` |
| 800 | oklch(0.370 0.070 150) `#214a2b` | oklch(0.370 0.076 300) `#463662` | oklch(0.370 0.008 150) `#3d413d` |
| 900 | oklch(0.290 0.049 150) `#18321e` | oklch(0.290 0.053 300) `#2f2542` | oklch(0.290 0.008 150) `#292c29` |
| 950 | oklch(0.220 0.033 150) `#0f1f12` | oklch(0.220 0.035 300) `#1d1728` | oklch(0.220 0.008 150) `#181c19` |

## Tokens
| Role | Light | Dark |
|---|---|---|
| bg | neutral-50 | neutral-950 |
| text | neutral-900 | neutral-100 |
| text-muted | neutral-600 | neutral-400 |
| border (decorative) | neutral-200 | neutral-800 |
| border-input | neutral-500 | neutral-500 |
| link / primary | brand-700 | brand-300 |
| on-primary | white | neutral-950 (on brand-400 buttons) |
| accent (main CTA) | accent-600 + white text | accent-300 + neutral-950 text |
| focus | brand-500 | brand-400 |

## Contrast report (computed with `reference/color-math.md`)
| Pair | Ratio | Threshold | Result |
|---|---|---|---|
| text neutral-900 on bg neutral-50 | 13.15:1 | 4.5 | pass |
| muted neutral-600 on bg neutral-50 | 4.90:1 | 4.5 | pass |
| link brand-700 on white | 7.14:1 | 4.5 | pass (AAA) |
| link brand-700 on bg neutral-50 | 6.64:1 | 4.5 | pass |
| white on primary button brand-700 | 7.14:1 | 4.5 | pass |
| white on accent-600 CTA | 5.53:1 | 4.5 | pass |
| input border neutral-500 on white | 3.61:1 | 3 (1.4.11) | pass |
| input border neutral-500 on bg neutral-50 | 3.36:1 | 3 | pass |
| **neutral-400 as input border on white** | **2.56:1** | 3 | **fail → use neutral-500** (fine for decorative dividers only) |
| focus brand-500 on white | 3.44:1 | 3 | pass |
| focus brand-500 on bg neutral-50 | 3.20:1 | 3 | pass |
| dark: text neutral-100 on neutral-950 | 14.53:1 | 4.5 | pass |
| dark: muted neutral-400 on neutral-950 | 6.72:1 | 4.5 | pass |
| dark: link brand-300 on neutral-950 | 9.47:1 | 4.5 | pass |
| dark: neutral-950 text on brand-400 button | 6.95:1 | 4.5 | pass |
| dark: accent-300 on neutral-950 | 9.01:1 | 4.5 | pass |
| dark: input border neutral-500 on neutral-950 | 4.77:1 | 3 | pass |
| dark: focus brand-400 on neutral-950 | 6.95:1 | 3 | pass |

The failing row is the lesson: a grey that looks fine as a divider is too faint to show where an input field is.

## CSS
```css
:root {
  color-scheme: light dark;
  --color-bg: oklch(0.975 0.008 150);         /* neutral-50 */
  --color-text: oklch(0.29 0.008 150);        /* neutral-900 */
  --color-text-muted: oklch(0.53 0.008 150);  /* neutral-600 */
  --color-border: oklch(0.885 0.008 150);     /* neutral-200, decorative */
  --color-border-input: oklch(0.62 0.008 150);/* neutral-500 */
  --color-link: oklch(0.45 0.091 150);        /* brand-700 */
  --color-primary: oklch(0.45 0.091 150);
  --color-on-primary: #fff;
  --color-accent: oklch(0.53 0.12 300);       /* accent-600 */
  --color-on-accent: #fff;
  --color-focus: oklch(0.62 0.125 150);       /* brand-500 */
}
@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: oklch(0.22 0.008 150);
    --color-text: oklch(0.94 0.008 150);
    --color-text-muted: oklch(0.71 0.008 150);
    --color-border: oklch(0.37 0.008 150);
    --color-link: oklch(0.80 0.078 150);
    --color-primary: oklch(0.71 0.101 150);
    --color-on-primary: oklch(0.22 0.008 150);
    --color-accent: oklch(0.80 0.084 300);
    --color-on-accent: oklch(0.22 0.008 150);
    --color-focus: oklch(0.71 0.101 150);
  }
}
a { color: var(--color-link); text-decoration: underline; text-underline-offset: 0.15em; }
:focus-visible { outline: 2px solid var(--color-focus); outline-offset: 2px; }
@media (forced-colors: active) { .btn { border: 1px solid ButtonText; } }
```
