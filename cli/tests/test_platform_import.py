"""Platform import (RFC 0006): Character.AI exports (CAI Tools, PersonaText, the official zip), SillyTavern, Oobabooga.
Each conversation becomes ONE personal moment memory (part-of one period per platform) with a quoted-Markdown transcript; the character becomes a COF
character; nothing personal travels with extract / export; hostile files never crash nor write anything ambiguous."""
import json
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pytest

from cof_cli import platform_import as PI
from cof_cli.validate import Report, validate_dir

ROOT = Path(__file__).resolve().parents[2]
FX = ROOT / "tests" / "fixtures" / "platform-import"


def cof(*args, cwd=None):
    return subprocess.run([sys.executable, "-c", "import sys; from cof_cli.cli import main; sys.exit(main())", *map(str, args)],
                          capture_output=True, text=True, cwd=cwd)


def valid(d: Path) -> Report:
    rep = Report(); validate_dir(d, rep, recompute=True)
    assert not rep.errors, rep.errors
    return rep


def manifest(d: Path) -> dict:
    return json.loads((d / "manifest.json").read_text("utf-8"))


def node(d: Path, vid: str) -> dict:
    return json.loads((d / "elements" / "memories" / vid / "memory.json").read_text("utf-8"))


def all_text(d: Path) -> str:
    return "\n".join(p.read_text("utf-8", errors="replace") for p in d.rglob("*") if p.is_file() and p.suffix in (".json", ".md", ".jsonl"))


def assert_personal_chat(d: Path, vid: str):
    n = node(d, vid)
    assert (n["origin"], n["visibility"], n["disclosure"], n["nature"], n["fidelity"]) == ("lived", "personal", "guarded", ["experienced"], "clear")
    v = manifest(d)["elements"]["memories"]["variants"][vid]
    assert v["kind"] == "moment" and v["media"]
    assert n["links"][0]["type"] == "part-of" and manifest(d)["elements"]["memories"]["variants"][n["links"][0]["to"].split("/")[1]]["kind"] == "period"
    A = {a["id"]: a for a in manifest(d)["assets"]}
    for aid in v["media"]:
        a = A[aid]
        assert a["role"] == "memory-media" and a["license"] == "LicenseRef-Personal"
        if a["mediaType"] == "text/markdown":
            assert a["language"] and a["digitalSourceType"].endswith("compositeWithTrainedAlgorithmicMedia")
    return n


# ---------------------------------------------------------------- formats

def test_caitools_card_png_and_history_zip(tmp_path):
    out = tmp_path / "wren"
    r = cof("import", FX / "caitools-card.png", FX / "Wren_Calloway_TavernHistory.zip", "-o", out, "--age", "30")
    assert r.returncode == 0, r.stdout + r.stderr
    valid(out)
    m = manifest(out)
    assert m["cof"] == "1.1" and m["name"] == "Wren Calloway"
    assert m["tags"]["ip"]["original"] is False and "content-unreviewed" in m["tags"]["manual"] and "imported-character-ai" in m["tags"]["manual"]
    assert m["provenance"]["source"][-2:] == ["import:character.ai/caitools-card-png", "import:character.ai/caitools-tavern-history"]
    assert m["rights"]["permissions"]["allowRedistribution"] is False and m["rights"]["permissions"]["allowTraining"] == "none"
    assert m["elements"]["appearance"]["variants"]["f1"]["age"] == {"value": 30, "unit": "years", "basis": "declared"}
    card = json.loads((out / "elements/personality/p1/card.json").read_text("utf-8"))["data"]
    assert "metadata" not in card and not any(k.startswith("char_") for k in card)
    assert card["extensions"]["cai_tools"]["metadata"]["tool"]["name"] == "CAI Tools"
    png = (out / "elements/appearance/f1/head.front.png").read_bytes()
    assert b"chara\x00" not in png                                   # the card lives in the personality, not twice
    # two chats, oldest first (chat_2.jsonl is the oldest), undated, ordered by an `after` link
    # RFC 0006 § 3.2: one period « Conversations on Character.AI » with the label, each chat an undated moment part-of it
    n1, n2 = assert_personal_chat(out, "ev1"), assert_personal_chat(out, "ev2")
    assert node(out, "ep1")["when"] == {"from": {"date": "2022", "approx": True}, "to": {"date": "2026", "approx": True},
                                        "label": {"en": "on Character.AI, between 2022 and 2026 (exact dates not in the export)"}}   # the service's lifetime, approximate
    assert "when" not in n1 and "when" not in n2 and m["elements"]["memories"]["variants"]["ep1"]["label"] == "Conversations on Character.AI"
    assert n2["links"] == [{"to": "memories/ep1", "type": "part-of"}, {"to": "memories/ev1", "type": "after"}] and n1["links"] == [{"to": "memories/ep1", "type": "part-of"}]
    assert m["elements"]["memories"]["variants"]["ev1"]["label"].startswith("Chat 1 · ")
    md1 = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "source_file: chat_2.jsonl" in md1 and "dated: false" in md1 and "(second chat)" in md1 and "1793" not in md1
    assert m["presets"]["default"]["slots"]["memories"] == ["ep1", "ev1", "ev2"]
    assert "3 personal memories" in r.stdout and "CAI Tools chats without real dates" in r.stdout
    assert (out / "COF.md").is_file()


def test_avatar_needs_an_age_or_an_explicit_no_avatar(tmp_path):
    out = tmp_path / "w"
    r = cof("import", FX / "caitools-card.png", "-o", out)
    assert r.returncode == 3 and "needs an age" in r.stderr and not out.exists()
    r = cof("import", FX / "caitools-card.png", "-o", out, "--no-avatar")
    assert r.returncode == 0, r.stderr
    assert "appearance" not in manifest(out)["elements"] and "avatar left out on request" in r.stdout
    out2 = tmp_path / "w2"
    r = cof("import", FX / "caitools-card.png", "-o", out2, "--age", "25", "--apparent")
    assert r.returncode == 0, r.stderr
    m = manifest(out2)
    assert m["elements"]["appearance"]["variants"]["f1"]["age"]["basis"] == "apparent" and m["presets"]["default"]["age_override"]["basis"] == "apparent"
    valid(out2)


def test_caitools_hybrid_json_card_is_normalised(tmp_path):
    out = tmp_path / "w"
    assert cof("import", FX / "caitools-card.json", "-o", out).returncode == 0
    card = json.loads((out / "elements/personality/p1/card.json").read_text("utf-8"))["data"]
    for k in ("char_name", "char_persona", "char_greeting", "world_scenario", "example_dialogue", "metadata"):
        assert k not in card
    assert "char_name" not in card["extensions"]["cai_tools"]                 # equal duplicates dropped
    assert card["personality"] == "Cartographer of the Lantern Sea" and card["first_mes"].startswith("*Wren")
    valid(out)


def test_caitools_tavern_chat_alone_makes_a_character_from_the_chat(tmp_path):
    out = tmp_path / "w"
    r = cof("import", FX / "caitools-chat.jsonl", "-o", out, "--lang", "fr", "--persona", "Yann")
    assert r.returncode == 0, r.stderr
    valid(out)
    n, p = assert_personal_chat(out, "ev1"), node(out, "ep1")
    assert "when" not in n and set(p["when"]) == {"from", "to", "label"} and p["when"]["from"] == {"date": "2022", "approx": True} and "2022" in p["when"]["label"]["fr"] and n["who"] == [{"label": {"fr": "Yann"}}] == p["who"]
    assert n["gist"]["fr"].startswith("Ma conversation avec Wren Calloway sur Character.AI") and p["gist"]["fr"].startswith("Ma conversation avec Wren Calloway sur Character.AI, ")
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "## 2 · Yann · undated" in md and "Café au lait" in md and "☕" in md
    card = (out / "elements/personality/p1/card.json").read_text("utf-8")
    assert json.loads(card)["data"]["first_mes"] == "" and "Café" not in card and "teapot" not in card    # RFC 0006 § 3.1.2
    assert "character made with its name only" in r.stdout
    x = tmp_path / "x"; assert cof("extract", out, "--preset", "default", "-o", x).returncode == 0
    assert "teapot" not in all_text(x) and "Yann" not in all_text(x)


def test_sillytavern_dated_swipes_and_notes(tmp_path):
    out = tmp_path / "w"
    r = cof("import", FX / "sillytavern-chat.jsonl", "-o", out)
    assert r.returncode == 0, r.stderr
    valid(out)
    n = assert_personal_chat(out, "ev1")
    assert n["when"] == {"date": "2026-11-02"} and node(out, "ep1")["when"] == {"from": {"date": "2026-11-02"}, "to": {"date": "2026-11-02"}} and n["who"][0]["label"]["en"] == "Sam"
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "first: 2026-11-02T18:04:11Z" in md and "## 4 · [note] · 2026-11-02T18:06:00Z" in md and "barely glances" not in md
    assert "swipes) dropped: 1" in r.stdout and "import:sillytavern/sillytavern-jsonl" in manifest(out)["provenance"]["source"]


def test_caitools_legacy_histories(tmp_path):
    out = tmp_path / "w"
    assert cof("import", FX / "caitools-legacy-histories.json", "-o", out).returncode == 0
    valid(out)
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "speaker_source: platform" in md and "## 2 · You · undated" in md


def test_personatext_with_avatar_dates_and_lorebook(tmp_path):
    out = tmp_path / "w"
    r = cof("import", FX / "wren.personatext.json", "-o", out)
    assert r.returncode == 3 and not out.exists()                            # an avatar is embedded: its age first
    r = cof("import", FX / "wren.personatext.json", "-o", out, "--age", "Wren Calloway=34")
    assert r.returncode == 0, r.stdout + r.stderr
    valid(out)
    m = manifest(out)
    f1 = m["elements"]["appearance"]["variants"]["f1"]
    assert f1["age"]["value"] == 34 and (out / "elements/appearance/f1/head.front.webp").is_file()
    assert next(a for a in m["assets"] if a["id"] == "a-face-f1-front")["mediaType"] == "image/webp"
    card = json.loads((out / "elements/personality/p1/card.json").read_text("utf-8"))["data"]
    assert "chat_history" not in card["extensions"] and "avatar_data_url" not in card["extensions"]
    assert card["character_book"]["entries"][0]["keys"] == ["Teapot Island"] and card["extensions"]["character_ai"]["external_id"] == "synthetic-wren-0001"
    assert m["metadata"]["dc:creator"] == ["example_creator_handle"]
    n = assert_personal_chat(out, "ev1")
    assert n["when"] == {"date": "2026-10-20"} and node(out, "ep1")["when"] == {"from": {"date": "2026-10-20"}, "to": {"date": "2026-10-21"}}
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "> ## not a heading" in md and "> > not a quote" in md


def test_oobabooga(tmp_path):
    src = tmp_path / "o.json"
    src.write_text(json.dumps({"internal": [["hi", "hello there"]], "visible": [["hi", "hello there"]], "data": [], "data_visible": [["hi", "hello there"], ["bye", "see you"]]}), "utf-8")
    out = tmp_path / "w"
    r = cof("import", src, "-o", out)
    assert r.returncode == 0, r.stderr
    valid(out)
    assert "import:oobabooga/oobabooga-json" in manifest(out)["provenance"]["source"]


def _official_zip(p: Path, with_authors=False):
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("export/user.json", json.dumps({"email": "secret@example.org", "date_joined": "2023-01-01"}))
        z.writestr("export/personas.json", json.dumps([{"name": "Sam Dupont", "definition": "34, nurse in Lyon", "greeting": ""}]))
        z.writestr("export/user_settings.json", json.dumps({"email": "secret@example.org", "name": "Sam Dupont", "first_message": "x"}))
        z.writestr("export/characters.json", json.dumps([{"name": "Wren Calloway", "greeting": "Ah, a visitor.", "definition": "A cartographer.", "user__username": "maker"}]))
        msgs = [{"text": "Ah, a visitor."}, {"text": "I lost an island."}, {"text": "Everyone does."}]
        if with_authors:
            msgs = [dict(x, src__is_human=i % 2 == 1, src__name="You" if i % 2 else "Wren Calloway") for i, x in enumerate(msgs)]
        z.writestr("export/chats.json", json.dumps({"histories": [{"msgs": msgs}]}) if with_authors else json.dumps({"chats": [{"turns": msgs}]}))
        z.writestr("export/readme.txt", "hello")


def test_official_zip_tolerant_inferred_speakers_and_no_account_data(tmp_path):
    z = tmp_path / "official.zip"; _official_zip(z)
    out = tmp_path / "w"
    r = cof("import", z, "-o", out)
    assert r.returncode == 0, r.stdout + r.stderr
    valid(out)
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "speaker_source: inferred-from-greeting" in md and "## 1 · Wren Calloway · undated" in md and "## 2 · You · undated" in md
    assert "who speaks was inferred" in r.stdout and "account files never read" in r.stdout
    assert "secret@example.org" not in all_text(out)
    assert json.loads((out / "elements/personality/p1/card.json").read_text("utf-8"))["data"]["creator"] == ""   # may be the user's own handle
    assert [p.name for p in tmp_path.iterdir() if p.is_dir()] == ["w"]


# ---------------------------------------------------------------- personal data guard

def test_personal_chats_never_travel_with_extract_or_export(tmp_path):
    out = tmp_path / "w"
    assert cof("import", FX / "sillytavern-chat.jsonl", "-o", out).returncode == 0
    secret = "I lost the teapot island."
    assert secret in all_text(out)
    x = tmp_path / "x"; assert cof("extract", out, "--preset", "default", "-o", x).returncode == 0
    assert secret not in all_text(x) and not (x / "elements" / "memories").exists()
    for fmt, dst in (("agent", tmp_path / "ag"), ("soul", tmp_path / "so"), ("card", tmp_path / "c.json")):
        assert cof("export", out, "--format", fmt, "-o", dst).returncode == 0
        t = all_text(dst) if dst.is_dir() else dst.read_text("utf-8")
        assert secret not in t, fmt
    k = tmp_path / "k"; assert cof("extract", out, "--preset", "default", "-o", k, "--keep-personal").returncode == 0
    assert secret in all_text(k)


# ---------------------------------------------------------------- transcript

def test_transcript_round_trip_is_exact():
    texts = ["plain", "two\nlines", "", "## looks like a heading", "> looks like a quote", "trailing space ", "\n\nblank around\n\n", "---", "emoji ☕ é"]
    msgs = [PI.Message(speaker="Wren" if i % 2 == 0 else "You", is_user=i % 2 == 1, text=t) for i, t in enumerate(texts)]
    chat = PI.Chat(messages=msgs, fmt="sillytavern-jsonl")
    md = PI.transcript_parts(chat, "Wren", "You", "import:sillytavern/sillytavern-jsonl")[0]
    assert [t for _, t in PI.read_transcript(md)] == texts
    assert md.endswith("\n") and md.startswith("---\ncof_transcript: 1\n")


def test_long_chat_is_split_and_fast(tmp_path):
    src = tmp_path / "big.jsonl"
    lines = [json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"})]
    for i in range(10_000):
        lines.append(json.dumps({"name": "You" if i % 2 else "Wren", "is_user": bool(i % 2), "send_date": 1790000000000 + i * 60000, "mes": f"message {i} " + "x" * 150}))
    src.write_text("\n".join(lines), "utf-8")
    out = tmp_path / "w"
    t = time.time()
    r = cof("import", src, "-o", out)
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 30
    valid(out)
    parts = sorted((out / "elements/memories/ev1").glob("chat-1.part-*.md"))
    assert len(parts) >= 2 and all(p.stat().st_size <= PI.SPLIT_BYTES + 2000 for p in parts)
    assert "part: 1/" in parts[0].read_text("utf-8")
    assert len(manifest(out)["elements"]["memories"]["variants"]["ev1"]["media"]) == len(parts)


# ---------------------------------------------------------------- hostile files

def test_keyword_pass_flags_content_and_content_option_settles_it(tmp_path):
    src = tmp_path / "v.jsonl"
    src.write_text("\n".join([json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"}),
                              json.dumps({"name": "X", "is_user": False, "send_date": "2026-01-01T10:00:00Z", "mes": "The knight was stabbed, blood everywhere."}),
                              json.dumps({"name": "You", "is_user": True, "send_date": "2026-01-01T10:01:00Z", "mes": "Oh no."})]), "utf-8")
    out = tmp_path / "w"
    r = cof("import", src, "-o", out)
    m = manifest(out)
    # the conversations' flags are reported, never written: they would outlive the personal memories in an extracted file
    assert m["tags"]["content"] == ["none"] and "content-unreviewed" in m["tags"]["manual"] and "your conversations mention violence" in r.stdout
    out2 = tmp_path / "w2"
    assert cof("import", src, "-o", out2, "--content", "violence,horror").returncode == 0
    m = manifest(out2)
    assert m["tags"]["content"] == ["violence", "horror"] and "content-unreviewed" not in m["tags"]["manual"]


def test_unrecognised_truncated_and_invalid_utf8(tmp_path):
    (tmp_path / "u.json").write_text('{"foo": 1}', "utf-8")
    (tmp_path / "t.json").write_text('{"spec": "chara_card_v2", "data": {"name": "W', "utf-8")
    for f in ("u.json", "t.json"):
        r = cof("import", tmp_path / f, "-o", tmp_path / ("o-" + f))
        assert r.returncode == 1 and "not a recognised export" in r.stderr and not (tmp_path / ("o-" + f)).exists()
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes(b'{"chat_metadata": {}, "user_name": "unused"}\n{"name": "W", "is_user": false, "mes": "caf\xe9 ok"}\n{not json}\n{"name": "You", "is_user": true, "mes": ""}\n')
    out = tmp_path / "w"
    r = cof("import", bad, "-o", out)
    assert r.returncode == 0, r.stderr
    assert "not valid UTF-8" in r.stdout and "illegible lines (not JSON): 1" in r.stdout and "empty messages: 1" in r.stdout
    valid(out)


def test_zip_with_unsafe_paths_and_bomb_limits(tmp_path, monkeypatch):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("../escape.json", "{}")
        f.writestr("/abs.json", "{}")
        f.writestr("chats.json", json.dumps({"chats": [{"turns": [{"text": "hi"}, {"text": "hello"}]}]}))
    out = tmp_path / "w"
    r = cof("import", z, "-o", out)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.count("unsafe path skipped") == 2 and not (tmp_path / "escape.json").exists()
    rep = PI.Report()
    monkeypatch.setattr(PI, "MAX_ZIP_ENTRIES", 2)
    with pytest.raises(PI.ImportStop):
        list(PI._zip_entries(z, rep))


def test_output_folder_not_empty_is_refused(tmp_path):
    out = tmp_path / "w"; out.mkdir(); (out / "keep.txt").write_text("mine")
    r = cof("import", FX / "caitools-chat.jsonl", "-o", out)
    assert r.returncode == 2 and (out / "keep.txt").read_text() == "mine" and not (out / "manifest.json").exists()


def test_same_chat_twice_is_imported_once(tmp_path):
    out = tmp_path / "w"
    shutil.copy(FX / "caitools-chat.jsonl", tmp_path / "again.jsonl")
    r = cof("import", FX / "caitools-chat.jsonl", tmp_path / "again.jsonl", "-o", out)
    assert r.returncode == 0 and list(manifest(out)["elements"]["memories"]["variants"]) == ["ep1", "ev1"] and "imported once" in r.stdout


def test_several_characters_make_several_cofs(tmp_path):
    other = tmp_path / "other.jsonl"
    other.write_text("\n".join([json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"}),
                                json.dumps({"name": "Mira", "is_user": False, "send_date": "2026-01-01T10:00:00Z", "mes": "Hi."}),
                                json.dumps({"name": "You", "is_user": True, "send_date": "2026-01-01T10:01:00Z", "mes": "Hello."})]), "utf-8")
    out = tmp_path / "all"
    r = cof("import", FX / "sillytavern-chat.jsonl", other, "-o", out)
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in out.iterdir()) == ["Mira", "Wren-Calloway"]


def test_inspect_shows_structure_never_values(tmp_path):
    z = tmp_path / "official.zip"; _official_zip(z, with_authors=True)
    for src in (z, FX / "wren.personatext.json", FX / "sillytavern-chat.jsonl"):
        r = cof("import", "--inspect", src)
        assert r.returncode == 0
        for secret in ("secret@example.org", "Wren", "teapot", "visitor", "cartographer", "2026-"):
            assert secret not in r.stdout, (src, secret)
    assert not list(tmp_path.glob("Wren*"))


def test_plain_card_import_is_unchanged(tmp_path):
    """A V2 card that is not a platform export keeps the 1.0 behaviour (avatar only with --keep-png, ip.original true)."""
    card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {"name": "Ada", "description": "An engineer.", "first_mes": "Hello.", "tags": ["Sci-Fi"]}}
    src = tmp_path / "ada.json"; src.write_text(json.dumps(card), "utf-8")
    out = tmp_path / "ada"
    r = cof("import", src, "-o", out, "--age", "30")
    assert r.returncode == 0, r.stderr
    m = manifest(out)
    assert m["tags"]["ip"]["original"] is True and "content-unreviewed" not in m["tags"]["manual"] and m["tags"]["manual"] == ["sci-fi"]
    assert "memories" not in m["elements"] and "import report" not in r.stdout


# ---------------------------------------------------------------- after the independent review (5 November)

def _pt_card(**data):
    d = {"name": "Wren Calloway", "description": "A cartographer.", "first_mes": "Hi.", "extensions": {"source": "character.ai"}}
    d.update(data)
    return {"spec": "chara_card_v2", "spec_version": "2.0", "data": d}


def test_content_pass_reads_every_string_of_the_card(tmp_path):
    v = tmp_path / "v.personatext.json"
    v.write_text(json.dumps(_pt_card(alternate_greetings=["The duel ends in blood."])), "utf-8")
    assert cof("import", v, "-o", tmp_path / "v").returncode == 0
    assert manifest(tmp_path / "v")["tags"]["content"] == ["violence"]


def test_a_stop_on_any_character_writes_nothing_at_all(tmp_path):
    out = tmp_path / "all"
    r = cof("import", FX / "caitools-card.png", FX / "sillytavern-chat.jsonl", FX / "wren.personatext.json", "-o", out)
    assert r.returncode in (0, 3) and (r.returncode == 0 or not out.exists())


def test_non_latin_names_get_distinct_folders(tmp_path):
    files = []
    for n in ("ウィン", "レン"):
        f = tmp_path / f"{len(files)}.jsonl"
        f.write_text("\n".join([json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"}),
                                json.dumps({"name": n, "is_user": False, "send_date": "2026-01-01T10:00:00Z", "mes": "こんにちは"}),
                                json.dumps({"name": "You", "is_user": True, "send_date": "2026-01-01T10:01:00Z", "mes": "やあ"})]), "utf-8")
        files.append(f)
    out = tmp_path / "jp"
    r = cof("import", *files, "-o", out, "--lang", "ja")
    assert r.returncode == 0, r.stderr
    assert sorted(p.name for p in out.iterdir()) == sorted(["ウィン", "レン"])


@pytest.mark.parametrize("name,content", [
    ("swipes.jsonl", '{"chat_metadata":{}}\n{"name":"W","is_user":false,"mes":"hi","swipes":5}\n'),
    ("ext.json", json.dumps({"char_name": "W", "first_mes": "hi", "metadata": {"tool": {"name": "CAI Tools"}}, "extensions": "x"})),
    ("desc.personatext.json", json.dumps({"spec": "chara_card_v2", "data": {"name": "W", "description": {"a": 1}, "source": 5, "extensions": {"source": "character.ai"}}})),
    ("deep.personatext.json", '{"spec":"chara_card_v2","data":{"name":"W","extensions":{"source":"character.ai","x":' + "[" * 600 + "]" * 600 + "}}}"),
    ("list.json", "[1, 2, 3]"),
])
def test_malformed_inputs_never_crash(tmp_path, name, content):
    src = tmp_path / name; src.write_text(content, "utf-8")
    r = cof("import", src, "-o", tmp_path / "o")
    assert "Traceback" not in r.stderr and r.returncode in (0, 1), r.stderr
    r = cof("import", "--inspect", src)
    assert "Traceback" not in r.stderr


def test_png_with_a_non_object_card(tmp_path):
    import base64, struct, zlib
    def chunk(t, b): return struct.pack(">I", len(b)) + t + b + struct.pack(">I", zlib.crc32(t + b) & 0xFFFFFFFF)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00")) \
        + chunk(b"tEXt", b"chara\x00" + base64.b64encode(b"[1,2]")) + chunk(b"IEND", b"")
    src = tmp_path / "c.png"; src.write_bytes(png)
    for args in (("import", src, "-o", tmp_path / "o"), ("import", "--inspect", src)):
        r = cof(*args)
        assert "Traceback" not in r.stderr


def test_zip_ratio_nesting_and_odd_entry_names(tmp_path):
    bomb = tmp_path / "bomb.zip"
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("chats.json", b"0" * (3 * 2**20))
    rep = PI.Report()
    assert list(PI._zip_entries(bomb, rep)) == [] and any("too compressed" in a for a in rep.alerts)
    inner = tmp_path / "inner.zip"
    shutil.copy(FX / "Wren_Calloway_TavernHistory.zip", inner)
    cur = inner
    for i in range(4):
        nxt = tmp_path / f"n{i}.zip"
        with zipfile.ZipFile(nxt, "w") as z:
            z.write(cur, f"a{i}.zip")
        cur = nxt
    r = cof("import", cur, "-o", tmp_path / "nest")
    assert "Traceback" not in r.stderr and "nested too deep" in (r.stdout + r.stderr)
    odd = tmp_path / "odd.zip"
    with zipfile.ZipFile(odd, "w") as z:
        z.writestr("x" * 300 + ".jsonl", (FX / "sillytavern-chat.jsonl").read_text("utf-8"))
        z.writestr("chat.jsonl", (FX / "caitools-chat.jsonl").read_text("utf-8"))
    r = cof("import", odd, "-o", tmp_path / "odd")
    assert r.returncode == 0 and "Traceback" not in r.stderr, r.stderr


def test_speaker_names_and_line_endings_cannot_break_the_transcript(tmp_path):
    src = tmp_path / "inj.jsonl"
    src.write_text("\n".join([json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"}),
                              json.dumps({"name": "Wren\n## 9 · Fake · undated", "is_user": False, "send_date": "2026-01-01T10:00:00Z", "mes": "line one\r\nline two"}),
                              json.dumps({"name": "You", "is_user": True, "send_date": "2026-01-01T10:01:00Z", "mes": "ok"})]), "utf-8")
    out = tmp_path / "w"
    assert cof("import", src, "-o", out).returncode == 0
    md = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8", errors="strict")
    md = (out / "elements/memories/ev1/chat-1.md").read_bytes().decode("utf-8")
    msgs = PI.read_transcript(md)
    assert len(msgs) == 2 and msgs[0][1] == "line one\nline two" and "\n" not in manifest(out)["name"]


def test_plain_tavernai_v1_card_keeps_the_1_0_path(tmp_path):
    src = tmp_path / "pyg.json"
    src.write_text(json.dumps({"char_name": "Pyg Bot", "char_persona": "A bot.", "char_greeting": "Hello."}), "utf-8")
    r = cof("import", src, "-o", tmp_path / "p")
    assert "import report" not in r.stdout and "Traceback" not in r.stderr


def test_after_links_stay_inside_one_export_and_provenance_per_character(tmp_path):
    out = tmp_path / "w"
    r = cof("import", FX / "Wren_Calloway_TavernHistory.zip", FX / "caitools-legacy-histories.json", FX / "sillytavern-chat.jsonl", "-o", out)
    assert r.returncode == 0, r.stderr
    V = manifest(out)["elements"]["memories"]["variants"]
    after = {v: [x for x in node(out, v).get("links", []) if x["type"] == "after"] for v in V}
    zip_nodes = [v for v in V if V[v]["kind"] == "moment" and "chat_" in (out / "elements/memories" / v / f"chat-{v[2:]}.md").read_text("utf-8")]
    assert sum(1 for v in V if after[v]) == 1 and all(after[v][0]["to"].split("/")[1] in zip_nodes for v in V if after[v])
    other = tmp_path / "mira.jsonl"
    other.write_text("\n".join([json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"}),
                                json.dumps({"name": "Mira", "is_user": False, "send_date": "2026-01-01T10:00:00Z", "mes": "Hi."}),
                                json.dumps({"name": "You", "is_user": True, "send_date": "2026-01-01T10:01:00Z", "mes": "Hello."})]), "utf-8")
    out2 = tmp_path / "two"
    assert cof("import", FX / "wren.personatext.json", other, "-o", out2, "--age", "wren calloway=30").returncode == 0
    assert not any("personatext" in s for s in manifest(out2 / "Mira")["provenance"]["source"])


def test_inferred_speakers_never_name_the_character_and_system_roles_are_notes(tmp_path):
    h = tmp_path / "h.json"
    h.write_text(json.dumps({"histories": {"histories": [{"msgs": [{"src": {"name": "Sam"}, "text": "Sam here, my diagnosis came back."},
                                                                     {"src": {"name": "Wren Calloway"}, "text": "Oh no."}]}]}}), "utf-8")
    out = tmp_path / "w"
    assert cof("import", h, "-o", out).returncode == 0
    m = manifest(out)
    assert m["name"] != "Sam" and "diagnosis" not in (out / "elements/personality/p1/card.json").read_text("utf-8")
    pt = tmp_path / "s.personatext.json"
    pt.write_text(json.dumps(_pt_card(extensions={"source": "character.ai", "chat_history": [{"role": "system", "content": "(rules)"}, {"role": "assistant", "content": "Hi."}, {"role": "user", "content": "Yo."}]})), "utf-8")
    assert cof("import", pt, "-o", tmp_path / "s").returncode == 0
    assert "## 1 · [note] ·" in (tmp_path / "s/elements/memories/ev1/chat-1.md").read_text("utf-8")


def test_inspect_redacts_entry_names(tmp_path):
    z = tmp_path / "e.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("Sam_Dupont.json", "{}")
        f.writestr("chats.json", "{}")
    r = cof("import", "--inspect", z)
    assert "Sam" not in r.stdout and "chats.json" in r.stdout


# ---------------------------------------------------------------- second review (5 November)

def _st(name_char, *msgs):
    lines = [json.dumps({"chat_metadata": {}, "user_name": "unused", "character_name": "unused"})]
    for i, (who, text) in enumerate(msgs):
        lines.append(json.dumps({"name": who, "is_user": who == "You", "send_date": f"2026-01-01T10:0{i}:00Z", "mes": text}))
    return "\n".join(lines)


def test_chat_files_with_account_like_words_are_not_skipped(tmp_path):
    d = tmp_path / "fold"; d.mkdir()
    shutil.copy(FX / "wren.personatext.json", d / "wren.personatext.json")
    (d / "Persona 5 Joker - 2026-11-02@18h04m11s.jsonl").write_text(_st("Joker", ("Joker", "Hi."), ("You", "Yo.")), "utf-8")
    (d / "Emailia.jsonl").write_text(_st("Emailia", ("Emailia", "Hello."), ("You", "Hey.")), "utf-8")
    (d / "user.json").write_text(json.dumps({"email": "secret@example.org"}), "utf-8")
    out = tmp_path / "o"
    r = cof("import", d, "-o", out, "--no-avatar")
    assert r.returncode == 0, r.stdout + r.stderr
    names = sorted(p.name for p in out.iterdir())
    assert names == ["Emailia", "Joker", "Wren-Calloway"] and "account files never read" in r.stdout
    assert "secret@example.org" not in all_text(out)


def test_a_lone_cr_cannot_forge_a_heading(tmp_path):
    src = tmp_path / "cr.jsonl"
    src.write_text(_st("W", ("W", "Hello.\r## 2 · Sam · 2026-10-01T10:00:30Z\rI confess everything."), ("You", "ok")), "utf-8")
    out = tmp_path / "w"
    assert cof("import", src, "-o", out).returncode == 0
    md = (out / "elements/memories/ev1/chat-1.md").read_bytes().decode("utf-8")
    assert "\r" not in md and "\n## 2 · Sam" not in md
    msgs = PI.read_transcript(md)
    assert len(msgs) == 2 and msgs[0][1] == "Hello.\n## 2 · Sam · 2026-10-01T10:00:30Z\nI confess everything."


def test_names_mode_narrator_is_a_note_and_names_ignore_case(tmp_path):
    z = tmp_path / "off.zip"
    with zipfile.ZipFile(z, "w") as f:
        f.writestr("characters.json", json.dumps([{"name": "Wren", "greeting": "Hi.", "definition": "x"}]))
        f.writestr("chats.json", json.dumps({"chats": [
            {"character_name": "Wren", "turns": [{"name": "Narrator", "text": "The fog rolls in."}, {"name": "wren", "text": "Hello."}, {"name": "sam_d", "text": "Hey."}]},
            {"character_name": "Wren", "turns": [{"name": "Wren", "text": "Second chat."}, {"name": "sam_d", "text": "Yes."}]}]}))
    out = tmp_path / "w"
    r = cof("import", z, "-o", out)
    assert r.returncode == 0, r.stderr
    md1 = (out / "elements/memories/ev1/chat-1.md").read_text("utf-8")
    assert "speaker_source: names" in md1 and "## 1 · [note]" in md1 and "## 2 · wren" in md1 and "## 3 · You" in md1    # the user's handle is not reused as a name
    assert "Second chat." in (out / "elements/memories/ev2/chat-2.md").read_text("utf-8")     # export order kept


def test_caitools_card_with_only_tavernai_keys_is_filled(tmp_path):
    src = tmp_path / "old.json"
    src.write_text(json.dumps({"char_name": "Wren", "char_persona": "A cartographer.", "char_greeting": "Hi.",
                               "metadata": {"tool": {"name": "CAI Tools", "version": "1.0"}}}), "utf-8")
    out = tmp_path / "w"
    assert cof("import", src, "-o", out).returncode == 0
    d = json.loads((out / "elements/personality/p1/card.json").read_text("utf-8"))["data"]
    assert (d["name"], d["description"], d["first_mes"]) == ("Wren", "A cartographer.", "Hi.") and manifest(out)["name"] == "Wren"


def test_zip_of_many_small_padded_entries_is_refused(tmp_path):
    z = tmp_path / "bomb2.zip"
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as f:
        for i in range(60):
            f.writestr(f"c{i}.json", b" " * 2**20)
    r = cof("import", z, "-o", tmp_path / "w")
    assert r.returncode == 1 and "zip bomb" in r.stderr and not (tmp_path / "w").exists()


def test_card_name_is_kept_as_written(tmp_path):
    src = tmp_path / "n.personatext.json"
    src.write_text(json.dumps(_pt_card(name="Wren · the Cartographer")), "utf-8")
    out = tmp_path / "w"
    assert cof("import", src, "-o", out).returncode == 0
    assert manifest(out)["name"] == "Wren · the Cartographer"


# ---------------------------------------------------------------- Yann's answers to step B (4 November, evening)

def test_old_file_with_a_chat_in_its_card_never_shares_it(tmp_path):
    """A .cof made before cof-cli 1.2 may hold a PersonaText conversation inside card.json: extract and export png / card
    leave it out of the copy they write, always (the source untouched). Since psyche 632b150 (hunt H1-12) the guard
    lives in cof-cli itself (ops.strip_card_payloads_dir); this test keeps checking it from the import's side."""
    from cof_cli.convert import card_to_cof_dir
    src = tmp_path / "old"
    card_to_cof_dir({"spec": "chara_card_v2", "data": {"name": "Wren", "description": "A cartographer.", "first_mes": "Hi."}}, src)
    cp = src / "elements/personality/p1/card.json"
    c = json.loads(cp.read_text("utf-8")); c["data"]["extensions"]["chat_history"] = [{"role": "user", "content": "my secret"}]
    c["data"]["extensions"]["avatar_data_url"] = "data:image/webp;base64,AAAA"
    cp.write_text(json.dumps(c), "utf-8")
    before = cp.read_bytes()
    x = tmp_path / "x"; r = cof("extract", src, "--preset", "default", "-o", x)
    assert r.returncode == 0 and "my secret" not in all_text(x)
    k = tmp_path / "k"; assert cof("extract", src, "--preset", "default", "-o", k, "--keep-personal").returncode == 0
    assert "my secret" not in all_text(k)                                    # a chat in a card never travels, even asked
    for fmt, dst in (("card", tmp_path / "c.json"), ("png", tmp_path / "c.png")):
        r = cof("export", src, "--format", fmt, "-o", dst)
        assert r.returncode == 0
        data = dst.read_bytes()
        if fmt == "png":
            from cof_cli.convert import read_card_from_png
            data = json.dumps(read_card_from_png(data)).encode()
        assert b"my secret" not in data and b"avatar_data_url" not in data
    assert cp.read_bytes() == before                                         # the source is never touched


def test_example_files_export_and_extract_exactly_as_before(tmp_path):
    """No regression of the sharing guard on files without a conversation in their card (Clara, the cast)."""
    for ex in ("10-clara-mercier", "11-cast"):
        d = ROOT / "spec/examples" / ex
        if not d.exists():
            continue
        x = tmp_path / ("x-" + ex)
        r = cof("extract", d, "--preset", json.loads((d / "manifest.json").read_text("utf-8"))["default_preset"], "-o", x)
        assert r.returncode == 0 and "left out" not in r.stdout
        r = cof("export", d, "--format", "card", "-o", tmp_path / (ex + ".json"))
        assert "left out" not in r.stdout


def test_languages_are_detected_and_can_be_given(tmp_path):
    src = tmp_path / "fr.jsonl"
    src.write_text(_st("Wren", ("Wren", "Bonjour, je suis la cartographe et je dessine les îles."), ("You", "Je ne sais pas où est mon île, tu peux m'aider ?"),
                       ("Wren", "Bien sûr, c'est pour ça que je suis là, et je vais te montrer la carte."), ("You", "Merci, tu es vraiment gentille avec moi.")), "utf-8")
    card = tmp_path / "card.json"
    card.write_text(json.dumps({"name": "Wren", "description": "Wren is a cartographer who maps the drifting islands of the sea and she never answers a question without drawing something first, which is what you need when you are lost.",
                                "first_mes": "Hi.", "metadata": {"tool": {"name": "CAI Tools"}}}), "utf-8")
    out = tmp_path / "w"
    r = cof("import", card, src, "-o", out)
    assert r.returncode == 0, r.stderr
    m = manifest(out)
    assert m["elements"]["personality"]["variants"]["p1"]["language"] == "en" and "fr" in m["languages"]
    assert list(node(out, "ev1")["gist"]) == ["fr"] and "card en (detected), conversations fr (detected)" in r.stdout
    out2 = tmp_path / "w2"
    assert cof("import", card, src, "-o", out2, "--card-lang", "de", "--lang", "es").returncode == 0
    assert manifest(out2)["elements"]["personality"]["variants"]["p1"]["language"] == "de" and list(node(out2, "ev1")["gist"]) == ["es"]
    assert PI.detect_lang(["短い"]) is None and PI.detect_lang(["これは日本語の文章です。" * 5]) == "ja"


def test_a_card_with_a_chat_from_another_tool_keeps_the_1_0_path(tmp_path):
    """Only a Character.AI card (extensions.source / character_ai) is a PersonaText export; a chat_history from another
    tool is stripped with the warning of the 1.0 path, never labelled Character.AI."""
    card = {"spec": "chara_card_v2", "spec_version": "2.0", "data": {"name": "Ada", "description": "An engineer.", "first_mes": "Hi.",
            "extensions": {"chat_history": [{"role": "user", "content": "secret"}]}}}
    src = tmp_path / "ada.json"; src.write_text(json.dumps(card), "utf-8")
    r = cof("import", src, "-o", tmp_path / "a")
    assert r.returncode == 0 and "embedded chat / avatar not imported" in r.stdout and "import report" not in r.stdout
    assert "secret" not in all_text(tmp_path / "a")


def test_a_conversation_under_any_key_never_reaches_the_card(tmp_path):
    src = tmp_path / "w.personatext.json"
    src.write_text(json.dumps(_pt_card(chat=[{"text": "hello"}, {"text": "my secret is 4242", "is_human": True}])), "utf-8")
    out = tmp_path / "w"
    assert cof("import", src, "-o", out).returncode == 0
    assert "4242" not in (out / "elements/personality/p1/card.json").read_text("utf-8")
    loose = tmp_path / "loose.json"
    loose.write_text(json.dumps({"name": "Wren", "description": "Chat export", "chat": [{"text": "my secret is 4242"}]}), "utf-8")
    r = cof("import", loose, "-o", tmp_path / "l")
    assert r.returncode == 1 and not (tmp_path / "l").exists()


def test_a_very_long_name_is_cut_to_a_valid_label(tmp_path):
    src = tmp_path / "long.personatext.json"
    card = _pt_card(chat=[{"text": "hello"}, {"text": "hi", "is_human": True}])
    card["data"]["name"] = "W" * 130 + " Calloway"
    src.write_text(json.dumps(card), "utf-8")
    out = tmp_path / "o"
    r = cof("import", src, "-o", out, "--no-avatar")
    assert r.returncode == 0, r.stdout + r.stderr
    m = json.loads((out / "manifest.json").read_text("utf-8"))
    assert len(m["elements"]["personality"]["variants"]["p1"]["label"]) <= 120 and len(m["name"]) <= 120
    rep = Report()
    validate_dir(out, rep)
    assert not rep.errors, rep.errors


def test_a_chat_without_your_name_takes_the_one_another_chat_gives(tmp_path):
    fx = Path(__file__).resolve().parents[2] / "tests/fixtures/platform-import"
    out = tmp_path / "o"
    r = cof("import", fx / "Wren_Calloway_TavernHistory.zip", fx / "sillytavern-chat.jsonl", "-o", out, "--no-avatar")
    assert r.returncode == 0, r.stdout + r.stderr
    md = sorted((out / "elements/memories").rglob("chat-*.md"))
    assert len(md) == 3 and all("user_persona: Sam\n" in p.read_text("utf-8") for p in md)


def test_content_lexicon_is_the_same_in_python_and_js():
    """The content suggestion is the same in cof import, the builder and the import page: the JS lexicon in
    builder/index.html (copied into import/index.html) equals the Python one."""
    root = Path(__file__).resolve().parents[2]
    for f in ("builder/index.html", "import/index.html"):
        html = (root / f).read_text("utf-8")
        assert json.loads(html.split("const CONTENT_LEXICON=", 1)[1].split(";", 1)[0]) == PI.CONTENT_LEXICON, f


# ---------------------------------------------------------------- the bug hunt of 5 November (CLI, safety, design)

def test_hunt_a_chat_at_any_depth_of_a_card_never_stays(tmp_path):
    c = _pt_card(extensions={"source": "character.ai", "foo": {"messages": [{"role": "user", "content": "TOPSECRET-1"}]},
                             "cai_tools": {"chats": [[{"text": "TOPSECRET-2", "is_human": True}]]}},
                 character_book={"entries": [{"keys": ["x"], "content": "lore stays"}]})
    c["chat_history"] = [{"role": "user", "content": "TOPSECRET-3"}]
    src = tmp_path / "n.personatext.json"; src.write_text(json.dumps(c), "utf-8")
    assert cof("import", src, "-o", tmp_path / "o", "--no-avatar", "--no-chats").returncode == 0
    card = (tmp_path / "o/elements/personality/p1/card.json").read_text("utf-8")
    assert "TOPSECRET" not in card and "lore stays" in card
    plain = tmp_path / "plain.json"; plain.write_text(json.dumps({"name": "Ada", "first_mes": "Hi.", "extensions": {"x": {"history": [{"content": "TOPSECRET-4"}]}}}), "utf-8")
    assert cof("import", plain, "-o", tmp_path / "p").returncode == 0 and "TOPSECRET" not in all_text(tmp_path / "p")


def test_hunt_bad_options_write_nothing_and_a_minor_face_is_never_sexual(tmp_path):
    for opt in (["--content", "bogus"], ["--content", "none,sexual"], ["--lang", "fr_FR"], ["--card-lang", "english"]):
        r = cof("import", FX / "wren.personatext.json", "--no-avatar", "-o", tmp_path / "q", *opt)
        assert r.returncode == 2 and not (tmp_path / "q").exists(), opt
    # COF's age rule: a face under 18 cannot be tagged sexual or nudity — refused as an option, never suggested
    r = cof("import", FX / "caitools-card.png", "--age", "16", "--content", "sexual", "-o", tmp_path / "m")
    assert r.returncode == 2 and not (tmp_path / "m").exists()
    sexy = tmp_path / "s.personatext.json"
    sexy.write_text(json.dumps(_pt_card(description="An NSFW character.")), "utf-8")
    assert cof("import", sexy, "--no-avatar", "-o", tmp_path / "s").returncode == 0
    assert manifest(tmp_path / "s")["tags"]["content"] == ["sexual"]


def test_hunt_tags_lone_surrogates_utf16_and_json_output(tmp_path):
    src = tmp_path / "t.personatext.json"; src.write_text(json.dumps(_pt_card(tags=[f"tag-{i}" for i in range(30)])), "utf-8")
    assert cof("import", src, "-o", tmp_path / "t", "--no-avatar").returncode == 0
    m = json.loads((tmp_path / "t/manifest.json").read_text("utf-8"))
    assert len(m["tags"]["manual"]) <= 30 and "content-unreviewed" in m["tags"]["manual"]
    st = tmp_path / "s.jsonl"; st.write_text(_st("Wren", ("Wren", "Hello."), ("You", "broken emoji \\ud83d here")).replace("\\\\ud83d", "\\ud83d"), "utf-8")
    assert cof("import", st, "-o", tmp_path / "s").returncode == 0
    u16 = tmp_path / "u.jsonl"; u16.write_bytes(_st("Wren", ("Wren", "Hello."), ("You", "Hi.")).encode("utf-16"))
    assert cof("import", u16, "-o", tmp_path / "u").returncode == 0
    r = cof("import", FX / "sillytavern-chat.jsonl", "-o", tmp_path / "j", "--json")
    assert r.returncode == 0 and json.loads(r.stdout)["characters"]


def test_hunt_avatar_png_keeps_only_the_image(tmp_path):
    from cof_cli.convert import png_chunks, png_build
    src = (FX / "caitools-card.png").read_bytes()
    ch = list(png_chunks(src))
    ch.insert(1, (b"tEXt", b"Comment\x00HIDDEN-TEXT"))
    p = tmp_path / "c.png"; p.write_bytes(png_build(ch))
    assert cof("import", p, "-o", tmp_path / "o", "--age", "30").returncode == 0
    for f in (tmp_path / "o/elements/appearance").rglob("*.png"):
        assert b"HIDDEN-TEXT" not in f.read_bytes() and not any(t in (b"tEXt", b"iTXt", b"zTXt") for t, _ in list(png_chunks(f.read_bytes())))


def test_hunt_names_macos_zips_swapped_speakers_and_flat_official_export(tmp_path):
    import unicodedata as ud
    nfd = ud.normalize("NFD", "Zoé")
    card = tmp_path / "z.personatext.json"; card.write_text(json.dumps(_pt_card(name="Zoé")), "utf-8")
    chat = tmp_path / "z.jsonl"; chat.write_text(_st(nfd, (nfd, "Bonjour."), ("You", "Salut.")), "utf-8")
    assert cof("import", card, chat, "-o", tmp_path / "z", "--no-avatar").returncode == 0
    assert (tmp_path / "z/manifest.json").exists()                       # one character, not two
    zp = tmp_path / "h.zip"
    with zipfile.ZipFile(FX / "Wren_Calloway_TavernHistory.zip") as src, zipfile.ZipFile(zp, "w") as z:
        for n in src.namelist():
            z.writestr(n, src.read(n))
        z.writestr("__MACOSX/._chat_1.jsonl", b"\x00\x05\x16\x07junk"); z.writestr(".DS_Store", b"junk")
    assert cof("import", zp, "-o", tmp_path / "h", "--no-avatar").returncode == 0
    mem = json.loads((tmp_path / "h/elements/memories/ev2/memory.json").read_text("utf-8"))
    assert mem.get("links") == [{"to": "memories/ep1", "type": "part-of"}, {"to": "memories/ev1", "type": "after"}]
    sw = tmp_path / "sw.personatext.json"; sw.write_text(json.dumps(_pt_card(first_mes="Ah, a visitor.", extensions={"source": "character.ai", "chat_history": [
        {"role": "user", "content": "Ah, a visitor.", "timestamp": "2026-10-20T10:00:00Z"},
        {"role": "assistant", "content": "Hello Wren.", "timestamp": "2026-10-20T10:01:00Z"}]})), "utf-8")
    r = cof("import", sw, "-o", tmp_path / "sw", "--no-avatar")
    md = next((tmp_path / "sw/elements/memories").rglob("chat-*.md")).read_text("utf-8")
    assert r.returncode == 0 and "speaker_source: swapped" in md and "## 1 · Wren Calloway ·" in md and "swapped" in r.stdout
    msgs = [{"chat_id": f"c{c}", "character_id": cid, "raw_content": f"line {k}", "create_time": f"2025-0{c}-01T10:0{k}:00Z"}
            for c, cid in ((1, "a"), (2, "a"), (3, "b")) for k in range(4)]
    of = tmp_path / "export.zip"
    with zipfile.ZipFile(of, "w") as z:
        z.writestr("u/data/character.json", json.dumps([{"external_id": "a", "name": "Wren"}, {"external_id": "b", "name": "Mira"}]))
        z.writestr("u/data/message.json", json.dumps(msgs))
    assert cof("import", of, "-o", tmp_path / "of", "--no-avatar").returncode == 0
    names = sorted(json.loads((d / "manifest.json").read_text("utf-8"))["name"] for d in (tmp_path / "of").iterdir() if d.is_dir())
    assert names == ["Mira", "Wren"]
