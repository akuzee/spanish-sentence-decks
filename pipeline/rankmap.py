"""Step 2: build the word -> frequency-rank lookup used to score sentence difficulty.

Input is the per-word TSV written by vocab_merge.py (columns: rank, spanish, pos, english, ...). Every headword
variant is indexed ("el,la" -> el, la; "a través (de)" -> "a través", "través"; "cualquier(a)" -> cualquier,
cualquiera), plus a few function-word forms the dictionary does not list separately.
Output: JSON {word: [rank, english_gloss, headword]}.
"""
import argparse, csv, json, re

EXTRA = {"el": 1, "la": 1, "los": 1, "las": 1, "un": 7, "una": 7, "unos": 7, "unas": 7, "yo": 30, "tú": 60, "él": 9, "ella": 9, "ellos": 9, "ellas": 9,
         "nosotros": 100, "usted": 120, "ustedes": 120, "mí": 20, "ti": 50, "te": 50, "me": 22, "nos": 60, "os": 150, "le": 25, "les": 25, "lo": 18, "se": 10,
         "esto": 111, "eso": 60, "aquello": 300, "está": 21, "estás": 21, "soy": 7, "eres": 7, "es": 7, "son": 7, "hay": 13, "del": 2, "al": 8, "qué": 50, "sí": 45, "no": 11}

def build(rows):
    m = {}
    def put(w, r, g="", h=""):
        w = w.strip().lower()
        if w and (w not in m or r < m[w][0]): m[w] = [r, g, h]
    for r in rows:
        rank = int(r["rank"]); head = re.sub(r"\[.*?\]", "", r["spanish"].lower()); G, H = r["english"], r["spanish"]
        for part in re.split(r"[;,/]", head):
            part = part.strip()
            if not part: continue
            base = re.sub(r"\(.*?\)", "", part).strip()
            put(base, rank, G, H); put(re.sub(r"[()]", "", part), rank, G, H)
            toks = base.split()
            if len(toks) > 1:
                for t in toks:
                    if len(t) >= 4 or t in ("pico", "vera"): put(t, rank, G, H)
    for w, r in EXTRA.items(): put(w, r)
    return m

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vocab", required=True, help="vocab TSV from vocab_merge.py (needs columns rank, spanish, english)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.vocab, encoding="utf-8"), delimiter="\t"))
    m = build(rows)
    json.dump(m, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    print("rank map entries:", len(m))

if __name__ == "__main__":
    main()
