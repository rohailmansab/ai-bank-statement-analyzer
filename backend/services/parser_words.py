import pandas as pd
import pdfplumber
import io
import re
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class WordParser(BaseParser):
    """
    Stage 3: Extracts words with coordinates and attempts to reconstruct rows
    based on vertical alignment. Useful when extract_text() returns jumbled results.
    """
    @property
    def parser_id(self) -> str:
        return "word_coordinate_parser"

    def parse(self, content: bytes) -> pd.DataFrame:
        transactions = []
        date_pattern = re.compile(r'\d{2}-[A-Za-z]{3}-\d{4}')
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                words = page.extract_words()
                if not words: continue
                
                # Group words into lines based on their vertical top coordinate
                # We allow a small tolerance for slight misalignments
                lines = {}
                tolerance = 2 
                
                for w in words:
                    y = w['top']
                    # Find if a close enough Y exists
                    found_y = None
                    for existing_y in lines.keys():
                        if abs(existing_y - y) <= tolerance:
                            found_y = existing_y
                            break
                    
                    if found_y is not None:
                        lines[found_y].append(w)
                    else:
                        lines[y] = [w]
                
                # Sort lines by Y coordinate
                sorted_y = sorted(lines.keys())
                
                for y in sorted_y:
                    # Sort words in line by X coordinate
                    line_words = sorted(lines[y], key=lambda x: x['x0'])
                    line_text = " ".join([w['text'] for w in line_words]).strip()
                    
                    # If this line starts with a date, it's a potential transaction
                    if date_pattern.search(line_text):
                        # For word parser, we just collect the line as a basic row
                        # The router or gtbank parser will handle complex merging
                        transactions.append(re.split(r'\s{2,}', line_text))
                        
        if not transactions:
            return pd.DataFrame()
            
        df = pd.DataFrame(transactions)
        return self.standardize_columns(df)
