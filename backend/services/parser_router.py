import pandas as pd
import io
import os
import json
from typing import List, Dict, Any, Tuple
from .parser_base import BaseParser
from .parser_table import TableParser
from .parser_text import TextParser
from .parser_words import WordParser
from .parser_gtbank import MultilineParser
from .parser_summary import SummaryTableParser
from .parser_config_driven import ConfigDrivenParser
from .normalizer import DataNormalizer
from .validator import DataValidator
from .bank_config import load_all_configs, detect_bank_from_text
from .ai_core import AICore, BankDetector
from .ai_prompts import PROMPT_TRANSACTION_EXTRACTION
from backend.config import USE_AI

class ParserRouter:
    def __init__(self):
        self._configs = load_all_configs()
        # Config-driven first (GTBank etc, merges all pages); then table/summary/text/word/gtbank
        self.parsers: List[BaseParser] = [
            ConfigDrivenParser(self._configs),
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
        self._header_text = ""
        self.ai = AICore() if USE_AI else None
        self.bank_detector = BankDetector(self.ai) if self.ai else None
        self.detected_bank = "other"

    async def parse(self, content: bytes, filename: str, extension: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Production-grade parsing with EXTRACTION → NORMALIZATION → VALIDATION pipeline.
        Returns: (DataFrame, validation_report)
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
                
                # VALIDATION
                is_valid, self.validation_report = DataValidator.validate(df)
                self.validation_report["parser_used"] = self.used_parser
                
                return df, self.validation_report
            except Exception as e:
                self.logs.append(f"Direct {extension} parse failed: {str(e)}")
        
        # PDF No-Fail Extraction Pipeline (Step 1: text/table extraction; optional OCR for scanned)
        if extension == '.pdf':
            import pdfplumber
            has_content = False
            sample_text = ""
            total_words = 0
            num_pages = 0

            try:
                pdf_file = pdfplumber.open(io.BytesIO(content))
            except Exception as e:
                err = str(e).lower()
                if "password" in err or "encrypted" in err:
                    raise ValueError("The PDF appears to be password-protected. Please provide an unlocked copy.")
                raise ValueError(f"PDF could not be opened: {e}") from e

            with pdf_file as pdf:
                num_pages = len(pdf.pages)
                self._header_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
                print(f"\n[PDF DIAGNOSTICS] Total Pages: {num_pages}")
                for page_num, page in enumerate(pdf.pages[:3]): # Check first few pages
                    text = page.extract_text() or ""
                    words = page.extract_words() or []
                    total_words += len(words)
                    
                    if not sample_text and text:
                        sample_text = text[:500].replace('\n', ' ')
                    
                    print(f"[PDF DIAGNOSTICS] Page {page_num+1}: {len(text)} chars, {len(words)} words")
                    
                    if len(text.strip()) > 10 or len(words) > 3:
                        has_content = True
            
            print(f"[PDF DIAGNOSTICS] Total words across pages: {total_words}")
            print(f"[PDF DIAGNOSTICS] Sample text: {sample_text[:200]}")
            
            if not has_content:
                try:
                    from .pdf_extractor import extract_text_and_tables
                    _ocr_text, _, _, _ = extract_text_and_tables(
                        content, max_pages=3, use_ocr_if_needed=True, ocr_char_threshold=100
                    )
                    if _ocr_text and len(_ocr_text.strip()) > 100:
                        has_content = True
                        sample_text = _ocr_text[:500]
                        self.logs.append("OCR (Tesseract) recovered text from scanned PDF")
                except Exception:
                    pass
                if not has_content:
                    msg = f"No text found in PDF. Sample: {sample_text}" if sample_text else "The PDF appears empty or scanned. Install pytesseract and pdf2image for OCR."
                    raise ValueError(msg)

            # Run through parsers with validation; keep best available if all fail strict checks
            best_df = None
            best_report = None
            best_parser = None
            best_parser_id = None

            for parser in self.parsers:
                try:
                    df = parser.parse(content)
                    if df.empty or len(df) < 1:
                        self.logs.append(f"Parser {parser.parser_id} returned 0 results")
                        continue
                    
                    # NORMALIZATION
                    df = DataNormalizer.normalize_dataframe(df)
                    
                    # VALIDATION
                    is_valid, self.validation_report = DataValidator.validate(df)
                    self.validation_report["parser_used"] = parser.parser_id
                    total_tx = self.validation_report.get("total_transactions", 0)
                    total_credit = self.validation_report.get("total_credit", 0) or 0
                    total_debit = self.validation_report.get("total_debit", 0) or 0

                    # Keep best so far: most rows with some amounts
                    if total_tx >= 1 and (total_credit > 0 or total_debit > 0):
                        if best_df is None or len(best_df) < len(df):
                            best_df = df
                            best_report = dict(self.validation_report)
                            best_parser = parser
                            best_parser_id = parser.parser_id
                    
                    # Check if we should retry with next parser
                    if DataValidator.should_retry_extraction(self.validation_report):
                        self.logs.append(f"Parser {parser.parser_id} validation failed, trying next parser")
                        continue
                    # For multi-page PDFs: accept if we have at least ~half tx per page or 10+ tx
                    min_tx_for_pages = max(10, num_pages // 2) if num_pages > 5 else 1
                    if num_pages > 5 and total_tx < min_tx_for_pages:
                        self.logs.append(
                            f"Parser {parser.parser_id} returned only {total_tx} transactions for {num_pages} pages (need ~{min_tx_for_pages}+), trying next parser"
                        )
                        continue
                    
                    # Success!
                    self.used_parser = parser.parser_id
                    if hasattr(parser, "metadata") and getattr(parser, "metadata", None):
                        self._config_driven_metadata = parser.metadata
                        self.detected_bank = self._config_driven_metadata.get("detected_bank", "other")
                    if not USE_AI and self._header_text:
                        self.detected_bank = detect_bank_from_text(self._header_text, self._configs)
                    self.logs.append(f"Successfully used {parser.parser_id}")
                    return df, self.validation_report
                    
                except Exception as e:
                    self.logs.append(f"Parser {parser.parser_id} attempt failed: {str(e)}")

            # Best-available fallback: use the best result we got from any parser
            if best_df is not None and not best_df.empty:
                self.used_parser = best_parser_id or "best_available"
                self.validation_report = best_report or {}
                self.validation_report["parser_used"] = self.used_parser
                self.validation_report["confidence"] = self.validation_report.get("confidence", "medium")
                if best_parser and hasattr(best_parser, "metadata") and getattr(best_parser, "metadata", None):
                    self._config_driven_metadata = best_parser.metadata
                    self.detected_bank = self._config_driven_metadata.get("detected_bank", "other")
                if not USE_AI and self._header_text:
                    self.detected_bank = detect_bank_from_text(self._header_text, self._configs)
                self.logs.append(f"Using best available result from {best_parser_id} ({len(best_df)} transactions)")
                return best_df, self.validation_report

            # If we reached here, no parser returned usable data
            summary = ". ".join(self.logs)
            self.validation_report = {
                "error": summary,
                "confidence": "failed",
                "parser_used": "none"
            }
            return pd.DataFrame(), self.validation_report


    async def parse_with_ai(self, content: bytes) -> pd.DataFrame:
        if not self.ai:
            return pd.DataFrame()
        import pdfplumber
        text = ""
        header_text = ""
        
        print("[AI FALLBACK] Starting AI-powered extraction...")
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            # Get header for bank detection
            header_text = pdf.pages[0].extract_text() or ""
            
            # Extract main text (increase limit to 20 pages)
            total_pages = len(pdf.pages)
            pages_to_extract = min(total_pages, 20)
            print(f"[AI FALLBACK] Extracting text from {pages_to_extract} of {total_pages} pages...")
            
            for page in pdf.pages[:pages_to_extract]:
                text += (page.extract_text() or "") + "\n"
        
        if len(text.strip()) < 100:
            # Fallback for scanned/complex PDFs
            print("[AI FALLBACK] Text extraction poor, trying word-based fallback...")
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages[:pages_to_extract]:
                    words = page.extract_words()
                    text += " ".join([w['text'] for w in words]) + "\n"

        # Step 1: Detect Bank
        self.detected_bank = await self.bank_detector.detect_bank(header_text)
        self.logs.append(f"Detected bank: {self.detected_bank}")
        print(f"[AI FALLBACK] Detected Bank: {self.detected_bank}")

        # Step 2: Use Universal Extraction Prompt (Increase limit to 50k chars)
        max_chars = 50000
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

