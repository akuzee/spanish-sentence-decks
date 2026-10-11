"""Prototype: choose a compact sentence set by coverage instead of a per-target-word cap.
Every word of the 5,000 list should appear >= K times (rarer words weighted higher), every grammar feature should be
represented at each level, and sentence quality breaks ties. Greedy set cover over the scored pool."""
import argparse, csv, json, re, sys, collections
import spacy, simplemma
ap = argparse.ArgumentParser(); ap.add_argument("--scored", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--rankmap", required=True)
ap.add_argument("--k", type=int, default=3, help="target appearances per list word"); ap.add_argument("--max-level", type=int, default=8); ap.add_argument("--out"); ap.add_argument("--min-per-level", type=int, default=0, help="after coverage, top each level up to this many sentences with the best-quality leftovers")
a = ap.parse_args()
cuts = json.load(open(a.levels))["cuts"]; RM = json.load(open(a.rankmap, encoding="utf-8")); rank = {k: v[0] for k, v in RM.items()}
rows = [r for r in csv.DictReader(open(a.scored, encoding="utf-8"), delimiter="\t") if r["quality"] == "1"]
for r in rows:
    for k in ("max_rank","unknown","n","has_name","spain_w","score"): r[k] = int(r[k])
    r["level"] = 1 + sum(1 for c in cuts if r["score"] >= c)
rows = [r for r in rows if r["level"] <= a.max_level]
nlp = spacy.load("es_core_news_md", disable=["ner", "parser"])
SKIP = {"PUNCT","PROPN","NUM","SYM","X","SPACE","DET","ADP","PRON","CCONJ","SCONJ","PART","AUX"}
for r, doc in zip(rows, nlp.pipe((r["es"] for r in rows), batch_size=512)):
    lem = set()
    for t in doc:
        if t.pos_ in SKIP: continue
        for c in (t.text.lower(), t.lemma_.lower(), simplemma.lemmatize(t.text.lower(), lang="es").lower()):
            if c in rank and rank[c] >= 50: lem.add(c); break   # ignore the ~50 most common function-like words
    r["lem"] = lem
PEN = {"tatoeba_native": 0, "tatoeba_tts": 60, "neri2": 120, "neri3": 220, "neri1": 300}
def quality(r): return PEN[r["src"]] + 150*r["has_name"] + 120*r["unknown"] + (80 if r["n"]<6 else 0) + (60 if r["n"]>12 else 0) + 300*r["spain_w"] + (5000 if r["vosotros"] else 0) - (40 if r["audio"] else 0)
need = collections.Counter(); 
for r in rows:
    for l in r["lem"]: need[l] = a.k
gram_need = {(f, L): 40 for f in ("subj","cond","perf","past","fut","imper","ger") for L in range(1, a.max_level + 1)}
def gain(r):
    g = sum((1 + rank[l] / 1000) for l in r["lem"] if need[l] > 0)          # rarer words are worth more
    g += sum(0.5 for f in r["feats"].split() if gram_need.get((f, r["level"]), 0) > 0)
    return g / (1 + quality(r) / 400)                                        # quality as a soft penalty
chosen = []; pool = rows[:]; taken = [False] * len(pool)
# greedy in rounds: recompute every candidate's gain, take the best batch, update coverage, repeat
while True:
    gains = [(gain(r), i) for i, r in enumerate(pool) if not taken[i]]
    gains = [(g, i) for g, i in gains if g > 0]
    if not gains: break
    gains.sort(reverse=True)
    batch = gains[:max(50, len(gains) // 40)]
    for g, i in batch:
        r = pool[i]
        if gain(r) <= 0: continue          # may have been satisfied by an earlier pick in this batch
        taken[i] = True; chosen.append(r)
        for l in r["lem"]:
            if need[l] > 0: need[l] -= 1
        for f in r["feats"].split():
            if gram_need.get((f, r["level"]), 0) > 0: gram_need[(f, r["level"])] -= 1
if a.min_per_level:
    byl = collections.Counter(r["level"] for r in chosen)
    for L in range(1, a.max_level + 1):
        extra = sorted([pool[i] for i in range(len(pool)) if not taken[i] and pool[i]["level"] == L], key=lambda r: (quality(r), r["score"]))
        for r in extra[:max(0, a.min_per_level - byl[L])]: chosen.append(r)
src = collections.Counter(r["src"] for r in chosen)
print(f"K={a.k}, levels<= {a.max_level}: {len(chosen)} sentences | audio {sum(1 for r in chosen if r['audio'])} | tatoeba {src['tatoeba_native']+src['tatoeba_tts']}, neri1/2 {src['neri1']+src['neri2']}, neri3 {src['neri3']}")
words = {l for r in rows for l in r['lem']}; covered = sum(1 for l in words if need[l] == 0)
print(f"  list words appearing in the pool: {len(words)}; fully covered {a.k}x: {covered}; mean sentences per level: {len(chosen)/a.max_level:.0f}; mean words/sentence {sum(r['n'] for r in chosen)/len(chosen):.1f}")
print("  level mix:", dict(sorted(collections.Counter(r['level'] for r in chosen).items())))
if a.out:
    with open(a.out, "w", encoding="utf-8") as f:
        for r in sorted(chosen, key=lambda r: r["score"]): f.write(r["es"] + "\n")
