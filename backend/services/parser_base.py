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
        """Ensures the DataFrame has Date, Description, Credit, Debit columns."""
        required = ['Date', 'Description', 'Credit', 'Debit']
        for col in required:
            if col not in df.columns:
                df[col] = 0.0 if col in ['Credit', 'Debit'] else ""
        
        # Ensure correct order and types
        df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Date'])
        df['Credit'] = pd.to_numeric(df['Credit'], errors='coerce').fillna(0.0)
        df['Debit'] = pd.to_numeric(df['Debit'], errors='coerce').fillna(0.0)
        
        return df[required]
