# Governance

*(Français : [GOVERNANCE.fr.md](GOVERNANCE.fr.md))*

- **Versioning**: semver. A `1.x` reader reads any `1.y` file; later minor versions only add optional fields; unknown keys are preserved and `extensions` is never purged.
- **Changes to the format** go through a public RFC in `rfcs/` (numbered, 14-day comment period), then a `CHANGELOG.md` entry. An additive minor may ship together with its RFC, the comment period then running after publication and its outcome landing in a patch release (1.1 did). Bug fixes in the reference tools do not need an RFC.
- **Vocabularies** (`vocabularies/`) are versioned separately and released under CC0.
- **Decisions**: initial maintainer Yann Souetre. Commitment: governance moves to a neutral body (an existing foundation or consortium) as soon as **two independent adopters** implement the format.
- **Neutrality**: the project's own gallery or tools never get privileges in the format; the catalogue API is open, other galleries and stores are welcome, the "COF-compatible" badge is free.
- **Conduct**: issues and RFCs in English or French; answers within 72 hours during the three months following the launch.
