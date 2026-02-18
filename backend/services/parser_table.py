import pandas as pd
import pdfplumber
import io
import re
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class TableParser(BaseParser):
    """
    Stage 1: Traditional table extraction.
    """
    @property
    def parser_id(self) -> str:
        return "table_parser"

    def parse(self, content: bytes) -> pd.DataFrame:
        transactions = []
        date_pattern = r'\d{1,4}[-/]\d{1,4}[-/]\d{1,4}'
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    if not table: continue
                    for row in table:
                        clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                        if not any(clean_row): continue
                        if any(re.search(date_pattern, cell) for cell in clean_row[:2]):
                            transactions.append(clean_row)

        if not transactions:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)
        return self.standardize_columns(df)
