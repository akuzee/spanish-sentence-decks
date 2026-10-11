"""Merge the two 'Top 5000' Spanish vocabulary decks into one note type and tier the cards.

old = 'Essential Spanish Vocabulary Top 5000' (pictures, Davies-2006 ranks); new = 'New Spanish Top 5000 with Examples'
(Azure audio, example sentences, newer ranks). Matching is by headword (the two decks use different frequency lists).
Tiers (by averaged rank and an English-cognate score) decide which cards start as long-interval reviews. The tier
thresholds were set for a B1 learner; see docs/METHOD.md to change them. The per-word TSV this writes is the input
for rankmap.py (sentence difficulty), so run this first even if you only want the sentence decks.
NOTE: the word list and glosses are from Davies' "A Frequency Dictionary of Spanish" (Routledge). Do not redistribute
the merged deck publicly without considering that copyright; see docs/SOURCES.md.
"""
import argparse, sqlite3, re, sys, html, collections, unicodedata, random, difflib, json, time, hashlib, os, zipfile, shutil, secrets, statistics
from common import Apkg
_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument("--old", required=True, help="Essential Spanish Vocabulary Top 5000 .apkg")
_ap.add_argument("--new", required=True, help="New Spanish Top 5000 with Examples .apkg")
_ap.add_argument("--out", required=True, help="merged .apkg"); _ap.add_argument("--report", required=True, help="per-word TSV (used by rankmap.py)")
_ap.add_argument("--work", default="work")
_a = _ap.parse_args()
_pk_old = Apkg(os.path.expanduser(_a.old), f"{_a.work}/vocab_old"); _pk_new = Apkg(os.path.expanduser(_a.new), f"{_a.work}/vocab_new")
OLD_DB, OLD_APKG, NEW_DB, NEW_APKG, OUT_APKG, REPORT = _pk_old.db_path, _pk_old.path, _pk_new.db_path, _pk_new.path, _a.out, _a.report
_old_media_json = _pk_old.media; _new_media_json = _pk_new.media
random.seed(20261010)

def strip(s): return html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ").strip()
def deacc(s): return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
def norm_head(s):
    s = unicodedata.normalize("NFC", s.lower())
    s = re.sub(r"\[.*?\]", "", s); s = re.sub(r"\s*,\s*", ",", s); s = re.sub(r"\s+", " ", s).strip()
    return s
def norm_gloss(s):
    s = deacc(s); s = re.sub(r"\(.*?\)|\[.*?\]", " ", s); s = re.sub(r"[^a-z ]", " ", s)
    return " ".join(s.split())

POS_SET = {"adj","adv","art","conj","interj","nc","nf","nf el","nf (el)","nf_el","nm","nm/f","nmf","num","prep","pron","v","n","adj, pron","adj, adv","adv, adj","pron, adj"}
def parse_old(sp, tags):
    """old Spanish field: 'absoluto (adj)', 'de (prep) de', 'me (pron) [also mí]', 'preocupar(se) (v)', 'debido: debido a (adj)'"""
    s = strip(sp)
    note = ""
    m = re.search(r"\[(.*?)\]", s)
    if m: note = m.group(1).strip(); s = s.replace(m.group(0), "").strip()
    groups = list(re.finditer(r"\(([^()]*)\)", s))
    pos = ""
    head = s
    POS_TOK = {"adj","adv","art","conj","interj","nc","nf","el","nm","nm/f","nmf","num","prep","pron","v","n"}
    for g in reversed(groups):
        toks = [t for t in re.split(r"[,\s]+", g.group(1).strip().lower()) if t]
        if toks and all(t in POS_TOK for t in toks):
            pos = g.group(1).strip(); head = s[:g.start()].strip()
            break
    if not pos:
        tg = [t for t in tags.split() if t in ("adj","adv","art","conj","interj","nc","nf","nm","nm/f","nmf","num","prep","pron","v","nf_el","n")]
        pos = tg[0].replace("nf_el", "nf (el)") if tg else ""
    head = re.sub(r"\s+", " ", head).strip(" :;")
    return head, pos, note

ALIAS = {
    "sin embargo embargo": ("embargo", "sin embargo"), "en cuanto a cuanto": ("cuanto", "en cuanto a"), "al final final": ("final", "al final"),
    "debido: debido a": ("debido", "debido a"), "en torno a torno": ("torno", "en torno a"), "y pico :pico": ("pico", "pico; y pico"),
    "no + obstante obstante": ("obstante", "no obstante"), "repente: de + repente": ("repente", "de repente"), "turno; en turno a": ("turno", "turno"),
    "seguida: en seguida": ("seguida", "en seguida"), "postre; a la postre": ("postre", "postre; a la postre"), "de veras vera": ("veras", "de veras"),
    "relieve; poner de relieve": ("relieve", "relieve; poner de relieve"), "colmo; para colmo": ("colmo", "colmo; para colmo"),
    "al frente: frente a frente": ("frente", "frente a"), "a menudo": ("menudo", "a menudo"), "a través": ("través", "a través (de)"),
    "solo": ("sólo", "solo"), "cualquier": ("cualquiera", "cualquier(a)"), "gana": ("ganas", "gana(s)"), "recurso": ("recursos", "recurso(s)"),
    "impuesto": ("impuestos", "impuesto(s)"), "gasto": ("gastos", "gasto(s)"), "medio": ("medios", "medio(s)"),
}
# ---------- load old
old = sqlite3.connect(OLD_DB)
O = []
for nid, tags, flds in old.execute("select id, tags, flds from notes"):
    sp, pic, en, au, rank = flds.split("\x1f")
    try: r = int(strip(rank))
    except: r = None
    if r == 0 or r is None: continue   # drop 'Key to Abbreviations'
    head, pos, note = parse_old(sp, tags)
    match_as, display = ALIAS.get(head, (head, head))
    # only alias 'medio'/'solo'-type singletons when the POS fits the new entry (nm for medios, adv for solo)
    if head == "medio" and pos != "nm": match_as, display = head, head
    if head == "solo" and pos != "adv": match_as, display = head, head
    aliased = display != head
    head = display
    O.append(dict(nid=nid, head=head, aliased=aliased, nhead=norm_head(match_as), pos=pos, note=note, en=strip(en), pic=pic.strip(), au=au.strip(), rank=r, raw=strip(sp)))
# ---------- load new
new = sqlite3.connect(NEW_DB)
N = []
for nid, flds in new.execute("select id, flds from notes"):
    rank, sp, wt, en, sex, eex, pic, au = flds.split("\x1f")
    try: r = int(strip(rank).replace(",", ""))
    except: r = None
    if r == 0 or r is None: continue
    N.append(dict(nid=nid, head=strip(sp), nhead=norm_head(strip(sp)), pos=strip(wt), en=strip(en), sex=sex.strip(), eex=eex.strip(), au=au.strip(), rank=r))
print("old notes", len(O), "new notes", len(N))

# ---------- match: pass 1 exact head+pos, pass 2 head only (gloss-similarity tiebreak), pass 3 first-token head
def first(h): return h.split(",")[0]
Nby = collections.defaultdict(list); Nfirst = collections.defaultdict(list)
for n in N: Nby[n['nhead']].append(n); Nfirst[first(n['nhead'])].append(n)
used = set(); pair = {}
def gsim(a, b): return difflib.SequenceMatcher(None, norm_gloss(a), norm_gloss(b)).ratio()
for o in O:
    c = [n for n in Nby.get(o['nhead'], []) if n['nid'] not in used and n['pos'] == o['pos']]
    if c:
        c.sort(key=lambda n: -gsim(o['en'], n['en'])); pair[o['nid']] = c[0]; used.add(c[0]['nid'])
for o in O:
    if o['nid'] in pair: continue
    c = [n for n in Nby.get(o['nhead'], []) if n['nid'] not in used]
    if not c: c = [n for n in Nfirst.get(first(o['nhead']), []) if n['nid'] not in used and len(first(o['nhead'])) > 1]
    if c:
        c.sort(key=lambda n: -gsim(o['en'], n['en'])); pair[o['nid']] = c[0]; used.add(c[0]['nid'])
matched = [(o, pair[o['nid']]) for o in O if o['nid'] in pair]
old_only = [o for o in O if o['nid'] not in pair]
new_only = [n for n in N if n['nid'] not in used]
print("matched", len(matched), "old-only", len(old_only), "new-only", len(new_only))

# ---------- cognate scoring
SUF = [("ción","tion"),("sión","sion"),("dad","ty"),("tad","ty"),("mente","ly"),("ario","ary"),("aria","ary"),("orio","ory"),
       ("oso","ous"),("osa","ous"),("ivo","ive"),("iva","ive"),("ico","ic"),("ica","ic"),("ante","ant"),("ente","ent"),
       ("encia","ence"),("ancia","ance"),("ismo","ism"),("ista","ist"),("ura","ure"),("ar","ate"),("ar","e"),("ar",""),("er",""),("ir",""),
       ("izar","ize"),("ificar","ify"),("ia","y"),("ía","y"),("o",""),("a",""),("e",""),("ancia","ancy"),("encia","ency"),("ión","ion"),
       ("io","y"),("ulo","ule"),("eza",""),("ez",""),("ador","ator"),("dor","der"),("cia","ce"),("ia","e"),("ción","cion")]
def variants(w):
    w = deacc(w); out = {w}
    for a, b in SUF:
        if w.endswith(a) and len(w) > len(a) + 2: out.add(w[:-len(a)] + b)
    more = set()
    for v in out:
        more |= {v.replace("f","ph"), v.replace("qu","c"), v.replace("cu","qu"), v.replace("ñ","n"), re.sub(r"^es([pt])", r"s\1", v),
                 v.replace("j","x"), v.replace("z","c"), v.replace("ll","l"), v.replace("nm","mm"), v.replace("t","th")}
    return out | more
STOP = {"to","the","a","an","of","be","or","and","in","on","at","for","with","up","out","off","one","oneself","sb","sth","someone","something","person","sg","pl","m","f","obj","subj","fam","neut","also"}
def gloss_words(en):
    en = deacc(en); en = re.sub(r"\(.*?\)|\[.*?\]", " ", en)
    return [w for w in re.findall(r"[a-z]+", en) if w not in STOP and len(w) >= 4]
def cognate_score(sp, glosses):
    sp = deacc(sp).split(",")[0].strip()
    if len(sp) < 4: return 0.0
    best = 0.0
    gw = set(w for g in glosses for w in gloss_words(g))
    for v in variants(sp):
        for g in gw:
            if v == g: return 1.0
            s = difflib.SequenceMatcher(None, v, g).ratio()
            pre = 0
            for x, y in zip(v, g):
                if x == y: pre += 1
                else: break
            if pre >= 5 and min(len(v), len(g)) >= 5: s = max(s, 0.85)
            best = max(best, s)
    return best

# ---------- assemble merged notes
def interleave(sex, eex):
    es = [strip(x) for x in re.split(r"<br\s*/?>", sex) if strip(x)]
    en = [strip(x) for x in re.split(r"<br\s*/?>", eex) if strip(x)]
    out = []
    for i, e in enumerate(es):
        t = en[i] if i < len(en) else ""
        out.append('<div class="ex"><div class="ex-es">%s</div><div class="ex-en">%s</div></div>' % (html.escape(e), html.escape(t)))
    return "".join(out)
def pos_tag(p): return re.sub(r"[^a-z/]", "_", p.lower().replace(" (el)", "_el").replace(" el", "_el").replace(", ", "+")).strip("_") or "unk"
def band_tag(r):
    lo = ((r - 1) // 500) * 500 + 1; return "rank::%04d-%04d" % (lo, lo + 499)

merged = []
for o, n in matched:
    glosses = [n['en'], o['en']]
    alt = o['en'] if norm_gloss(o['en']) != norm_gloss(n['en']) else ""
    merged.append(dict(src="both", head=(o['head'] if o['aliased'] else n['head']), pos=n['pos'] or o['pos'], en=n['en'], alt=alt, note=o['note'],
                       sex=n['sex'], eex=n['eex'], pic=o['pic'], au=n['au'] or o['au'], rank_old=o['rank'], rank_new=n['rank'],
                       cog=cognate_score(n['head'], glosses)))
for o in old_only:
    merged.append(dict(src="old-only", head=o['head'], pos=o['pos'], en=o['en'], alt="", note=o['note'], sex="", eex="",
                       pic=o['pic'], au=o['au'], rank_old=o['rank'], rank_new=None, cog=cognate_score(o['head'], [o['en']])))
for n in new_only:
    merged.append(dict(src="new-only", head=n['head'], pos=n['pos'], en=n['en'], alt="", note="", sex=n['sex'], eex=n['eex'],
                       pic="", au=n['au'], rank_old=None, rank_new=n['rank'], cog=cognate_score(n['head'], [n['en']])))
for m in merged:
    rs = [r for r in (m['rank_old'], m['rank_new']) if r is not None]
    m['rank'] = int(round(sum(rs) / len(rs)))
merged.sort(key=lambda m: (m['rank'], m['head']))

# ---------- tiers -> scheduling (days; 0 = new card)
def U(a, b): return random.randint(a, b)
tier_count = collections.Counter()
for m in merged:
    r, c = m['rank'], m['cog']
    if r <= 1000: tier, fwd, rev = "known", U(150, 270), U(90, 180)
    elif r <= 2000: tier, fwd, rev = "probable", U(90, 150), U(30, 90)
    elif c >= 0.85: tier, fwd, rev = "cognate", U(120, 240), 0
    elif c >= 0.72: tier, fwd, rev = "cognate-weak", U(60, 150), 0
    else: tier, fwd, rev = "study", 0, 0
    m['tier'], m['fwd'], m['rev'] = tier, fwd, rev
    tier_count[tier] += 1
print("tiers:", dict(tier_count))

# ---------- build collection (schema 11) from the new deck's db as a structural template
BUILD = os.path.join(os.path.dirname(os.path.abspath(OUT_APKG)), "_build_vocab"); shutil.rmtree(BUILD, ignore_errors=True); os.makedirs(BUILD)
dbp = os.path.join(BUILD, "collection.anki2"); shutil.copy(NEW_DB, dbp)
con = sqlite3.connect(dbp); cur = con.cursor()
for t in ("notes", "cards", "revlog", "graves"): cur.execute(f"delete from {t}")
colrow = cur.execute("select conf, models, decks, dconf from col").fetchone()
conf, models, decks, dconf = (json.loads(x) for x in colrow)
now = int(time.time()); now_ms = now * 1000
tmpl_model = next(iter(models.values()))
MID = now_ms; DID = now_ms + 1
FIELDS = ["Spanish", "Word Type", "English", "English Alt", "Examples", "Picture", "Audio", "Rank", "Rank 2006", "Rank 2025", "Spanish Examples", "English Examples", "Note"]
fld_t = tmpl_model['flds'][0]
flds = []
for i, name in enumerate(FIELDS):
    f = dict(fld_t); f.update(name=name, ord=i, sticky=False, rtl=False, font="Arial", size=20); f['media'] = []; flds.append(f)
CSS = """
.card { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 22px; text-align: center; color: #222; background: #fff; padding: 10px; }
.night_mode .card, .nightMode .card { color: #eee; background: #1e1e1e; }
.head { font-size: 40px; font-weight: 600; margin: 8px 0 2px; }
.pos { font-size: 15px; color: #888; margin-bottom: 10px; }
.gloss { font-size: 26px; margin: 6px 0; }
.alt { font-size: 16px; color: #777; margin-top: 2px; }
.note { font-size: 14px; color: #999; font-style: italic; }
.pic img { max-width: 260px; max-height: 220px; border-radius: 6px; margin: 10px 0; }
.ex { margin: 12px auto 0; max-width: 560px; text-align: left; border-left: 3px solid #d0d0d0; padding-left: 10px; }
.ex-es { font-size: 18px; }
.ex-en { font-size: 15px; color: #777; }
.meta { font-size: 12px; color: #aaa; margin-top: 18px; }
hr#answer { border: 0; border-top: 1px solid #ccc; margin: 14px 0; }
"""
Q_FWD = """<div class="head">{{Spanish}}</div>
<div class="pos">{{Word Type}}</div>
{{Audio}}"""
A_FWD = """{{FrontSide}}
<hr id=answer>
<div class="gloss">{{English}}</div>
{{#English Alt}}<div class="alt">also: {{English Alt}}</div>{{/English Alt}}
{{#Note}}<div class="note">{{Note}}</div>{{/Note}}
{{#Picture}}<div class="pic">{{Picture}}</div>{{/Picture}}
{{#Examples}}{{Examples}}{{/Examples}}
<div class="meta">#{{Rank}}</div>"""
Q_REV = """<div class="gloss">{{English}}</div>
{{#English Alt}}<div class="alt">also: {{English Alt}}</div>{{/English Alt}}
<div class="pos">{{Word Type}}</div>
{{#Picture}}<div class="pic">{{Picture}}</div>{{/Picture}}"""
A_REV = """{{FrontSide}}
<hr id=answer>
<div class="head">{{Spanish}}</div>
{{Audio}}
{{#Note}}<div class="note">{{Note}}</div>{{/Note}}
{{#Examples}}{{Examples}}{{/Examples}}
<div class="meta">#{{Rank}}</div>"""
tm = tmpl_model['tmpls'][0]
def mk_tmpl(name, ord_, q, a):
    t = dict(tm); t.update(name=name, ord=ord_, qfmt=q, afmt=a, bqfmt="", bafmt="", did=None); return t
model = dict(tmpl_model)
model.update(id=MID, name="Spanish Top 5000 (merged)", mod=now, usn=-1, sortf=FIELDS.index("Rank"), did=DID, type=0,
             flds=flds, tmpls=[mk_tmpl("Forward", 0, Q_FWD, A_FWD), mk_tmpl("Reverse", 1, Q_REV, A_REV)], css=CSS,
             req=[[0, "any", [0]], [1, "any", [2]]], tags=[], vers=[])
models = {str(MID): model}
tmpl_deck = [d for d in decks.values() if d['id'] != 1][0]
default_deck = decks["1"]
deck = dict(tmpl_deck)
DESC = ("Merged from 'Essential Spanish Vocabulary Top 5000' (pictures, 2006 Davies ranks) and 'New Spanish Top 5000 with Examples' "
        "(Azure audio, example sentences, 2025 ranks). %d notes.<br><br>"
        "<b>Tiers</b> (tags): tier::known (rank &le;1000, starts as long-interval review), tier::probable (1001&ndash;2000, review ~1&ndash;5 months), "
        "tier::cognate / tier::cognate-weak (strong / weaker English cognate: the Spanish&rarr;English card starts as a 2&ndash;8 month review, the English&rarr;Spanish card is a normal new card), tier::study (new cards).<br>"
        "Abbreviations: adj adjective, adv adverb, art article, conj conjunction, interj interjection, nc common noun, nf feminine noun, nf (el) feminine noun taking 'el', "
        "nm masculine noun, nm/f masc/fem noun, nmf noun with masc/fem meanings, num number, prep preposition, pron pronoun, v verb.") % len(merged)
deck.update(id=DID, name="Spanish Top 5000 (merged)", mod=now, usn=-1, desc=DESC, conf=1, newToday=[0,0], revToday=[0,0], lrnToday=[0,0], timeToday=[0,0])
decks = {"1": default_deck, str(DID): deck}
conf.update(curModel=str(MID), curDeck=DID, activeDecks=[DID], nextPos=1)
# collection creation = start of today (local) so review 'due' == days from now on import
lt = time.localtime(now); crt = int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))
cur.execute("update col set crt=?, mod=?, scm=?, usn=-1, ls=0, conf=?, models=?, decks=?, dconf=?, tags=?",
            (crt, now_ms, now_ms, json.dumps(conf), json.dumps(models), json.dumps(decks), json.dumps(dconf), json.dumps({})))

# ---------- media plan: only referenced files, new names must be unique
old_media = _old_media_json; new_media = _new_media_json
old_rev = {v: k for k, v in old_media.items()}; new_rev = {v: k for k, v in new_media.items()}
def refs(s): return re.findall(r'\[sound:([^\]]+)\]', s) + re.findall(r'<img[^>]+src="([^"]+)"', s)
media_out = {}  # filename -> (which zip, index)
missing = collections.Counter()
for m in merged:
    for fn in refs(m['pic']):
        if fn in old_rev: media_out[fn] = ("old", old_rev[fn])
        else: missing["pic"] += 1; m['pic'] = ""
    for fn in refs(m['au']):
        if fn in new_rev: media_out[fn] = ("new", new_rev[fn])
        elif fn in old_rev: media_out[fn] = ("old", old_rev[fn])
        else: missing["audio"] += 1; m['au'] = ""
print("media files to pack:", len(media_out), "missing refs dropped:", dict(missing))

# ---------- notes & cards
B91 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~"
def guid():
    n = secrets.randbits(64); s = ""
    while n: s += B91[n % 91]; n //= 91
    return s or "a"
def csum(s): return int(hashlib.sha1(strip(s).encode("utf-8")).hexdigest()[:8], 16)
nid = now_ms + 10; cid = now_ms + 1_000_000
new_pos = 0
tag_summary = collections.Counter()
for m in merged:
    tags = ["spanish5000", band_tag(m['rank']), "pos::" + pos_tag(m['pos']), "tier::" + m['tier'], "src::" + m['src']]
    if m['cog'] >= 0.85: tags.append("cognate::strong")
    elif m['cog'] >= 0.72: tags.append("cognate::weak")
    for t in tags: tag_summary[t] += 1
    examples = interleave(m['sex'], m['eex']) if m['sex'] else ""
    fields = [m['head'], m['pos'], m['en'], m['alt'], examples, m['pic'], m['au'], str(m['rank']),
              str(m['rank_old'] or ""), str(m['rank_new'] or ""), m['sex'], m['eex'], m['note']]
    flds_s = "\x1f".join(fields)
    nid += 1
    cur.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
                (nid, guid(), MID, now, -1, " " + " ".join(tags) + " ", flds_s, m['rank'], csum(m['head']), 0, ""))
    for ord_, ivl in ((0, m['fwd']), (1, m['rev'])):
        cid += 1
        if ivl > 0:
            cur.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, nid, DID, ord_, now, -1, 2, 2, ivl, ivl, 2500, 1, 0, 0, 0, 0, 0, ""))
        else:
            new_pos += 1
            cur.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (cid, nid, DID, ord_, now, -1, 0, 0, new_pos, 0, 0, 0, 0, 0, 0, 0, 0, ""))
conf['nextPos'] = new_pos + 1
cur.execute("update col set conf=?", (json.dumps(conf),))
con.commit()
print("notes:", cur.execute("select count(*) from notes").fetchone()[0], "cards:", cur.execute("select count(*) from cards").fetchone()[0],
      "review cards:", cur.execute("select count(*) from cards where type=2").fetchone()[0], "new cards:", new_pos)
cur.execute("vacuum"); con.commit(); con.close()

# ---------- write apkg
zo = zipfile.ZipFile(OLD_APKG); zn = zipfile.ZipFile(NEW_APKG)
out = zipfile.ZipFile(OUT_APKG, "w", zipfile.ZIP_DEFLATED)
out.write(dbp, "collection.anki2")
media_json = {}
for i, (fn, (src, idx)) in enumerate(sorted(media_out.items())):
    data = (zo if src == "old" else zn).read(idx)
    out.writestr(zipfile.ZipInfo(str(i), date_time=time.localtime(now)[:6]), data, compress_type=zipfile.ZIP_STORED)
    media_json[str(i)] = fn
out.writestr("media", json.dumps(media_json, ensure_ascii=False))
out.close()
print("wrote", OUT_APKG, "%.1f MB" % (os.path.getsize(OUT_APKG) / 1e6))

# ---------- report
with open(REPORT, "w", encoding="utf-8") as f:
    f.write("rank\ttier\tcognate\tsrc\tspanish\tpos\tenglish\tenglish_alt\tfwd_ivl\trev_ivl\trank_old\trank_new\n")
    for m in merged:
        f.write("\t".join(str(x) for x in (m['rank'], m['tier'], "%.2f" % m['cog'], m['src'], m['head'], m['pos'], m['en'], m['alt'], m['fwd'], m['rev'], m['rank_old'] or "", m['rank_new'] or "")) + "\n")
print("tags:", sorted(tag_summary.items()))
