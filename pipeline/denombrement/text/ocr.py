"""Tesseract: a second reading of single lines where the scan's text layer is garbled."""
from __future__ import annotations

import pymupdf
import pytesseract
from PIL import Image

DPI = 300


def read_line(page: pymupdf.Page, bbox: tuple[float, float, float, float]) -> str:
    """OCR one text line of a page (French model, single-line mode)."""
    x0, y0, x1, y1 = bbox
    clip = pymupdf.Rect(x0 - 6, y0 - 5, x1 + 10, y1 + 5) & page.rect
    pix = page.get_pixmap(dpi=DPI, clip=clip)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    for psm in (7, 6):  # single line; a block when the line mode finds nothing
        text = pytesseract.image_to_string(img, lang="fra", config=f"--psm {psm}").strip()
        if text:
            return " ".join(text.split())
    return ""
