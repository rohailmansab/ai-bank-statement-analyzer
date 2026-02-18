import re
import pandas as pd
import pdfplumber
import io
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class TextParser(BaseParser):
    """
    Stage 2: Standard line-by-line text extraction.
    Tries to find transaction lines using patterns without complex state merging.
    """
    @property
    def parser_id(self) -> str:
        return "standard_text_parser"

    def parse(self, content: bytes) -> pd.DataFrame:
        transactions = []
        # Support various date formats
        date_patterns = [
            r'^\d{2}-[A-Za-z]{3}-\d{4}',
            r'^\d{2}/\d{2}/\d{4}',
            r'^\d{4}-\d{2}-\d{2}'
        ]
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue
                
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line: continue
                    
                    if any(re.search(p, line) for p in date_patterns):
                        parts = re.split(r'\s{2,}', line)
                        if len(parts) >= 3:
                            transactions.append(parts)

        if not transactions:
            return pd.DataFrame()
            
        df = pd.DataFrame(transactions)
        return self.standardize_columns(df)
