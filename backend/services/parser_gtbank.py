import re
import pandas as pd
import pdfplumber
import io
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class MultilineParser(BaseParser):
    """
    Stage 4: Specialized parser for GTBank and complex multiline layouts.
    Uses a robust state-machine to detect transaction starts via Date regex
    and merges all subsequent lines until the next date is found.
    """
    @property
    def parser_id(self) -> str:
        return "gtbank_parser"

    def parse(self, content: bytes) -> pd.DataFrame:
        transactions = []
        # Detection regex: Expanded to support more date formats
        date_pattern = re.compile(r'(\d{1,2}[-/ ]?[A-Za-z]{3,9}[-/ ]?\d{2,4}|\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2} [A-Za-z]{3} \d{4})', re.IGNORECASE)
        amount_pattern = re.compile(r'^-?\d{1,3}(?:,\d{3})*(?:\.\d{2})$')
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                print(f"[DEBUG] Page {page_num+1} Words Found: {len(words)}")
                if not words: continue
                
                # Fuzzy grouping into lines (bucket by 2.5 pixels for better robustness)
                lines_buckets = {}
                for w in words:
                    bucket = int(w['top'] // 2.5) * 2.5
                    if bucket not in lines_buckets: lines_buckets[bucket] = []
                    lines_buckets[bucket].append(w)
                
                sorted_buckets = sorted(lines_buckets.keys())
                current_tx = None
                
                for bucket in sorted_buckets:
                    line_words = sorted(lines_buckets[bucket], key=lambda x: x['x0'])
                    # Context for date searching
                    start_text = " ".join([w['text'] for w in line_words[:4]])
                    match = date_pattern.search(start_text)
                    
                    if match:
                        if current_tx:
                            transactions.append(self._finalize_tx(current_tx))
                        
                        tx_date = match.group(1)
                        current_tx = {
                            'Date': tx_date,
                            'Fragments': [],
                            'Debit': 0.0,
                            'Credit': 0.0,
                            'Balance': 0.0
                        }
                        
                        for w in line_words:
                            text = w['text'].strip()
                            if amount_pattern.match(text):
                                val = ParserUtils.clean_numeric(text)
                                rel_x = w['x0'] / page.width
                                
                                # Refined GTBank Heuristic Based on Diagnostics:
                                # Outflow (Debit) is usually < 0.48
                                # Inflow (Credit) is usually between 0.48 - 0.72
                                # Balance is usually > 0.72
                                if 0.3 <= rel_x < 0.48:
                                    current_tx['Debit'] = abs(val)
                                elif 0.48 <= rel_x < 0.72:
                                    current_tx['Credit'] = val
                                elif rel_x >= 0.72:
                                    current_tx['Balance'] = val
                            elif not date_pattern.match(text) and len(text) > 1:
                                current_tx['Fragments'].append(text)
                                
                    elif current_tx:
                        # continuation text or amounts
                        for w in line_words:
                            text = w['text'].strip()
                            if amount_pattern.match(text) and current_tx['Balance'] == 0:
                                val = ParserUtils.clean_numeric(text)
                                rel_x = w['x0'] / page.width
                                if 0.3 <= rel_x < 0.55: current_tx['Debit'] = abs(val)
                                elif 0.55 <= rel_x < 0.78: current_tx['Credit'] = val
                                elif rel_x >= 0.78: current_tx['Balance'] = val
                            else:
                                if len(text) > 1:
                                    current_tx['Fragments'].append(text)

                if current_tx:
                    transactions.append(self._finalize_tx(current_tx))

        if not transactions:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)
        return self.standardize_columns(df)

    def _finalize_tx(self, tx):
        description = " ".join(tx['Fragments']).strip()
        description = re.sub(r'\s{2,}', ' ', description)
        
        # Accept transaction even if amounts are missing (better than nothing)
        return {
            'Date': tx['Date'],
            'Description': description if description else "Transaction",
            'Debit': tx['Debit'],
            'Credit': tx['Credit'],
            'Balance': tx['Balance']
        }

