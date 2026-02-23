"""
Step 1: Text and table extraction from PDF.
Uses pdfplumber for native PDFs; optional OCR (pytesseract) for scanned documents.
"""
import io
from typing import Tuple, Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    from .parser_exceptions import PasswordProtectedPDFError
except ImportError:
    PasswordProtectedPDFError = Exception  # fallback if module not yet loaded


def extract_text_and_tables(content: bytes) -> Tuple[str, list]:
    """
    Extract full text and list of tables from PDF using pdfplumber.
    Returns (full_text, list of tables per page; each table is list of rows).
    Raises PasswordProtectedPDFError if PDF is password-protected.
    """
    if not pdfplumber:
        return "", []
    try:
        text_parts = []
        all_tables = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                text_parts.append(t)
                tables = page.extract_tables() or []
                all_tables.extend(tables)
        return "\n".join(text_parts), all_tables
    except Exception as e:
        err_msg = str(e).lower()
        if "password" in err_msg or "encrypted" in err_msg or "decrypt" in err_msg:
            raise PasswordProtectedPDFError(f"PDF is password-protected: {e}") from e
        raise


def extract_text_only(content: bytes, max_pages: Optional[int] = None) -> str:
    """Extract text from PDF (for bank detection and key-value regex). Raises PasswordProtectedPDFError if encrypted."""
    if not pdfplumber:
        return ""
    try:
        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = pdf.pages[:max_pages] if max_pages else pdf.pages
            for page in pages:
                text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as e:
        err_msg = str(e).lower()
        if "password" in err_msg or "encrypted" in err_msg or "decrypt" in err_msg:
            raise PasswordProtectedPDFError(f"PDF is password-protected: {e}") from e
        raise


def get_word_count(content: bytes, max_pages: int = 5) -> int:
    """Total word count on first max_pages (used to detect empty/scanned PDFs)."""
    if not pdfplumber:
        return 0
    total = 0
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages[:max_pages]:
            words = page.extract_words() or []
            total += len(words)
    return total


def is_likely_scanned(content: bytes, min_text_chars: int = 100, max_pages_check: int = 3) -> bool:
    """True if PDF has very little extractable text (likely scanned/image-only)."""
    text = extract_text_only(content, max_pages=max_pages_check)
    return len(text.strip()) < min_text_chars


def extract_text_via_ocr(content: bytes, max_pages: int = 5) -> Optional[str]:
    """
    For scanned PDFs: render pages to images and run Tesseract OCR.
    Requires: pip install pytesseract pdf2image (and Tesseract installed on system).
    Returns None if OCR not available or fails.
    """
    try:
        import pytesseract
    except ImportError:
        print("[PDF EXTRACTOR] pytesseract not installed; OCR skipped.")
        return None
    try:
        from pdf2image import convert_from_bytes
    except ImportError:
        print("[PDF EXTRACTOR] pdf2image not installed; OCR skipped.")
        return None

    try:
        images = convert_from_bytes(content, first_page=1, last_page=max_pages)
        text_parts = []
        for img in images:
            text_parts.append(pytesseract.image_to_string(img))
        return "\n".join(text_parts) if text_parts else None
    except Exception as e:
        print(f"[PDF EXTRACTOR] OCR failed: {e}")
        return None
