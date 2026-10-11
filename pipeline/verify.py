"""Import an .apkg into a fresh collection with the official Anki library and check what Anki will see:
note/card counts, that review cards land exactly `interval` days after import day, media completeness,
new-card order, and database integrity. Requires `pip install anki`."""
import argparse, os, re, shutil, time

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("apkg"); ap.add_argument("--tmp", default="work/_verify")
    ap.add_argument("--age-days", type=int, default=400, help="pretend the target collection is this old (exercises the due-date remap)")
    a = ap.parse_args()
    from anki.collection import Collection, ImportAnkiPackageRequest, ImportAnkiPackageOptions
    shutil.rmtree(a.tmp, ignore_errors=True); os.makedirs(a.tmp)
    path = os.path.join(a.tmp, "collection.anki2")
    col = Collection(path); col.db.execute("update col set crt=?", int(time.time()) - a.age_days * 86400); col.close(); col = Collection(path)
    res = col.import_anki_package(ImportAnkiPackageRequest(package_path=os.path.abspath(a.apkg), options=ImportAnkiPackageOptions(
        merge_notetypes=False, update_notes=0, update_notetypes=0, with_scheduling=True, with_deck_configs=False)))
    log = res.log
    print(f"imported: new {len(log.new)}, duplicate {len(log.duplicate)}, conflicting {len(log.conflicting)}, missing notetype {len(log.missing_notetype)}")
    print("decks:", [d.name for d in col.decks.all_names_and_ids() if d.id != 1])
    print("notes:", col.note_count(), "cards:", col.card_count())
    today = col.sched.today
    for t, q, n, lo, hi, ilo, ihi in col.db.all("select type, queue, count(*), min(due), max(due), min(ivl), max(ivl) from cards group by type, queue"):
        print(f"  type {t} queue {q}: {n} cards, due {lo}-{hi}, ivl {ilo}-{ihi}")
    rev = col.db.all("select due, ivl from cards where type=2")
    bad = [(d, i) for d, i in rev if d - today != i]
    print("review cards whose due date != interval:", len(bad), bad[:3])
    files = set(os.listdir(os.path.join(a.tmp, "collection.media"))) if os.path.isdir(os.path.join(a.tmp, "collection.media")) else set()
    refs = set()
    for (flds,) in col.db.all("select flds from notes"):
        refs |= set(re.findall(r"\[sound:([^\]]+)\]", flds)) | set(re.findall(r'<img[^>]+src="([^"]+)"', flds))
    print("media referenced:", len(refs), "missing:", len(refs - files))
    first = col.db.all("select n.flds from cards c join notes n on n.id=c.nid where c.type=0 order by c.due limit 5")
    print("first new cards:", [f[0].split("\x1f")[0][:40] for f in first])
    print("integrity:", col.db.scalar("pragma integrity_check")); col.close()

if __name__ == "__main__":
    main()
