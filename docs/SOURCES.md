# Sources and credits

Every sentence, recording and frequency rank in these decks comes from someone else's work. This file lists
what was taken from where, under which terms, and what that means for redistribution. If you are one of the
authors below and want something changed or removed, open an issue.

## Sentence decks (inputs to the pipeline)

| label in the pipeline | deck | author | what we used | underlying license |
|---|---|---|---|---|
| `tatoeba_native` | *9000 Spanish sentences – difficulty sorted with native audio* ([AnkiWeb 1713698257](https://ankiweb.net/shared/info/1713698257)) | AnkiWeb author (see deck page) | 9,263 Spanish/English sentence pairs with the recordings | Sentences: Tatoeba, CC BY 2.0 FR. Audio: Tatoeba user **arh**, CC BY-NC-ND 3.0 (see below). The deck author wrote: *"I'm perfectly happy for anyone else to re-share this (as long as it's properly attributed to the above sources and to this deck)."* |
| `tatoeba_tts` | *spanish 7500 intermediate/advanced sentences* (AnkiWeb, 2017) | AnkiWeb author (see deck page) | 7,627 sentence pairs; the author's synthetic (TTS) recordings | Sentences: Tatoeba, CC BY 2.0 FR. TTS audio: no license stated by the deck author. |
| `neri1`, `neri2`, `neri3` | *Neri's Spanish Sentences* Parts 1–3 (*"spanish 10 000 sentences from easier to hardest"*) | [Neri](https://www.patreon.com/neri/about) | Read cards only (Speak cards duplicate them): 2,000 + 2,855 + 57,787 sentence pairs | No license stated. The lines are film/TV subtitle translations, whose underlying text is copyrighted by the respective studios. |

### Tatoeba
Tatoeba ([tatoeba.org](https://tatoeba.org)) releases sentence text under
[CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/). Attribution to the Tatoeba Project is required
and is included in every deck description.

Audio on Tatoeba is licensed per contributor. The Castilian recordings in these decks were made by
[arh](https://tatoeba.org/en/user/profile/arh) (native speaker, central Spain; 108,000+ recordings), who licenses
them under **CC BY-NC-ND 3.0** with attribution to his Tatoeba profile and to the Tatoeba Project. Non-commercial
use is allowed, the recordings may not be modified, and the sentence author may replace a recording at any time.
The recordings here are unmodified.

### What that means for sharing the output decks
- **Tatoeba-only variants** (`--sources tatoeba`): text CC BY 2.0 FR, audio CC BY-NC-ND 3.0 → fine to share
  non-commercially with the credits above. The TTS recordings from the 7500 deck are the one grey spot; if in
  doubt, build with the native-audio deck only.
- **Variants that include Neri's subtitle lines**: the subtitle text has no clear license and the deck author has
  not stated one. We recommend *not* uploading those variants to AnkiWeb unless you have Neri's permission.
  The pipeline lets anyone who downloaded Neri's decks build the full merge locally in a few minutes.
- AnkiWeb removes copyrighted material on request and the uploader carries the responsibility, so when in doubt,
  leave it out.

## Frequency ranks (how difficulty is measured)

Sentence difficulty is driven by the frequency rank of each word's lemma. The ranks come from the two
*Top 5000* vocabulary decks on AnkiWeb, *Essential Spanish Vocabulary Top 5000* (2017; pictures; 2006 ranks) and
*New Spanish Top 5000 with Examples* (2025; Azure audio; example sentences), merged by headword by
`pipeline/vocab_merge.py`. Both decks reproduce Mark Davies' *A Frequency Dictionary of Spanish* (Routledge,
2006/2018): headwords, ranks and glosses are the dictionary's. Because of that:

- the merged vocabulary deck is **not** part of the public release (build it locally if you own the source decks);
- the word → rank table (`data/rankmap.json`) is not committed either;
- the public sentence decks carry only a per-sentence *Target Rank* number; the short dictionary gloss of the
  target word can be left out of a build with `--no-gloss`.

## Tools
spaCy `es_core_news_md` (MIT model license), simplemma (MIT), Anki (AGPL; used only to verify the packages).
