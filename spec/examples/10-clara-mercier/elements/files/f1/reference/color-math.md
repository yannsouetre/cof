# Colour maths (exact formulas)

## sRGB transfer (8-bit value v → linear c)
s = v / 255;  c = s / 12.92 if s ≤ 0.04045, else ((s + 0.055) / 1.055)^2.4
Inverse: s = 12.92 c if c ≤ 0.0031308, else 1.055 c^(1/2.4) − 0.055

## WCAG 2.x relative luminance and contrast ratio
Y = 0.2126 R + 0.7152 G + 0.0722 B   (R, G, B linear)
ratio = (Y_lighter + 0.05) / (Y_darker + 0.05)   → from 1:1 to 21:1
Checks: #777777 on #ffffff = 4.48:1 (fails 4.5); #000 on #fff = 21:1.
(WCAG 2.0 printed 0.03928 as the threshold; the difference is negligible for 8-bit colours.)

## Linear sRGB → OKLab (Björn Ottosson, 2020)
l = 0.4122214708 R + 0.5363325363 G + 0.0514459929 B
m = 0.2119034982 R + 0.6806995451 G + 0.1073969566 B
s = 0.0883024619 R + 0.2817188376 G + 0.6299787005 B
l' = ∛l, m' = ∛m, s' = ∛s
L = 0.2104542553 l' + 0.7936177850 m' − 0.0040720468 s'
a = 1.9779984951 l' − 2.4285922050 m' + 0.4505937099 s'
b = 0.0259040371 l' + 0.7827717662 m' − 0.8086757660 s'

## OKLab → linear sRGB
l' = L + 0.3963377774 a + 0.2158037573 b
m' = L − 0.1055613458 a − 0.0638541728 b
s' = L − 0.0894841775 a − 1.2914855480 b
l = l'³, m = m'³, s = s'³
R = +4.0767416621 l − 3.3077115913 m + 0.2309699292 s
G = −1.2684380046 l + 2.6097574011 m − 0.3413193965 s
B = −0.0041960863 l − 0.7034186147 m + 1.7076147010 s

## OKLCH ↔ OKLab
C = √(a² + b²), H = atan2(b, a) in degrees;  a = C cos H, b = C sin H
Check: sRGB red #ff0000 = oklch(0.628 0.258 29.2); white = oklch(1 0 —).

## Gamut mapping (keep L and H, reduce C)
A colour is in sRGB when R, G, B (linear) are all within [0, 1]. If not, binary-search C between 0 and the requested value (≈ 30 iterations) and keep the largest C that fits. Do not clamp channels: clamping shifts hue and lightness.

## Python (stdlib) — contrast of two hex colours
```python
def lum(h):
    c = [int(h[i:i+2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def ratio(a, b):
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)
```
