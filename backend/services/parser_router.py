import pandas as pd
import io
import os
import json
import openai
from google import genai
from typing import List, Dict, Any, Tuple
from .parser_base import BaseParser
from .parser_table import TableParser
from .parser_text import TextParser
from .parser_words import WordParser
from .parser_gtbank import MultilineParser
from .parser_summary import SummaryTableParser
from .normalizer import DataNormalizer
from .validator import DataValidator
from .ai_core import AICore, BankDetector
from .ai_prompts import PROMPT_TRANSACTION_EXTRACTION
from backend.config import OPENAI_API_KEY, GEMINI_API_KEY

class ParserRouter:
    def __init__(self):
        # The 6-stage fallback sequence
        self.parsers: List[BaseParser] = [
            SummaryTableParser(),  # Handle monthly summary tables first
            TableParser(),
            TextParser(),
            WordParser(),
            MultilineParser()
        ]
        self.logs = []
        self.used_parser = "none"
        self.validation_report = {}
        self.ai = AICore()
        self.bank_detector = BankDetector(self.ai)
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
        
        # PDF No-Fail Extraction Pipeline
        if extension == '.pdf':
            # Verification: Does the PDF have ANY content?
            import pdfplumber
            has_content = False
            sample_text = ""
            total_words = 0
            
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                print(f"\n[PDF DIAGNOSTICS] Total Pages: {len(pdf.pages)}")
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
                msg = f"No text found in PDF. Sample: {sample_text}" if sample_text else "The PDF document appears to be empty or scanned (images only)."
                raise ValueError(msg)

            # Run through parsers with validation
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
                    
                    # Check if we should retry with next parser
                    if DataValidator.should_retry_extraction(self.validation_report):
                        self.logs.append(f"Parser {parser.parser_id} validation failed, trying next parser")
                        continue
                    
                    # Success!
                    self.used_parser = parser.parser_id
                    self.logs.append(f"Successfully used {parser.parser_id}")
                    return df, self.validation_report
                    
                except Exception as e:
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

