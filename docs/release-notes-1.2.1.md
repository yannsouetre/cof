# COF 1.2.1 — 8 November 2026

**Save your Character.AI characters: the character, and your conversations as its private memories, in one open file — then take it further than a backup.**

Character.AI filed for Chapter 11 on 12 October 2026, and its users want a copy of their characters and of their conversations that does not depend on any one app. COF 1.2.1 imports the exports people can make today. It changes no rule of the format: every file it writes is a valid COF 1.1 / 1.2 file, read by every 1.x tool. The conventions are [RFC 0006](../rfcs/0006-platform-import.md), open for comments until 22 November 2026. COF is an independent project, not affiliated with or endorsed by Character.AI; CAI Tools and PersonaText are third-party tools.

## For people coming from Character.AI

- **The import page**, [yannsouetre.github.io/cof/import/](https://yannsouetre.github.io/cof/import/): drop your files at once (a CAI Tools card and history, a PersonaText file, a SillyTavern chat, the official Character.AI zip), check three things (the avatar's age or « import without the avatar », your name in the conversations, the content), and download your `.cof`. A second copy leaves your conversations out, for another app. Six languages. The page reads your files in your browser and nothing else: a Content-Security-Policy forbids it any network request.
- **Your conversations become the character's memories.** One period, « Conversations on Character.AI », and each conversation a memory of its own inside it (`lived`, `personal`, `guarded`), titled by the start of your first message, with its whole transcript.
- **The explorer, Character.AI version**, [yannsouetre.github.io/cof/viewer/character-ai/](https://yannsouetre.github.io/cof/viewer/character-ai/): it welcomes you, opens your file on the graph of its memories, and « + » opens a conversation whole.
- **More than a backup.** The same file can then hold what a COF character carries: looks and outfits, a voice, presets (a look, an age, a style, a language), memories with pictures and sounds, a psyche drawn as a graph (values, fears, wounds, habits, linked to the memories). Add them in the [builder](https://yannsouetre.github.io/cof/builder/); every COF tool reads them.
- **Your conversations stay yours.** They are never written in the character's card, never in the copy without conversations, and every sharing command of COF leaves personal memories out unless asked.
- **A character made by someone else stays theirs**: the file is marked for personal use (no redistribution, no AI training), `tags.ip.original: false`.

## What it does not do

- It never asks for a password and never contacts Character.AI; it reads the files your export tools made.
- It never invents a date: CAI Tools records the time of the export, not of the conversation, so those conversations are « undated »; their period spans the service's lifetime, « between 2022 and 2026 », both bounds marked approximate.
- An avatar is kept only with an age (the age the character looks), or left out on request: COF asks an age for every face, and a face under 18 cannot be tagged `sexual` or `nudity`.
- Account files (e-mail, birthday) found in an export are never read.

## For implementers

- **`cof import`** (cof-cli 1.2.1) reads, by content: CAI Tools cards (PNG, JSON), Tavern chats and history zips, the legacy `histories` JSON, PersonaText, SillyTavern, Oobabooga and the official Character.AI zip (tolerant reading: a flat message list is split by chat id; who speaks is said when it had to be guessed). Options: `--age N|NAME=N`, `--apparent`, `--no-avatar`, `--lang`, `--card-lang`, `--persona`, `--content`, `--no-chats`, `--keep-source`, `--inspect` (an unknown export's structure, every value redacted), `--json`.
- **Memories** (RFC 0006 § 3.2): one `period` per platform, each conversation a `moment` linked `part-of` it — an undated moment needs no date to sit in its period (RFC 0002 § 3.2); `after` between undated chats whose order the export gives; preset tags for the avatar's age and the source (the explorer's left column).
- **Transcript format**: Markdown with a front matter (`cof_transcript: 1`, speakers, `speaker_source: platform | names | inferred-from-greeting | swapped`), each message a heading `## n · speaker · ISO date` and quoted lines; split above 1 MB. RFC 0006 § 3.3.
- **Builder 0.14.1**: « 📥 Import conversations » in the Memories step; a Character.AI card at the Personality step is normalised (conservative rights, content tags suggested from its text, its PersonaText conversation offered as a personal memory).
- **Explorer 1.2.1**: long memory texts fold; imported conversations preview with « + ». `viewer/character-ai/` is generated from it (`tools/viewer-cai/gen.py`).
- The import page is generated from the builder's code (`tools/import-page/gen.py`): the two cannot drift, and a test compares its files with `cof import`'s, byte for byte.

## Known limits

- The readers follow the CAI Tools and PersonaText formats as published; the newest CAI Tools versions and the structure of Character.AI's official export are not documented. An unknown file is said so, with « Report it »: a [GitHub form](https://github.com/yannsouetre/cof/issues/new?template=import-format.yml) that asks for the file's structure (`cof import --inspect`), never its content.
- Images inside conversations are not imported; one language is detected per import (`--lang` to change it).

## Tests

cof-cli tests; builder suites (import, import page against `cof import` byte for byte, the Character.AI explorer, cards, ages, images, objects, psyche); two independent reviews and a bug hunt by five competing agents (56 findings, 39 fixed before the release).
