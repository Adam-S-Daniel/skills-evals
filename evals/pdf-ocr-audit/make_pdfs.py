#!/usr/bin/env python3
"""Build eight tiny, deterministic synthetic PDFs for this fixture.

Shares the stdlib PDF primitives from rename-pdfs; only the multipage layout
is local. No dates, randomness, compression, or PDF-writing dependency.
The committed bytes are the eval input; this generator never runs at eval
time. It and expected.json live OUTSIDE seed/; the harness copies only seed/
into both arms' workspaces, keeping the generator and answer key out of reach.
Run from anywhere, optionally with --out-dir to build in a temporary folder.
"""
from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


_shared_path = Path(__file__).resolve().parent.parent / "rename-pdfs" / "make_pdfs.py"
_spec = importlib.util.spec_from_file_location("rename_pdf_builder", _shared_path)
assert _spec is not None and _spec.loader is not None
_shared = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_shared)


def build_multipage_pdf(pages: list[list[str] | None]) -> bytes:
    """None denotes a raster-only page; a list carries embedded text."""
    assert pages
    kids = " ".join(f"{5 + 2 * i} 0 R" for i in range(len(pages)))
    objects = [
        _shared._obj(1, "<< /Type /Catalog /Pages 2 0 R >>"),
        _shared._obj(2, f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>"),
        _shared._obj(3, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
        _shared._stream_obj(4, "/Type /XObject /Subtype /Image /Width 20 /Height 20 "
                            "/ColorSpace /DeviceGray /BitsPerComponent 8 ",
                            bytes([0x80]) * 400),
    ]
    for index, lines in enumerate(pages):
        page_num = 5 + 2 * index
        if lines is None:
            resources = "/XObject << /Im0 4 0 R >>"
            content = b"q\n200 0 0 200 72 500 cm\n/Im0 Do\nQ\n"
        else:
            resources = "/Font << /F1 3 0 R >>"
            content = _shared._text_content_stream(lines)
        objects.extend([
            _shared._obj(page_num,
                         "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                         f"/Resources << {resources} >> /Contents {page_num + 1} 0 R >>"),
            _shared._stream_obj(page_num + 1, "", content),
        ])
    return _shared._assemble_pdf(objects, root_obj_num=1)


# Nonempty nonsense still counts as a text layer under the current skill.
NOISY_LINES = ["xzQ9 vv0 zzJ3 qp7 Kxx ".strip()] * 20
FILES = [
    ("signed-lease-scan.pdf",
     build_multipage_pdf([["Example digital document"], ["Second text page"]])),
    ("quarterly-report.pdf", build_multipage_pdf([None, None])),
    ("project-brief.pdf",
     build_multipage_pdf([["Example searchable page"], None])),
    ("meeting-notes.pdf", b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog\n"),
    ("scanned-invoice.pdf", _shared.build_text_pdf(NOISY_LINES)),
    ("annual-report.pdf",
     build_multipage_pdf([["Example annual report"], ["Good text layer"]])),
    ("statement-2024-q1.pdf", _shared.build_image_only_pdf()),
    ("POLICY.PDF", _shared.build_text_pdf(["Example uppercase extension document"])),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path,
                        default=Path(__file__).resolve().parent / "seed" / "archive")
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in FILES:
        (args.out_dir / name).write_bytes(data)
    print(f"wrote {len(FILES)} PDFs to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
