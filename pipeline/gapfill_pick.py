"""Step 3d: Tatoeba sentences are the backbone (all kept); subtitle lines are admitted only if they add a new
example for a word that still has fewer than K examples (K by rarity), or for a grammar feature under quota at its
level. Reports size, source mix and per-level subtitle share."""
import argparse, collections, csv, json, random, sys
import spacy, simplemma
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--scored", required=True); ap.add_argument("--levels", required=True); ap.add_argument("--curation", required=True)
ap.add_argument("--easy-pick", required=True, help="output of coverage_pick.py for the easy section"); ap.add_argument("--rankmap", required=True); ap.add_argument("--k-scheme", default="1000:3,3000:5,5000:8"); ap.add_argument("--gram-per-level", type=int, default=40); ap.add_argument("--out")
a = ap.parse_args()
RM = json.load(open(a.rankmap, encoding="utf-8")); rank = {k: v[0] for k, v in RM.items()}
sc = {r["es"]: r for r in csv.DictReader(open(a.scored, encoding="utf-8"), delimiter="\t")}
cuts = json.load(open(a.levels))["cuts"]; cur = {c["es"]: c for c in csv.DictReader(open(a.curation, encoding="utf-8"), delimiter="\t")}
easy = set(l.rstrip("\n") for l in open(a.easy_pick, encoding="utf-8"))
rows = [r for r in sc.values() if r["quality"] == "1" and not cur[r["es"]]["neardup"] and not cur[r["es"]]["lowq"] and cur[r["es"]]["c1"] != "1" and (int(r["max_rank"]) > 1000 or r["es"] in easy)]
for r in rows: r["level"] = 1 + sum(1 for c in cuts if int(r["score"]) >= c); r["score"] = int(r["score"]); r["audio"] = "yes" if r["audio"] else "no"
nlp = spacy.load("es_core_news_md", disable=["ner", "parser"]); SKIP = {"PUNCT","PROPN","NUM","SYM","X","SPACE","DET","ADP","PRON","CCONJ","SCONJ","PART","AUX"}
for r, doc in zip(rows, nlp.pipe((r["es"] for r in rows), batch_size=512)):
    lem = set()
    for t in doc:
        if t.pos_ in SKIP: continue
        for c in (t.text.lower(), t.lemma_.lower(), simplemma.lemmatize(t.text.lower(), lang="es").lower()):
            if c in rank and rank[c] >= 50: lem.add(c); break
    r["lem"] = lem
scheme = sorted((int(x.split(":")[0]), int(x.split(":")[1])) for x in a.k_scheme.split(","))
def K(l):
    for lim, k in scheme:
        if rank[l] <= lim: return k
    return scheme[-1][1]
need = collections.Counter({l: K(l) for r in rows for l in r["lem"]})
gram = {(f, L): a.gram_per_level for f in ("subj","cond","perf","past","fut","imper","ger") for L in range(1, 11)}
def take(r):
    for l in r["lem"]:
        if need[l] > 0: need[l] -= 1
    for f in r["feats"].split():
        if gram.get((f, r["level"]), 0) > 0: gram[(f, r["level"])] -= 1
tat = [r for r in rows if r["src"].startswith("tatoeba")]; subs = [r for r in rows if not r["src"].startswith("tatoeba")]
for r in tat: take(r)
def gain(r): return sum(1 + rank[l] / 1000 for l in r["lem"] if need[l] > 0) + sum(0.5 for f in r["feats"].split() if gram.get((f, r["level"]), 0) > 0)
chosen = []; taken = [False] * len(subs)
while True:
    gains = sorted(((gain(r), i) for i, r in enumerate(subs) if not taken[i]), reverse=True)
    gains = [(g, i) for g, i in gains if g > 0]
    if not gains: break
    for g, i in gains[:max(50, len(gains) // 40)]:
        if gain(subs[i]) <= 0: continue
        taken[i] = True; chosen.append(subs[i]); take(subs[i])
final = tat + chosen
print(f"scheme {a.k_scheme}: {len(final)} sentences = {len(tat)} Tatoeba + {len(chosen)} subtitle gap-fillers (of {len(subs)}) | audio {sum(1 for r in final if r['audio']=='yes')}")
tot = collections.Counter(r["level"] for r in final); sub = collections.Counter(r["level"] for r in chosen)
print("  per level (sentences / subtitle share): " + ", ".join(f"L{L}: {tot[L]} / {100*sub[L]/tot[L]:.0f}%" for L in sorted(tot)))
random.seed(2); print("  kept subtitle examples:", " | ".join(r["es"] for r in random.sample(chosen, 5)))
print("  dropped subtitle examples:", " | ".join(r["es"] for r in random.sample([r for i, r in enumerate(subs) if not taken[i]], 5)))
if a.out:
    with open(a.out, "w", encoding="utf-8") as f:
        for r in final: f.write(r["es"] + "\n")
