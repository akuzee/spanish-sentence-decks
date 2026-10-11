"""Losslessly shrink an .apkg by zip-compressing its media entries (Anki stores them uncompressed). Speech MP3s with
silence padding compress well; nothing about the files themselves changes. Anki imports compressed entries fine."""
import argparse, os, zipfile

def main():
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("apkg"); ap.add_argument("--out", required=True); a = ap.parse_args()
    z = zipfile.ZipFile(a.apkg); out = zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED, compresslevel=6)
    for info in z.infolist():
        out.writestr(info.filename, z.read(info.filename), compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
    out.close()
    print(f"{os.path.getsize(a.apkg)/1e6:.1f} MB -> {os.path.getsize(a.out)/1e6:.1f} MB ({os.path.getsize(a.out)} bytes, {os.path.getsize(a.out)/2**20:.1f} MiB)")

if __name__ == "__main__":
    main()
