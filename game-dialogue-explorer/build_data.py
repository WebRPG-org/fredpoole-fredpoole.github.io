"""Build corpus-data.js for the Game Dialogue Explorer.

Reads the per-character statistics shipped with the Video Game Dialogue Corpus
(https://github.com/seannyD/VideoGameDialogueCorpusPublic) and writes a compact
JavaScript data file the explorer page embeds.

Usage:
    python3 build_data.py /path/to/VideoGameDialogueCorpusPublic
"""
import csv
import glob
import json
import os
import sys

# Corpus group labels -> gender categories used by the explorer.
GENDER_MAP = {
    "female": "Female",
    "GenericFemale": "Female",
    "male": "Male",
    "GenericMale": "Male",
    "trans": "Trans",
    "neutral": "Neutral",
    "genderless": "Neutral",
    "ambiguous": "Neutral",
}
GENDER_PRIORITY = ["Female", "Male", "Trans", "Neutral"]


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def folder_key(folder):
    # "../data/Hades/Hades/" -> "Hades/Hades"
    return folder.replace("../data/", "").strip("/")


def load_feature_table(path, skip_cols):
    """Per-character word counts keyed by (folder, charName)."""
    out = {}
    if not os.path.exists(path):
        return out, []
    rows = read_csv(path)
    cols = [c for c in rows[0].keys() if c not in skip_cols]
    for r in rows:
        counts = {c: num(r[c]) for c in cols if num(r[c])}
        out[(folder_key(r[".folder"]), r[".charName"])] = counts
    return out, cols


def main(repo):
    skip = {".folder", ".series", ".game", ".group", ".charName", ".totalWords"}
    kw, kw_cols = load_feature_table(os.path.join(repo, "results/keyness/keywordsByCharacter.csv"), skip)
    pron, pron_cols = load_feature_table(os.path.join(repo, "results/keyness/pronounsByCharacter.csv"), skip)
    qw, qw_cols = load_feature_table(os.path.join(repo, "results/keyness/questionWordsByCharacter.csv"), skip)

    games = []
    for meta_path in sorted(glob.glob(os.path.join(repo, "data/*/*/meta.json"))):
        game_dir = os.path.dirname(meta_path)
        key = os.path.relpath(game_dir, os.path.join(repo, "data"))
        if key.startswith("Test"):
            continue
        stats_path = os.path.join(game_dir, "stats_by_character.csv")
        if not os.path.exists(stats_path):
            continue
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        chars = {}
        for r in read_csv(stats_path):
            name = r["charName"]
            c = chars.setdefault(name, {"groups": [], "stats": None})
            if r["group"] not in c["groups"]:
                c["groups"].append(r["group"])
            # Stats are identical across a character's group rows; keep the first.
            if c["stats"] is None:
                c["stats"] = [num(r[k]) for k in ("lines", "words", "sentences", "syllables")]

        rows = []
        for name, c in chars.items():
            genders = [GENDER_MAP[g] for g in c["groups"] if g in GENDER_MAP]
            gender = next((g for g in GENDER_PRIORITY if g in genders), "Other")
            k = (key, name)
            rows.append({
                "n": name,
                "g": gender,
                "grp": c["groups"],
                "s": c["stats"],
                "kw": kw.get(k),
                "pr": [pron[k].get(col, 0) for col in pron_cols] if k in pron else None,
                "qw": [qw[k].get(col, 0) for col in qw_cols] if k in qw else None,
            })
        rows.sort(key=lambda r: -r["s"][1])
        # Drop empty keys to keep the file small.
        for r in rows:
            for f in ("kw", "pr", "qw"):
                if r[f] is None:
                    del r[f]

        if not rows:
            continue
        sf = meta.get("sourceFeatures", {})
        games.append({
            "id": key,
            "title": meta.get("game", key).replace("Attoreny", "Attorney"),
            "series": meta.get("series", ""),
            "year": meta.get("year"),
            "source": meta.get("source", ""),
            "sourceType": sf.get("type", ""),
            "completeness": sf.get("completeness", ""),
            "choices": sf.get("choices", ""),
            "pcs": meta.get("mainPlayerCharacters", []),
            "groups": meta.get("characterGroups", {}),
            "chars": rows,
        })

    out = {"pronounCols": pron_cols, "questionCols": qw_cols, "keywordCols": kw_cols, "games": games}
    dest = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corpus-data.js")
    with open(dest, "w", encoding="utf-8") as f:
        f.write("window.CORPUS = ")
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print(f"Wrote {len(games)} games, {sum(len(g['chars']) for g in games)} characters to {dest}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
