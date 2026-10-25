# Example 11 — Clara & Martien (two characters, one file)

A **cast file**: two distinct characters travel together. Each one is a logical container with its own elements, presets, default preset and rights.

| Character | Presets | Rights |
|---|---|---|
| **Clara Mercier** (`clara-mercier`, default) | `default` (EN, 29), `fr` (FR, 29) | root `rights`, copied from example 10: personal non-profit use, no modification, no redistribution |
| **Martien** (`martien`) | `m1-default` | its own `identities.martien.rights`, which **replace** the root rights: modification and redistribution allowed |

What it demonstrates:
- **Relations between the characters (1.1, RFC 0003)** — the file is now `cof: "1.1"`: Clara is `female`, the Martian has no gender (`none`, with a label saying so), and Clara declares one relation — `friend` with the Martian, since 29, "met on a March evening on the Saône embankment". It is stored once; the explorer and `cof export --agent` show the Martian's side too. `cof extract --identity clara-mercier` drops it with a note (the other character is not in the extracted file).
- **Two memories of one evening (1.1, RFC 0002 § 4.5)** — the meeting on the Saône embankment exists twice: Clara's memory (`ev1`, her gist, her feelings, the picture and the remembered lines) and the Martian's (`ev2`, *his* gist — "my first evening on Earth" — and his own feelings), linked `same-event`; the Martian's node shares the picture through `media_from: memories/ev1` and declares who is shown on its own. Each preset lists its character's node. `cof extract --identity martien` keeps the picture (Clara is fictional), rewrites the `who` entry that named her into a plain person, and drops the `same-event` link.
- **Every element belongs to one character.** Each variant carries `identity`, which is required as soon as a file holds several characters. A preset only uses its own character's elements: Clara's face in a Martien preset is a blocking error.
- **Likeness never crosses characters.** A file carrying a face, a body, a voice, weights or a 3D character is used by one character only.
- **Neutral files may be stored once.** The studio background (`a-env-e1-desktop`) is one image used by two distinct environment elements, `e1` (Clara) and `env-martien`. Exporting either character copies it.
- **Rights and default preset per character** (`identities.<id>.rights`, `identities.<id>.default_preset`).
- **Built by `cof merge`.** The sources are the `default` and `fr` presets of example 10 (`cof extract --preset`) and example 04, plus the shared studio. The merge carried each source file's rights onto its character. Export one character back with `cof extract duo.cof --identity martien -o martien/`: its rights become the file's.

Images: see examples 10 and 04 (Google Gemini, CC BY 4.0). Voice samples and motion clips come from example 10, under the same licences.
