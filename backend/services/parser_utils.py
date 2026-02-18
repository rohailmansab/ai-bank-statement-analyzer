import re
import pandas as pd
from datetime import datetime

class ParserUtils:
    @staticmethod
    def clean_numeric(val):
        """Robustly convert strings with currency symbols, commas, and parentheses to floats."""
        if pd.isna(val) or val == "":
            return 0.0
        try:
            # Remove currency symbols and non-numeric chars except . and -
            clean_val = re.sub(r'[^\d.-]', '', str(val).replace(',', ''))
            
            # Handle cases like "100.00CR" or "100.00DR"
            val_lower = str(val).lower()
            if 'dr' in val_lower or 'debit' in val_lower:
                return -abs(float(clean_val))
            
            # Handle (1,000) for negative numbers
            if str(val).strip().startswith('(') and str(val).strip().endswith(')'):
                return -abs(float(clean_val))
                
            return float(clean_val)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def normalize_date(date_str):
        """Standardize various date formats to YYYY-MM-DD."""
        if not date_str or not isinstance(date_str, str):
            return None
            
        date_patterns = [
            '%d-%b-%Y', '%d-%B-%Y', '%Y-%m-%d', '%d/%m/%Y', 
            '%m/%d/%Y', '%d-%m-%Y', '%b %d %Y', '%B %d %Y'
        ]
        
        # Clean the string first
        clean_date = date_str.strip().replace(',', '')
        
        for pattern in date_patterns:
            try:
                return datetime.strptime(clean_date, pattern).strftime('%Y-%m-%d')
            except ValueError:
                continue
        return None
