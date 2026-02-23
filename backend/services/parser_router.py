import pandas as pd
import io
import os
import json
from typing import List, Dict, Any, Tuple
from .parser_base import BaseParser
from .parser_table import TableParser
from .parser_text import TextParser, parse_transactions_from_text
from .parser_words import WordParser
from .parser_gtbank import MultilineParser
from .parser_summary import SummaryTableParser
from .parser_config_driven import ConfigDrivenParser
from .normalizer import DataNormalizer
from .ai_core import AICore, BankDetector
from .ai_prompts import PROMPT_TRANSACTION_EXTRACTION
from .pdf_extractor import extract_text_via_ocr, extract_text_only
from .bank_config import detect_bank_from_text, load_all_configs
from backend.config import OPENAI_API_KEY, GEMINI_API_KEY


def _build_report_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """Build validation report from df without calling DataValidator (avoids max_credit bug)."""
    # Ensure columns exist
    if "Credit" not in df.columns:
        df["Credit"] = 0.0
    if "Debit" not in df.columns:
        df["Debit"] = 0.0

    report = {
        "total_transactions": len(df),
        "total_credit": float(df["Credit"].sum()) if not df["Credit"].empty else 0.0,
        "total_debit": float(df["Debit"].sum()) if not df["Debit"].empty else 0.0,
        "date_range": None,
        "months_found": 0,
        "issues": [],
        "confidence": "high",
    }
    if "Date" in df.columns:
        try:
            d = pd.to_datetime(df["Date"], errors="coerce").dropna()
            if not d.empty:
                report["date_range"] = {"start": d.min().strftime("%Y-%m-%d"), "end": d.max().strftime("%Y-%m-%d")}
                report["months_found"] = int(d.dt.to_period("M").nunique())
        except Exception:
            pass
    return report


# Reject results that look like a summary (few rows) so we try AI fallback for full transaction list
MIN_ACCEPTABLE_TRANSACTIONS = 10


class ParserRouter:
    """
    Multi-step pipeline per robust bank statement design:
    Step 1: Text/table extraction (pdfplumber; optional OCR for scanned PDFs).
    Step 2: Rule-based parsing with config-driven bank formats first, then heuristics.
    Step 3: Targeted AI only for categorization (not full-doc extraction in normal path).
    Step 4: AI full-doc extraction only as last resort when all parsers fail.
    """
    def __init__(self):
        configs = load_all_configs()
        # Config-driven parser first (bank detection + config-guided extraction)
        self.parsers: List[BaseParser] = [
            ConfigDrivenParser(configs),
            SummaryTableParser(),
            TableParser(),
            TextParser(),
            WordParser(),
            MultilineParser(),
        ]
        self.logs = []
        self.used_parser = "none"
        self.validation_report = {}
        self._config_driven_metadata: Dict[str, Any] = {}
        self.ai = AICore()
        self.bank_detector = BankDetector(self.ai)
        self.detected_bank = "other"

    async def parse(self, content: bytes, filename: str, extension: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Production-grade parsing with EXTRACTION → NORMALIZATION → report build.
        Returns: (DataFrame, validation_report). Report built here to avoid validator max_credit bug.
        """
        extension = extension.lower()
        
        # Fast path for non-PDF
        if extension in ['.csv', '.xlsx', '.xls']:
            try:
                if extension == '.csv':
                    df = pd.read_csv(io.BytesIO(content))
                else:
                    df = pd.read_excel(io.BytesIO(content))
                self.used_parser = f"standard_{extension[1:]}"
                self.logs.append(f"Successfully parsed {extension} file")
                
                # NORMALIZATION
                df = DataNormalizer.normalize_dataframe(df)
                
                # REPORT (no validator call - avoids max_credit bug)
                self.validation_report = _build_report_from_df(df)
                self.validation_report["parser_used"] = self.used_parser
                
                return df, self.validation_report
            except Exception as e:
                self.logs.append(f"Direct {extension} parse failed: {str(e)}")
        
        # PDF No-Fail Extraction Pipeline
        if extension == '.pdf':
            # Verification: Does the PDF have ANY content?
            import pdfplumber
            has_content = False
            sample_text = ""
            total_words = 0
            
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                num_pages = len(pdf.pages)
                # Check first page only for speed; enough to detect empty/scanned PDFs
                page = pdf.pages[0]
                text = page.extract_text() or ""
                words = page.extract_words() or []
                total_words = len(words)
                if text:
                    sample_text = text[:500].replace('\n', ' ')
                has_content = len(text.strip()) > 10 or len(words) > 3
            
            if not has_content:
                # Step 1 (scanned PDFs): optional OCR then parse from text
                self.logs.append("No text in PDF; attempting OCR for scanned document.")
                ocr_text = extract_text_via_ocr(content)
                if ocr_text and len(ocr_text.strip()) > 50:
                    df = parse_transactions_from_text(ocr_text)
                    if not df.empty:
                        df = DataNormalizer.normalize_dataframe(df)
                        self.validation_report = _build_report_from_df(df)
                        self.validation_report["parser_used"] = "ocr_text_parser"
                        self.used_parser = "ocr_text_parser"
                        self.logs.append("Parsed transactions from OCR text.")
                        return df, self.validation_report
                msg = f"No text found in PDF. Sample: {sample_text}" if sample_text else "The PDF document appears to be empty or scanned (images only). Install pytesseract and pdf2image for OCR support."
                raise ValueError(msg)

            # Run through parsers with validation (config-driven first, then heuristics)
            for parser in self.parsers:
                df_parsed = None
                try:
                    df_parsed = parser.parse(content)
                    if df_parsed is None or df_parsed.empty or len(df_parsed) < 1:
                        self.logs.append(f"Parser {parser.parser_id} returned 0 results")
                        continue
                    df = df_parsed
                    # Capture config-driven metadata (bank, key-values) when applicable
                    if isinstance(parser, ConfigDrivenParser):
                        self._config_driven_metadata = getattr(parser, "metadata", {}) or {}
                        self.detected_bank = self._config_driven_metadata.get("detected_bank", "other")
                    # NORMALIZATION
                    df = DataNormalizer.normalize_dataframe(df)
                    # REPORT (no validator call - avoids max_credit bug)
                    self.validation_report = _build_report_from_df(df)
                    self.validation_report["parser_used"] = parser.parser_id
                    # Retry with next parser only if report looks bad
                    r = self.validation_report
                    if r.get("confidence") == "low" or (r.get("total_credit", 0) == 0 and r.get("total_debit", 0) == 0) or r.get("months_found", 0) == 0:
                        self.logs.append(f"Parser {parser.parser_id} report weak, trying next parser")
                        continue
                    # Summary-table parser often returns only a few rows (one per month); prefer full transaction parsers
                    if parser.parser_id == "summary_table_parser" and r.get("total_transactions", 0) < 8:
                        self.logs.append(f"Parser {parser.parser_id} returned only {r.get('total_transactions')} rows (likely summary), trying next parser")
                        continue
                    # Reject any result with too few transactions so endpoint can try AI fallback
                    if r.get("total_transactions", 0) < MIN_ACCEPTABLE_TRANSACTIONS:
                        self.logs.append(f"Parser {parser.parser_id} returned only {r.get('total_transactions')} transactions (min {MIN_ACCEPTABLE_TRANSACTIONS}), trying next or AI fallback")
                        continue
                    # Success
                    self.used_parser = parser.parser_id
                    self.logs.append(f"Successfully used {parser.parser_id}")
                    if self.detected_bank == "other":
                        header = extract_text_only(content, max_pages=1)
                        self.detected_bank = detect_bank_from_text(header)
                    return df, self.validation_report
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    self.logs.append(f"Parser {parser.parser_id} attempt failed: {str(e)}")

        # If we reached here, everything failed
        summary = ". ".join(self.logs)
        self.validation_report = {
            "error": summary,
            "confidence": "failed",
            "parser_used": "none"
        }
        return pd.DataFrame(), self.validation_report


    async def parse_with_ai(self, content: bytes) -> pd.DataFrame:
        import pdfplumber
        text = ""
        header_text = ""
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            header_text = pdf.pages[0].extract_text() or ""
            total_pages = len(pdf.pages)
            pages_to_extract = min(total_pages, 15)
            for page in pdf.pages[:pages_to_extract]:
                text += (page.extract_text() or "") + "\n"
        if len(text.strip()) < 100:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages[:pages_to_extract]:
                    words = page.extract_words()
                    text += " ".join([w['text'] for w in words]) + "\n"

        self.detected_bank = await self.bank_detector.detect_bank(header_text)
        self.logs.append(f"Detected bank: {self.detected_bank}")
        max_chars = 40000
        df_list = await self.ai.extract_json(text[:max_chars], PROMPT_TRANSACTION_EXTRACTION)
        
        if df_list:
            df = pd.DataFrame(df_list)
            # Normalize column names to match system expectations
            column_mapping = {
                'date': 'Date',
                'description': 'Description',
                'credit': 'Credit',
                'debit': 'Debit',
                'balance': 'Balance'
            }
            df = df.rename(columns=column_mapping)
            self.logs.append("Successfully extracted via Universal AI Prompt")
            return df

        return pd.DataFrame()

    @property
    def status(self) -> Dict[str, Any]:
        return {
            "status": "success" if self.used_parser != "none" else "failed",
            "parser_used": self.used_parser,
            "diagnostic_logs": self.logs
        }