"""Step 1: pool every sentence from the source decks into one TSV.

Nothing is thrown away here. Each row gets a `quality` flag (1 = passes the quality filter) and a `drop_reason`,
so the 'macro' variant can use every distinct sentence while the other variants use only quality rows.
Typography is normalised for all rows: stray spaces before punctuation, missing ¿/¡, unaccented question words
at the start of a direct question, capitalisation.
"""
import argparse, collections, csv, json, re, sys
from common import Apkg, strip_html, dedup_key

QWORDS = {"que": "qué", "como": "cómo", "donde": "dónde", "cuando": "cuándo", "cuanto": "cuánto", "cuanta": "cuánta", "cuantos": "cuántos",
          "cuantas": "cuántas", "quien": "quién", "quienes": "quiénes", "cual": "cuál", "cuales": "cuáles", "adonde": "adónde"}

def tidy(es: str) -> str:
    es = strip_html(es)
    es = re.sub(r"\s+([?!.,;:])", r"\1", es)
    es = re.sub(r"([¿¡])\s+", r"\1", es)
    if es.endswith("?") and "¿" not in es: es = "¿" + es
    if es.endswith("!") and "¡" not in es: es = "¡" + es
    if es.startswith("¿"):
        es = re.sub(r"^¿(\w+)\b", lambda m: "¿" + QWORDS.get(m.group(1).lower(), m.group(1)) if m.group(1).lower() in QWORDS else m.group(0), es)
        es = re.sub(r"^¿Por que\b", "¿Por qué", es, flags=re.I)
    if es and es[0].islower(): es = es[0].upper() + es[1:]
    if len(es) > 1 and es[0] in "¿¡" and es[1].islower(): es = es[0] + es[1].upper() + es[2:]
    return es

def nwords(s: str) -> int:
    return len(re.findall(r"[A-Za-zÀ-ÿñÑ]+(?:'[A-Za-zÀ-ÿ]+)?", s))

def first_variant(raw: str) -> str:
    """Subtitle decks stack several Spanish renderings separated by <br>; keep the best-accented one."""
    variants = [v for v in re.split(r"<br\s*/?>", raw, flags=re.I) if strip_html(v)]
    variants.sort(key=lambda v: -sum(1 for c in strip_html(v) if c in "áéíóúñ¿¡"))
    return variants[0] if variants else raw

def quality_check(es: str, en: str) -> str:
    n = nwords(es)
    if not en or dedup_key(en) == dedup_key(es): return "no/identical english"
    if n < 4: return "<4 words"
    if n > 16: return ">16 words"
    if re.search(r"[♪\[\]{}<>|_*#@]|^[-–—]|https?:", es) or re.search(r"[♪\[\]{}<>|_*#@]|^[-–—]", en): return "artifact chars"
    if not re.search(r"[.?!…»\"']$", es): return "no terminal punctuation"
    if re.search(r"\d{3,}", es): return "long numbers"
    return ""

# How each known source deck maps onto (spanish, english, audio, extra). Keyed by note-type name fragments.
def extract(apkg: Apkg, src_label: str):
    for nid, model, tags, f in apkg.notes():
        if src_label == "tatoeba_native":          # 'Spanish sentences cloze': EnglishSentenceID, SpanishSentenceID, English, Spanish, ClozeWord, Difficulty, Text, Audio, ...
            yield f[3], f[2], f[7], {"cloze": f[4], "diff9000": f[5]}
        elif src_label == "tatoeba_tts":           # 'hirasawa_yui': audio, sentence, english translation, ...
            yield re.sub(r"^\s*•\s*", "", strip_html(f[1])), f[2], f[0], {}
        elif src_label.startswith("neri"):        # Neri's Sentences (Read)/(Speak): Sentence, Sentence (English), ..., [1]=audio
            if "Read" not in model or len(f) < 6: continue
            yield f[0], f[1], f[5] if "[sound:" in f[5] else "", {}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sources", required=True, help="JSON file: {label: path_to_apkg, ...}. Labels: tatoeba_native, tatoeba_tts, neri1, neri2, neri3")
    ap.add_argument("--work", default="work", help="directory for extracted databases")
    ap.add_argument("--out", required=True, help="output TSV")
    a = ap.parse_args()
    sources = json.load(open(a.sources, encoding="utf-8"))
    PRIORITY = {"tatoeba_native": 0, "tatoeba_tts": 1, "neri2": 2, "neri3": 3, "neri1": 4}
    rows = []
    for label, path in sources.items():
        pk = Apkg(path, f"{a.work}/{label}")
        n0 = len(rows)
        for es_raw, en, audio, extra in extract(pk, label):
            es = tidy(first_variant(es_raw)); en = strip_html(en)
            rows.append(dict(src=label, es=es, en=en, audio=audio.strip(), cloze=extra.get("cloze", ""), diff9000=extra.get("diff9000", "")))
        print(f"{label}: {len(rows) - n0} sentences from {path}", file=sys.stderr)
    keep: dict[str, dict] = {}; dropped = collections.Counter()
    for r in rows:
        r["n"] = nwords(r["es"]); r["drop_reason"] = quality_check(r["es"], r["en"]); r["quality"] = 0 if r["drop_reason"] else 1
        r["has_name"] = int(bool(re.search(r"(?<=[a-záéíóúñ,;] )[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+", r["es"])))
        k = dedup_key(r["es"])
        if k in keep:
            kept = keep[k]
            better = (PRIORITY[r["src"]], -r["quality"]) < (PRIORITY[kept["src"]], -kept["quality"])
            if better:
                if not r["audio"] and kept["audio"]: r["audio"] = kept["audio"]
                keep[k] = r
            elif not kept["audio"] and r["audio"]: kept["audio"] = r["audio"]
            dropped["duplicate"] += 1
        else:
            keep[k] = r
    out = list(keep.values())
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["src", "es", "en", "audio", "cloze", "diff9000", "n", "has_name", "quality", "drop_reason"], delimiter="\t", lineterminator="\n")
        w.writeheader(); w.writerows(out)
    print(f"distinct sentences: {len(out)} (duplicates removed: {dropped['duplicate']}); quality rows: {sum(r['quality'] for r in out)}", file=sys.stderr)
    print("non-quality reasons:", dict(collections.Counter(r["drop_reason"] for r in out if r["drop_reason"])), file=sys.stderr)

if __name__ == "__main__":
    main()
