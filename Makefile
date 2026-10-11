# Usage: copy sources.example.json to sources.json, edit the paths, then `make decks`.
PY ?= python3
PIPE = pipeline
DATA = data
DECKS = decks
VOCAB_OLD ?= ~/Downloads/Spanish_5000_Words_Merged.apkg
VOCAB_NEW ?= ~/Downloads/New_Spanish_5000_Words_Merged.apkg

.PHONY: all vocab vocab-public pool rankmap score decks verify clean
all: decks

vocab: $(DATA)/vocab_words.tsv
$(DATA)/vocab_words.tsv:
	mkdir -p $(DATA) $(DECKS)
	cd $(PIPE) && $(PY) vocab_merge.py --old $(VOCAB_OLD) --new $(VOCAB_NEW) --out ../$(DECKS)/Spanish_Top_5000_Merged.apkg --report ../$(DATA)/vocab_words.tsv --work ../work

vocab-public: $(DATA)/vocab_words.tsv
	cd $(PIPE) && $(PY) vocab_merge.py --old $(VOCAB_OLD) --new $(VOCAB_NEW) --mode public --out ../$(DECKS)/Spanish_5000_Words_Merged.apkg --report ../$(DATA)/vocab_words_public.tsv --work ../work
	# if a package still exceeds AnkiWeb's limit: shrink_audio.py re-encodes the MP3s (lossy); repack.py only re-compresses the zip (lossless)

rankmap: $(DATA)/rankmap.json
$(DATA)/rankmap.json: $(DATA)/vocab_words.tsv
	cd $(PIPE) && $(PY) rankmap.py --vocab ../$(DATA)/vocab_words.tsv --out ../$(DATA)/rankmap.json

pool: $(DATA)/pool.tsv
$(DATA)/pool.tsv: sources.json
	mkdir -p $(DATA)
	cd $(PIPE) && $(PY) pool.py --sources ../sources.json --work ../work --out ../$(DATA)/pool.tsv

score: $(DATA)/scored.tsv
$(DATA)/scored.tsv: $(DATA)/pool.tsv $(DATA)/rankmap.json
	cd $(PIPE) && $(PY) score.py --pool ../$(DATA)/pool.tsv --rankmap ../$(DATA)/rankmap.json --out ../$(DATA)/scored.tsv --levels ../$(DATA)/levels.json

BUILD = cd $(PIPE) && $(PY) build_sentences.py --scored ../$(DATA)/scored.tsv --levels ../$(DATA)/levels.json --rankmap ../$(DATA)/rankmap.json --sources-json ../sources.json --work ../work
decks: $(DATA)/scored.tsv
	mkdir -p $(DECKS)
	# AnkiWeb uploads (<150 MB each): the main deck is split in two so every recording stays at its original quality
	$(BUILD) --variant quality --audio all --level-max 8 --name "Spanish Sentences::1 Levels 1–8"               --out ../$(DECKS)/Spanish_Sentences_Levels_1-8.apkg   --report ../$(DATA)/report_levels_1-8.tsv
	$(BUILD) --variant quality --audio all --level-min 9 --name "Spanish Sentences::2 Advanced (levels 9–10)"  --out ../$(DECKS)/Spanish_Sentences_Advanced_9-10.apkg --report ../$(DATA)/report_levels_9-10.tsv
	$(BUILD) --variant macro   --audio native --name "Spanish Sentences – Macro (everything, by difficulty)"     --out ../$(DECKS)/Spanish_Sentences_Macro.apkg --report ../$(DATA)/report_macro.tsv
	# GitHub Releases only (no size limit): one-file versions with all audio
	$(BUILD) --variant quality --audio all --name "Spanish Sentences – sorted by difficulty"   --out ../$(DECKS)/Spanish_Sentences_FullAudio.apkg --report ../$(DATA)/report_quality.tsv
	$(BUILD) --variant latam   --audio all --name "Spanish Sentences – Latin American cut"     --out ../$(DECKS)/Spanish_Sentences_LatAm.apkg --report ../$(DATA)/report_latam.tsv
	$(BUILD) --variant latam --sources tatoeba --name "Spanish Sentences – Tatoeba only (LatAm cut)" --out ../$(DECKS)/Spanish_Sentences_Tatoeba_LatAm.apkg
	$(BUILD) --variant latam --sources tatoeba --audio native --name "Spanish Sentences – Tatoeba, Latin American cut, native audio" --out ../$(DECKS)/Spanish_Sentences_Tatoeba_LatAm_NativeAudio.apkg --report ../$(DATA)/report_tatoeba_latam.tsv
	$(BUILD) --variant latam --level B1 --split-core 2 --name "Spanish Sentences – B1 LatAm (Core/Extended)" --out ../$(DECKS)/Spanish_Sentences_B1_LatAm.apkg --report ../$(DATA)/report_b1_latam.tsv

verify:
	cd $(PIPE) && for f in ../$(DECKS)/*.apkg; do echo "== $$f"; $(PY) verify.py $$f --tmp ../work/_verify; done

clean:
	rm -rf work $(DATA)/*.tsv $(DATA)/*.json $(DECKS)/*.apkg _build_*
