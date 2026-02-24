from abc import ABC, abstractmethod
import pandas as pd

class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> pd.DataFrame:
        """Parse bytes content into a standardized DataFrame."""
        pass

    @property
    @abstractmethod
    def parser_id(self) -> str:
        """Unique identifier for the parser strategy."""
        pass

    def standardize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensures the DataFrame has Date, Description, Credit, Debit; keeps Balance if present."""
        required = ['Date', 'Description', 'Credit', 'Debit']
        df = df.copy()
        for col in required:
            if col not in df.columns:
                df[col] = 0.0 if col in ['Credit', 'Debit'] else ""
        if 'Balance' not in df.columns:
            df['Balance'] = 0.0
        # Try multiple date formats so fewer rows are dropped (GTBank: 02-Sep- 2025, 30-Jan-2026, 30/01/2026)
        dates = df['Date'].astype(str).str.strip()
        dates = dates.str.replace(r"([A-Za-z]{3})\s+-\s*(\d{4})\s*$", r"\1-\2", regex=True)
        dates = dates.str.replace(r"-\s+(\d{4})\s*$", r"-\1", regex=True)
        out_dt = pd.to_datetime(dates, format='mixed', dayfirst=True, errors='coerce')
        if out_dt.isna().any():
            for fmt in ('%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d %b %Y', '%d-%m-%Y'):
                miss = out_dt.isna()
                if not miss.any():
                    break
                try:
                    parsed = pd.to_datetime(dates[miss], format=fmt, errors='coerce')
                    out_dt = out_dt.fillna(parsed)
                except (TypeError, ValueError):
                    continue
        df['Date'] = out_dt
        df = df.dropna(subset=['Date'])
        df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0.0)
        df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0.0)
        df['Balance'] = pd.to_numeric(df['Balance'], errors='coerce').fillna(0.0)
        out_cols = required + ['Balance'] if 'Balance' in df.columns else required
        return df[[c for c in out_cols if c in df.columns]]
