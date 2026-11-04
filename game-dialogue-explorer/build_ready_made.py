"""Build ready-made-games.js: games added to the explorer that are not in the corpus.

Each game is built from a dialogue file plus a tag file (ready-made/<name>-tags.csv)
that sets each speaker's gender. Only word counts and statistics are written out,
never the dialogue text. The counting mirrors the explorer's own importer.

Usage:
    python3 build_ready_made.py disco=/path/to/output.json

Edit a tag file and run this again to change gender tags.
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

PRONOUN_COLS = ["i", "me", "my", "you", "he", "she", "they", "them", "his", "hers", "theirs"]
QUESTION_COLS = ["who", "what", "why", "where", "when", "how"]
STYLE_MARKERS = [
    r"\?",
    r"!",
    r"\b(maybe|perhaps|probably|might|i think|i guess|i suppose|sort of|kind of)\b",
    r"\b(sorry|apologi[sz]e\w*|apologies|forgive me|my fault)\b",
    r"\b(please|thank|thanks)\b",
    r"\b(really|very|so much|totally|absolutely|extremely)\b",
    r"\b(damn\w*|hell|shit\w*|bastard\w*|crap|bloody|fuck\w*|dammit|piss\w*)\b",
    r"(^|[.!?\n]\s*)(go|come|look|stop|listen|wait|get|give|tell|leave|take|move|hurry|run)\b",
]
STYLE_RES = [re.compile(p, re.M) for p in STYLE_MARKERS]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)*")


def tokenize(t):
    return TOKEN_RE.findall(t.lower().replace("’", "'").replace("‘", "'"))


def syllables(w):
    w = re.sub(r"[^a-z]", "", w)
    if not w:
        return 0
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    m = re.findall(r"[aeiouy]{1,2}", w)
    return len(m) if m else 1


def strip(t):
    t = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", t).replace("*", "")
    return re.sub(r"\s+", " ", t).strip()


def read_tags(name):
    tags = {}
    with open(os.path.join(HERE, "ready-made", name + "-tags.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            tags[r["speaker"]] = r
    return tags


def build_record(game_id, meta, lines, tags):
    acc = {}
    for spk, text in lines:
        if not text:
            continue
        a = acc.setdefault(spk, {"lines": 0, "words": 0, "sent": 0, "syl": 0, "kw": {}, "text": []})
        toks = tokenize(text)
        if not toks:
            continue
        a["lines"] += 1
        a["words"] += len(toks)
        a["sent"] += max(1, len(re.findall(r"[.!?]+(?=\s|$)", text)))
        a["syl"] += sum(syllables(w) for w in toks)
        for w in toks:
            a["kw"][w] = a["kw"].get(w, 0) + 1
        a["text"].append(text.lower())

    chars = []
    for n, a in acc.items():
        if not a["words"]:
            continue
        tag = tags.get(n, {})
        gender = tag.get("gender") or "Other"
        group = tag.get("group") or ("" if tag else "not coded")
        text = "\n".join(a["text"])
        kw = {w: k for w, k in a["kw"].items() if k >= 2 or a["words"] < 400}
        kw = dict(sorted(kw.items(), key=lambda x: -x[1])[:4000])
        chars.append({
            "n": n, "g": gender, "grp": [group] if group else [],
            "s": [a["lines"], a["words"], a["sent"], a["syl"]],
            "pr": [a["kw"].get(w, 0) for w in PRONOUN_COLS],
            "qw": [a["kw"].get(w, 0) for w in QUESTION_COLS],
            "st": [len(r.findall(text)) for r in STYLE_RES],
            "kw": kw,
        })
    chars.sort(key=lambda c: -c["s"][1])
    pcs = [n for n, t in tags.items() if (t.get("player_character") or "").lower() == "yes"]
    return dict(meta, id=game_id, pcs=pcs, groups={}, chars=chars)


def disco_elysium(path):
    """Disco Elysium conversations export: {"conversations": [[{"actor", "dialogue"}, ...], ...]}."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    lines = []
    for conv in data["conversations"]:
        for row in conv:
            text = row.get("dialogue", "")
            if text.startswith("["):
                continue  # game-logic checks such as [Action/Check: ...]
            # NPC lines mix speech in quotes with narration; keep only the spoken part.
            quoted = re.findall(r"\"([^\"]+)\"", text)
            if quoted:
                text = " ".join(quoted)
            lines.append((row["actor"], strip(text)))
    meta = {
        "title": "Disco Elysium",
        "series": "Disco Elysium",
        "year": 2019,
        "source": "https://huggingface.co/datasets/allura-org/disco-elysium-conversations-raw",
        "sourceType": "game data",
        "completeness": "partial",
        "choices": "partial",
        "custom": {
            "where": "ready",
            "notes": "About 1,700 conversations (roughly 200,000 words) from a community export of the game's files. "
                     "Narration outside quotation marks was removed from character lines. The skills are the player "
                     "character's inner voices and are tagged Neutral; objects, documents and minor speakers are untagged (Other).",
            "rights": "Dialogue by ZA/UM. Only word counts are stored here.",
            "importOpts": {"format": "json"},
        },
    }
    return build_record("extra/DiscoElysium", meta, lines, read_tags("disco-elysium"))


BUILDERS = {"disco": disco_elysium}


def main(args):
    sources = dict(a.split("=", 1) for a in args)
    out_path = os.path.join(HERE, "ready-made-games.js")
    games = []
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            raw = f.read()
        games = json.loads(raw[raw.index("=") + 1:].rstrip().rstrip(";"))
    for key, path in sources.items():
        rec = BUILDERS[key](path)
        games = [g for g in games if g["id"] != rec["id"]] + [rec]
        coded = sum(c["s"][1] for c in rec["chars"] if c["g"] != "Other")
        total = sum(c["s"][1] for c in rec["chars"])
        print(f"{rec['title']}: {len(rec['chars'])} speakers, {total} words, {coded / total:.0%} of words gender-tagged")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("window.READY_MADE = ")
        json.dump(games, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("Wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1:])
