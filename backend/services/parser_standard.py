import pandas as pd
import pdfplumber
import io
import re
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class StandardParser(BaseParser):
    @property
    def parser_id(self) -> str:
        return "standard"

    def parse(self, content: bytes) -> pd.DataFrame:
        # We handle PDF here, CSV/Excel is already handled by pandas in main parser logic
        # but for consistency, StandardParser will focus on clean PDF tables.
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
                        
                        # Check for date in first two columns
                        if any(re.search(date_pattern, cell) for cell in clean_row[:2]):
                            transactions.append(clean_row)

        if len(transactions) < 2:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)
        return self.map_columns(df)

    def map_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # Heuristic mapping
        cols = list(df.columns)
        mapping = {}
        
        # Date detection
        for i, col in enumerate(cols):
            if any(re.search(r'\d', str(val)) for val in df[col].head(5)):
                mapping['Date'] = col
                break
        
        # Credit/Debit detection (columns with mostly numbers)
        amount_cols = []
        for i, col in enumerate(cols):
            if i == mapping.get('Date'): continue
            vals = df[col].astype(str).str.replace(',', '').str.replace(r'[^\d.]', '', regex=True)
            if pd.to_numeric(vals, errors='coerce').notna().mean() > 0.5:
                amount_cols.append(col)
        
        if len(amount_cols) >= 2:
            mapping['Debit'] = amount_cols[0]
            mapping['Credit'] = amount_cols[1]
        elif len(amount_cols) == 1:
            mapping['Amount'] = amount_cols[0]

        # Description is usually the first non-date, non-amount column
        for i, col in enumerate(cols):
            if col not in mapping.values():
                mapping['Description'] = col
                break

        res_df = pd.DataFrame()
        res_df['Date'] = df[mapping.get('Date', cols[0])]
        res_df['Description'] = df[mapping.get('Description', cols[1] if len(cols)>1 else cols[0])]
        
        if 'Debit' in mapping and 'Credit' in mapping:
            res_df['Debit'] = df[mapping['Debit']].apply(ParserUtils.clean_numeric).abs()
            res_df['Credit'] = df[mapping['Credit']].apply(ParserUtils.clean_numeric)
        elif 'Amount' in mapping:
            amounts = df[mapping['Amount']].apply(ParserUtils.clean_numeric)
            res_df['Credit'] = [a if a > 0 else 0 for a in amounts]
            res_df['Debit'] = [abs(a) if a < 0 else 0 for a in amounts]
        
        return self.standardize_columns(res_df)
