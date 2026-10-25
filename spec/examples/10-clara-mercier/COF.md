# COF.md — how to read this file (Clara Mercier)

This is a **Character Open File** (COF 1.1, a ZIP with `manifest.json` at its root; MIME `application/vnd.cof.character+zip`).
It carries one or more AI characters: their personality, looks, voice, body, past and rights, in one portable container.
Specification, schemas and tools: https://github.com/yannsouetre/cof — `pip install cof-cli` gives `cof validate`, `cof info`, `cof export`, `cof extract`, `cof memory add`.
This note is a courtesy for readers without the specification; **the specification and `manifest.json` win** whenever they differ.

## Reading
- `manifest.json` is the index. Characters: `id1` (Clara Mercier). Presets (a consistent way to present a character — age, style, language): `default`, `en-manga`, `en-12`, `en-65`, `en-future`, `en-agent`, `fr`, `fr-manga`, `fr-12`, `fr-65`, `fr-futur`, `fr-agent`; `default_preset` says which to use when nobody chooses.
- Elements by category (`personality`, `appearance`, `voice`, `posture`, `files`, `motion`, `memories`): each category has `variants`; a preset's `slots` lists the variants it applies, `alternatives` the ones it offers; `extends` inherits from another preset.
- Every file of the container is declared in `assets` (path, `mediaType`, `sha256`, `license`, `role`); a variant names its files by asset id. Sub-files (`card.json`, `psyche.json`, `profile.json`, `memory.json`) are JSON next to their variant under `elements/<category>/<variant>/`.
- Short texts that are per language are maps keyed by BCP 47 (`{"fr": …, "en": …}`); pick the preset's personality language, else the identity's `language`, else the first entry.
- `cof export --format agent --preset <id>` turns a preset into `SOUL.md` + `IDENTITY.md` + `MEMORY.md` for a text agent; the ComfyUI nodes read the file directly.

## Rules you must honour
- **Rights**: `rights.permissions` (and a character's own `identities.<id>.rights`) say what may be done — `aiDisclosure`: true, `allowAntisocialOrHateUsage`: false, `allowExcessivelyViolentUsage`: false, `allowImpersonationOfRealPerson`: false, `allowPoliticalOrReligiousUsage`: false, `allowRedistribution`: false, `allowSexualUsage`: false, `allowTraining`: "none", `allowVoiceCloning`: false, `avatarPermission`: "onlyAuthor", `commercialUsage`: "personalNonProfit", `creditNotation`: "required", `modification`: "prohibited". `aiDisclosure` true means: say you are synthetic when asked.
- **Ages**: a preset's age is the lowest age of what it applies (`age`, `age_override`). A preset under 18 shows nothing nude or intimate, ever; `allowSexualUsage` is an opt-in that a host must ask for explicitly, never a default.
- **Real persons** (`fictional: false`) come with a consent record; their likeness, voice and memories never travel to another character or another file.
- **Content flags** (`tags.content`) list what the file holds (`nudity`, `violence`…); `none` means nothing flagged.
- **Memories** (`elements/memories`, COF 1.1 / RFC 0002): nodes `moment` or `period`, each with a `memory.json` (gist per language, when, where, who, feelings, `fidelity`, links). `disclosure: secret` is never told; `guarded` only when it matters; `visibility: personal` nodes are one user's data and never leave this file without their consent; `explicit` nodes show no media to anyone but an adult preset with the opt-in. Readers order by age, else date, else links.

## Writing back what the character lives (hosts and agents)
The canon is read-only for tools. What happens at use time is added as **new memory nodes** with `origin: "lived"`, and `visibility: "personal"` when it concerns one user:
1. Create `elements/memories/<id>/memory.json` — `{"gist": {"<lang>": "one paragraph"}, "when": {"date": "YYYY-MM-DD"}, "origin": "lived", "visibility": "personal", "disclosure": "open", "fidelity": "clear", "nature": ["experienced"]}` (ids `ev<n>` for moments, `ep<n>` for periods; never reuse an id).
2. Declare it in `manifest.json` › `elements.memories.variants.<id>`: `{"kind": "moment", "label": "…", "memory": "elements/memories/<id>/memory.json", "identity": "<character>"}`, and list the id in the `slots.memories` of the presets that may recall it. Media go under the same folder, declared in `assets` with role `memory-media` and their `sha256`.
3. Set `cof` to `"1.1"` if it says `"1.0"`, then run `cof validate` — or let the tool do all of it: `cof memory add <file.cof> --identity <id> --gist fr="…" --date 2026-10-25 --personal`.
Do not rewrite existing nodes; a changed feeling is a new `lived` node linked `about` the old one. Never add a memory that shows a real person who is not a consenting identity of this file.

_Written by cof-cli for COF 1.1; regenerate with `cof pack`. Not part of the character._
