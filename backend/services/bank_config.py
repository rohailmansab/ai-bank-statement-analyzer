"""
Bank format configuration loader and rule-based bank detection.
Supports configuration-driven parsing without code changes for new bank layouts.
"""
import os
import re
import json
from typing import Dict, Any, List, Optional

# Directory for bank format JSON configs (next to backend)
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG_DIR = os.path.join(_BASE_DIR, "config", "bank_formats")


def load_all_configs() -> Dict[str, Dict[str, Any]]:
    """Load all JSON configs from bank_formats directory. Keys are bank_id."""
    configs = {}
    if not os.path.isdir(_CONFIG_DIR):
        return configs
    for name in os.listdir(_CONFIG_DIR):
        if name.endswith(".json"):
            path = os.path.join(_CONFIG_DIR, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                bid = data.get("bank_id", name.replace(".json", ""))
                configs[bid] = data
            except Exception as e:
                print(f"[BANK CONFIG] Skip {name}: {e}")
    return configs


def detect_bank_from_text(text: str, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
    """
    Rule-based bank detection from PDF header/first page text.
    Returns bank_id (e.g. 'gtbank', 'uba') or 'default' if no match.
    """
    if configs is None:
        configs = load_all_configs()
    text_lower = (text or "")[:3000].lower()
    best_match = "default"
    for bank_id, cfg in configs.items():
        if bank_id == "default":
            continue
        keywords = cfg.get("keywords") or []
        for kw in keywords:
            if kw.lower() in text_lower:
                return bank_id
    return best_match


def get_config(bank_id: str, configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Get config for bank_id; fallback to default."""
    if configs is None:
        configs = load_all_configs()
    return configs.get(bank_id) or configs.get("default") or {}


def extract_key_values(text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract key-value pairs (account number, opening/closing balance, statement period)
    using regex patterns from config.
    """
    result = {}
    patterns = config.get("key_value_patterns") or {}
    for key, regex_list in patterns.items():
        if not isinstance(regex_list, list):
            regex_list = [regex_list]
        for pattern in regex_list:
            try:
                m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if m:
                    if m.lastindex and m.lastindex >= 1:
                        result[key] = [g for g in m.groups() if g is not None]
                    else:
                        result[key] = m.group(0)
                    break
            except re.error:
                continue
    return result
