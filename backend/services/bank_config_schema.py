"""
BankConfig dataclass and loader for configuration-driven parsing.
Supports both regex-based key_value_patterns and Alpha Bank-style header_keywords
and transaction_table (header + column_mapping). PEP 8 compliant.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import os
import json
import re


@dataclass
class TransactionTableConfig:
    """Parsing rules for the transaction table section."""

    header: List[str]
    column_mapping: Dict[str, str]  # standard field -> PDF header name


@dataclass
class BankConfig:
    """
    Holds parsing rules for a specific bank.
    Used by BankStatementParser to extract key-values and map table columns.
    """

    bank_id: str
    bank_name: str
    date_format: str
    header_keywords: Dict[str, str]  # field name -> literal label (e.g. "Account No:")
    key_value_patterns: Dict[str, List[str]]  # field name -> list of regex patterns
    transaction_table: Optional[TransactionTableConfig]
    table_column_mapping: Dict[str, str]  # PDF header (lower) -> standard field
    date_formats: List[str]
    amount_cleanup: Dict[str, Any]
    keywords: List[str] = field(default_factory=list)

    def get_account_number_regexes(self) -> List[str]:
        """Return regex patterns for account number extraction."""
        return self.key_value_patterns.get("account_number", [])

    def get_opening_balance_regexes(self) -> List[str]:
        """Return regex patterns for opening balance."""
        return self.key_value_patterns.get("opening_balance", [])

    def get_closing_balance_regexes(self) -> List[str]:
        """Return regex patterns for closing balance."""
        return self.key_value_patterns.get("closing_balance", [])

    def extract_key_value(self, text: str, field_name: str) -> Optional[Any]:
        """
        Extract a single field using key_value_patterns.
        Returns first captured group(s) or full match; None if not found.
        """
        patterns = self.key_value_patterns.get(field_name) or []
        for pattern in patterns:
            try:
                m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if m:
                    if m.lastindex and m.lastindex >= 1:
                        groups = [g for g in m.groups() if g is not None]
                        return groups[0].strip() if len(groups) == 1 else groups
                    return m.group(0).strip()
            except re.error:
                continue
        return None

    def extract_all_key_values(self, text: str) -> Dict[str, Any]:
        """Extract all configured key-value fields from text."""
        result = {}
        for key in self.key_value_patterns:
            val = self.extract_key_value(text, key)
            if val is not None:
                result[key] = val
        return result


def _config_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config", "bank_formats")


def _raw_config_to_bank_config(bank_id: str, raw: Dict[str, Any]) -> BankConfig:
    """Convert raw JSON dict to BankConfig (supports both existing and Alpha-style)."""
    header_keywords = raw.get("header_keywords") or {}
    key_value_patterns = raw.get("key_value_patterns") or {}
    tt = raw.get("transaction_table") or {}
    header = tt.get("header") or []
    col_map = tt.get("column_mapping") or {}
    # table_column_mapping: PDF header -> standard (used by existing parsers)
    table_col = raw.get("table_column_mapping") or {}
    # Build standard -> PDF mapping from column_mapping if present
    for std_name, pdf_name in col_map.items():
        table_col[pdf_name.lower().strip()] = std_name
    date_formats = raw.get("date_formats") or []
    if not date_formats and raw.get("date_format"):
        date_formats = [raw["date_format"]]
    if not date_formats:
        date_formats = ["%d-%b-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"]
    amount_cleanup = raw.get("amount_cleanup") or {}
    keywords = raw.get("keywords") or []
    transaction_table = (
        TransactionTableConfig(header=header, column_mapping=col_map)
        if (header or col_map)
        else None
    )
    return BankConfig(
        bank_id=bank_id,
        bank_name=raw.get("bank_name") or raw.get("name") or bank_id,
        date_format=raw.get("date_format") or "%Y-%m-%d",
        header_keywords=header_keywords,
        key_value_patterns=key_value_patterns,
        transaction_table=transaction_table,
        table_column_mapping=table_col,
        date_formats=date_formats,
        amount_cleanup=amount_cleanup,
        keywords=keywords,
    )


def load_bank_configs() -> Dict[str, BankConfig]:
    """Load all JSON configs from bank_formats directory; returns bank_id -> BankConfig."""
    configs = {}
    config_dir = _config_dir()
    if not os.path.isdir(config_dir):
        return configs
    for name in os.listdir(config_dir):
        if not name.endswith(".json"):
            continue
        path = os.path.join(config_dir, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            bid = raw.get("bank_id", name.replace(".json", ""))
            configs[bid] = _raw_config_to_bank_config(bid, raw)
        except Exception as e:
            print(f"[BANK CONFIG] Skip {name}: {e}")
    return configs


def detect_bank_from_text_with_configs(
    text: str, configs: Optional[Dict[str, BankConfig]] = None
) -> str:
    """Rule-based bank detection; returns bank_id or 'default'."""
    if configs is None:
        configs = load_bank_configs()
    text_lower = (text or "")[:3000].lower()
    for bank_id, cfg in configs.items():
        if bank_id == "default":
            continue
        for kw in cfg.keywords:
            if kw.lower() in text_lower:
                return bank_id
    return "default"


def get_bank_config(
    bank_id: str, configs: Optional[Dict[str, BankConfig]] = None
) -> Optional[BankConfig]:
    """Get BankConfig for bank_id; fallback to default if present."""
    if configs is None:
        configs = load_bank_configs()
    return configs.get(bank_id) or configs.get("default")
