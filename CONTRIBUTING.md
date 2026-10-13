# Contributing

*(Français : [CONTRIBUTING.fr.md](CONTRIBUTING.fr.md))*

Thanks for helping! COF is an open format; the most valuable contributions are **readers and writers in other tools**, **characters**, and **feedback from real use**.

## Where to start
- **Use it**: open a `.cof` in the [builder](https://yannsouetre.github.io/cof/builder/), export a PNG card to SillyTavern, a workspace to an agent (`cof export --format agent`), tell us what broke.
- **Integrate it**: a reader in your app is usually a few dozen lines — see [`docs/IMPLEMENTING.md`](docs/IMPLEMENTING.md) and run the positive (`spec/examples/`) and negative (`tests/invalid/`) test vectors in your CI.
- **Add vocabulary entries** (`vocabularies/`): direct PRs welcome (descriptors, translations, mappings) — CC0.

## Changing the format
Normative changes go through an RFC: copy `rfcs/0000-template.md`, open a PR, 14-day comment period. Keep 1.x backward compatible: add optional fields, never change the meaning of an existing one.

## Code
- `cli/` — Python ≥ 3.11, `pip install -e cli && pytest cli/tests` must pass; regenerate the negative corpus with `python tests/invalid/build.py` when you touch a rule.
- `builder/` — a single offline HTML page, plain JavaScript, no framework, no network call at runtime; every interface string goes through `t()` (six languages).
- One concern per PR; tests for every converter and every new rule.

## Example characters
Only **fully fictional** characters, with real licences for every file (generator plan terms included), `digitalSourceType` on AI-generated media, and `cof validate` OK. No real person, no third-party franchise, no intimate content in the examples or the gallery seed.

## Reporting a rights or safety problem
Use the *Rights / takedown* issue template, or see [SECURITY.md](SECURITY.md) for anything that must not be public.
