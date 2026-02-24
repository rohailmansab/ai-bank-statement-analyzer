"""
Step 1: PDF text and table extraction.
Uses pdfplumber for native PDFs; optional OCR (Tesseract) for scanned documents.
"""
import io
from typing import List, Tuple, Optional, Any
import pdfplumber

# Optional OCR: only used when text extraction yields too little content
_OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    pass


def extract_text_and_tables(
    content: bytes,
    max_pages: Optional[int] = None,
    use_ocr_if_needed: bool = True,
    ocr_char_threshold: int = 800,
) -> Tuple[str, List[Any], int, bool]:
    """
    Extract text and tables from PDF.
    Returns: (full_text, list_of_tables_per_page, num_pages, used_ocr).
    If text from first few pages is below ocr_char_threshold, attempts OCR on first page.
    """
    used_ocr = False
    full_text = ""
    all_tables: List[Any] = []
    num_pages = 0

    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            num_pages = len(pdf.pages)
            pages_to_use = pdf.pages[:max_pages] if max_pages else pdf.pages
            for page in pages_to_use:
                text = page.extract_text() or ""
                full_text += text + "\n"
                tables = page.extract_tables()
                all_tables.append(tables or [])
    except Exception as e:
        if "password" in str(e).lower() or "encrypted" in str(e).lower():
            raise ValueError("The PDF appears to be password-protected. Please provide an unlocked copy.")
        raise ValueError(f"PDF could not be opened: {e}") from e

    # Scanned or low-text document: run OCR when text is below threshold (use more pages for large PDFs)
    sample_len = len((full_text or "").strip())
    if use_ocr_if_needed and _OCR_AVAILABLE and sample_len < ocr_char_threshold and num_pages > 0:
        ocr_pages = min(max(3, num_pages // 2), 10)  # 3–10 pages so OCR is used more for multi-page PDFs
        ocr_text = _ocr_first_pages(content, ocr_pages)
        if ocr_text:
            full_text = ocr_text + "\n" + full_text
            used_ocr = True

    return full_text.strip(), all_tables, num_pages, used_ocr


def _ocr_first_pages(content: bytes, num_pages: int) -> str:
    """Run Tesseract OCR on first N pages. Requires pdf2image or PyMuPDF to render PDF to image."""
    out = []
    try:
        # Prefer pdf2image if available (poppler)
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(content, first_page=1, last_page=num_pages, dpi=150)
        except ImportError:
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=content, filetype="pdf")
                images = []
                for i in range(min(num_pages, len(doc))):
                    page = doc[i]
                    pix = page.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    images.append(img)
                doc.close()
            except ImportError:
                return ""
        for img in images:
            out.append(pytesseract.image_to_string(img))
        return "\n".join(out)
    except Exception:
        return ""


def extract_text_only(content: bytes, max_pages: Optional[int] = None) -> str:
    """Convenience: get full text from PDF (with optional OCR fallback)."""
    text, _, _, _ = extract_text_and_tables(content, max_pages=max_pages)
    return text
