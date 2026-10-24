#!/usr/bin/env python
"""Record/check the bytes of the final PDF build inputs and delivered PDFs.

Default and --check are read-only. --record is explicit and must be called only
after a successful rebuild and visual review. This manifest detects subsequent
byte changes; it is not proof of rendering correctness or visual acceptance.
"""
from __future__ import annotations
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

PKG=Path(__file__).resolve().parents[1]
ROOT=PKG.parent
DEFAULT_MANIFEST=PKG/'config/build_manifest.json'


def expected_files(root=ROOT):
    root=Path(root)
    builder=root/'03_reproduction_package/scripts/build_pdf_v6.py'
    tree=ast.parse(builder.read_text(encoding='utf-8-sig'))
    maps={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in {'FIG_MAP','FIG_MAP_SI'}:
                    maps[target.id]=ast.literal_eval(node.value)
    if set(maps)!={'FIG_MAP','FIG_MAP_SI'} or set(maps['FIG_MAP'])!=set(range(1,5)) or set(maps['FIG_MAP_SI'])!=set(range(1,9)):
        raise ValueError('builder must declare four main and eight SI figure filenames')
    files=['01_manuscript/Manuscript_v6.md','02_supplementary/SI_v6.md',
           '03_reproduction_package/scripts/build_pdf_v6.py',
           '01_manuscript/Manuscript_v6.pdf','02_supplementary/SI_v6.pdf',
           '01_manuscript/figures/TOC_graphic.png']
    files += ['01_manuscript/figures/'+maps[key][i] for key in ('FIG_MAP','FIG_MAP_SI') for i in sorted(maps[key])]
    if len(files)!=18 or len(set(files))!=18:
        raise ValueError('expected 18 distinct build-manifest files')
    return sorted(files)


def snapshot(root=ROOT):
    root=Path(root).resolve()
    rows=[]
    for relative in expected_files(root):
        path=(root/relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'missing or unsafe build file: {relative}')
        h=hashlib.sha256()
        with path.open('rb') as fh:
            for block in iter(lambda:fh.read(1<<20),b''):h.update(block)
        rows.append(dict(path=relative,bytes=path.stat().st_size,sha256=h.hexdigest()))
    return rows


def verify(root=ROOT,manifest=DEFAULT_MANIFEST):
    path=Path(manifest)
    if not path.is_file():raise ValueError(f'missing build manifest: {path}; rebuild first, then explicitly --record')
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('schema_version')!=1 or not data.get('recorded_at_utc'):
        raise ValueError('invalid manifest schema or missing record timestamp')
    stored=data.get('files')
    if not isinstance(stored,list):raise ValueError('manifest files must be a list')
    expected=expected_files(root)
    paths=[row.get('path') for row in stored]
    if len(paths)!=len(expected) or len(set(paths))!=len(paths) or set(paths)!=set(expected):
        raise ValueError('manifest does not cover the exact 18-file build surface')
    old={row['path']:row for row in stored}
    current=snapshot(root)
    changed=[row['path'] for row in current if row!=old[row['path']]]
    if changed:raise ValueError('build bytes changed since recording: '+', '.join(changed))
    return len(current)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    mode=ap.add_mutually_exclusive_group()
    mode.add_argument('--record',action='store_true')
    mode.add_argument('--check',action='store_true')
    ap.add_argument('--root',default=str(ROOT))
    ap.add_argument('--manifest',default=None)
    args=ap.parse_args(argv)
    root=Path(args.root).resolve()
    manifest=Path(args.manifest) if args.manifest else root/'03_reproduction_package/config/build_manifest.json'
    try:
        if args.record:
            data=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                scope='Byte identity after an explicitly recorded build; not proof of rendering or visual correctness.',
                files=snapshot(root))
            manifest.parent.mkdir(parents=True,exist_ok=True)
            manifest.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
            print(f'RECORDED {len(data["files"])} files: {manifest}')
        else:
            print(f'PASS: build manifest matches all {verify(root,manifest)} input/output files')
        return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr)
        return 1


if __name__=='__main__':raise SystemExit(main())
