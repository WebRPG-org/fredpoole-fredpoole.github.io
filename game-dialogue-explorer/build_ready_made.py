"""Build ready-made-games.js: games added to the explorer that are not in the corpus.

Each game is built from a dialogue file plus a tag file (ready-made/<name>-tags.csv)
that sets each speaker's gender. Only word counts and statistics are written out,
never the dialogue text. The counting mirrors the explorer's own importer.

Usage:
    python3 build_ready_made.py disco=/path/to/output.json gtav=/path/to/gta-pages/ genshin=/path/to/result.json

Edit a tag file and run this again to change gender tags.
"""
import csv
import html
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


def speaker_name(s):
    """Drop notes such as "(text message)" or "In Spanish" from a transcript's speaker label."""
    s = html.unescape(html.unescape(s)).replace(":", " ")
    s = re.sub(r"\([^)]*\)|\bIn (Spanish|German|French|Italian|Polish|Russian|Hungarian)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


# Spelling variants on Grand Theft Wiki. Michael and Amanda go by Townley in the prologue.
GTA_ALIASES = {
    "Lamar Davies": "Lamar Davis", "Lamar Davisp": "Lamar Davis", "Lamar Daivs": "Lamar Davis",
    "Ron Jakowksi": "Ron Jakowski", "Ron Jakowsi": "Ron Jakowski", "Sssquatch": "Sasquatch",
    "Michael Townley": "Michael De Santa", "Michael Tonwley": "Michael De Santa", "Amanda Townley": "Amanda De Santa",
    "Police officer": "Police Officer",
}


def gta_v(folder):
    """Grand Theft Wiki mission script pages (saved .html), where each line is <p><b>Speaker</b>: text</p>."""
    lines, pages = [], 0
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".html"):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            page = f.read()
        body = page[page.find("mw-parser-output"):]
        body = body[:body.find("printfooter")]
        pages += 1
        for para in re.findall(r"<p>(.*?)</p>", body, re.S):
            m = re.match(r"\s*<b>([^<]{1,80})</b>\s*(?:\([^)]*\))?\s*:(.*)$", para, re.S)
            if not m:
                continue
            spk = speaker_name(m.group(1))
            text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
            if spk:
                lines.append((GTA_ALIASES.get(spk, spk), strip(text)))
    meta = {
        "title": "Grand Theft Auto V",
        "series": "Grand Theft Auto",
        "year": 2013,
        "source": "https://www.grandtheftwiki.com/Category:Scripts_for_GTA_V",
        "sourceType": "fan wiki transcripts",
        "completeness": "partial",
        "choices": "no",
        "custom": {
            "where": "ready",
            "notes": f"The {pages} mission scripts transcribed on Grand Theft Wiki: mostly side missions (Strangers and Freaks, "
                     "Paparazzo, Epsilon, Tonya, rampages) plus a few story missions, so the main story is under-represented. "
                     "Stage directions in brackets were removed. Unnamed and one-off speakers are untagged (Other).",
            "rights": "Dialogue by Rockstar Games; transcripts by Grand Theft Wiki contributors. Only word counts are stored here.",
            "importOpts": {"format": "auto"},
        },
    }
    return build_record("extra/GTAV", meta, lines, read_tags("gta-v"))


def genshin_impact(path):
    """genshin-voice result.json: {id: {"language", "speaker", "transcription", ...}}, one entry per voiced line."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    lines = []
    for row in data.values():
        spk, text = (row.get("speaker") or "").strip(), row.get("transcription") or ""
        if row.get("language") != "English(US)" or not spk or spk.startswith("#") or not text:
            continue
        text = re.sub(r"<[^>]+>|\{[^}]*\}|#", " ", text)  # color tags and name placeholders
        lines.append((spk, strip(text)))
    meta = {
        "title": "Genshin Impact",
        "series": "Genshin Impact",
        "year": 2020,
        "source": "https://huggingface.co/datasets/simon3000/genshin-voice",
        "sourceType": "voice-line data",
        "completeness": "voiced lines only",
        "choices": "no",
        "custom": {
            "where": "ready",
            "notes": "Every English voiced line in the game up to mid-2026 (story, quests, events, character voice-overs and "
                     "combat lines), from a community dataset. Unvoiced text is missing, including most of the Traveler's "
                     "dialogue choices, so the Traveler looks quieter than in play. Hero (Aether) and Heroine (Lumine) are "
                     "the two versions of the Traveler and mostly say the same lines. Minor speakers are untagged (Other).",
            "rights": "Dialogue by HoYoverse. Only word counts are stored here.",
            "importOpts": {"format": "json"},
        },
    }
    return build_record("extra/GenshinImpact", meta, lines, read_tags("genshin-impact"))


def rdr2(path):
    """Game Scripts Wiki full transcript (saved .html), where each line is <b>Speaker:</b> text<br />."""
    with open(path, encoding="utf-8") as f:
        page = f.read()
    lines = []
    for seg in re.split(r"<br\s*/?>", page):
        m = re.match(r"\s*<b>([^<]{1,60}?):?\s*</b>\s*:?(.*)$", seg, re.S)
        if not m:
            continue
        spk = speaker_name(m.group(1))
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        if spk and len(spk.split()) <= 5:
            lines.append((spk, strip(text)))
    meta = {
        "title": "Red Dead Redemption 2",
        "series": "Red Dead Redemption",
        "year": 2018,
        "source": "https://game-scripts-wiki.blogspot.com/2022/01/red-dead-redemption-2.html",
        "sourceType": "fan transcript",
        "completeness": "main story",
        "choices": "no",
        "custom": {
            "where": "ready",
            "notes": "A fan transcript of the story missions, prologue to epilogue, from Game Scripts Wiki. Side content, "
                     "camp chatter and most ambient lines are missing. Stage directions in brackets were removed. "
                     "Unnamed and one-off speakers are untagged (Other).",
            "rights": "Dialogue by Rockstar Games; transcript by Game Scripts Wiki. Only word counts are stored here.",
            "importOpts": {"format": "auto"},
        },
    }
    return build_record("extra/RDR2", meta, lines, read_tags("rdr2"))


CP77_ALIASES = {"Takamura": "Takemura", "Takemira": "Takemura", "Talkemuro": "Takemura", "Tokemu": "Takemura",
                "Alt Cunningham": "Alt", "AIt Cunningham": "Alt", "Cunningham": "Alt", "Jarkie": "Jackie", "JackIe": "Jackie",
                "Mama Weles": "Mamá Welles", "Conch Fred": "Coach Fred", "Cooch Fred": "Coach Fred",
                "Milt Nouman": "Milt Nauman", "Mil Nauman": "Milt Nauman", "Mit Nauman": "Milt Nauman",
                "Snider Murphy": "Spider Murphy", "T-Bud": "T-Bug", "Caselus Ryder": "Cassius Ryder",
                "Stinis": "Stints", "Sunts": "Stints", "Roxonne": "Roxanne", "Honoko": "Hanako", "Harako": "Hanako",
                "Johnne": "Johnny", "Karry": "Kerry", "Victor": "Viktor", "Panama": "Panam", "Clatre": "Claire",
                "Grouple": "Groupie", "Net Watch Agent": "NetWatch Agent", "NCPD officer": "NCPD Officer",
                "Tyger Claws Boss": "Tyger Claw Boss"}


def cyberpunk_2077(path):
    """Game Scripts Wiki full transcript (saved .html): <font color=..><b>Speaker:</b></font> text<br />."""
    with open(path, encoding="utf-8") as f:
        page = f.read()
    start = page.find("entry-content")
    body = re.sub(r"</?font[^>]*>", "", page[start:page.find("post-footer", start)])
    lines = []
    for seg in re.split(r"<br\s*/?>", body):
        m = re.match(r"\s*<b>([^<]{1,60}?):?\s*</b>\s*:?(.*)$", seg, re.S)
        if not m:
            continue
        spk = speaker_name(m.group(1))
        spk = CP77_ALIASES.get(spk, spk)
        text = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        if spk and len(spk.split()) <= 5 and not spk.startswith("["):
            lines.append((spk, strip(text)))
    meta = {
        "title": "Cyberpunk 2077",
        "series": "Cyberpunk",
        "year": 2020,
        "source": "https://game-scripts-wiki.blogspot.com/2020/12/cyberpunk-2077-full-transcript.html",
        "sourceType": "fan transcript",
        "completeness": "main story",
        "choices": "yes",
        "custom": {
            "where": "ready",
            "notes": "A fan transcript of one playthrough of the main story (base game, no Phantom Liberty), from Game Scripts Wiki. "
                     "Most side jobs, gigs and ambient lines are missing, and other dialogue choices would change V's lines. "
                     "V's gender is chosen by the player (this playthrough's V is not identified), so V is tagged Neutral. "
                     "Misspelled speaker names were merged. Unnamed and one-off speakers are untagged (Other).",
            "rights": "Dialogue by CD PROJEKT RED; transcript by Game Scripts Wiki. Only word counts are stored here.",
            "importOpts": {"format": "auto"},
        },
    }
    return build_record("extra/Cyberpunk2077", meta, lines, read_tags("cyberpunk-2077"))


BUILDERS = {"disco": disco_elysium, "gtav": gta_v, "genshin": genshin_impact, "rdr2": rdr2, "cp77": cyberpunk_2077}


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
