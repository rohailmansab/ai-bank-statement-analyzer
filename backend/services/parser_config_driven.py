"""
Config-driven parser: uses bank format JSON for key-value extraction and
table column mapping. Minimal AI; rule-based and heuristics first.
"""
import re
import pandas as pd
import pdfplumber
import io
from typing import Dict, Any, List, Optional
from .parser_base import BaseParser
from .parser_utils import ParserUtils
from .bank_config import load_all_configs, detect_bank_from_text, get_config, extract_key_values


class ConfigDrivenParser(BaseParser):
    """
    Step 2 (rule-based) in the multi-step workflow.
    Extracts text/tables via pdfplumber, then applies config for key-value
    extraction and table header -> standard field mapping.
    """

    def __init__(self, configs: Optional[Dict[str, Dict[str, Any]]] = None):
        self._configs = configs or load_all_configs()
        self._metadata: Dict[str, Any] = {}

    @property
    def parser_id(self) -> str:
        return "config_driven"

    @property
    def metadata(self) -> Dict[str, Any]:
        """Key-value extras: account_number, opening_balance, closing_balance, statement_period."""
        return self._metadata

    def parse(self, content: bytes) -> pd.DataFrame:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            header_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

        bank_id = detect_bank_from_text(header_text, self._configs)
        config = get_config(bank_id, self._configs)

        # Key-value extraction (account number, balances, period)
        self._metadata = extract_key_values(full_text, config)
        self._metadata["detected_bank"] = bank_id

        # Transaction table: try tables first, then fallback to text/line parsing
        df = self._extract_transaction_table(content, config)
        if df is not None and not df.empty:
            df = self._apply_column_mapping(df, config)
            return self.standardize_columns(df)
        return pd.DataFrame()

    def _extract_transaction_table(self, content: bytes, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Extract main transaction table from PDF using pdfplumber tables."""
        date_pattern = re.compile(
            r"\d{1,2}[-/\s]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2})[-/\s]\d{2,4}",
            re.IGNORECASE,
        )
        data_frames: List[pd.DataFrame] = []

        def make_unique_columns(names: List[str]) -> List[str]:
            """Ensure no duplicate column names to avoid pandas Reindexing errors."""
            seen = {}
            out = []
            for i, n in enumerate(names):
                key = (n or "").strip() or f"Col{i}"
                if key in seen:
                    seen[key] += 1
                    out.append(f"{key}_{seen[key]}")
                else:
                    seen[key] = 0
                    out.append(key)
            return out

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables or []:
                    if not table or len(table) < 2:
                        continue
                    raw_headers = [str(h).strip() if h is not None else f"Col{i}" for i, h in enumerate(table[0])]
                    data_rows = []
                    for row in table[1:]:
                        clean_row = [str(c).strip() if c is not None else "" for c in row]
                        if not any(clean_row):
                            continue
                        # Check first 5 columns so we catch tables where Date is column 4 or 5 (e.g. GTBank iBank)
                        if any(date_pattern.search(c) for c in clean_row[:5]):
                            data_rows.append(clean_row)
                    if not data_rows:
                        continue
                    max_cols = max(len(r) for r in data_rows)
                    headers = make_unique_columns(
                        raw_headers if len(raw_headers) >= max_cols else raw_headers + [f"Col{i}" for i in range(len(raw_headers), max_cols)]
                    )
                    df_page = pd.DataFrame(data_rows, columns=headers[:max_cols])
                    data_frames.append(df_page)

        if not data_frames:
            return None
        # If multiple tables (e.g. summary + transaction table), prefer the one with most rows (main transaction table)
        if len(data_frames) > 1:
            data_frames = [max(data_frames, key=len)]
        combined = pd.concat(data_frames, ignore_index=True)
        # Ensure no duplicate columns after concat (different tables may have different column sets)
        if combined.columns.duplicated().any():
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    def _apply_column_mapping(self, df: pd.DataFrame, config: Dict[str, Any]) -> pd.DataFrame:
        """Map table columns to Date, Description, Credit, Debit, Balance using config or heuristics."""
        mapping = config.get("table_column_mapping") or {}
        col_lower_to_original = {str(c).lower().strip(): c for c in df.columns}

        def find_source_column(std_name: str, possible_headers: List[str]):
            # Collect all candidate columns that map to this standard name (no duplicates)
            seen: set = set()
            candidates: List[Any] = []
            for raw_header, mapped in mapping.items():
                if str(mapped).strip() != std_name:
                    continue
                r = raw_header.lower().strip()
                if r in col_lower_to_original:
                    c = col_lower_to_original[r]
                    if c not in seen:
                        seen.add(c)
                        candidates.append(c)
                else:
                    for orig in df.columns:
                        if r in str(orig).lower():
                            if orig not in seen:
                                seen.add(orig)
                                candidates.append(orig)
                            break
            for h in possible_headers:
                if h in col_lower_to_original:
                    c = col_lower_to_original[h]
                    if c not in seen:
                        seen.add(c)
                        candidates.append(c)
                else:
                    for c in df.columns:
                        if h in str(c).lower() and c not in seen:
                            seen.add(c)
                            candidates.append(c)
                            break
            if not candidates:
                return None
            # Prefer column with more unique values (avoids same date/description in every row)
            if len(candidates) == 1:
                return candidates[0]
            best = max(
                candidates,
                key=lambda col: df[col].astype(str).nunique() if col in df.columns else 0,
            )
            return best

        standard_sources = [
            ("Date", ["date", "value date", "transaction date"]),
            ("Description", ["description", "particulars", "narration", "details"]),
            ("Credit", ["credit", "deposit", "credit amount"]),
            ("Debit", ["debit", "withdrawal", "debit amount"]),
            ("Balance", ["balance", "running balance", "closing balance"]),
        ]
        out = pd.DataFrame()
        for std_name, possible in standard_sources:
            src = find_source_column(std_name, possible)
            if src is not None and src in df.columns:
                col_data = df[src]
                # If duplicate column names exist, col_data can be DataFrame; take first column
                if isinstance(col_data, pd.DataFrame):
                    col_data = col_data.iloc[:, 0]
                out[std_name] = col_data.values
            else:
                out[std_name] = "" if std_name == "Description" else 0.0

        if out.empty:
            return df
        return out
