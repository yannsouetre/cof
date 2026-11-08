# RFC 0006 — Importing a platform export: the character, and each chat as a personal memory

- Status: **published with COF 1.2.1 on 8 November 2026, open for comments until 22 November 2026** (as RFC 0004 and 0005) — validated by Yann on 4 November 2026
- Author: Yann Souetre (with Claude)
- Date: 2026-11-04
- Kind: **conventions only** — no schema change, no new field, no new enum value
- Target: any COF 1.x tool; reference implementation `cof import` (cof-cli 1.2.x) and the builder
- Builds on: RFC 0002 (memories: § 3.3 policy axes, § 4.1 media, § 4.2 `memory.json`, § 5.7 personal data)

## 1. Motivation

Character.AI filed for Chapter 11 on 12 October 2026; its sale is expected in late November or early December 2026 and, without a buyer, the service closes. Its users want to keep their characters **and** their conversations. Exports exist (the extension CAI Tools, PersonaText, the official data export, SillyTavern files), none of them keeps a conversation as what it is: a user's personal data, attached to the character it was held with.

COF already has the right place for it. A conversation is something the user **lived** with the character: a `lived` memory, `visibility: personal`, which `cof extract`, `cof export` and the builder's build drop unless asked (RFC 0002 § 5.7). This RFC fixes how an importer writes it, so that every importer (cof-cli, the builder, a host, a third-party tool) writes the same thing and every reader finds it. It also fixes three things an import must never do.

## 2. What does not change

No schema, no validator rule, no new field. Every file written under this RFC is a valid COF 1.1 file (1.2 if it uses 1.2 fields for other reasons). A 1.0 reader sees a character; a 1.1 reader also sees memories it will not share.

## 3. Conventions (normative for an importer that claims to follow RFC 0006)

### 3.1 The character

1. The card becomes `elements.personality.p1` (Character Card V3, as `cof import` does today). Keys foreign to the Character Card spec that a platform tool adds to `data` (CAI Tools: `metadata`, and the duplicate TavernAI keys `char_name`, `char_persona`, `char_greeting`, `world_scenario`, `example_dialogue`) move to `data.extensions.<tool>` (`cai_tools`), duplicates dropped when equal to their V2 counterpart.
2. **A conversation never goes into the card.** An importer MUST remove from the card every chat payload a tool embedded in it (PersonaText: `data.extensions.chat_history`) and every embedded media it extracts elsewhere (PersonaText: `data.extensions.avatar_data_url`, decoded into the appearance image). The card is canon: it travels with every extract and export, so a chat left inside it escapes the personal-data guard. *(Found on 4 November 2026: `cof import` of a PersonaText file copied the whole chat into `card.json`, and `cof extract` and `cof export --format card` carried it — fixed in cof-cli 1.2.0 and the builder by `strip_card_payloads`. A platform importer goes further: the chat becomes personal memories, the avatar a face. For files made before the fix, the sharing paths — `cof extract`, `cof export --format png|card`, a builder's build — leave such a payload out of the copy they write, unless the user keeps personal data, and say so; the source file is never modified.)*
3. `tags.ip.original: false` (an imported character is not presented as the importer's original work); `franchise` only when the card names one, never guessed.
4. Rights: the conservative defaults of `cof import` (`personalNonProfit`, no redistribution, no training, `creditNotation: required`). The creator handle, when the export carries it, goes to the card's `creator` and `metadata."dc:creator"`.
5. `fictional`: `true` unless the user says the character is a real person. The import report says it was not verified.
6. Avatar: the face needs an age (SPEC § 9.4). The importer asks for it — declared (`basis: declared`) or apparent (`basis: apparent`, a number is still required). Without an answer the import **stops** and says why, so that an avatar is never lost by oversight; the user who really wants to go on without it says so explicitly (`cof import --no-avatar`, the builder's "Import without avatar"), and the report recalls it. An importer never guesses an age.

### 3.2 One period per platform, one moment per chat

The conversations of one platform become **one** node of kind `period` (« Conversations on Character.AI »), and each conversation **one** node of kind `moment` linked `part-of` that period (RFC 0002 § 3.2: the link settles the undated — a moment needs no date to sit in its period).

The period:

| Field | Value |
|---|---|
| variant id / label | `ep<n>`, numbered in the order the platforms first appear / "Conversations on <platform>" (localised) |
| `gist` | a mechanical sentence: who, which platform, how many conversations and messages, dated or not |
| `when` | when every chat of the platform is dated, `from.date` / `to.date` = the days of the earliest and latest messages (real timestamps only). Otherwise, for Character.AI, the service's lifetime with both bounds approximate — `from: { date: "2022", approx: true }`, `to: { date: <export year>, approx: true }` (Character.AI opened in September 2022; no chat is older, none is later than its export) — and `when.label` « on Character.AI, between 2022 and <export year> (exact dates not in the export) »: a reader draws the period, its conversations stay undated |
| `nature`, `origin` / `visibility` / `disclosure`, `fidelity`, `who`, `tags` | as for the moments below; no media |

Each conversation:

| Field | Value |
|---|---|
| variant id / label | `ev<n>` / « Chat <n> · <title> » (localised); `n` follows the conversations' order, oldest first when the export tells it (a CAI Tools history zip numbers its files from the newest, `chat_1`: they are imported in reverse, and `source_file` keeps the original name). The exports name no conversation: the title is the start of the user's first message (else of the first message), whitespace collapsed, 48 characters at most, cut at a space when one is near, « … » when cut — « Chat <n> » alone when there is no text |
| `gist` | a mechanical sentence in the language of the conversations (given, else detected — kana, Han characters, stop words of en / fr / de / es —, else English; the card's language is settled the same way, separately): who, which platform, how many messages, dated or not — no summary, no AI (§ 5) |
| `nature` | `["experienced"]` |
| `origin` / `visibility` / `disclosure` | `lived` / `personal` / `guarded` |
| `fidelity` | `clear` |
| `who` | one entry, the user's persona: `{ "label": { <lang>: <persona name: the one given, else the chat's own, else the one another chat of the import gives, else "You"> } }` — not `shown` (nobody is shown in a text), no `real` (§ 3.4) |
| `when` | **only from real timestamps**: `date` = the day of the earliest message (the transcript's front matter keeps the first and last instants). Without real timestamps, no `when` at all: the period says where it sits |
| `links` | `part-of` the platform's period, first; for undated chats whose order the export gives, then `after` from the later chat to the earlier |
| `tags` | the platform slug first (`character-ai`: readers that show one keyword show it), then `imported` |
| media | the transcript (§ 3.3) |

A builder that imports again for a platform that already has its period adds the new moments to it. A tool MAY later add other `moment` nodes `part-of` the period (memories distilled from a transcript, with the user's own model key and review); that is out of the scope of this RFC.

### 3.3 The transcript

One `memory-media` asset per chat: `text/markdown` (set explicitly, never guessed from the extension), `language` = the user's language, `license: LicenseRef-Personal`, `digitalSourceType: http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia` (a human's and a model's messages together), path `elements/memories/ep<n>/chat-<n>.md`.

Layout (UTF-8, `\n`, one trailing newline):

```
---
cof_transcript: 1
source: import:character.ai/caitools-tavern-history
character: Wren Calloway
user_persona: You
messages: 4
speaker_source: platform          # platform | names | inferred-from-greeting | swapped
dated: false                      # true only with real timestamps
first: 2026-10-20T09:12:44Z       # only when dated
last: 2026-10-20T09:40:02Z
part: 1/1                         # when a chat is split
exported_by: cof-cli 1.2.x
---

## 1 · Wren Calloway · undated
> *Wren looks up from a half-inked chart.* Ah, a visitor.

## 2 · You · undated
> I lost the teapot island.
```

- Heading `## <n> · <speaker> · <ISO 8601 UTC time | undated>`; every line of a message prefixed `> ` (`>` for an empty line), so a message never collides with a heading or the front matter, and stripping the prefix gives the text back exactly, every line ending (CR LF, CR, LF) written as LF — so that no line of a message can escape its quote (the exact source bytes are what `--keep-source` keeps); `*actions*`, `{{user}}` / `{{char}}` and HTML entities kept as they are; system and narrator lines use the speaker `[note]`; alternative replies (swipes) are dropped, the chosen one is kept.
- Above **1 MB** a chat MAY be split into `chat-<n>.part-<k>.md`, several media of the same node, `part: k/K` in each front matter.
- **Clarification of RFC 0002 § 4.1.** "A short text (a few remembered lines of a conversation)" describes what an author writes. On a `lived` node, a text media MAY be the verbatim trace of the exchange, however long: it is opened on demand, never loaded with the gists. Readers SHOULD show a long text folded, with its first lines (this RFC proposes the same sentence for RFC 0002 during its comment period).

### 3.4 Speakers

When the export says who speaks (`is_user`, `src.is_human`, `role`), `speaker_source: platform`. When only the speakers' names tell the character's lines apart, `names`. When nothing does (the official Character.AI export, per LoreWeaver), the importer infers — the first message is the character's greeting, then turns alternate — writes `speaker_source: inferred-from-greeting` in the front matter, and shows the first three messages in its report. Names taken from inferred speakers never name the character (the first speaker could be the user). The user's persona is named, never marked `real: true`: absent means "not stated", and the warning `real` raises for an unmodelled person would repeat on every chat without protecting anyone (the node is already personal). When the first message is credited to the user and is word for word the card's greeting, the export swapped the two (a known CAI Tools issue): the importer turns every line back, writes `speaker_source: swapped` and says so.

### 3.5 Provenance

`provenance.source` gains one entry per file read: `import:<platform>/<format>`. Platform: `character.ai` when the file says so (CAI Tools, PersonaText), else the tool (`sillytavern`). Formats of the reference implementation: `caitools-card-png`, `caitools-card-json`, `caitools-tavern-chat`, `caitools-tavern-history`, `caitools-histories-json`, `personatext`, `sillytavern-jsonl`, `oobabooga-json`, `official-zip`; a plain Character Card given together with chats is `import:card/card-png` or `import:card/card-json`. A transcript's own front matter repeats its source.

### 3.6 Content flags

`tags.content` needs at least one value and has no "not reviewed". An importer runs a keyword pass on the card and the transcripts (no AI) and asks the user (the builder always asks). `tags.content` then holds what the user confirmed, or what the keyword pass found **in the card** (every string of it: greetings, lorebook, prompts, extensions), or `["none"]` when nothing was flagged — what the pass finds in the conversations is reported to the user and never written in `tags.content`, which would outlive the personal memories in an extracted file; **and** while no person has confirmed it, `tags.manual` carries the tag **`content-unreviewed`**, which a builder removes when the user confirms. A reader that knows this convention treats such a file as not classified. (Alternatives in § 5.)

COF's age rule applies as everywhere: with an avatar under 18, `sexual` and `nudity` cannot be chosen, and the keyword pass never suggests them. The importer never infers, asks or stores the user's own age.

### 3.7 What an importer never does

1. Contact the platform, ask for a token or a password, or download anything (an image URL in a message stays text).
2. Copy account data (e-mail, birth date, account ids of the user) found in an export: only characters and chats are read. Archive entries and files whose **whole name** is an account file's (`user.json`, `account_settings.json`, `personas.json`, `profile.json`…) are not read (the report counts them) — a part of a name never decides (`wren.personatext.json` is a chat); an object carrying an e-mail, a password, a birth date or a phone number is never a character; in the official export the creator handle is not mapped (it may be the user's own). The optional copy of a source chat file beside its transcript (`--keep-source`, personal media) is offered only for files that hold one conversation and no account data (CAI Tools and SillyTavern chats, PersonaText, Oobabooga).
3. Execute or trust anything in the files: they are untrusted input (size, entry, compression-ratio and nesting limits on archives, no `..` paths, bounded JSON depth, invalid UTF-8 and truncated files reported, never fatal to the rest of the import).
4. Write part of an import: every check that can stop it (avatar age, options, destinations) runs for every character before the first file is written.
5. Put a conversation's text in the card: a character known only from a chat gets its name, nothing else.

## 4. Impact and compatibility

None on files: everything above is expressible in COF 1.1. Tools: `cof import` gains formats and options; the builder gains a chat import in the Memories step; the explorer folds long texts; `docs/IMPLEMENTING.md` gains a section "importing from a platform". Each personal node raises one validator warning: the importer's report groups them.

## 5. Alternatives considered

- **One node per message, or AI-distilled moments at import.** Too many nodes, and an AI summary would be a guess presented as a memory; distillation stays a later, explicit step with the user's key and review.
- **Transcript as JSONL** (`application/x-ndjson`). Lossless but outside RFC 0002 § 4.1 (`text/markdown` / `text/plain`), unreadable for a person, not shown by readers. The quoted Markdown is lossless too.
- **A `files` variant of kind `memory`.** Has no personal visibility: it would travel with every export.
- **`visibility: canon`.** Would make a user's chats part of the character for everyone who receives the file.
- **A new `tags.content` value `unknown`** (additive, files would declare 1.3). Truer and machine-readable, but a format change: the import would wait for a 1.3, and every host would have to decide what `unknown` means. Can come later by its own RFC if hosts ask for it.
- **A mandatory content question, no convention.** Batch imports would stop at every character, and a hurried "none" would look reviewed.
- **Leaving the avatar out when no age is given.** An avatar lost by oversight, possibly after the platform has closed (§ 3.1.6 stops instead, with an explicit way out).
- **`who[].real: true` for the user** (RFC 0002 § 5.9 asks it when a host *shows* the user in a media): nobody is shown in a text; see § 3.4.

## 6. Open questions

1. The official export: its structure is unknown; the convention holds whatever it is, the reference parser stays tolerant until a real file (or its key tree, `cof import --inspect`) is available.
