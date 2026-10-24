"""Build the v1.5 release from committed Git blobs, preserving exact bytes."""
from pathlib import Path, PurePosixPath
import argparse, hashlib, io, json, subprocess, tarfile, zipfile

def excluded(name):
    p=PurePosixPath(name)
    return (any(x in {".git", "__pycache__", "_build", "dist", "04_cover_letter", "07_收尾_20261023", "08_独立终审修订_20261024"} for x in p.parts)
        or ".bak" in p.name or p.suffix in {".pyc", ".pyo"}
        or p.name in {"00_提交前必读.md", "05_下一步清单.md", "RELEASE_v1.4_清单.md", "rebuild_pdfs.ps1"})

def main():
    a=argparse.ArgumentParser();a.add_argument("--tag",required=True);a.add_argument("--ref",default="HEAD");a.add_argument("--output-dir",required=True);o=a.parse_args()
    if o.tag != "v1.5":raise SystemExit("Only reviewed v1.5 is permitted")
    root=Path(__file__).resolve().parents[1]
    tracked=set(subprocess.check_output(["git","ls-files","-z"],cwd=root).decode().split(chr(0)))-{""}
    raw=subprocess.check_output(["git","archive","--format=tar",o.ref],cwd=root)
    payload={}
    with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
        for m in tar.getmembers():
            if not m.isfile():continue
            if m.name not in tracked:raise SystemExit("Archive entry is not tracked: "+m.name)
            if excluded(m.name):continue
            if m.name.startswith("data/") and not m.name.endswith(".md.orig"):raise SystemExit("Unexpected input data: "+m.name)
            payload[m.name]=tar.extractfile(m).read()
    prefix="topology-holdout-support-audit-"+o.tag+"/"
    checksum="".join(hashlib.sha256(payload[n]).hexdigest()+"  "+n+chr(10) for n in sorted(payload)).encode()
    out=Path(o.output_dir);out.mkdir(parents=True,exist_ok=True)
    path=out/(prefix[:-1]+".zip")
    with zipfile.ZipFile(path,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n,b in sorted({**payload,"SHA256SUMS.txt":checksum}.items()):
            i=zipfile.ZipInfo(prefix+n,(2026,10,25,0,0,0));i.create_system=3;i.external_attr=0o100644<<16;i.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(i,b,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    h=hashlib.sha256(path.read_bytes()).hexdigest();path.with_suffix(".zip.sha256").write_text(h+"  "+path.name+chr(10),encoding="utf-8",newline="")
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    print(json.dumps({"file":str(path),"sha256":h,"bytes":path.stat().st_size,"payload_files":len(payload)},indent=2))
if __name__=="__main__":main()
