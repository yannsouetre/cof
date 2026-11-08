"""Agent hosts (8 Nov. 2026): AGENTS.md in the agent export, the Hermes profile, and the way back (--from-agent)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

from cof_cli.agents import HERMES_DELIM, HERMES_MEMORY_CHARS, export_hermes, hermes_memory, import_agent_memories, parse_agent_dir
from cof_cli.convert import export_agent

ROOT = Path(__file__).resolve().parents[2]
CLARA = ROOT / "spec" / "examples" / "10-clara-mercier"


def test_agent_export_writes_agents_md(tmp_path):
    done = export_agent(CLARA, tmp_path / "ws")
    txt = (tmp_path / "ws" / "AGENTS.md").read_text("utf-8")
    assert done["agents_md"] and "memory/YYYY-MM-DD.md" in txt and "HH:MM ·" in txt and "COF.md" in txt


def test_hermes_profile_fits_the_host(tmp_path):
    done = export_hermes(CLARA, tmp_path / "h")
    mem = (tmp_path / "h" / "memories" / "MEMORY.md").read_text("utf-8")
    assert len(mem) <= HERMES_MEMORY_CHARS and HERMES_DELIM in mem and done["hermes_memory_entries"] == 5
    soul = (tmp_path / "h" / "SOUL.md").read_text("utf-8")
    assert "## Identity" in soul and "- Name: Clara Mercier" in soul and "Avatar" not in soul.split("## Identity")[1].split("##")[0]
    assert (tmp_path / "h" / "README-COF.md").is_file() and (tmp_path / "h" / "COF.md").is_file()


def test_hermes_memory_keeps_the_most_salient_within_the_limit():
    entries = [(10, "a" * 1000), (90, "b" * 1000), (50, "c" * 1000)]
    text, dropped = hermes_memory(entries, limit=2100)
    assert dropped == 1 and text.startswith("b" * 1000) and text.endswith("c" * 1000) and "a" * 10 not in text


def test_parse_openclaw_notes_and_hermes_entries(tmp_path):
    (tmp_path / "memory").mkdir()
    (tmp_path / "memory" / "2026-11-08.md").write_text("# day\n\n- 09:12 · Saw the Alps from the train. · with: the user, Léo · where: a train · tags: alps, travel\n- plain note without time\n", "utf-8")
    (tmp_path / "memories").mkdir()
    (tmp_path / "memories" / "MEMORY.md").write_text("User prefers French.\n§\nWe planned a review.\n", "utf-8")
    E = parse_agent_dir(tmp_path)
    assert [e["source"] for e in E] == ["openclaw", "openclaw", "hermes", "hermes"]
    assert E[0] == {"text": "Saw the Alps from the train.", "with": ["the user", "Léo"], "where": "a train", "tags": ["alps", "travel"],
                    "source": "openclaw", "file": "memory/2026-11-08.md", "date": "2026-11-08", "time": "09:12"}
    assert E[1]["text"] == "plain note without time" and E[1]["time"] == ""


def test_from_agent_adds_lived_personal_memories_once(tmp_path):
    work = tmp_path / "clara"
    shutil.copytree(CLARA, work)
    ws = tmp_path / "ws"
    (ws / "memory").mkdir(parents=True)
    (ws / "memory" / "2026-11-08.md").write_text("- 09:12 · Saw the Alps from the train. · tags: alps\n", "utf-8")
    added = import_agent_memories(work, ws, lang="en")
    assert len(added) == 1
    assert import_agent_memories(work, ws, lang="en") == []            # idempotent
    m = json.loads((work / "manifest.json").read_text("utf-8"))
    node = json.loads((work / m["elements"]["memories"]["variants"][added[0]]["memory"]).read_text("utf-8"))
    assert node["origin"] == "lived" and node["visibility"] == "personal" and node["when"] == {"date": "2026-11-08"}
    assert node["tags"] == ["lived:openclaw", "alps"] and node["gist"] == {"en": "Saw the Alps from the train."}
    r = subprocess.run([sys.executable, "-m", "cof_cli.cli", "validate", str(work)], capture_output=True, text=True, cwd=ROOT / "cli")
    assert r.returncode == 0, r.stdout[-800:]
