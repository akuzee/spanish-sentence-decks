"""Append text to the top-level deck description inside existing .apkg files without rebuilding them."""
import argparse, json, os, shutil, sqlite3, tempfile, zipfile

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("apkgs", nargs="+"); ap.add_argument("--append", required=True); a = ap.parse_args()
    for path in a.apkgs:
        z = zipfile.ZipFile(path); tmp = tempfile.mkdtemp(); db = os.path.join(tmp, "collection.anki2"); open(db, "wb").write(z.read("collection.anki2"))
        con = sqlite3.connect(db); decks = json.loads(con.execute("select decks from col").fetchone()[0])
        tops = [d for d in decks.values() if d["id"] != 1 and "::" not in d["name"]]
        for d in tops:
            if a.append not in d.get("desc", ""): d["desc"] = (d.get("desc", "") + "<br><br>" + a.append) if d.get("desc") else a.append
        con.execute("update col set decks=?", (json.dumps(decks),)); con.commit(); con.execute("vacuum"); con.close()
        out = path + ".tmp"; zo = zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
        for info in z.infolist():
            if info.filename == "collection.anki2": zo.write(db, "collection.anki2")
            else: zo.writestr(info, z.read(info.filename), compress_type=info.compress_type)
        zo.close(); z.close(); shutil.move(out, path); shutil.rmtree(tmp, ignore_errors=True)
        print(f"{os.path.basename(path)}: updated {len(tops)} deck description(s), {os.path.getsize(path)/1e6:.1f} MB")

if __name__ == "__main__":
    main()
