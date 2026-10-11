# Adjusting a deck to your level

Every note carries a `level::01` … `level::10` tag: the difficulty deciles of the whole sentence pool.
Roughly, for a plain sentence of ordinary length:

| level | hardest word is about | feels like |
|---|---|---|
| 1–3 | top 300 words, 2–5 words long | A1 |
| 4 | top 500 | A1/A2 |
| 5–6 | top 1,000–1,500 | A2 |
| 7 | top 2,000 | B1 |
| 8 | top 3,000, or common words with subjunctive/conditional | B1/B2 |
| 9 | top 5,000 | B2 |
| 10 | beyond the 5,000 list, or several hard words at once | B2/C1 |

Grammar shifts a sentence up: subjunctive adds roughly one level, conditional a bit less, perfect/past/future a
little. So a level-8 sentence is either a B2 word in a simple frame or a B1 word in a subjunctive clause.

## The three operations you need (Anki desktop, Browse window)

1. **Search a band.** In the search box: `tag:level::01 OR tag:level::02` (or `tag:level::0*` for 1–9,
   `"deck:Spanish Sentences – Quality cut" tag:level::03`).
2. **Delete or suspend it.** Select all (Ctrl/Cmd-A) → Notes → Delete, or Cards → Toggle Suspend if you'd rather
   keep them around.
3. **Turn a band into long-interval reviews** (the "I probably know this, test me later" treatment):
   select all → Cards → Set Due Date → type `90-180!` → OK. The `!` makes Anki also set the interval to the
   due date, so the cards become review cards that show up once, spread over the next 3–6 months, and then follow
   the normal schedule. If you fail one, it comes back like any lapsed card.

Do the operations in that order: delete what is below you, set the band just under your level as reviews, leave
the rest as new cards in their difficulty order.

## Recommended presets

| you are | delete | set as reviews (`90-180!`) | study as new |
|---|---|---|---|
| A1 | nothing | nothing | everything from level 1 |
| A2 | levels 1–2 | levels 3–4 | 5 and up |
| B1 | levels 1–4 | levels 5–6 | 7 and up |
| B2 | levels 1–6 | levels 7–8 | 9 and up |
| C1 | levels 1–7 | level 8 | 9 and up |

The review bands are large (each level is ~5,500 sentences in the full pool, ~1,300 in the Tatoeba-only deck).
If that is too many reviews, keep only part of the band: sort the browser by the *Score* field, select the top
1,000 of the band, and set only those. The pre-built `--level` decks do exactly that, with a cap of 1,000.

Shift the whole table by one level if the first new cards feel too easy or too hard. Nothing is lost by
guessing wrong: deleted cards can be re-imported from the same file (Anki skips notes that already exist and adds
the missing ones).

## Other useful tags

| tag | meaning |
|---|---|
| `region::vosotros` | uses *vosotros* forms (Spain) |
| `region::spain` | contains Spain-leaning vocabulary (*ordenador, zumo, coger, vale, …*) |
| `gram::subj`, `gram::cond`, `gram::perf`, `gram::past`, `gram::fut`, `gram::imper`, `gram::ger` | grammar detected in the sentence |
| `audio::yes` | has a recording |
| `src::tatoeba_native`, `src::tatoeba_tts`, `src::neri1/2/3` | where the sentence came from |
| `quality::low`, `drop::*` | (macro deck only) failed the quality filter, and why |
| `tier::core`, `tier::extended`, `tier::review` | (split decks only) which subdeck/role it was given |

Example: Latin American learner who wants the subjunctive drilled first:
`tag:gram::subj -tag:region::vosotros -tag:region::spain` → select all → Cards → Reposition → start 1.

## Building your own preset instead
`python pipeline/build_sentences.py --level B2 --review-cap 500 --variant latam --split-core 2 …` does all of
the above at build time (see `docs/METHOD.md`).
