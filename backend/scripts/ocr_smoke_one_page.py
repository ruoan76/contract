#!/usr/bin/env python3
"""单页 OCR 冒烟（不经过 HTTP）。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ai_review.ocr import ocr_pdf_pages


def main() -> None:
    pdf = sys.argv[1] if len(sys.argv) > 1 else ""
    if not pdf:
        print("usage: ocr_smoke_one_page.py <pdf>")
        sys.exit(1)
    import fitz

    doc = fitz.open(pdf)
    tmp = Path("/tmp/ocr_smoke_one.pdf")
    d2 = fitz.open()
    d2.insert_pdf(doc, from_page=0, to_page=0)
    d2.save(str(tmp))
    d2.close()
    doc.close()
    pages = ocr_pdf_pages(tmp, max_pages=1)
    print("chars", len("\n".join(pages)))
    print(pages[0][:300] if pages else "(empty)")


if __name__ == "__main__":
    main()
