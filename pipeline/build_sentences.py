"""Step 4: build an .apkg from the scored sentence pool.

Variants      --variant macro    every distinct sentence, including fragments and odd lines (nothing cut)
              --variant quality  only sentences that pass the quality filter (4-16 words, complete, no artifacts)
              --variant latam    quality, minus sentences with vosotros forms or Spain-specific vocabulary
Sources       --sources all | tatoeba   (tatoeba = only the two Tatoeba-derived decks; cleanest licensing)
Level         --level none       every card new, in difficulty order (use the level:: tags to adjust yourself)
              --level A2|B1|B2|C1  sentences below the level are dropped, the band just under it becomes
                                 long-interval reviews (capped by --review-cap), the rest are new cards
Audio         --audio all|native|none   which recordings to pack (native = only the CC-licensed Tatoeba recordings)
Structure     --split-core N     subdeck "1 Core" = best N sentences per target word, "2 Extended" = the rest
                                 (0 = one flat deck)
Cards: Read (Spanish -> English) and Translate (English -> Spanish, with optional hints).
"""
import argparse, collections, csv, json, os, random, re, sys
from common import Apkg, PackageWriter, esc

SRC_PEN = {"tatoeba_native": 0, "tatoeba_tts": 60, "neri2": 120, "neri3": 220, "neri1": 300}
SRC_LABEL = {"tatoeba_native": "Tatoeba · native audio", "tatoeba_tts": "Tatoeba · TTS", "neri1": "subtitles (Neri 1)", "neri2": "subtitles (Neri 2)", "neri3": "subtitles (Neri 3)"}
FEAT_LABEL = {"subj": "subjunctive", "cond": "conditional", "perf": "perfect", "imper": "imperative", "past": "past", "fut": "future", "ger": "gerund"}
# (levels dropped, levels turned into reviews); everything above is studied as new cards
LEVEL_POLICY = {"none": (set(), set()), "A1": (set(), set()), "A2": ({1, 2}, {3, 4}), "B1": ({1, 2, 3, 4}, {5, 6}), "B2": ({1, 2, 3, 4, 5, 6}, {7, 8}), "C1": ({1, 2, 3, 4, 5, 6, 7}, {8})}
FIELDS = ["Spanish", "English", "Audio", "Spanish Marked", "Target", "Target Gloss", "Sentence with blank", "Key word", "Level", "Grammar", "Source", "Score", "Target Rank", "Words"]
CSS = """
.card { font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 22px; text-align: center; color: #222; background: #fff; padding: 12px; }
.night_mode .card, .nightMode .card { color: #eee; background: #1e1e1e; }
.es { font-size: 30px; line-height: 1.35; margin: 10px 0; }
.es b { color: #1a5fb4; } .night_mode .es b, .nightMode .es b { color: #8ab4f8; }
.en { font-size: 24px; color: #333; margin: 8px 0; } .night_mode .en, .nightMode .en { color: #ddd; }
.audio { margin: 6px 0; }
.target { font-size: 17px; color: #666; margin-top: 14px; } .target b { color: #1a5fb4; }
.hint { font-size: 18px; margin-top: 12px; color: #777; }
.hint a { color: #888; text-decoration: none; border: 1px solid #ccc; border-radius: 12px; padding: 2px 12px; font-size: 15px; }
.meta { font-size: 12px; color: #aaa; margin-top: 20px; }
hr#answer { border: 0; border-top: 1px solid #ccc; margin: 16px 0; }
"""
Q_READ = '<div class="es">{{Spanish}}</div>\n<div class="audio">{{Audio}}</div>'
A_READ = """<div class="es">{{Spanish Marked}}</div>
<div class="audio">{{Audio}}</div>
<hr id=answer>
<div class="en">{{English}}</div>
{{#Target}}<div class="target"><b>{{Target}}</b>{{#Target Gloss}} &middot; {{Target Gloss}}{{/Target Gloss}}{{#Target Rank}} &middot; #{{Target Rank}}{{/Target Rank}}</div>{{/Target}}
<div class="meta">level {{Level}}{{#Grammar}} &middot; {{Grammar}}{{/Grammar}} &middot; {{Source}}</div>"""
Q_TRANS = """<div class="en">{{English}}</div>
{{#Sentence with blank}}<div class="hint">{{hint:Sentence with blank}}</div>{{/Sentence with blank}}
{{#Key word}}<div class="hint">{{hint:Key word}}</div>{{/Key word}}"""
A_TRANS = """<div class="en">{{English}}</div>
<hr id=answer>
<div class="es">{{Spanish Marked}}</div>
<div class="audio">{{Audio}}</div>
{{#Target}}<div class="target"><b>{{Target}}</b>{{#Target Gloss}} &middot; {{Target Gloss}}{{/Target Gloss}}</div>{{/Target}}
<div class="meta">level {{Level}}{{#Grammar}} &middot; {{Grammar}}{{/Grammar}} &middot; {{Source}}</div>"""

def mark(es, target):
    if not target: return esc(es)
    return re.sub(r"(?<![\wáéíóúñü])(%s)(?![\wáéíóúñü])" % re.escape(target), lambda m: "<b>" + esc(m.group(1)) + "</b>", esc(es), count=1)

def skeleton(es, target):
    if not target: return ""
    out = re.sub(r"(?<![\wáéíóúñü])%s(?![\wáéíóúñü])" % re.escape(target), "_" * max(4, len(target)), es, count=1)
    return esc(out) if out != es else ""

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scored", required=True); ap.add_argument("--levels", required=True, help="levels.json written by score.py")
    ap.add_argument("--rankmap", required=True); ap.add_argument("--sources-json", required=True, help="same JSON given to pool.py (for media)")
    ap.add_argument("--work", default="work")
    ap.add_argument("--variant", choices=["macro", "quality", "latam"], default="quality")
    ap.add_argument("--sources", choices=["all", "tatoeba"], default="all")
    ap.add_argument("--level", choices=list(LEVEL_POLICY), default="none")
    ap.add_argument("--review-cap", type=int, default=1000, help="max sentences kept as reviews from the band under --level")
    ap.add_argument("--split-core", type=int, default=0, help="N best sentences per target word go to '1 Core'; 0 = flat deck")
    ap.add_argument("--no-gloss", action="store_true", help="omit the dictionary gloss of the target word")
    ap.add_argument("--vosotros-penalty", type=int, default=1000, help="how far vosotros sentences are pushed back in the order (score points; ~1000 = one level later, 3000 = to the end)")
    ap.add_argument("--audio", choices=["all", "native", "none"], default="all", help="which recordings to include: all, only the native (Tatoeba/arh) ones, or none")
    ap.add_argument("--tts-max-level", type=int, default=10, help="with --audio all: include the synthetic (TTS) recordings only for sentences up to this level (1-10)")
    ap.add_argument("--tts-bitrate", default="", help="with --audio all: re-encode the synthetic recordings to this MP3 bitrate, mono (e.g. 24k) to fit AnkiWeb's size limit; native recordings are never touched")
    ap.add_argument("--name", required=True, help="deck name"); ap.add_argument("--out", required=True); ap.add_argument("--report")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args(); random.seed(a.seed)
    RM = json.load(open(a.rankmap, encoding="utf-8")); cuts = json.load(open(a.levels))["cuts"]
    sources = json.load(open(a.sources_json, encoding="utf-8"))
    pk = {label: Apkg(os.path.expanduser(path), f"{a.work}/{label}") for label, path in sources.items()}
    rows = list(csv.DictReader(open(a.scored, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        for k in ("max_rank", "second", "hard", "unknown", "gram", "score", "n", "has_name", "quality", "spain_w"): r[k] = int(r[k])
        r["level"] = 1 + sum(1 for c in cuts if r["score"] >= c)
    # ---- variant / source filters
    if a.sources == "tatoeba": rows = [r for r in rows if r["src"].startswith("tatoeba")]
    if a.variant in ("quality", "latam"): rows = [r for r in rows if r["quality"] == 1]
    if a.variant == "latam": rows = [r for r in rows if not r["vosotros"] and r["spain_w"] == 0]
    # ---- level policy
    drop_lv, rev_lv = LEVEL_POLICY[a.level]
    def quality(r):
        q = SRC_PEN[r["src"]] + 150 * r["has_name"] + 120 * r["unknown"] + (80 if r["n"] < 6 else 0) + (60 if r["n"] > 12 else 0)
        q += 300 * r["spain_w"] + (5000 if r["vosotros"] else 0) + (400 if r["quality"] == 0 else 0)
        return q - (40 if r["audio"] else 0)
    studied = [r for r in rows if r["level"] not in drop_lv and r["level"] not in rev_lv]
    band = sorted([r for r in rows if r["level"] in rev_lv and not r["vosotros"]], key=lambda r: (quality(r) // 100, -r["score"]))
    reviews = band[:a.review_cap]
    for r in reviews: r["tier"] = "review"
    # ---- core / extended split and ordering
    studied.sort(key=lambda r: (quality(r), r["score"]))
    per = collections.Counter()
    for r in studied:
        t = r["target"].lower() or "_"; per[t] += 1; k = per[t]
        core = a.split_core and k <= a.split_core and not r["vosotros"]
        r["tier"] = "core" if core else ("extended" if a.split_core else "flat")
        demote = 300 * max(0, k - a.split_core - 1) if (a.split_core and not core) else 0
        r["order"] = r["score"] + demote + (a.vosotros_penalty if r["vosotros"] else 0) + 250 * r["spain_w"] + (1500 if r["quality"] == 0 else 0)
    for r in reviews: r["order"] = r["score"]
    core = sorted([r for r in studied if r["tier"] == "core"], key=lambda r: r["order"])
    rest = sorted([r for r in studied if r["tier"] != "core"], key=lambda r: r["order"])
    print(f"variant={a.variant} sources={a.sources} level={a.level}: {len(core)} core, {len(rest)} {'extended' if a.split_core else 'flat'}, {len(reviews)} reviews, dropped {len(rows) - len(studied) - len(reviews)}", file=sys.stderr)
    # ---- synthetic recordings: optional level cap and re-encode (native recordings stay byte-identical)
    tts_bytes = {}
    if a.audio == "all" and a.tts_bitrate:
        import concurrent.futures, subprocess, tempfile
        need = []
        for r in core + rest + reviews:
            mm = re.search(r"\[sound:([^\]]+)\]", r["audio"])
            if mm and r["src"] == "tatoeba_tts" and r["level"] <= a.tts_max_level: need.append(mm.group(1))
        tmp = tempfile.mkdtemp(prefix="tts_")
        def enc(fn):
            data = pk["tatoeba_tts"].read_media(fn)
            if not data: return fn, None
            src = os.path.join(tmp, str(abs(hash(fn))) + ".mp3"); dst = src + ".out.mp3"; open(src, "wb").write(data)
            ok = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", "22050", "-c:a", "libmp3lame", "-b:a", a.tts_bitrate, dst], capture_output=True).returncode == 0
            out = open(dst, "rb").read() if ok else data
            for f in (src, dst):
                try: os.remove(f)
                except OSError: pass
            return fn, (out if len(out) < len(data) else data)
        print(f"re-encoding {len(need)} synthetic recordings at {a.tts_bitrate} mono…", file=sys.stderr)
        with concurrent.futures.ThreadPoolExecutor(8) as ex:
            for fn, data in ex.map(enc, need): tts_bytes[fn] = data
    # ---- package
    template_db = next(iter(pk.values())).db_path
    w = PackageWriter(template_db, os.path.join(os.path.dirname(os.path.abspath(a.out)), "_build_" + os.path.basename(a.out).replace(".apkg", "")))
    MID = w.now_ms; DID_P, DID_C, DID_X = w.now_ms + 1, w.now_ms + 2, w.now_ms + 3
    w.add_model(MID, "Spanish Sentence (merged)", FIELDS, [("Read", Q_READ, A_READ), ("Translate", Q_TRANS, A_TRANS)], CSS, FIELDS.index("Score"), DID_C if a.split_core else DID_P)
    naudio = 0; tagc = collections.Counter()
    def add(r, did):
        nonlocal naudio
        target = r["target"] if r["max_rank"] > 1000 else ""
        gloss = RM[r["target_key"]][1] if (target and r["target_key"] and r["target_key"] in RM and not a.no_gloss) else ""
        m = re.search(r"\[sound:([^\]]+)\]", r["audio"]); au = ""
        if a.audio == "none" or (a.audio == "native" and r["src"] != "tatoeba_native"): m = None
        if m and r["src"] == "tatoeba_tts" and r["level"] > a.tts_max_level: m = None
        if m:
            data = tts_bytes.get(m.group(1)) or (pk[r["src"]].read_media(m.group(1)) if r["src"] in pk else None)
            if data: w.media[m.group(1)] = data; au = "[sound:%s]" % m.group(1); naudio += 1
        feats = [FEAT_LABEL[f] for f in r["feats"].split() if f in FEAT_LABEL]
        tags = ["spanish_sentences", "tier::" + r["tier"], "level::%02d" % r["level"], "src::" + r["src"], "audio::" + ("yes" if au else "no")]
        tags += ["gram::" + f for f in r["feats"].split() if f]
        if r["vosotros"]: tags.append("region::vosotros")
        if r["spain_w"]: tags.append("region::spain")
        if r["quality"] == 0: tags += ["quality::low", "drop::" + re.sub(r"[^a-z0-9]+", "_", r["drop_reason"].lower()).strip("_")]
        for t in tags: tagc[t] += 1
        fields = [esc(r["es"]), esc(r["en"]), au, mark(r["es"], target), esc(target), esc(gloss), skeleton(r["es"], target), esc(target),
                  str(r["level"]), ", ".join(feats), SRC_LABEL[r["src"]], str(r["score"]), str(r["max_rank"]) if target and r["max_rank"] < 6500 else "", str(r["n"])]
        if r["tier"] == "review": cards = [(0, did, random.randint(120, 240)), (1, did, random.randint(60, 150))]
        else: cards = [(0, did, 0), (1, did, 0)]
        w.add_note(MID, fields, tags, r["score"], cards)
    if a.split_core:
        for r in core: add(r, DID_C)
        for r in rest: add(r, DID_X)
        for r in reviews: add(r, DID_C)
    else:
        for r in rest + reviews: add(r, DID_P)
    total = len(core) + len(rest) + len(reviews)
    desc = (f"{total} Spanish sentences with English translations, sorted by difficulty (hardest word's frequency rank, grammar, length). "
            f"Variant: <b>{a.variant}</b>, sources: <b>{a.sources}</b>, level preset: <b>{a.level}</b>. "
            + (f"<b>1 Core</b> = best {a.split_core} sentences per target word ({len(core)}); <b>2 Extended</b> = the rest ({len(rest)}). " if a.split_core else "")
            + (f"{len(reviews)} sentences from the band just below the level start as long-interval reviews (tag tier::review). " if reviews else "")
            + "Latin American learners: Spain-specific sentences are tagged region::vosotros / region::spain; search tag:region::* and suspend them. "
            "Tags: level::01-10 (difficulty deciles), gram::*, src::*, audio::*"
            + (", quality::low + drop::* for lines that failed the quality filter" if a.variant == "macro" else "") + ". "
            f"Cards: <b>Read</b> (Spanish &rarr; English) and <b>Translate</b> (English &rarr; Spanish with optional hints). Audio on {naudio} sentences"
            + (f" (native recordings everywhere they exist; synthetic recordings up to level {a.tts_max_level}" + (f", re-encoded to {a.tts_bitrate} mono" if a.tts_bitrate else "") + ")" if a.audio == "all" and (a.tts_max_level < 10 or a.tts_bitrate) else "") + "; "
            "enable 'Don't play audio automatically' in the deck options if you only want it on demand. "
            "Sentences: Tatoeba (CC BY 2.0 FR); native audio by Tatoeba user arh (CC BY-NC-ND 3.0). See the project README for full credits.")
    w.add_deck(DID_P, a.name, desc)
    if a.split_core: w.add_deck(DID_C, a.name + "::1 Core"); w.add_deck(DID_X, a.name + "::2 Extended")
    size = w.finish(a.out, MID, DID_C if a.split_core else DID_P)
    print(f"wrote {a.out} ({size / 1e6:.1f} MB): {total} notes, {2 * total} cards, {naudio} with audio", file=sys.stderr)
    print("tags:", {k: v for k, v in sorted(tagc.items()) if not k.startswith("level")}, file=sys.stderr)
    if a.report:
        with open(a.report, "w", encoding="utf-8", newline="") as f:
            wr = csv.writer(f, delimiter="\t", lineterminator="\n"); wr.writerow(["tier", "order", "level", "score", "src", "spanish", "english", "target", "grammar", "audio", "region"])
            for r in core + rest + reviews:
                wr.writerow([r["tier"], r["order"], r["level"], r["score"], r["src"], r["es"], r["en"], r["target"] if r["max_rank"] > 1000 else "", r["feats"], "yes" if r["audio"] else "no",
                             ("vosotros " if r["vosotros"] else "") + ("spain" if r["spain_w"] else "")])

if __name__ == "__main__":
    main()
