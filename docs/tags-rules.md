# Tag rules (v0.3)

| Slot | Written by | Rules |
|---|---|---|
| `tags.auto` | the builder / `cof validate` (regenerable) | morphology (`humanoid`…), age bracket from the lowest age (`child` < 13, `teen` < 18, `adult`, `elder` ≥ 65), languages (ISO 639-1), layers present (`has-voice`, `has-3d`, `has-motion`, `has-weights`), `multi-preset` if ≥ 2 presets, `style-<style>` of the default preset, `imported-ccv3` on import |
| `tags.manual` | the author | ≤ 30, lowercase, `[a-z0-9-]` |
| `tags.content` | the author (suggested by the builder from permissions and descriptions) | closed vocabulary: `none`, `nudity`, `sexual`, `violence`, `gore`, `drugs`, `profanity`, `horror`, `political`, `religious`; `allowSexualUsage: true` or an `intimate` element ⇒ the builder suggests `sexual`/`nudity` |
| `tags.ip` | the author | `original: true`, otherwise a named `franchise` / `based_on`; the builder warns on matches against `vocabularies/franchises.txt` (contributed list, not exhaustive) |
| `style` / `style_tags` | builder (suggestion) + author | `style` ∈ `visual-styles-1.0`; free-form refinements in `style_tags` |

A tag is never proof: it is **declarative** and can be held against the author through provenance.
