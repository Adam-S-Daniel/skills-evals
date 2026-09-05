#!/usr/bin/env python3
"""Generate a handful of sample utility-billing PDFs for inbox/.

Hand-rolls minimal, valid single-page PDF 1.4 files using only the stdlib —
no reportlab, no third-party PDF library needed to author these. Output is
byte-deterministic (no timestamps, no compression, fixed object numbering)
so re-running this script reproduces the same PDFs exactly.

Run from anywhere:
    python3 make_pdfs.py
writes the PDFs into ./inbox/ next to this script (or --out-dir to redirect).

The PDFs are committed alongside this script; it is not invoked automatically.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def _pdf_string(s: str) -> str:
    """Escape a literal string for a PDF `(...)` string object."""
    return s.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _text_content_stream(lines: list[str], font_size: int = 11, leading: int = 14,
                          x: int = 72, y: int = 720) -> bytes:
    parts = ["BT", f"/F1 {font_size} Tf", f"{x} {y} Td"]
    for i, line in enumerate(lines):
        if i > 0:
            parts.append(f"0 -{leading} Td")
        parts.append(f"({_pdf_string(line)}) Tj")
    parts.append("ET")
    return ("\n".join(parts) + "\n").encode("latin-1")


def _obj(num: int, body: str) -> bytes:
    return f"{num} 0 obj\n{body}\nendobj\n".encode("latin-1")


def _stream_obj(num: int, extra_dict: str, stream_bytes: bytes) -> bytes:
    header = f"{num} 0 obj\n<< {extra_dict}/Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
    return header + stream_bytes + b"\nendstream\nendobj\n"


def _assemble_pdf(objects: list[bytes], root_obj_num: int) -> bytes:
    """Wrap fully-formed indirect objects (each ending in `endobj\\n`) in a
    PDF header, xref table, and trailer. `objects[i]` is object number i+1.
    """
    header = b"%PDF-1.4\n"
    body = bytearray()
    offsets = [0]  # object 0 is the free-list head
    pos = len(header)
    for obj_bytes in objects:
        offsets.append(pos)
        body += obj_bytes
        pos += len(obj_bytes)
    xref_offset = len(header) + len(body)
    n = len(objects) + 1
    xref_lines = [f"xref\n0 {n}\n", "0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n")
    xref_bytes = "".join(xref_lines).encode("ascii")
    trailer = (f"trailer\n<< /Size {n} /Root {root_obj_num} 0 R >>\n"
               f"startxref\n{xref_offset}\n%%EOF\n").encode("ascii")
    return header + bytes(body) + xref_bytes + trailer


def build_text_pdf(lines: list[str]) -> bytes:
    """A single searchable page showing `lines` in the base-14 Helvetica font."""
    content = _text_content_stream(lines)
    objects = [
        _obj(1, "<< /Type /Catalog /Pages 2 0 R >>"),
        _obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        _obj(3, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                "/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"),
        _obj(4, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
        _stream_obj(5, "", content),
    ]
    return _assemble_pdf(objects, root_obj_num=1)


def build_image_only_pdf(width: int = 20, height: int = 20, gray: int = 0x80) -> bytes:
    """A single page carrying only a raster XObject — no text-showing
    operator anywhere, so pypdf's extract_text() returns "". Stands in for a
    scan with no OCR text layer.
    """
    image_data = bytes([gray]) * (width * height)
    content = f"q\n{width * 10} 0 0 {height * 10} 72 600 cm\n/Im0 Do\nQ\n".encode("ascii")
    objects = [
        _obj(1, "<< /Type /Catalog /Pages 2 0 R >>"),
        _obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        _obj(3, "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                "/Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"),
        _stream_obj(4, f"/Type /XObject /Subtype /Image /Width {width} /Height {height} "
                       f"/ColorSpace /DeviceGray /BitsPerComponent 8 ", image_data),
        _stream_obj(5, "", content),
    ]
    return _assemble_pdf(objects, root_obj_num=1)


# -- Sample content -------------------------------------------------------
# Fictional company, fictional people, fictional numbers; example.com only.
# Each source filename carries the date/time it was scanned, which does not
# necessarily match the date printed in the document itself.

STATEMENT_LINES = [
    "Example Utilities Ltd",
    "100 Example Street, Springfield",
    "billing@example.com",
    "",
    "Account Statement",
    "",
    "Billing Period: 1 Jan 2026 to 31 Jan 2026",
    "Account Number: 4821",
    "",
    "Previous Balance: $128.40",
    "Payments Received: $128.40",
    "New Charges: $146.75",
    "Total Due: $146.75",
    "",
    "Thank you for your business.",
]

INVOICE_LINES = [
    "Example Utilities Ltd",
    "100 Example Street, Springfield",
    "billing@example.com",
    "",
    "Invoice",
    "",
    "Invoice Date: February 14, 2026",
    "Invoice Number: 4471",
    "",
    "Description: Water Service - January 2026",
    "Amount Due: $92.10",
    "",
    "Please remit payment within 30 days.",
]

RECEIPT_LINES = [
    "Example Utilities Ltd",
    "100 Example Street, Springfield",
    "billing@example.com",
    "",
    "Receipt",
    "",
    "Date: December 15, 2025",
    "Description: Security Deposit Refund",
    "Amount: $75.00",
    "",
    "This receipt confirms your deposit refund has been processed.",
]

BILL_LINES = [
    "Example Utilities Ltd",
    "100 Example Street, Springfield",
    "billing@example.com",
    "",
    "Bill",
    "",
    "Bill Date: March 3, 2026",
    "Account Number: 9002",
    "",
    "Electric Service - February 2026: $184.22",
    "Total Due: $184.22",
    "",
    "Payment is due upon receipt.",
]

# (filename, bytes) pairs written into inbox/.
FILES: list[tuple[str, bytes]] = [
    ("Scan_20260205_081533.pdf", build_text_pdf(STATEMENT_LINES)),
    ("Scan_20260301_114022.pdf", build_text_pdf(INVOICE_LINES)),
    ("Scan_20260118_161230.pdf", build_image_only_pdf()),
    ("20251215-Receipt-Example Utilities Ltd-Deposit Refund.pdf", build_text_pdf(RECEIPT_LINES)),
    # Two scans of the same document, byte-identical content.
    ("Scan_20260306_070211.pdf", build_text_pdf(BILL_LINES)),
    ("Scan_20260306_071455.pdf", build_text_pdf(BILL_LINES)),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "inbox")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in FILES:
        (args.out_dir / name).write_bytes(data)
    print(f"wrote {len(FILES)} PDFs to {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
