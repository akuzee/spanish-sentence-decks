# How the decks are built

This is the long version. The short version is in the README.

## 1. Pooling (`pipeline/pool.py`)
Every note of every source deck is read directly from the `.apkg` (SQLite + media index). Only the *Read*
direction of the Neri decks is used, because the *Speak* cards repeat the same sentences. Each Spanish line is
normalised:

- stray spaces before `? ! . , ; :` removed; `¿`/`¡` added when a sentence ends in `?`/`!` without one;
- a direct question starting with an unaccented *que/como/donde/cuando/cuanto/quien/cual/adonde* gets its accent
  (`¿Que piensas?` → `¿Qué piensas?`); nothing else is touched, because other accent errors are not decidable
  without context;
- when a subtitle card stacks several Spanish renderings (`A. <br> B.`), the best-accented one is kept;
- first letter capitalised.

Nothing is deleted at this stage. A `quality` flag marks lines that pass the quality filter: 4–16 words, an
English translation that exists and differs from the Spanish, no subtitle artifacts (`♪ [ ] -` leading dashes,
URLs), ends in punctuation, no long numbers. Duplicates (same letters, ignoring accents, case and punctuation) are
collapsed, keeping the copy from the highest-priority source (native-audio Tatoeba > TTS Tatoeba > Neri 2 > Neri 3
> Neri 1) and inheriting audio from a duplicate if the kept copy has none.

Pool size from the five decks: 79,532 cards → 54,754 distinct quality sentences (+ ~24,000 fragments under
four words that only the *macro* variant keeps).

## 2. Frequency ranks (`pipeline/vocab_merge.py`, `pipeline/rankmap.py`)
The two *Top 5000* vocabulary decks use different editions of Davies' frequency list, so they are merged by
headword (4,399 shared words, 601 only in each). A word's rank is the average of the two lists when both have it.
`rankmap.py` turns the merged list into a lookup that also accepts the variants a headword can take
(`el,la`, `a través (de)`, `cualquier(a)`, phrase entries like `sin embargo`).

## 3. Scoring (`pipeline/score.py`)
Each sentence is parsed with spaCy `es_core_news_md`. For every content token (not punctuation, numbers or proper
nouns) the lemma is looked up in the rank map. Because the statistical lemmatiser misses many conjugated forms,
three sources are tried and the best (lowest) rank wins: spaCy's lemma, simplemma's lemma, and a rule-based
fallback that strips clitics (`dímelo` → `di` → *decir*) and conjugation endings and maps irregular stems
(`salg-` → *salir*, `tuv-` → *tener*, …). Content words still unresolved count as rank 6,500 ("beyond the list").

    score = 0.6 · rank(hardest word)
          + 0.25 · rank(second-hardest word)
          + 150 · (number of words ranked above 2000)
          + 80 · (number of words)
          + grammar

    grammar = 600 subjunctive + 400 conditional + 250 perfect (haber + participle)
            + 150 imperative + 150 past (preterite/imperfect) + 120 future + 80 gerund

The hardest word is stored as the sentence's **target word**; it is highlighted on the answer side and drives
the Core/Extended split. Rough anchors on this scale, for a plain six-word sentence:

| hardest word rank | ≈ score | level tag |
|---|---|---|
| 500 | 900 | 4 |
| 1,000 | 1,250 | 6 |
| 2,000 | 1,950 | 7 |
| 3,000 | 2,700 | 8 |
| 4,000+ / off-list | 3,300+ | 9–10 |

Level tags `level::01` … `level::10` are the deciles of the quality pool's score distribution (cut points in
`data/levels.json`), so they mean the same thing in every variant.

Sanity check: on the 9,000-sentence deck, whose author sorted by the frequency of the cloze word, our score rises
monotonically across that deck's own difficulty quintiles (means ≈ 1300 / 2000 / 2500 / 3000 / 3500). That deck's
*Difficulty* field ranks inflected surface forms from a Wiktionary frequency list (so *pasaste* counts as rare even
though *pasar* is common), which is why it is kept as a field but not reused for ordering.

Proper nouns are excluded from scoring, except that a lowercase token the parser tags as a name (it does this to
unfamiliar verbs between two names, as in *Tom estafó a Mary*) is kept and treated as an unresolved content word.

### Regional flags
- **vosotros**: a verb tagged second-person plural by the parser, an unambiguous ending
  (`-áis/-éis/-asteis/-isteis/-abais/-íais/-aréis/-aríais …`, imperative `-ad/-ed/-id` + clitic), or one of
  *vosotros/vosotras/vuestro/os/sois/vais/habéis…* → tag `region::vosotros`. 194 sentences in the pool.
- **Spain-leaning vocabulary**: a hand list of ~80 words/phrases that Latin American Spanish usually says
  differently (*ordenador, zumo, patata, coger, vale, piso, tío, autobús, conducir, enfadado, echar de menos,
  gilipollas …*), weighted 1 (common elsewhere too) or 2 (strong marker) → tag `region::spain`. 470 sentences.

## 3b. Curation for the published decks (`pipeline/curate.py`)
Three flags per sentence, each a judgement call made once and documented here:

- **C1+**: the sentence needs C1-level vocabulary: a content word outside the 5,000-word list, or two or more
  words beyond rank 4,000 (a common B2 ceiling). 4,810 of the 54,754 quality sentences. Everything else is "pre-C1"
  and goes in the main deck; the C1+ sentences form the challenge deck. The reasoning: sentence drilling pays off
  up to about C1, after which ordinary reading and listening does the job, but the material is kept for completeness.
- **near-repetition**: the same bag of lemmas with the same grammar features as a better sentence, or an 85%+
  lemma overlap for sentences of six words or more, again with the same grammar. A different tense is not a
  repetition (*lo hizo* / *lo haré* both stay). 2,555 removed; the kept copy is the best-quality one.
- **extra low quality**: on top of the pool filter, subtitle lines that carry a character name (1,346) and lines that
  trail off with an ellipsis (11).

Not applied, deliberately: a cap on how many sentences share a target word. The most common target words ("todo",
"favor", "aquí") head hundreds of sentences each, but those are sentences made entirely of common words, which is
exactly what the easy levels should contain.

## 4. Building (`pipeline/build_sentences.py`)
Variants: `macro` (everything), `quality` (quality flag only), `latam` (quality minus both regional flags).
`--sources tatoeba` restricts to the two Tatoeba decks.

Ordering inside a deck is by score, with small penalties that only matter for ties and for pushing doubtful
material back: subtitle sources after Tatoeba, sentences with character names, sentences with an unresolved word,
Spain-leaning vocabulary; vosotros sentences go to the very end. With `--split-core N`, the best N sentences per
target word (by those same quality criteria) form subdeck *1 Core*; everything else is *2 Extended* in the same
order, with the fourth-and-later sentence of a word demoted a little further. Anki draws new cards from Core
first when you study the parent deck.

Level presets (`--level`) use the level tags: the levels below the preset are dropped, the band just under it is
kept as long-interval reviews (Read card 120–240 days, Translate card 60–150 days, capped at `--review-cap`,
default 1,000, choosing the highest-scored, best-quality sentences of the band), the rest are new cards.

| preset | dropped | reviews | new |
|---|---|---|---|
| A1 / none | – | – | levels 1–10 |
| A2 | 1–2 | 3–4 | 5–10 |
| B1 | 1–4 | 5–6 | 7–10 |
| B2 | 1–6 | 7–8 | 9–10 |
| C1 | 1–7 | 8 | 9–10 |

## 5. Card design
Note type *Spanish Sentence (merged)* with fields Spanish, English, Audio, Spanish Marked (target word in bold),
Target, Target Gloss, Sentence with blank, Key word, Level, Grammar, Source, Score, Target Rank, Words.

- **Read**: Spanish (+ audio button) → English, target word and gloss, level/grammar/source line.
- **Translate**: English → the full Spanish sentence. Two collapsed hints (Anki `{{hint:…}}`): the sentence with
  the target word blanked, and the target word itself. Meant as scaffolding for the first encounters; the point is
  to produce the whole sentence.

Audio is attached wherever a source had it (native Castilian recordings from the 9,000 deck, TTS from the 7,500
deck). Turn on *Don't play audio automatically* in the deck options if you want it only on demand.

## 6. How review cards survive import
Legacy `.apkg` files store review due dates as days since the collection's creation. The builder sets the
package's creation date to the build day and `due = interval`, and Anki's importer shifts due dates by the
difference between the package's and the target collection's "today". Net effect: a card built as "review in
90 days" is due 90 days after the *build* date. `verify.py` checks this by importing into a collection that is
artificially 400 days old. Import within a few days of building, or rebuild.

## 7. Packaging
Anki writes media into an .apkg uncompressed. Our writers deflate every entry instead, which is lossless and
imports normally, and happens to matter a lot for synthetic speech: the Azure recordings in the vocabulary deck
shrink to ~52% (silence padding compresses), real recordings barely change. That is the difference between 154 MB
and 105 MB for the vocabulary deck. `pipeline/repack.py` applies the same to any existing package.

The sentence decks' native recordings are real speech and barely compress, and the synthetic clips are already
lean 32 kbps files, so the 54,754-sentence deck with all its audio (192 MB) cannot be squeezed under AnkiWeb's limit
without audible loss. The AnkiWeb release therefore splits the deck by vocabulary (`--c1 exclude` / `--c1 only`): the curated pre-C1
deck (150 MB) and the C1+ deck (40 MB), each with every recording untouched. Native recordings are never
re-encoded in any build (also a condition of their CC BY-NC-ND license). For other size targets the builder also has
`--tts-max-level` (drop synthetic clips above a level) and `--tts-bitrate` (re-encode them, average-bitrate mono),
and `pipeline/shrink_audio.py` is the blunt fallback that re-encodes every MP3 in a package.

## 8. Known limitations
- About 8% of sentences contain a content word the lemmatiser could not map (mostly genuinely rare words), which
  pushes them slightly later than they deserve.
- The parser occasionally misses a subjunctive or tags *hubieras* as indicative; grammar weights are therefore a
  nudge, not a guarantee.
- Subtitle lines lose their scene; a few only make sense in context. They are ranked after Tatoeba for that reason.
- Proper names in Tatoeba sentences (Tom, Mary, Juan, María) are kept; names are ignored for scoring.
- Difficulty is lexical and grammatical, not idiomatic: a short idiom made of common words scores low.
