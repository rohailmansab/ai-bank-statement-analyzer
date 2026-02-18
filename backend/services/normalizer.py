import pandas as pd
import re
from typing import Optional
from datetime import datetime

class DataNormalizer:
    """
    Production-grade data normalization layer.
    Ensures all parsed data is clean, consistent, and ready for analysis.
    """
    
    @staticmethod
    def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Main normalization pipeline.
        Input: Raw parsed DataFrame
        Output: Clean, validated DataFrame
        """
        if df.empty:
            return df
        
        # Step 1: Normalize column names
        df = DataNormalizer._normalize_columns(df)
        
        # Step 2: Clean amounts (remove commas, convert to float)
        df = DataNormalizer._clean_amounts(df)
        
        # Step 3: Normalize dates
        df = DataNormalizer._normalize_dates(df)
        
        # Step 4: Clean descriptions
        df = DataNormalizer._clean_descriptions(df)
        
        # Step 5: Remove duplicates and junk
        df = DataNormalizer._remove_junk(df)
        
        # Step 6: Fill missing values
        df = DataNormalizer._fill_missing(df)
        
        return df
    
    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Use smart column detection instead of fixed mapping.
        This ensures correct credit/debit identification regardless of column order.
        """
        from .column_detector import SmartColumnDetector
        
        # Detect columns intelligently
        detected = SmartColumnDetector.detect_columns(df)
        
        print(f"[COLUMN DETECTION] Detected mapping: {detected}")
        
        # Create new DataFrame with standard columns
        normalized = pd.DataFrame()
        
        if detected['Date']:
            normalized['Date'] = df[detected['Date']]
        else:
            normalized['Date'] = ''
        
        if detected['Description']:
            normalized['Description'] = df[detected['Description']]
        else:
            normalized['Description'] = ''
        
        if detected['Credit']:
            normalized['Credit'] = df[detected['Credit']]
        else:
            normalized['Credit'] = 0
        
        if detected['Debit']:
            normalized['Debit'] = df[detected['Debit']]
        else:
            normalized['Debit'] = 0
        
        if detected['Balance']:
            normalized['Balance'] = df[detected['Balance']]
        else:
            normalized['Balance'] = 0
        
        return normalized
    
    @staticmethod
    def _clean_amounts(df: pd.DataFrame) -> pd.DataFrame:
        """Remove commas and convert to float safely."""
        for col in ['Credit', 'Debit', 'Balance']:
            if col in df.columns:
                df[col] = df[col].apply(DataNormalizer._safe_float_conversion)
        return df
    
    @staticmethod
    def _safe_float_conversion(value) -> float:
        """Convert any value to float safely."""
        if pd.isna(value) or value == '' or value is None:
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove commas, spaces, currency symbols
        cleaned = str(value).replace(',', '').replace(' ', '').replace('₦', '').replace('NGN', '')
        
        # Handle negative signs
        cleaned = cleaned.replace('(', '-').replace(')', '')
        
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return 0.0
    
    @staticmethod
    def _normalize_dates(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize date formats to YYYY-MM-DD."""
        if 'Date' not in df.columns:
            return df
        
        df['Date'] = df['Date'].apply(DataNormalizer._parse_date)
        
        # Remove rows with invalid dates
        df = df[df['Date'].notna()]
        
        return df
    
    @staticmethod
    def _parse_date(date_value) -> Optional[datetime]:
        """Parse various date formats."""
        if pd.isna(date_value) or date_value == '':
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        date_str = str(date_value).strip()
        
        # Common date formats
        formats = [
            '%d-%b-%Y',      # 02-Sep-2025
            '%d/%m/%Y',      # 02/09/2025
            '%Y-%m-%d',      # 2025-09-02
            '%d-%m-%Y',      # 02-09-2025
            '%d %b %Y',      # 02 Sep 2025
            '%d-%B-%Y',      # 02-September-2025
            '%d/%m/%y',      # 02/09/25
            '%d-%b-%y',      # 02-Sep-25
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except (ValueError, TypeError):
                continue
        
        return None
    
    @staticmethod
    def _clean_descriptions(df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize descriptions."""
        if 'Description' not in df.columns:
            return df
        
        df['Description'] = df['Description'].apply(lambda x: str(x).strip() if pd.notna(x) else 'Transaction')
        
        # Remove multiple spaces
        df['Description'] = df['Description'].str.replace(r'\s+', ' ', regex=True)
        
        return df
    
    @staticmethod
    def _remove_junk(df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows and junk lines."""
        # Remove exact duplicates
        df = df.drop_duplicates()
        
        # Remove rows where description looks like a header
        junk_patterns = [
            r'^date$',
            r'^description$',
            r'^credit$',
            r'^debit$',
            r'^balance$',
            r'^transaction',
            r'^opening balance',
            r'^closing balance',
            r'^total$'
        ]
        
        pattern = '|'.join(junk_patterns)
        df = df[~df['Description'].str.lower().str.match(pattern, na=False)]
        
        return df
    
    @staticmethod
    def _fill_missing(df: pd.DataFrame) -> pd.DataFrame:
        """Fill missing values with safe defaults."""
        df['Credit'] = df['Credit'].fillna(0)
        df['Debit'] = df['Debit'].fillna(0)
        df['Balance'] = df['Balance'].fillna(0)
        df['Description'] = df['Description'].fillna('Transaction')
        
        return df
