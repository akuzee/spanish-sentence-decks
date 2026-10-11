# Draft AnkiWeb descriptions

AnkiWeb descriptions take plain text with limited HTML. One deck page per file. Replace GITHUB_URL.

## Spanish Sentences – Tatoeba only (Latin American cut)

13,191 Spanish sentences with English translations and native audio, sorted from easy to hard by a single
difficulty score, with Spain-specific sentences (vosotros forms, Spain-only vocabulary) removed.

WHAT YOU GET
• Two cards per sentence: Read (Spanish → English) and Translate (English → the full Spanish sentence, with two
  optional hints: the sentence with its key word blanked, and the key word).
• The hardest word of each sentence is highlighted on the answer with its meaning and frequency rank.
• Tags level::01 … level::10 (difficulty deciles), gram::subj/cond/perf/past/fut/imper/ger, audio::yes.

START AT YOUR LEVEL
In the browser, search a band (e.g. tag:level::01 OR tag:level::02), then delete it or use Cards → Set Due Date
→ "90-180!" to turn it into occasional reviews. Suggested: A2 delete 1–2 / review 3–4; B1 delete 1–4 /
review 5–6; B2 delete 1–6 / review 7–8. Full guide: GITHUB_URL/blob/main/docs/LEVELS.md

HOW IT IS SORTED
Each word is lemmatised and looked up in a 5,000-word frequency list; the score is mainly the rank of the
hardest word, plus a bump for grammar (subjunctive, conditional, perfect, past, future…). Method, code and other
variants (quality cut, everything-included "macro", B1 preset): GITHUB_URL

AUDIO
Native recordings (central Spain accent) for every sentence from the 9000-sentence deck; synthetic voice for the
rest. To play on demand only: deck options → "Don't play audio automatically".

CREDITS
Sentences from the Tatoeba Project (tatoeba.org), CC BY 2.0 FR. Audio recorded by Tatoeba user arh
(tatoeba.org/en/user/profile/arh), CC BY-NC-ND 3.0, unmodified. Sentence selection via the AnkiWeb decks
"9000 Spanish sentences – difficulty sorted with native audio" (ankiweb.net/shared/info/1713698257) and
"spanish 7500 intermediate/advanced sentences"; thanks to both authors. Re-sorted and re-packaged by Adam Kuzee.
Problems with a sentence? Open an issue at GITHUB_URL.

## Spanish Sentences – Latin American cut (54,097) / Quality cut (54,754) / Macro (78,016)

(Only publish these if the subtitle material is cleared; see docs/SOURCES.md.)

Same as above, plus ~41,000 colloquial lines from film and TV subtitles (Neri's Spanish Sentences, Parts 1–3),
no audio on those. "Quality cut" keeps every complete 4–16-word sentence; "Latin American cut" also removes
sentences with vosotros or Spain-only vocabulary; "Macro" removes nothing at all (fragments and odd lines are
tagged quality::low) for people who want to do their own cutting.
