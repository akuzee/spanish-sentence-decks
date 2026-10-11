# Usage: copy sources.example.json to sources.json, edit the paths, then `make decks`.
PY ?= python3
PIPE = pipeline
DATA = data
DECKS = decks
VOCAB_OLD ?= ~/Downloads/Spanish_Top_5000_Vocabulary.apkg
VOCAB_NEW ?= ~/Downloads/New_Spanish_Top_5000_Vocabulary.apkg

.PHONY: all vocab pool rankmap score decks verify clean
all: decks

vocab: $(DATA)/vocab_words.tsv
$(DATA)/vocab_words.tsv:
	mkdir -p $(DATA) $(DECKS)
	cd $(PIPE) && $(PY) vocab_merge.py --old $(VOCAB_OLD) --new $(VOCAB_NEW) --out ../$(DECKS)/Spanish_Top_5000_Merged.apkg --report ../$(DATA)/vocab_words.tsv --work ../work

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
	# AnkiWeb uploads (<150 MB): native recordings only
	$(BUILD) --variant quality --audio native --name "Spanish Sentences – sorted by difficulty"            --out ../$(DECKS)/Spanish_Sentences.apkg --report ../$(DATA)/report_quality.tsv
	$(BUILD) --variant macro   --audio native --name "Spanish Sentences – Macro (everything, by difficulty)" --out ../$(DECKS)/Spanish_Sentences_Macro.apkg --report ../$(DATA)/report_macro.tsv
	$(BUILD) --variant latam   --audio native --name "Spanish Sentences – Latin American cut"               --out ../$(DECKS)/Spanish_Sentences_LatAm.apkg --report ../$(DATA)/report_latam.tsv
	# full-audio builds (also include the 7500 deck's TTS recordings), for GitHub Releases
	$(BUILD) --variant quality --name "Spanish Sentences – sorted by difficulty"   --out ../$(DECKS)/Spanish_Sentences_FullAudio.apkg
	$(BUILD) --variant latam --sources tatoeba --name "Spanish Sentences – Tatoeba only (LatAm cut)" --out ../$(DECKS)/Spanish_Sentences_Tatoeba_LatAm.apkg
	$(BUILD) --variant latam --sources tatoeba --audio native --name "Spanish Sentences – Tatoeba, Latin American cut, native audio" --out ../$(DECKS)/Spanish_Sentences_Tatoeba_LatAm_NativeAudio.apkg --report ../$(DATA)/report_tatoeba_latam.tsv
	$(BUILD) --variant latam --level B1 --split-core 2 --name "Spanish Sentences – B1 LatAm (Core/Extended)" --out ../$(DECKS)/Spanish_Sentences_B1_LatAm.apkg --report ../$(DATA)/report_b1_latam.tsv

verify:
	cd $(PIPE) && for f in ../$(DECKS)/*.apkg; do echo "== $$f"; $(PY) verify.py $$f --tmp ../work/_verify; done

clean:
	rm -rf work $(DATA)/*.tsv $(DATA)/*.json $(DECKS)/*.apkg _build_*
