"""Re-encode the .mp3 recordings inside an .apkg to a smaller bitrate (mono) so the package fits AnkiWeb's size
limit. Filenames are unchanged, so the notes need no edits. Requires ffmpeg on PATH."""
import argparse, concurrent.futures, json, os, shutil, subprocess, sys, tempfile, zipfile

def encode(args):
    src, dst, bitrate, rate = args
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", src, "-ac", "1", "-ar", str(rate), "-codec:a", "libmp3lame", "-b:a", bitrate, dst], capture_output=True)
    return r.returncode == 0 and os.path.getsize(dst) < os.path.getsize(src)

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("apkg"); ap.add_argument("--out", required=True)
    ap.add_argument("--bitrate", default="40k"); ap.add_argument("--rate", type=int, default=24000); ap.add_argument("--jobs", type=int, default=8)
    a = ap.parse_args()
    z = zipfile.ZipFile(a.apkg); media = json.loads(z.read("media"))
    tmp = tempfile.mkdtemp(prefix="shrink_"); jobs = []
    for idx, name in media.items():
        if name.lower().endswith(".mp3"):
            src = os.path.join(tmp, idx + ".src.mp3"); open(src, "wb").write(z.read(idx)); jobs.append((src, os.path.join(tmp, idx + ".mp3"), a.bitrate, a.rate))
    print(f"re-encoding {len(jobs)} mp3 files at {a.bitrate} mono…", file=sys.stderr)
    with concurrent.futures.ThreadPoolExecutor(a.jobs) as ex: ok = list(ex.map(encode, jobs))
    done = {os.path.basename(j[1])[:-4] for j, k in zip(jobs, ok) if k}
    out = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED); before = after = 0
    for info in z.infolist():
        if info.filename in done:
            data = open(os.path.join(tmp, info.filename + ".mp3"), "rb").read(); before += info.file_size; after += len(data)
            out.writestr(zipfile.ZipInfo(info.filename, date_time=info.date_time), data, compress_type=zipfile.ZIP_STORED)
        else:
            out.writestr(info, z.read(info.filename), compress_type=zipfile.ZIP_STORED if info.filename.isdigit() else zipfile.ZIP_DEFLATED)
    out.close(); shutil.rmtree(tmp, ignore_errors=True)
    print(f"audio {before/1e6:.1f} MB -> {after/1e6:.1f} MB ({len(done)}/{len(jobs)} files); package {os.path.getsize(a.apkg)/1e6:.1f} MB -> {os.path.getsize(a.out)/1e6:.1f} MB", file=sys.stderr)

if __name__ == "__main__":
    main()
