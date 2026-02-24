"""
Bank Statement Parser: orchestrates the multi-step workflow from the design document.
Step 1: PDF text/table extraction (with optional OCR for scanned docs).
Step 2: Identify bank from content and load configuration.
Step 3: Rule-based parsing (key-value + transaction table).
Step 4: Data cleaning and normalization.
Step 5: Output structured JSON (account_holder, account_details, statement_summary, transactions).
"""
import io
from typing import Dict, Any, Tuple, Optional
import pandas as pd

from .pdf_extractor import extract_text_and_tables
from .bank_config import load_all_configs, detect_bank_from_text, get_config, get_bank_config, extract_key_values
from .parser_config_driven import ConfigDrivenParser
from .normalizer import DataNormalizer
from .validator import DataValidator


class BankStatementParser:
    """
    Orchestrates the entire parsing process: extract → identify bank → load config
    → rule-based parse → normalize → validate. Minimal AI dependence for core parsing.
    """

    def __init__(self):
        self._configs = load_all_configs()
        self._config_driven_parser = ConfigDrivenParser(self._configs)
        self._metadata: Dict[str, Any] = {}
        self._used_ocr = False

    def parse(self, content: bytes) -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, Any]]:
        """
        Parse PDF content. Returns (df, validation_report, extraction_metadata).
        Raises ValueError for password-protected or unreadable PDFs.
        """
        # Step 1: Extract text and tables (with OCR fallback for scanned PDFs)
        try:
            full_text, _tables, num_pages, self._used_ocr = extract_text_and_tables(
                content, use_ocr_if_needed=True, ocr_char_threshold=200
            )
        except ValueError as e:
            raise e
        except Exception as e:
            raise ValueError(f"PDF could not be read: {e}") from e

        if not full_text or len(full_text.strip()) < 50:
            raise ValueError(
                "The PDF document appears to be empty or scanned (images only). "
                "Install pytesseract and pdf2image for OCR support."
            )

        # Step 2: Identify bank and load configuration (use extracted text, including OCR)
        bank_id = detect_bank_from_text(full_text[:3000], self._configs)
        config = get_config(bank_id, self._configs)
        self._metadata = extract_key_values(full_text, config)
        self._metadata["detected_bank"] = bank_id

        # Step 3: Rule-based transaction extraction (config-driven parser on PDF bytes)
        df = self._config_driven_parser.parse(content)
        if df.empty:
            return pd.DataFrame(), {"error": "No transaction table found", "confidence": "failed"}, self._metadata

        # Step 4: Data cleaning and normalization
        df = DataNormalizer.normalize_dataframe(df)

        # Step 5: Validation
        is_valid, validation_report = DataValidator.validate(df)
        validation_report["parser_used"] = "bank_statement_parser"
        validation_report["used_ocr"] = self._used_ocr

        return df, validation_report, self._metadata

    @property
    def metadata(self) -> Dict[str, Any]:
        """Key-value extraction: account_number, opening_balance, closing_balance, etc."""
        return self._metadata

    @property
    def used_ocr(self) -> bool:
        return self._used_ocr
