import re
import pandas as pd
import pdfplumber
import io
from .parser_base import BaseParser
from .parser_utils import ParserUtils

class SummaryTableParser(BaseParser):
    """
    Specialized parser for monthly summary tables in format:
    MONTH    INCOME    EXPENSES
    MARCH    5,652,950.00    2,091,149.20
    """
    @property
    def parser_id(self) -> str:
        return "summary_table_parser"

    def parse(self, content: bytes) -> pd.DataFrame:
        transactions = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                
                # Look for month names followed by amounts
                month_pattern = re.compile(
                    r'(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+'
                    r'([\d,]+\.?\d*)\s+'
                    r'([\d,]+\.?\d*)',
                    re.IGNORECASE
                )
                
                for match in month_pattern.finditer(text):
                    month = match.group(1).capitalize()
                    income = ParserUtils.clean_numeric(match.group(2))
                    expenses = ParserUtils.clean_numeric(match.group(3))
                    
                    # Create a synthetic transaction for each month
                    transactions.append({
                        'Date': f'01-{month[:3]}-2024',  # Use first day of month
                        'Description': f'{month} Monthly Summary',
                        'Credit': income,
                        'Debit': expenses,
                        'Balance': income - expenses
                    })
        
        if not transactions:
            return pd.DataFrame()
        
        df = pd.DataFrame(transactions)
        return self.standardize_columns(df)
