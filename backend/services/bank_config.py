"""
Load bank format configs from backend/config/bank_formats/*.json and provide
detect_bank_from_text, get_config, extract_key_values for config-driven parsing.
Supports document-style config: bank_name, date_format, header_keywords, transaction_table.
"""
import os
import re
import json
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

_CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "config", "bank_formats")


@dataclass
class BankConfig:
    """
    Parsing rules for a specific bank (document-aligned).
    Holds regex patterns for key-value pairs and table column mapping.
    """
    bank_id: str
    bank_name: str
    date_format: str
    keywords: List[str]
    header_keywords: Dict[str, str]
    key_value_patterns: Dict[str, List[str]]
    transaction_table: Dict[str, Any]  # header: list, column_mapping: dict
    table_column_mapping: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BankConfig":
        """Build BankConfig from JSON config dict."""
        tt = data.get("transaction_table") or {}
        mapping = data.get("table_column_mapping") or {}
        # Normalize: doc uses "column_mapping" with std names as values; we also support raw header -> std
        if not mapping and tt.get("column_mapping"):
            rev = {v: k for k, v in tt["column_mapping"].items()}
            mapping = rev
        return cls(
            bank_id=data.get("bank_id", "default"),
            bank_name=data.get("bank_name", "Unknown Bank"),
            date_format=data.get("date_format", "%d/%m/%Y"),
            keywords=data.get("keywords") or [],
            header_keywords=data.get("header_keywords") or {},
            key_value_patterns=data.get("key_value_patterns") or {},
            transaction_table=tt,
            table_column_mapping=mapping,
        )


def load_all_configs() -> Dict[str, Dict[str, Any]]:
    """Load all JSON configs from config/bank_formats/ keyed by bank_id."""
    configs = {}
    if not os.path.isdir(_CONFIG_DIR):
        return configs
    for name in os.listdir(_CONFIG_DIR):
        if not name.endswith(".json"):
            continue
        path = os.path.join(_CONFIG_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            bank_id = data.get("bank_id", name.replace(".json", ""))
            configs[bank_id] = data
        except Exception:
            continue
    return configs


def detect_bank_from_text(text: str, configs: Dict[str, Dict[str, Any]]) -> str:
    """Return bank_id if any config's keywords appear in text (case-insensitive)."""
    if not text or not configs:
        return "default"
    text_lower = text.lower()
    for bank_id, cfg in configs.items():
        if bank_id == "default":
            continue
        keywords = cfg.get("keywords") or []
        for kw in keywords:
            if kw and kw.lower() in text_lower:
                return bank_id
    return "default"


def get_config(bank_id: str, configs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Return config dict for bank_id or default."""
    if bank_id in configs:
        return configs[bank_id]
    return configs.get("default", {})


def get_bank_config(bank_id: str, configs: Dict[str, Dict[str, Any]]) -> Optional[BankConfig]:
    """Return BankConfig for bank_id or default (for type-safe use)."""
    data = get_config(bank_id, configs)
    if not data:
        return None
    return BankConfig.from_dict(data)


def extract_key_values(full_text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply key_value_patterns from config and return dict of first match per key."""
    result = {}
    patterns = config.get("key_value_patterns") or {}
    for key, regex_list in patterns.items():
        if not isinstance(regex_list, list):
            continue
        for pattern in regex_list:
            try:
                m = re.search(pattern, full_text, re.IGNORECASE | re.DOTALL)
                if m:
                    result[key] = m.group(1).strip() if m.lastindex >= 1 else m.group(0).strip()
                    break
            except Exception:
                continue
    return result
