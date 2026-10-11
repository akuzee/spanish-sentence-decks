"""Step 3: score every pooled sentence for difficulty and flag regional (Spain) features.

Difficulty = 0.6 * rank(hardest word) + 0.25 * rank(second-hardest) + 150 * (#words ranked > 2000)
             + 80 * (#words) + grammar, where grammar adds 600 subjunctive, 400 conditional, 250 perfect,
             150 imperative, 150 past, 120 future, 80 gerund.
Words are lemmatised (spaCy es_core_news_md + simplemma + a rule-based verb fallback) and looked up in the
rank map; content words missing from it count as rank 6500. The hardest word becomes the sentence's target word.
Region flags: vosotros forms (parser Person=2|Number=Plur, ending patterns, vosotros/os/vuestro) and a list of
Spain-leaning vocabulary. Level cuts (deciles of the quality pool) are written to a sidecar levels.json.
"""
import argparse, collections, csv, json, re, sys, time
from common import deaccent

UNK = 6500
SKIP_POS = {"PUNCT", "PROPN", "NUM", "SYM", "X", "SPACE"}
GRAM_W = {"subj": 600, "cond": 400, "perf": 250, "imper": 150, "past": 150, "fut": 120, "ger": 80}
FIX = {"buen":"bueno","buena":"bueno","buenos":"bueno","buenas":"bueno","gran":"grande","quizá":"quizás","mías":"mío","mía":"mío","míos":"mío",
       "di":"decir","dí":"decir","haz":"hacer","ve":"ir","ven":"venir","pon":"poner","sal":"salir","ten":"tener","sé":"ser","da":"dar","vamos":"ir","vámonos":"ir",
       "vaya":"ir","vayas":"ir","vayan":"ir","vayamos":"ir","fue":"ser","fui":"ser","fueron":"ser","fuera":"ser","apuesto":"apostar","pase":"pasar","pases":"pasar",
       "sepa":"saber","sepas":"saber","quepa":"caber","oye":"oír","oiga":"oír","oído":"oír","estés":"estar","esté":"estar","estén":"estar","hayas":"haber","haya":"haber",
       "hayan":"haber","tenga":"tener","tengas":"tener","venga":"venir","vengas":"venir","ponga":"poner","pongas":"poner","salga":"salir","salgas":"salir","diga":"decir",
       "digas":"decir","haga":"hacer","hagas":"hacer","pueda":"poder","puedas":"poder","quiera":"querer","quieras":"querer","traiga":"traer","caiga":"caer",
       "conozca":"conocer","parezca":"parecer","juegue":"jugar","llegue":"llegar","pague":"pagar","busque":"buscar"}
IRR = {"salg":"salir","teng":"tener","pong":"poner","dig":"decir","hag":"hacer","veng":"venir","oig":"oír","caig":"caer","traig":"traer","conozc":"conocer",
       "parezc":"parecer","quep":"caber","sep":"saber","pued":"poder","pud":"poder","quier":"querer","quis":"querer","tuv":"tener","estuv":"estar","anduv":"andar",
       "hic":"hacer","dij":"decir","vin":"venir","sup":"saber","cup":"caber","hub":"haber","hay":"haber","fu":"ser","er":"ser","vay":"ir","ib":"ir","vuelv":"volver",
       "pid":"pedir","sient":"sentir","sint":"sentir","duerm":"dormir","durm":"dormir","muer":"morir","mur":"morir","sig":"seguir","consig":"conseguir","piens":"pensar",
       "empiez":"empezar","entiend":"entender","encuentr":"encontrar","recuerd":"recordar","cuent":"contar","jueg":"jugar","prefier":"preferir","prefir":"preferir",
       "sirv":"servir","repit":"repetir","mient":"mentir","mint":"mentir","cierr":"cerrar","muestr":"mostrar","suel":"soler","produzc":"producir","conduzc":"conducir",
       "traduzc":"traducir","obteng":"obtener","conteng":"contener","manteng":"mantener","deteng":"detener","supong":"suponer","propong":"proponer","compong":"componer"}
ENDS = sorted(["ieron","aron","iendo","ando","ieran","ieras","iera","iese","aran","aras","ara","ase","aba","abas","aban","ábamos","ía","ías","ían","íamos","emos","amos","imos",
               "éis","áis","aste","iste","asteis","isteis","ado","ido","ados","idos","ada","ida","adas","idas","án","ás","é","ó","ió","ais","eis","as","es","an","en","a","e","o"], key=len, reverse=True)
CLIT = re.compile(r"^(.+?)(me|te|se|nos|os|lo|la|le|los|las|les|melo|mela|melos|melas|telo|tela|telos|telas|selo|sela|selos|selas|noslo|nosla|oslo|osla)$")

VOS_WORDS = {"vosotros","vosotras","vuestro","vuestra","vuestros","vuestras","os","sois","vais","habéis","estáis","tenéis","sabéis","podéis","queréis","sed","venid","mirad","oíd","id","dad","haced","decid","poned","salid","tened","venís","decís","vivís","salís","sentís","oís","reís"}
VOS_RE = re.compile(r"(?:[aeáé]is|[aeií]steis|abais|íais|ar[eé]is|er[eé]is|ir[eé]is|r[ií]ais|arais|ierais|aseis|ieseis|[aei]d(?:me|lo|la|le|los|las|les|nos)|aos|eos|íos)$")
SAFE = {"país","maíz","raíz","seis","dieciséis","gratis","tenis","crisis","tesis","dosis","oasis","análisis","énfasis","paréntesis","hipótesis","síntesis","anís","caos"}
SPAIN = {"ordenador":2,"ordenadores":2,"móvil":1,"móviles":1,"zumo":2,"zumos":2,"patata":2,"patatas":2,"coger":2,"coges":2,"coge":2,"cogemos":2,"cogen":2,"cogí":2,"cogiste":2,
         "cogió":2,"cogimos":2,"cogieron":2,"cogido":2,"cogiendo":2,"coja":2,"cojas":2,"cojan":2,"cogía":2,"cogían":2,"vale":1,"guay":2,"mola":2,"molar":2,"molan":2,"chaval":2,
         "chavales":2,"chavala":2,"curro":2,"currar":2,"flipar":2,"flipo":2,"flipas":2,"majo":2,"maja":2,"majos":2,"hostia":2,"hostias":2,"aparcar":2,"aparca":2,"aparcado":2,
         "aparcamiento":2,"jersey":2,"jerseys":2,"bolígrafo":1,"bolígrafos":1,"boli":2,"enfadado":1,"enfadada":1,"enfadar":1,"enfades":1,"enfada":1,"fontanero":2,"grifo":2,
         "cerillas":2,"cerilla":2,"melocotón":2,"melocotones":2,"gilipollas":2,"cabrear":2,"cabreado":2,"cabreada":2,"cutre":2,"follar":2,"pijo":2,"pija":2,"tebeo":2,
         "ordenata":2,"albaricoque":2,"fregona":2,"tirita":2,"chándal":2,"bragas":2,"coño":2,"chulo":1,"chula":1,"tío":1,"tía":1,"tíos":1,"piso":1,"pisos":1,"nevera":1,
         "conducir":1,"conduce":1,"conduces":1,"conduzco":1,"condujo":1,"conduciendo":1,"autobús":1,"autobuses":1,"gafas":1,"calcetines":1,"pendientes":1,"zapatillas":1,
         "billete":1,"billetes":1,"ascensor":1,"judías":1,"gamba":1,"gambas":1,"echar de menos":2,"echo de menos":2,"echas de menos":2,"echa de menos":2,"echamos de menos":2,
         "echan de menos":2,"eché de menos":2,"echaba de menos":2,"qué va":2,"ni de coña":2,"a tope":1,"vale ya":2,"joder":1,"madre mía":1}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", required=True); ap.add_argument("--rankmap", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--levels", help="where to write levels.json (default: next to --out)")
    a = ap.parse_args()
    import spacy, simplemma
    RM = json.load(open(a.rankmap, encoding="utf-8")); rank = {k: v[0] for k, v in RM.items()}
    rows = list(csv.DictReader(open(a.pool, encoding="utf-8"), delimiter="\t"))
    nlp = spacy.load("es_core_news_md", disable=["ner", "parser"])

    def lookup(tok):
        surf = tok.text.lower(); cands = [surf, tok.lemma_.lower(), simplemma.lemmatize(surf, lang="es").lower()]
        if surf in FIX: cands.append(FIX[surf])
        m = CLIT.match(surf)
        if m and len(m.group(1)) >= 2:
            stem = deaccent(m.group(1))
            cands += [stem, FIX.get(stem, ""), simplemma.lemmatize(stem, lang="es").lower(), stem + "r", stem[:-1] + "r" if stem.endswith(("a", "e", "i")) else ""]
            if stem in ("vamo", "vámo"): cands.append("ir")
        if tok.pos_ in ("VERB", "AUX") and not any(c in rank for c in cands):
            sd = deaccent(surf)
            for e in ENDS:
                if sd.endswith(e) and len(sd) - len(e) >= 2:
                    st = sd[:-len(e)]
                    if st in IRR: cands.append(IRR[st]); break
                    for inf in (st + "ar", st + "er", st + "ir", st[:-1] + "ar" if st.endswith(("i", "u")) else ""):
                        if inf in rank: cands.append(inf)
                    if any(c in rank for c in cands[-4:]): break
        best, key = None, ""
        for c in cands:
            if c in rank and (best is None or rank[c] < best): best, key = rank[c], c
        return best, key

    t0 = time.time(); out = []
    for i, (row, doc) in enumerate(zip(rows, nlp.pipe((r["es"] for r in rows), batch_size=512))):
        ranks, unknown, feats, vos = [], [], set(), []
        target = ("", 0, "")
        has_haber = any(t.lemma_ == "haber" for t in doc if t.pos_ == "AUX")
        for tok in doc:
            w = tok.text.lower()
            # --- region: vosotros
            if w in VOS_WORDS and not (w in ("id", "dad", "sed") and tok.pos_ not in ("VERB", "AUX")): vos.append(tok.text)
            elif tok.pos_ in ("VERB", "AUX") and "2" in tok.morph.get("Person") and "Plur" in tok.morph.get("Number"): vos.append(tok.text)
            elif tok.pos_ in ("VERB", "AUX") and w not in SAFE and len(w) > 4 and VOS_RE.search(w) and not w.endswith(("dad", "tad", "tud", "ed", "ados", "idos")): vos.append(tok.text)
            # a lowercase token tagged PROPN is a parser slip (e.g. "Tom estafó a Mary" tags the verb as a name): keep it
            if (tok.pos_ in SKIP_POS and not (tok.pos_ == "PROPN" and tok.text[:1].islower())) or not re.search(r"[a-záéíóúñü]", w): continue
            if tok.pos_ in ("VERB", "AUX"):
                mood, tense, vf = tok.morph.get("Mood"), tok.morph.get("Tense"), tok.morph.get("VerbForm")
                if "Sub" in mood: feats.add("subj")
                if "Cnd" in mood: feats.add("cond")
                if "Imp" in mood: feats.add("imper")
                if "Fut" in tense: feats.add("fut")
                if ("Past" in tense or "Imp" in tense) and "Fin" in vf: feats.add("past")
                if "Part" in vf and tok.pos_ == "VERB" and has_haber: feats.add("perf")
                if "Ger" in vf: feats.add("ger")
            r, key = lookup(tok)
            if r is None:
                if tok.pos_ in ("NOUN", "VERB", "ADJ", "ADV") and len(tok.text) > 2: unknown.append(tok.text); r, key = UNK, ""
                else: continue
            ranks.append(r)
            if r > target[1]: target = (tok.text, r, key)
        if not ranks: ranks = [1]
        srt = sorted(ranks, reverse=True); mx, second = srt[0], (srt[1] if len(srt) > 1 else 0)
        hard = sum(1 for r in ranks if r > 2000); n = int(row["n"])
        gram = sum(GRAM_W[f] for f in feats)
        score = round(0.6 * mx + 0.25 * second + 150 * hard + 80 * n + gram)
        lowc = " " + re.sub(r"[^\wáéíóúñü ]", " ", row["es"].lower()) + " "
        sp = [k for k in SPAIN if " " + k + " " in lowc and not (k == "vale" and "vale la pena" in lowc)]
        row.update(max_rank=mx, second=second, hard=hard, unknown=len(unknown), unk_words=" ".join(unknown), target=target[0], target_key=target[2],
                   gram=gram, feats=" ".join(sorted(feats)), score=score, vosotros=" ".join(vos), spain=" ".join(sp), spain_w=sum(SPAIN[k] for k in sp))
        out.append(row)
        if i % 10000 == 0: print(f"  ... {i} ({time.time() - t0:.0f}s)", file=sys.stderr, flush=True)
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()), delimiter="\t", lineterminator="\n"); w.writeheader(); w.writerows(out)
    # level cuts: deciles of the quality pool, shared by every variant built from this file
    qs = sorted(r["score"] for r in out if int(r["quality"]) == 1)
    cuts = [qs[int(len(qs) * i / 10)] for i in range(1, 10)]
    json.dump({"cuts": cuts, "n_quality": len(qs)}, open(a.levels or a.out.rsplit(".", 1)[0] + "_levels.json", "w"))
    print(f"scored {len(out)} sentences in {time.time() - t0:.0f}s; level cuts {cuts}", file=sys.stderr)
    print("unknown-word sentences:", sum(1 for r in out if r["unknown"]), "| vosotros:", sum(1 for r in out if r["vosotros"]), "| spain vocab:", sum(1 for r in out if r["spain"]), file=sys.stderr)

if __name__ == "__main__":
    main()
