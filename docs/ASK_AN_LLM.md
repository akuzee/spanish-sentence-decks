# Ask an LLM to build you an add-on deck

The published decks are one selection from a much larger pool. If you want more practice at your level before
moving on, or more of one thing (subjunctive, past tenses, words ranked 1,500–2,500, only sentences with audio),
an LLM can pull it from the bank and hand you a file to import. This page is written so you can paste it to
Claude, ChatGPT or similar together with your request.

## What exists

- **`bank/sentence_bank.tsv.gz`** in this repository (also attached to the GitHub release): all 78,016 distinct
  sentences from the five source decks, scored and tagged. Tab-separated, one row per sentence, columns:

  | column | meaning |
  |---|---|
  | `spanish`, `english` | the sentence and its translation |
  | `level` | difficulty decile 1 (easiest) to 10, same scale as the deck tags `level::01`–`level::10` |
  | `score` | the raw difficulty score behind the level |
  | `hardest_word`, `hardest_word_rank` | the rarest word in the sentence and its frequency rank (1 = most common; `off-list` = beyond the 5,000 most frequent) |
  | `grammar` | detected features: `subj` (subjunctive), `cond`, `perf` (haber + participle), `past`, `fut`, `imper`, `ger` |
  | `source` | `tatoeba_native` (native audio), `tatoeba_tts` (synthetic audio), `neri1/2/3` (film subtitles, no audio) |
  | `audio_file` | filename of the recording, if any |
  | `region` | `vosotros` and/or `spain` for Spain-specific sentences |
  | `quality` | `ok`, or why the line failed the quality filter (fragment, artifacts, …) |
  | `c1` | `1` if the sentence needs C1 vocabulary (a word beyond the 5,000 list) |
  | `near_duplicate_of`, `low_quality_reason` | curation notes; non-empty means the published decks left it out |
  | `in_main_deck`, `in_c1_deck` | `1` if the sentence is already in the published main / challenge deck |

- The published decks use the note type **Spanish Sentence (merged)** with fields `Spanish`, `English`, `Audio`,
  `Spanish Marked`, `Target`, `Target Gloss`, `Sentence with blank`, `Key word`, `Level`, `Grammar`, `Source`,
  `Score`, `Target Rank`, `Words`.

## What to do (instructions for the LLM)

1. Load the bank. Exclude rows already in the user's deck (`in_main_deck = 1`, and `in_c1_deck = 1` if they
   have that one). Prefer `quality = ok`, empty `near_duplicate_of` and empty `low_quality_reason`, unless the user
   asks for volume above all.
2. Filter to what the user is struggling with. Typical requests and the columns to use:
   - "more sentences at my level": `level` between the user's current level ±1;
   - "more subjunctive / conditional / past tense": `grammar` contains `subj` / `cond` / `past`, at the user's level;
   - "words I keep missing": `hardest_word` in the user's list, or `hardest_word_rank` in a band such as 1500–2500;
   - "only with audio": `audio_file` non-empty (these are all Tatoeba sentences);
   - "no subtitle lines": `source` starts with `tatoeba`; "Latin American only": `region` empty.
3. Rank the candidates: Tatoeba before subtitles, with audio before without, 6–12 words before very short or
   very long, then by `score` ascending so the add-on also runs easy to hard. Take as many as the user asked for
   (a few hundred is a typical add-on).
4. Write a tab-separated file with the columns `Spanish`, `English`, `Audio`, `Level`, `Grammar`, `Source`,
   `Target`, `Target Rank`, and a `tags` column such as `addon level::07 gram::subj`. For `Audio` write
   `[sound:FILENAME]` when `audio_file` is non-empty; the recording will play if the user has imported the
   Macro deck or the full-audio deck (Anki keeps all media in one folder), and is silently ignored otherwise.
   `Spanish Marked` and `Sentence with blank` may be left empty.
5. Tell the user how to import: Anki → File → Import → choose the file → note type *Spanish Sentence (merged)*,
   deck of their choice (a subdeck of the main deck keeps it together), map the columns to the fields, tick
   "allow HTML in fields". Anki skips sentences that already exist.

If the user wants a proper `.apkg` with audio instead, the pipeline in this repository builds one:
write the chosen sentences to a text file (one per line) and run
`pipeline/build_sentences.py … --only-list that_file.txt` after `make score` (needs the source decks on disk;
see README).

## A prompt the user can paste

> Here is `sentence_bank.tsv.gz` from github.com/akuzee/spanish-sentence-decks and its `docs/ASK_AN_LLM.md`.
> I'm using the main deck and I'm around level 6. I keep failing sentences with the subjunctive and with
> words ranked 1,500–2,500. Build me an add-on of about 300 sentences I don't have yet, Tatoeba first, with
> audio where possible, sorted easy to hard, as a TSV I can import into the "Spanish Sentence (merged)" note type.
