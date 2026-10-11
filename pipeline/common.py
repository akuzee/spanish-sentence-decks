"""Shared helpers: text cleaning, .apkg reading, and writing legacy (schema 11) Anki packages."""
import hashlib, html, json, os, re, secrets, shutil, sqlite3, time, unicodedata, zipfile

def strip_html(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()

def deaccent(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def dedup_key(s: str) -> str:
    return re.sub(r"[^a-z0-9ñ ]", "", deaccent(s.lower())).strip()

def esc(s: str) -> str:
    return html.escape(s, quote=False)

class Apkg:
    """Read-only view of an .apkg: its collection database (extracted to work_dir) and media index."""
    def __init__(self, path: str, work_dir: str):
        self.path = path
        self.zip = zipfile.ZipFile(path)
        names = self.zip.namelist()
        self.db_name = "collection.anki21" if "collection.anki21" in names else "collection.anki2"
        os.makedirs(work_dir, exist_ok=True)
        self.db_path = os.path.join(work_dir, self.db_name)
        if not os.path.exists(self.db_path):
            with open(self.db_path, "wb") as f:
                f.write(self.zip.read(self.db_name))
        self.media = json.loads(self.zip.read("media")) if "media" in names else {}
        self.media_rev = {v: k for k, v in self.media.items()}
        self.con = sqlite3.connect(self.db_path)
        self.models = json.loads(self.con.execute("select models from col").fetchone()[0])

    def notes(self):
        for nid, mid, tags, flds in self.con.execute("select id, mid, tags, flds from notes"):
            yield nid, self.models[str(mid)]["name"], tags, flds.split("\x1f")

    def read_media(self, filename: str) -> bytes | None:
        idx = self.media_rev.get(filename)
        return self.zip.read(idx) if idx is not None else None

_B91 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~"
def guid() -> str:
    n = secrets.randbits(64); s = ""
    while n:
        s += _B91[n % 91]; n //= 91
    return s or "a"

def csum(first_field: str) -> int:
    return int(hashlib.sha1(strip_html(first_field).encode("utf-8")).hexdigest()[:8], 16)

def local_day_start(now: int) -> int:
    lt = time.localtime(now)
    return int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))

class PackageWriter:
    """Builds a legacy-format .apkg (collection.anki2, schema 11) from scratch using an existing schema-11
    database as the structural template. Review cards are written with due = interval (days), relative to a
    collection creation date of 'today', so Anki's importer lands them exactly `ivl` days after import day."""
    def __init__(self, template_db: str, build_dir: str):
        shutil.rmtree(build_dir, ignore_errors=True); os.makedirs(build_dir)
        self.db_path = os.path.join(build_dir, "collection.anki2")
        shutil.copy(template_db, self.db_path)
        self.con = sqlite3.connect(self.db_path); self.cur = self.con.cursor()
        for t in ("notes", "cards", "revlog", "graves"):
            self.cur.execute(f"delete from {t}")
        conf, models, decks, dconf = (json.loads(x) for x in self.cur.execute("select conf, models, decks, dconf from col").fetchone())
        self.conf, self.dconf = conf, dconf
        self._tmpl_model = next(iter(models.values()))
        self._tmpl_deck = [d for d in decks.values() if d["id"] != 1][0]
        self.default_deck = decks["1"]
        self.now = int(time.time()); self.now_ms = self.now * 1000
        self.models, self.decks = {}, {"1": self.default_deck}
        self._nid = self.now_ms + 10; self._cid = self.now_ms + 1_000_000; self._pos = 0
        self.media: dict[str, bytes] = {}

    def add_model(self, mid, name, fields, templates, css, sortf, default_did):
        fld_t = self._tmpl_model["flds"][0]; tm = self._tmpl_model["tmpls"][0]
        flds = []
        for i, fname in enumerate(fields):
            f = dict(fld_t); f.update(name=fname, ord=i, sticky=False, rtl=False, font="Arial", size=20); f["media"] = []; flds.append(f)
        tmpls = []
        for i, (tname, q, a) in enumerate(templates):
            t = dict(tm); t.update(name=tname, ord=i, qfmt=q, afmt=a, bqfmt="", bafmt="", did=None); tmpls.append(t)
        m = dict(self._tmpl_model)
        m.update(id=mid, name=name, mod=self.now, usn=-1, sortf=sortf, did=default_did, type=0, flds=flds, tmpls=tmpls, css=css,
                 req=[[i, "any", [0]] for i in range(len(templates))], tags=[], vers=[])
        self.models[str(mid)] = m
        return m

    def add_deck(self, did, name, desc=""):
        d = dict(self._tmpl_deck)
        d.update(id=did, name=name, mod=self.now, usn=-1, desc=desc, conf=1, newToday=[0, 0], revToday=[0, 0], lrnToday=[0, 0], timeToday=[0, 0])
        self.decks[str(did)] = d

    def add_note(self, mid, fields, tags, sort_value, cards):
        """cards: list of (ord, deck_id, interval_days) where interval 0 means a new card (queued in call order)."""
        self._nid += 1
        self.cur.execute("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
                         (self._nid, guid(), mid, self.now, -1, " " + " ".join(tags) + " ", "\x1f".join(fields), sort_value, csum(fields[0]), 0, ""))
        for ord_, did, ivl in cards:
            self._cid += 1
            if ivl > 0:
                self.cur.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (self._cid, self._nid, did, ord_, self.now, -1, 2, 2, ivl, ivl, 2500, 1, 0, 0, 0, 0, 0, ""))
            else:
                self._pos += 1
                self.cur.execute("insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                 (self._cid, self._nid, did, ord_, self.now, -1, 0, 0, self._pos, 0, 0, 0, 0, 0, 0, 0, 0, ""))
        return self._nid

    def finish(self, out_path, cur_model, cur_deck):
        self.conf.update(curModel=str(cur_model), curDeck=cur_deck, activeDecks=[cur_deck], nextPos=self._pos + 1)
        self.cur.execute("update col set crt=?, mod=?, scm=?, usn=-1, ls=0, conf=?, models=?, decks=?, dconf=?, tags=?",
                         (local_day_start(self.now), self.now_ms, self.now_ms, json.dumps(self.conf), json.dumps(self.models),
                          json.dumps(self.decks), json.dumps(self.dconf), json.dumps({})))
        self.con.commit(); self.cur.execute("vacuum"); self.con.commit(); self.con.close()
        z = zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED)
        z.write(self.db_path, "collection.anki2")
        index = {}
        for i, (fn, data) in enumerate(sorted(self.media.items())):
            # media is deflated (Anki itself stores it raw): speech MP3s with silence padding shrink ~45%, losslessly
            z.writestr(zipfile.ZipInfo(str(i), date_time=time.localtime(self.now)[:6]), data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
            index[str(i)] = fn
        z.writestr("media", json.dumps(index, ensure_ascii=False)); z.close()
        return os.path.getsize(out_path)
