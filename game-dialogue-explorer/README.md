# Game Dialogue Explorer

A browser tool for studying representation in video game dialogue. Pick a game, filter characters by gender, and compare who talks, how much, and how.

It is built on [The Video Game Dialogue Corpus](https://github.com/seannyD/VideoGameDialogueCorpusPublic) and covers 73 game scripts from it. It also includes ready-made additions that are not in the corpus (Disco Elysium, Genshin Impact, Grand Theft Auto V, Red Dead Redemption 2, Cyberpunk 2077 and Where Winds Meet in Chinese), and you can add your own game scripts.

## What it does

- **Overview:** each gender's share of the cast compared with its share of words and lines, the top speakers, and where the game sits among all the others.
- **Characters:** a sortable table of lines, words, share of dialogue, words per line and words per sentence, with a profile for each character.
- **Language patterns:** pronouns, question words, speech style (hedges, apologies, politeness, swearing, commands) and distinctive words, compared by gender or character.
- **Full script:** load a script file to search words and phrases and see every matching line in context.
- **Add a game:** paste or upload a transcript (`NAME: line`), a spreadsheet (CSV/TSV) or JSON, tag each speaker's gender, and save the game in your browser or as a file to share.
- **Find more game scripts:** links at the bottom of the page to places where you can find dialogue for more games.

Everything runs in the browser. Added games keep only word counts and statistics, and script files you load never leave your computer.

## Files

| File | What it is |
| --- | --- |
| `index.html` | The tool |
| `corpus-data.js` | Per-character statistics from the corpus, reformatted for the tool |
| `ready-made-games.js` | Statistics for the ready-made additions (counts only, no dialogue) |
| `build_ready_made.py`, `ready-made/` | Rebuild the ready-made additions. Each game has a tag file, such as `ready-made/disco-elysium-tags.csv`, that sets each speaker's gender. Edit it, then rerun `build_ready_made.py` with the source files (see the top of the script). Sources: [Disco Elysium export](https://huggingface.co/datasets/allura-org/disco-elysium-conversations-raw), [Genshin Voice](https://huggingface.co/datasets/simon3000/genshin-voice), [Grand Theft Wiki GTA V scripts](https://www.grandtheftwiki.com/Category:Scripts_for_GTA_V), [Game Scripts Wiki RDR2 transcript](https://game-scripts-wiki.blogspot.com/2022/01/red-dead-redemption-2.html), [Game Scripts Wiki Cyberpunk 2077 transcript](https://game-scripts-wiki.blogspot.com/2020/12/cyberpunk-2077-full-transcript.html), [燕云十六声 Huiji wiki archive](https://github.com/anonymous99-Rise/yanyun-guide) (CC BY-NC-SA; Chinese words are split with Node's `Intl.Segmenter`, so Node is needed) |
| `build_data.py` | Rebuilds `corpus-data.js` from a copy of the corpus repository: `python3 build_data.py /path/to/VideoGameDialogueCorpusPublic` |

## Publishing on GitHub Pages

1. Put these files in a repository, or in a folder of your existing site.
2. In the repository, go to **Settings › Pages**, choose **Deploy from a branch**, and pick the branch and folder.
3. The tool will be at `https://<your-username>.github.io/<repository>/`.

## Credit and license

The corpus data is by Seán G. Roberts, Stephanie Rennick and contributors, published as [The Video Game Dialogue Corpus](https://github.com/seannyD/VideoGameDialogueCorpusPublic) ([doi 10.5281/zenodo.16994468](https://doi.org/10.5281/zenodo.16994468)) under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

**Changes made to the data:** `corpus-data.js` combines the corpus's per-character statistics (`stats_by_character.csv`) and keyness tables (`results/keyness/`). It merges the corpus's "neutral", "genderless" and "ambiguous" groups into one Neutral category, and leaves out games that have no per-character statistics. The ready-made additions are not part of the corpus: their gender tags were added for this tool, and speakers without a tag count as Other. This project is not made or endorsed by the corpus authors.

If you use the data, please cite:

- Rennick, S. & Roberts, S. G. (in press). The Video Game Dialogue Corpus. *Corpora* 19(1).
- Rennick, S., Clinton, M., Ioannidou, E., Oh, L., Clooney, C., E. T., Healy, E. & Roberts, S. G. (2023). Gender bias in video game dialogue. *Royal Society Open Science* 10(5). https://doi.org/10.1098/rsos.221095

Game titles, characters and dialogue belong to their publishers. Do not commit game scripts to this repository.
