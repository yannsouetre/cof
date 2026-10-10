# Règles des tags (v0.3)

| Slot | Qui écrit | Règles |
|---|---|---|
| `tags.auto` | le builder / `cof validate` (régénérables) | morphologie (`humanoid`…), tranche d'âge depuis l'âge le plus bas (`child` < 13, `teen` < 18, `adult`, `elder` ≥ 65), langues (ISO 639-1), couches présentes (`has-voice`, `has-3d`, `has-motion`, `has-weights`), `multi-preset` si ≥ 2 presets, `style-<style>` du preset par défaut, `imported-ccv3` à l'import |
| `tags.manual` | l'auteur | ≤ 30, minuscules, `[a-z0-9-]` |
| `tags.content` | l'auteur (proposé par le builder depuis les permissions et descriptifs) | vocabulaire fermé : `none`, `nudity`, `sexual`, `violence`, `gore`, `drugs`, `profanity`, `horror`, `political`, `religious` ; `allowSexualUsage: true` ou élément `intimate` ⇒ le builder propose `sexual`/`nudity` |
| `tags.ip` | l'auteur | `original: true`, sinon `franchise` / `based_on` nommés ; le builder alerte par correspondance avec `vocabularies/franchises.txt` (liste contributive, non exhaustive) |
| `style` / `style_tags` | builder (proposition) + auteur | `style` ∈ `visual-styles-1.0` ; précisions libres en `style_tags` |

Un tag n'est jamais une preuve : il est **déclaratif** et opposable via la provenance.
