"""
Robust, modular bank statement parser.

Orchestrates: PDF extraction (with OCR for scanned docs) -> bank detection ->
config-driven key-value and transaction table parsing -> cleaning ->
structured JSON output. Handles password-protected PDFs, scanned PDFs,
unrecognized formats, and malformed data. PEP 8 compliant.
"""
from __future__ import annotations

import io
import os
import re
from typing import Dict, Any, List, Optional, Union

import pandas as pd

from .parser_exceptions import (
    BankStatementParserError,
    PasswordProtectedPDFError,
    ScannedPDFError,
    UnrecognizedFormatError,
    MalformedDataError,
)
from .pdf_extractor import (
    extract_text_and_tables,
    extract_text_only,
    extract_text_via_ocr,
    is_likely_scanned,
)
from .bank_config_schema import (
    BankConfig,
    load_bank_configs,
    detect_bank_from_text_with_configs,
    get_bank_config,
)
from .normalizer import DataNormalizer


def _safe_float(val: Any) -> float:
    """Convert value to float; strip currency and commas."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).replace(",", "").replace(" ", "").replace("₦", "").replace("NGN", "")
    s = s.replace("(", "-").replace(")", "")
    for sym in ["$", "USD", "N"]:
        s = s.replace(sym, "")
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


def _normalize_date_cell(val: Any, formats: List[str]) -> Optional[str]:
    """Parse date string to YYYY-MM-DD using given formats."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    from datetime import datetime

    s = str(val).strip()
    for fmt in formats:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue
    return None


class BankStatementParser:
    """
    Main parser: takes a PDF file path or bytes, identifies the bank,
    loads config, extracts key-values and transactions, normalizes,
    and returns a structured JSON object.
    """

    def __init__(
        self,
        configs: Optional[Dict[str, BankConfig]] = None,
        use_ocr_for_scanned: bool = True,
    ):
        self._configs = configs or load_bank_configs()
        self.use_ocr_for_scanned = use_ocr_for_scanned
        self._last_errors: List[str] = []

    def parse(
        self,
        source: Union[str, bytes],
    ) -> Dict[str, Any]:
        """
        Parse a bank statement from a file path or PDF bytes.

        Returns a JSON-like dict with:
          - account_holder: { name, address }
          - account_details: { account_number, currency }
          - statement_summary: { opening_balance, closing_balance, total_debit, total_credit }
          - transactions: [ { date, description, debit, credit, balance }, ... ]

        Raises:
          PasswordProtectedPDFError: PDF is encrypted.
          ScannedPDFError: PDF has no text and OCR failed or unavailable.
          UnrecognizedFormatError: Bank not identified or no config.
          MalformedDataError: Required data missing or invalid.
        """
        self._last_errors = []
        content = self._read_source(source)
        text, tables = self._extract_content(content)
        bank_id = detect_bank_from_text_with_configs(text, self._configs)
        config = get_bank_config(bank_id, self._configs)
        if not config and bank_id != "default":
            config = get_bank_config("default", self._configs)
        if not config:
            raise UnrecognizedFormatError(
                "No bank configuration found and no default config available."
            )

        key_values = config.extract_all_key_values(text)
        account_holder = self._build_account_holder(key_values, config)
        account_details = self._build_account_details(key_values, config)
        df = self._extract_transaction_table(content, text, tables, config)
        df = DataNormalizer.normalize_dataframe(df)
        transactions = self._dataframe_to_transactions(df, config)
        statement_summary = self._build_statement_summary(
            key_values, transactions, config
        )
        self._validate_output(transactions, statement_summary)

        return {
            "account_holder": account_holder,
            "account_details": account_details,
            "statement_summary": statement_summary,
            "transactions": transactions,
        }

    def _read_source(self, source: Union[str, bytes]) -> bytes:
        """Read PDF from path or return bytes as-is."""
        if isinstance(source, bytes):
            return source
        path = os.path.abspath(os.path.expanduser(source))
        if not os.path.isfile(path):
            raise MalformedDataError(f"File not found: {path}")
        with open(path, "rb") as f:
            return f.read()

    def _extract_content(self, content: bytes) -> tuple:
        """Extract text and tables; use OCR if scanned. Raises on password-protected."""
        try:
            text, tables = extract_text_and_tables(content)
        except PasswordProtectedPDFError:
            raise
        except Exception as e:
            err = str(e).lower()
            if "password" in err or "encrypted" in err:
                raise PasswordProtectedPDFError(str(e)) from e
            raise MalformedDataError(f"PDF extraction failed: {e}") from e

        if is_likely_scanned(content) and (not text or len(text.strip()) < 100):
            if self.use_ocr_for_scanned:
                ocr_text = extract_text_via_ocr(content)
                if ocr_text and len(ocr_text.strip()) > 50:
                    text = ocr_text
                    tables = []
                else:
                    raise ScannedPDFError(
                        "PDF appears to be scanned but OCR failed or is unavailable. "
                        "Install pytesseract and pdf2image."
                    )
            else:
                raise ScannedPDFError(
                    "PDF appears to be scanned (no extractable text). Enable OCR or use a digital PDF."
                )

        if not text or len(text.strip()) < 20:
            raise MalformedDataError(
                "Insufficient text extracted from PDF; document may be empty or corrupted."
            )
        return text, tables

    def _build_account_holder(
        self, key_values: Dict[str, Any], config: BankConfig
    ) -> Dict[str, str]:
        """Build account_holder: name, address."""
        name = key_values.get("account_holder_name") or key_values.get("account_name")
        if isinstance(name, list):
            name = name[0] if name else ""
        address = key_values.get("address")
        if isinstance(address, list):
            address = address[0] if address else ""
        return {
            "name": (str(name).strip() if name else ""),
            "address": (str(address).strip() if address else ""),
        }

    def _build_account_details(
        self, key_values: Dict[str, Any], config: BankConfig
    ) -> Dict[str, str]:
        """Build account_details: account_number, currency."""
        acc = key_values.get("account_number")
        if isinstance(acc, list):
            acc = acc[0] if acc else ""
        currency = key_values.get("currency")
        if isinstance(currency, list):
            currency = currency[0] if currency else ""
        return {
            "account_number": (str(acc).strip() if acc else ""),
            "currency": (str(currency).strip() if currency else "NGN"),
        }

    def _extract_transaction_table(
        self,
        content: bytes,
        text: str,
        tables: list,
        config: BankConfig,
    ) -> pd.DataFrame:
        """Build transaction DataFrame from extracted tables or text."""
        date_pattern = re.compile(
            r"\d{1,2}[-/\s]?(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2})[-/\s]\d{2,4}",
            re.IGNORECASE,
        )
        if tables:
            for table in tables:
                if not table or len(table) < 2:
                    continue
                headers = [str(h).strip() if h is not None else "" for h in table[0]]
                rows = []
                for row in table[1:]:
                    clean = [str(c).strip() if c is not None else "" for c in row]
                    if not any(clean):
                        continue
                    if any(date_pattern.search(c) for c in clean[:3]):
                        rows.append(clean)
                if not rows:
                    continue
                max_cols = max(len(r) for r in rows)
                if len(headers) < max_cols:
                    headers.extend([f"Col{i}" for i in range(len(headers), max_cols)])
                df = pd.DataFrame(rows, columns=headers[:max_cols])
                mapped = self._apply_column_mapping(df, config)
                if not mapped.empty and "Date" in mapped.columns:
                    return mapped
        rows = []
        # Fallback: simple line-based from text
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            if re.search(r"^\d{2}[-/]\d{2}[-/]\d{2,4}", line) or re.search(
                r"^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}", line
            ):
                parts = re.split(r"\s{2,}", line)
                if len(parts) >= 3:
                    rows.append(parts)
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        return self._apply_column_mapping(df, config)

    def _apply_column_mapping(self, df: pd.DataFrame, config: BankConfig) -> pd.DataFrame:
        """Map raw columns to Date, Description, Credit, Debit, Balance."""
        col_lower = {str(c).lower().strip(): c for c in df.columns}
        std_to_possible = [
            ("Date", ["date", "trans date", "value date", "transaction date"]),
            ("Description", ["description", "remarks", "particulars", "narration"]),
            ("Credit", ["credit", "deposit"]),
            ("Debit", ["debit", "withdrawal"]),
            ("Balance", ["balance", "running balance"]),
        ]
        out = {}
        for std_name, possible in std_to_possible:
            src = None
            for pdf_name, mapped in config.table_column_mapping.items():
                if str(mapped).strip() == std_name and pdf_name in col_lower:
                    src = col_lower[pdf_name]
                    break
            if not src:
                for p in possible:
                    if p in col_lower:
                        src = col_lower[p]
                        break
            if src is not None:
                out[std_name] = df[src].values
            else:
                out[std_name] = "" if std_name == "Description" else 0.0
        if not out:
            return df
        return pd.DataFrame(out)

    def _dataframe_to_transactions(
        self, df: pd.DataFrame, config: BankConfig
    ) -> List[Dict[str, Any]]:
        """Convert normalized DataFrame to list of transaction dicts."""
        if df.empty or "Date" not in df.columns:
            return []
        required = ["Date", "Description", "Credit", "Debit", "Balance"]
        for c in required:
            if c not in df.columns:
                df[c] = "" if c == "Description" else 0.0
        formats = config.date_formats or ["%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"]
        out = []
        for _, row in df.iterrows():
            date_val = row.get("Date")
            if pd.isna(date_val) or str(date_val).strip() == "":
                continue
            date_str = _normalize_date_cell(date_val, formats)
            if not date_str:
                date_str = str(date_val).strip()
            out.append({
                "date": date_str,
                "description": str(row.get("Description", "") or "").strip(),
                "debit": _safe_float(row.get("Debit")),
                "credit": _safe_float(row.get("Credit")),
                "balance": _safe_float(row.get("Balance")),
            })
        return out

    def _build_statement_summary(
        self,
        key_values: Dict[str, Any],
        transactions: List[Dict],
        config: BankConfig,
    ) -> Dict[str, float]:
        """Build statement_summary: opening_balance, closing_balance, total_debit, total_credit."""
        def one_val(key: str) -> float:
            v = key_values.get(key)
            if isinstance(v, list):
                v = v[0] if v else None
            return _safe_float(v)

        opening = one_val("opening_balance")
        closing = one_val("closing_balance")
        total_debit = sum(t.get("debit", 0) or 0 for t in transactions)
        total_credit = sum(t.get("credit", 0) or 0 for t in transactions)
        if closing == 0.0 and transactions:
            last = transactions[-1]
            closing = _safe_float(last.get("balance"))
        return {
            "opening_balance": opening,
            "closing_balance": closing,
            "total_debit": total_debit,
            "total_credit": total_credit,
        }

    def _validate_output(
        self,
        transactions: List[Dict],
        statement_summary: Dict[str, float],
    ) -> None:
        """Optionally raise MalformedDataError if output is clearly invalid."""
        if not transactions and statement_summary.get("total_debit", 0) == 0 and statement_summary.get("total_credit", 0) == 0:
            self._last_errors.append("No transactions extracted")
        return

    def get_last_errors(self) -> List[str]:
        """Return list of non-fatal errors from last parse."""
        return list(self._last_errors)


class AICategorizer:
    """
    Optional: interact with an external AI model for transaction categorization.
    Use from async code: await categorizer.categorize_transactions(transactions)
    to add a 'category' field (e.g. Salary, Transfer, Bills, Other).
    """

    def __init__(self, ai_core: Optional[Any] = None):
        self._ai = ai_core

    async def categorize_transactions(
        self, transactions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add 'category' to each transaction using AI. Call with await from async code."""
        if not self._ai or not transactions:
            for t in transactions:
                t.setdefault("category", "Other")
            return transactions
        try:
            from .ai_core import AICore
            core = self._ai if isinstance(self._ai, AICore) else AICore()
            for t in transactions:
                desc = (t.get("description") or "").strip()
                if not desc:
                    t["category"] = "Other"
                    continue
                prompt = (
                    "Classify this bank transaction into one word: "
                    "Salary, Business, Loan, Gift, Refund, Transfer, Bills, "
                    "Shopping, Investment, Other. Reply with only the word.\n"
                    f"Transaction: {desc[:200]}"
                )
                try:
                    result = await core.call_ai(prompt)
                    t["category"] = (result or "Other").strip() or "Other"
                except Exception:
                    t["category"] = "Other"
        except Exception:
            for t in transactions:
                t["category"] = t.get("category", "Other")
        return transactions


# --- Example usage ---
"""
Example usage:

    from backend.services.bank_statement_parser import BankStatementParser
    import json

    parser = BankStatementParser()

    # From file path
    result = parser.parse("/path/to/statement.pdf")

    # From bytes (e.g. upload)
    with open("statement.pdf", "rb") as f:
        result = parser.parse(f.read())

    # Output structure
    print(json.dumps(result, indent=2))
    # result["account_holder"]  -> { "name": "...", "address": "..." }
    # result["account_details"] -> { "account_number": "...", "currency": "NGN" }
    # result["statement_summary"] -> { "opening_balance", "closing_balance", ... }
    # result["transactions"]    -> [ { "date", "description", "debit", "credit", "balance" }, ... ]

    # Optional: categorize with AI (from async code)
    # from backend.services.bank_statement_parser import AICategorizer
    # from backend.services.ai_core import AICore
    # categorizer = AICategorizer(AICore())
    # result["transactions"] = await categorizer.categorize_transactions(result["transactions"])

    # Error handling
    from backend.services.parser_exceptions import (
        PasswordProtectedPDFError,
        ScannedPDFError,
        UnrecognizedFormatError,
        MalformedDataError,
    )
    try:
        result = parser.parse("statement.pdf")
    except PasswordProtectedPDFError:
        print("PDF is password-protected")
    except ScannedPDFError:
        print("Scanned PDF; enable OCR or install pytesseract")
    except UnrecognizedFormatError:
        print("Bank format not recognized")
    except MalformedDataError as e:
        print("Invalid or missing data:", e)
"""
if __name__ == "__main__":
    import json as json_module

    parser = BankStatementParser()
    print("BankStatementParser ready. Use parser.parse(path_or_bytes) to parse a statement.")
