"""Project-wide paths and constants."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PDF_DIR = ROOT / "pdf"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
EXTRACTED_DIR = DATA_DIR / "extracted"
CURATED_DIR = DATA_DIR / "curated"
WEB_DATA_DIR = ROOT / "web" / "public" / "data"

# The single date the source describes (no time dimension, see doc/Plan.md §1).
YEAR = 1594


def source_pdf() -> Path:
    """Return the scan of the Dénombrement in pdf/, which may hold other PDFs (licences) too."""
    pdfs = sorted(p for p in PDF_DIR.glob("*.pdf") if "nombrement" in p.name)  # é may be decomposed
    if len(pdfs) != 1:
        raise FileNotFoundError(f"expected exactly one Dénombrement PDF in {PDF_DIR}, found {len(pdfs)}")
    return pdfs[0]
