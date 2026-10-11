"""Step 3b: curation flags for the published decks.
- c1:       the sentence needs C1-level vocabulary: a content word outside the 5,000-word list, or two or more words
            beyond rank 4,000 (B2 ceiling). Everything else is 'pre-C1'.
- neardup:  a close repetition of a better sentence: same bag of lemmas, or >= 85% lemma overlap for sentences of
            6+ words. The kept copy is the best-quality one (Tatoeba, audio, no names).
- lowq:     extra quality cut on top of pool.py: subtitle lines with character names, lines that trail off (…),
            lines shouting in capitals, English that trails off or is a fragment.
Writes es, c1, neardup, lowq, reason.
"""
import argparse, collections, csv, json, re, sys
import spacy, simplemma
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("--scored", required=True); ap.add_argument("--rankmap", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--jaccard", type=float, default=0.85)
a = ap.parse_args()
RM = json.load(open(a.rankmap, encoding="utf-8")); rank = {k: v[0] for k, v in RM.items()}
rows = list(csv.DictReader(open(a.scored, encoding="utf-8"), delimiter="\t"))
for r in rows:
    for k in ("max_rank","second","unknown","n","has_name","spain_w","score","quality"): r[k] = int(r[k])
nlp = spacy.load("es_core_news_md", disable=["ner", "parser"])
SKIP = {"PUNCT","PROPN","NUM","SYM","X","SPACE"}
for r, doc in zip(rows, nlp.pipe((r["es"] for r in rows), batch_size=512)):
    lem = []; hard = 0
    for t in doc:
        if t.pos_ in SKIP: continue
        w = t.text.lower(); cands = (w, t.lemma_.lower(), simplemma.lemmatize(w, lang="es").lower())
        key = next((c for c in cands if c in rank), None)
        lem.append(key or ("?" + w))
        if key and rank[key] > 4000: hard += 1
    r["lem"] = lem; r["hard4000"] = hard
PEN = {"tatoeba_native": 0, "tatoeba_tts": 60, "neri2": 120, "neri3": 220, "neri1": 300}
def quality(r): return PEN[r["src"]] + 150*r["has_name"] + 120*r["unknown"] + (80 if r["n"]<6 else 0) + (60 if r["n"]>12 else 0) + 300*r["spain_w"] + (5000 if r["vosotros"] else 0) - (40 if r["audio"] else 0)
# --- c1
for r in rows: r["c1"] = int(r["max_rank"] > 5000 or r["hard4000"] >= 2)
# --- low quality (extra)
def lowq(r):
    es, en = r["es"], r["en"]
    if r["src"].startswith("neri") and r["has_name"]: return "subtitle line with a character name"
    if re.search(r"(\.\.\.|…)\s*$", es) or re.search(r"(\.\.\.|…)\s*$", en): return "trails off"
    if re.search(r"(\.\.\.|…)", es) and r["n"] <= 6: return "broken by an ellipsis"
    letters = re.findall(r"[A-ZÁÉÍÓÚÑa-záéíóúñ]", es)
    if letters and sum(1 for c in letters if c.isupper()) / len(letters) > 0.5: return "shouting"
    if not re.search(r"[A-Za-z]{2,}", en): return "english is not a sentence"
    return ""
for r in rows: r["lowq"] = lowq(r) if r["quality"] else "failed the pool quality filter"
# --- near duplicates (among quality, non-lowq rows), by lemma bag, then by Jaccard for longer sentences
cands = [r for r in rows if r["quality"] and not r["lowq"]]
cands.sort(key=lambda r: (quality(r), r["score"]))        # best first; the first of a group is kept
seen_bag = {}
for r in cands:
    # same lemmas AND the same grammar features = repetition; a different tense is not
    bag = (tuple(sorted(r["lem"])), r["feats"]); r["neardup"] = ""
    if bag in seen_bag: r["neardup"] = "same words as: " + seen_bag[bag]
    else: seen_bag[bag] = r["es"]
# Jaccard on lemma sets for 6+ word sentences: index by (sorted lemma set minus one) to find candidates cheaply
index = collections.defaultdict(list)
for r in cands:
    if r["neardup"] or r["n"] < 6: continue
    s = frozenset(r["lem"]); r["lset"] = s
    for l in s: index[l].append(r)
checked = 0
for r in cands:
    if r["neardup"] or r["n"] < 6: continue
    s = r["lset"]; best = None
    counts = collections.Counter()
    for l in s:
        for o in index[l]:
            if o is not r: counts[id(o)] += 1
    for oid, c in counts.items():
        if c / len(s) < a.jaccard * 0.9: continue
        o = next(x for x in index[next(iter(s))] if id(x) == oid) if False else None
    # simpler: compare against candidates sharing >= jaccard*len(s) lemmas
    for l in s:
        for o in index[l]:
            if o is r or o.get("neardup") or "lset" not in o: continue
            inter = len(s & o["lset"]); jac = inter / len(s | o["lset"])
            if jac >= a.jaccard and o["feats"] == r["feats"] and (quality(o), o["score"]) < (quality(r), r["score"]):
                r["neardup"] = f"{jac:.2f} overlap with: " + o["es"]; break
        if r["neardup"]: break
with open(a.out, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter="\t", lineterminator="\n"); w.writerow(["es", "c1", "neardup", "lowq"])
    for r in rows: w.writerow([r["es"], r["c1"], r.get("neardup", ""), r["lowq"]])
q = [r for r in rows if r["quality"]]
print(f"quality pool {len(q)} | C1+ {sum(r['c1'] for r in q)} | extra low-quality {sum(1 for r in q if r['lowq'])} | near-duplicates {sum(1 for r in q if r.get('neardup'))}", file=sys.stderr)
print("low-quality reasons:", dict(collections.Counter(r["lowq"] for r in q if r["lowq"])), file=sys.stderr)
keep = [r for r in q if not r["c1"] and not r["lowq"] and not r.get("neardup")]
src = collections.Counter(r["src"] for r in keep)
print(f"pre-C1 curated main deck: {len(keep)} sentences | audio {sum(1 for r in keep if r['audio'])} | tatoeba {src['tatoeba_native']+src['tatoeba_tts']}, neri1/2 {src['neri1']+src['neri2']}, neri3 {src['neri3']}", file=sys.stderr)
c1 = [r for r in q if r["c1"] and not r["lowq"] and not r.get("neardup")]
print(f"C1+ deck: {len(c1)} sentences | audio {sum(1 for r in c1 if r['audio'])}", file=sys.stderr)
per = collections.Counter(r["target"].lower() or "_" for r in keep)
print("target-word repetition in the pre-C1 set: words with >30 sentences:", sum(1 for c in per.values() if c > 30), "| max", per.most_common(3), file=sys.stderr)
keep_sorted = sorted(keep, key=lambda r: (quality(r), r["score"]))
for cap in (8, 12, 20, 30):
    cnt = collections.Counter(); n = 0; aud = 0; n3 = 0
    for r in keep_sorted:
        t = r["target"].lower() or "_"
        if cnt[t] < cap: cnt[t] += 1; n += 1; aud += bool(r["audio"]); n3 += r["src"] == "neri3"
    print(f"  cap {cap:2d} sentences per target word -> {n} sentences, audio {aud}, Part 3 {n3}", file=sys.stderr)
import random; random.seed(4)
print("near-dup examples:", file=sys.stderr)
for r in random.sample([r for r in q if r.get("neardup")], 6): print("   DROP", r["es"], "|", r["neardup"], file=sys.stderr)
print("C1+ examples:", file=sys.stderr)
for r in random.sample(c1, 6): print("   ", r["es"], "| hardest rank", r["max_rank"], "| words>4000:", r["hard4000"], file=sys.stderr)
