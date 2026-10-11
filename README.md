# Spanish sentence decks, sorted by difficulty

Five popular Anki sentence decks for Spanish, pooled, cleaned, de-duplicated and **re-sorted by a single
difficulty score**, so you can start wherever your level is and have the sentences get harder as you go.
Every sentence has an English translation; about a quarter have audio (native Castilian recordings or TTS).

Two cards per sentence: **Read** (Spanish → English) and **Translate** (English → the full Spanish sentence,
with two optional hints you can click when you are new to it).

> This is a re-sort of other people's work; see [Credits](#credits). If you made one of the source decks and want
> something changed or removed, open an issue.
> The code is MIT. The sentences and recordings belong to their authors (Tatoeba contributors above all).

## Pick a deck

| deck | sentences | what it is | audio | where |
|---|---|---|---|---|
| **Spanish Sentences – sorted by difficulty** (main) | 54,754 | Every sentence that passes the quality filter (4–16 words, complete, no artifacts). Spain-specific sentences are tagged, not removed, and nudged a little later. | 12,008: 6,192 native + 5,816 synthetic (levels 1–9, ~20 kbps) | **AnkiWeb**, Releases (146 MB) |
| Macro | 78,016 | Every distinct line from all five sources, including 2–3-word fragments and odd lines, nothing removed (low-quality lines are tagged `quality::low`) | 9,262 native | AnkiWeb, Releases (131 MB) |
| Latin American cut | 54,097 | The main deck minus the 657 sentences with *vosotros* or Spain-only vocabulary | 11,736 (same recipe) | AnkiWeb, Releases (143 MB) |
| Full audio | 54,754 | The main deck with every synthetic recording at its original bitrate, all levels (too big for AnkiWeb) | 13,556 | Releases (192 MB) |
| Tatoeba only · Latin American cut | 13,191 | Only the two Tatoeba-based decks, for the cleanest licensing | 6,041 native (88 MB) or all 13,191 (182 MB) | Releases |
| B1 · Latin American · Core/Extended | 22,467 | A ready-made preset: easy levels dropped, 1,000 "probably known" sentences as long-interval reviews, best 2 sentences per target word in a *Core* subdeck | 9,620 | Releases (142 MB) |

All decks share the same note type and the same `level::01` … `level::10` tags, so you can switch or merge later.
AnkiWeb has a file-size limit of about 150 MB, so the AnkiWeb uploads keep every native recording as is and carry
the synthetic recordings up to level 9, re-encoded to about 20 kbps mono; the unabridged full-audio file is on
[Releases](https://github.com/akuzee/spanish-sentence-decks/releases). Everything rebuilds locally with `make decks`.

**Download:** AnkiWeb: *(links added after upload)* · GitHub: [Releases](https://github.com/akuzee/spanish-sentence-decks/releases)

## The vocabulary deck

The same repository builds **Spanish Top 5000 Vocabulary (merged)**: the pictures of *Essential Spanish Vocabulary
Top 5000* joined with the example sentences and audio of *New Spanish Top 5000 with Examples*, 5,601 words matched
by headword and ordered by frequency, with `rank::` band, `cognate::` and `pos::` tags for cutting to your level
(table in [docs/LEVELS.md](docs/LEVELS.md)). Its frequency ranks are also what the sentence scoring uses.
One file, 105 MB, original audio: packages compress their media losslessly (see docs/METHOD.md), which is what
brought it under AnkiWeb's limit.

## Adjust it to your level

Each sentence has a level tag (1 = easiest 10%, 10 = hardest 10%). In Anki's browser:

| you are | delete | set as reviews | study as new |
|---|---|---|---|
| A1 | – | – | everything |
| A2 | levels 1–2 | levels 3–4 | 5+ |
| B1 | levels 1–4 | levels 5–6 | 7+ |
| B2 | levels 1–6 | levels 7–8 | 9+ |
| C1 | levels 1–7 | level 8 | 9+ |

"Set as reviews" means: select the band → *Cards → Set Due Date* → `90-180!`. Those cards then appear once over
the next few months and only stick around if you miss them. Full walkthrough, other useful tags and how to shift
the table: [docs/LEVELS.md](docs/LEVELS.md).

Latin American learners: the `region::vosotros` and `region::spain` tags mark the Spain-specific sentences, so
`tag:region::*` → suspend removes them from any deck in one go.

## How difficulty is measured (short version)

Every word is lemmatised and looked up in a 5,000-word frequency list. A sentence's score is mostly the rank of
its **hardest word** (which becomes the "target word" shown on the answer), plus the second-hardest word, a count
of rare words, a little for length, and a bump for grammar the parser detects: subjunctive (most), conditional,
perfect tenses, imperative, past, future, gerund. Decks are sorted by that score. Details, weights and known
weaknesses: [docs/METHOD.md](docs/METHOD.md).

## Cards

- **Read**: Spanish sentence (audio button if available) → English. The hardest word is highlighted with its
  dictionary gloss and frequency rank.
- **Translate**: English → produce the whole Spanish sentence. Hints (collapsed): the Spanish sentence with the
  key word blanked, and the key word alone. Use them for the first encounters, ignore them later.

Audio plays automatically on the side it appears on; set *Don't play audio automatically* in the deck options
if you prefer a button.

## Build it yourself

```bash
pip install -r requirements.txt && python -m spacy download es_core_news_md
cp sources.example.json sources.json      # point it at the source .apkg files you downloaded from AnkiWeb
make vocab      # merges the two Top-5000 vocab decks -> data/vocab_words.tsv (frequency ranks)
make decks      # pool -> score -> five .apkg files in decks/
make verify     # imports each deck into a scratch Anki collection and checks it
```

Or one variant at a time, e.g. a B2 preset of the Tatoeba-only deck:

```bash
cd pipeline && python build_sentences.py --scored ../data/scored.tsv --levels ../data/levels.json \
  --rankmap ../data/rankmap.json --sources-json ../sources.json --sources tatoeba --variant latam \
  --level B2 --review-cap 500 --name "Spanish Sentences – B2" --out ../decks/b2.apkg
```

Pipeline steps: `pool.py` (read, clean, dedupe) → `score.py` (lemmatise, rank, grammar, regional flags) →
`build_sentences.py` (variant, level preset, Core/Extended split, package) → `verify.py`.

## Support

If this saved you some time, you can buy me a coffee: https://buymeacoffee.com/akuzee. Nothing is paywalled and nothing will be.

## Credits

- **Sentences**: the [Tatoeba Project](https://tatoeba.org) (CC BY 2.0 FR), via the AnkiWeb decks
  *9000 Spanish sentences – difficulty sorted with native audio* and *spanish 7500 intermediate/advanced
  sentences*; and the subtitle-based *Neri's Spanish Sentences* Parts 1–3 by [Neri](https://www.patreon.com/neri).
- **Audio**: native recordings by Tatoeba user [arh](https://tatoeba.org/en/user/profile/arh)
  (CC BY-NC-ND 3.0, unmodified); TTS recordings by the author of the 7500 deck.
- **Frequency ranks**: the *Top 5000* vocabulary decks on AnkiWeb, built on Mark Davies' *A Frequency Dictionary
  of Spanish* (Routledge).
- **Tools**: spaCy, simplemma, Anki.

Full table with licenses and what it means for redistribution: [docs/SOURCES.md](docs/SOURCES.md).
