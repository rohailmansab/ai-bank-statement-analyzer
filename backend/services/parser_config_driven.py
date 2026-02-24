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
            num_pages = len(pdf.pages)
            header_text = (pdf.pages[0].extract_text() or "") if pdf.pages else ""
            full_text = ""
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"

        # When native text is low (or multi-page with few chars per page), try OCR
        try_ocr = len(full_text.strip()) < 1500 or (num_pages > 5 and len(full_text.strip()) < 500 * num_pages)
        if try_ocr:
            try:
                from .pdf_extractor import extract_text_and_tables
                ocr_text, _, _, used = extract_text_and_tables(
                    content, use_ocr_if_needed=True, ocr_char_threshold=2000
                )
                if used and ocr_text and len(ocr_text.strip()) > len(full_text.strip()):
                    full_text = ocr_text + "\n" + full_text
                    if not header_text.strip():
                        header_text = (ocr_text.split("\n")[0] or "")[:500]
            except Exception:
                pass

        bank_id = detect_bank_from_text(header_text, self._configs)
        config = get_config(bank_id, self._configs)

        # GTBank ibank: dates in PDF are often "02-Sep-\n2025"; normalize so date is on one line
        if "gtbank" in (header_text or "").lower() or "ibank.gtbank" in (header_text or "").lower():
            full_text = re.sub(
                r"(\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*-?)\s*\n\s*(\d{4})",
                r"\1\2",
                full_text,
                flags=re.IGNORECASE,
            )

        # For GTBank multi-page: try PyMuPDF (fitz) text too – sometimes better order than pdfplumber
        if bank_id == "gtbank" and num_pages > 5:
            try:
                import fitz
                doc = fitz.open(stream=content, filetype="pdf")
                fitz_text = ""
                for i in range(len(doc)):
                    fitz_text += (doc[i].get_text() or "") + "\n"
                doc.close()
                if fitz_text and len(fitz_text.strip()) > len(full_text.strip()):
                    full_text = fitz_text.strip()
                    print(f"[GTBank] using PyMuPDF text ({len(full_text)} chars) for extraction")
            except Exception:
                pass

        # Key-value extraction (account number, balances, period)
        self._metadata = extract_key_values(full_text, config)
        self._metadata["detected_bank"] = bank_id

        # Transaction table: try tables first
        df = self._extract_transaction_table(content, config)
        table_df = None
        if df is not None and not df.empty:
            df = self._apply_column_mapping(df, config)
            table_df = self.standardize_columns(df)

        if bank_id == "gtbank":
            # Merge ALL sources (table + text + words), then deduplicate to get maximum coverage
            all_dfs: List[pd.DataFrame] = []
            n_table, n_text, n_word = 0, 0, 0
            if table_df is not None and not table_df.empty:
                all_dfs.append(table_df)
                n_table = len(table_df)
            if full_text.strip():
                text_df = self._extract_gtbank_from_text(full_text)
                if text_df is not None and not text_df.empty:
                    n_text_raw = len(text_df)
                    text_df = self.standardize_columns(text_df)
                    n_text = len(text_df)
                    all_dfs.append(text_df)
                    if n_text < n_text_raw:
                        print(f"[GTBank] text source: {n_text_raw} rows -> {n_text} after date parse (dropped {n_text_raw - n_text})")
            word_df = self._extract_gtbank_from_words(content)
            if word_df is not None and not word_df.empty:
                n_word_raw = len(word_df)
                word_df = self.standardize_columns(word_df)
                n_word = len(word_df)
                all_dfs.append(word_df)
                if n_word < n_word_raw:
                    print(f"[GTBank] words source: {n_word_raw} rows -> {n_word} after date parse (dropped {n_word_raw - n_word})")
            # Aggressive: any line in full text with date + amount (for ibank.gtbank.com statements)
            if full_text.strip():
                raw_df = self._extract_gtbank_raw_lines(full_text)
                if raw_df is not None and not raw_df.empty:
                    raw_df = self.standardize_columns(raw_df)
                    if not raw_df.empty:
                        all_dfs.append(raw_df)
            if all_dfs:
                total_before_dedupe = sum(len(d) for d in all_dfs)
                best_df = self._merge_and_dedupe_transactions(all_dfs)
                if best_df is not None and not best_df.empty:
                    print(f"[GTBank] table={n_table} text={n_text} words={n_word} -> merged {total_before_dedupe} -> {len(best_df)} unique")
                    return best_df
        else:
            if table_df is not None and not table_df.empty:
                return table_df
        return pd.DataFrame()

    def _extract_transaction_table(self, content: bytes, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Extract main transaction table from PDF using pdfplumber tables."""
        # dd/mm/yyyy, dd-Mon-yyyy (allow newline: 02-Sep-\n2025); require 4-digit year for DD-Mon so we don't match "02-Sep- 02"
        date_pattern = re.compile(
            r"\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[-/\s]*\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4}",
            re.IGNORECASE,
        )
        amount_re = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
        gtbank_headers = {"trans date", "value date", "debit", "credit", "balance", "remarks"}
        data_frames: List[pd.DataFrame] = []

        def norm(s: str) -> str:
            return (s or "").replace("\n", " ").replace("\r", " ").strip()

        def is_transaction_table(headers: List[str]) -> bool:
            h_lower = {str(x).strip().lower() for x in headers if x}
            if not h_lower:
                return False
            has_date = any("date" in h or "trans" in h for h in h_lower)
            has_amount = "debit" in h_lower or "credit" in h_lower or "balance" in h_lower
            if has_date and has_amount:
                return True
            if gtbank_headers.issubset(h_lower) or len(gtbank_headers & h_lower) >= 4:
                return True
            return False

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
                    raw_headers = [norm(str(h)) if h is not None else f"Col{i}" for i, h in enumerate(table[0])]
                    data_rows = []
                    for row in table[1:]:
                        clean_row = [norm(str(c)) if c is not None else "" for c in row]
                        if not any(clean_row):
                            continue
                        if any(date_pattern.search(c) for c in clean_row[:5]):
                            data_rows.append(clean_row)
                    if not data_rows:
                        continue
                    if not is_transaction_table(raw_headers):
                        data_rows_strict = [r for r in data_rows if any(amount_re.search(c) for c in r)]
                        if len(data_rows_strict) >= 2:
                            max_cols = max(len(r) for r in data_rows_strict)
                            df_page = pd.DataFrame(data_rows_strict, columns=[f"Col{i}" for i in range(max_cols)])
                            if max_cols >= 10:
                                rename = {}
                                if 3 < max_cols:
                                    rename["Col3"] = "Trans Date"
                                if 6 < max_cols:
                                    rename["Col6"] = "Debit"
                                if 8 < max_cols:
                                    rename["Col8"] = "Balance"
                                if 9 < max_cols:
                                    rename["Col9"] = "Remarks"
                                df_page = df_page.rename(columns=rename)
                            data_frames.append(df_page)
                        continue
                    max_cols = max(len(r) for r in data_rows)
                    headers = make_unique_columns(
                        raw_headers if len(raw_headers) >= max_cols else raw_headers + [f"Col{i}" for i in range(len(raw_headers), max_cols)]
                    )
                    df_page = pd.DataFrame(data_rows, columns=headers[:max_cols])
                    data_frames.append(df_page)
        if not data_frames:
            text_settings = {"vertical_strategy": "text", "horizontal_strategy": "text"}
            for page in pdf.pages:
                tables = page.extract_tables(table_settings=text_settings)
                for table in tables or []:
                    if not table or len(table) < 2:
                        continue
                    raw_headers = [norm(str(h)) if h is not None else f"Col{i}" for i, h in enumerate(table[0])]
                    if not is_transaction_table(raw_headers):
                        data_rows = []
                        for row in table[1:]:
                            clean_row = [norm(str(c)) if c is not None else "" for c in row]
                            if not any(clean_row):
                                continue
                            if any(date_pattern.search(c) for c in clean_row[:5]) and any(amount_re.search(c) for c in clean_row):
                                data_rows.append(clean_row)
                        if len(data_rows) >= 2:
                            max_cols = max(len(r) for r in data_rows)
                            headers = make_unique_columns([f"Col{i}" for i in range(max_cols)])
                            data_frames.append(pd.DataFrame(data_rows, columns=headers[:max_cols]))
                        continue
                    data_rows = []
                    for row in table[1:]:
                        clean_row = [norm(str(c)) if c is not None else "" for c in row]
                        if not any(clean_row):
                            continue
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

        # Per-page text fallback: when we have few rows, extract date+amount lines from each page's text
        num_pages = len(pdf.pages)
        total_rows = sum(len(d) for d in data_frames)
        if total_rows < max(25, num_pages * 2):
            amount_re = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if len(page_text.strip()) < 20:
                    continue
                page_rows = self._page_text_to_transaction_rows(page_text, date_pattern, amount_re)
                if page_rows:
                    data_frames.append(pd.DataFrame(page_rows))

        if not data_frames:
            return None
        # Keep ALL transaction tables from ALL pages (42 pages = 42+ table chunks); drop only tiny summary tables
        min_transaction_rows = 2
        large_tables = [d for d in data_frames if len(d) >= min_transaction_rows]
        if not large_tables:
            data_frames = [max(data_frames, key=len)]
        else:
            data_frames = large_tables
        # Align columns by name (case-insensitive) so concat works across pages with slight header differences
        all_cols: Dict[str, str] = {}
        for df in data_frames:
            for c in df.columns:
                key = str(c).strip().lower()
                if key and key not in all_cols:
                    all_cols[key] = c
        unified = []
        for df in data_frames:
            rename = {}
            for c in df.columns:
                key = str(c).strip().lower()
                if key in all_cols and all_cols[key] != c:
                    rename[c] = all_cols[key]
            if rename:
                df = df.rename(columns=rename)
            unified.append(df)
        combined = pd.concat(unified, ignore_index=True)
        if combined.columns.duplicated().any():
            combined = combined.loc[:, ~combined.columns.duplicated(keep="first")]
        return combined

    def _merge_and_dedupe_transactions(self, dfs: List[pd.DataFrame]) -> pd.DataFrame:
        """Concatenate transaction DataFrames, normalize Date, drop duplicates, sort by date."""
        if not dfs:
            return pd.DataFrame()
        combined = pd.concat(dfs, ignore_index=True)
        # Ensure standard columns exist
        for col in ("Date", "Description", "Debit", "Credit", "Balance"):
            if col not in combined.columns:
                combined[col] = "" if col == "Description" else 0.0
        # Normalize date to string for deduplication (e.g. 30-Jan-2026)
        combined["_date_norm"] = combined["Date"].astype(str).str.strip().str[:20]
        combined["_debit"] = pd.to_numeric(combined["Debit"], errors="coerce").fillna(0)
        combined["_credit"] = pd.to_numeric(combined["Credit"], errors="coerce").fillna(0)
        # Drop duplicates: same date + same amounts = same transaction
        combined = combined.drop_duplicates(
            subset=["_date_norm", "_debit", "_credit"],
            keep="first",
        )
        combined = combined.drop(columns=["_date_norm", "_debit", "_credit"], errors="ignore")
        # Sort by date (string sort is ok for DD-MMM-YYYY / YYYY-MM-DD)
        if "Date" in combined.columns:
            combined = combined.sort_values("Date").reset_index(drop=True)
        return combined

    def _page_text_to_transaction_rows(
        self, page_text: str, date_pattern: re.Pattern, amount_re: re.Pattern
    ) -> List[Dict[str, Any]]:
        """Extract transaction rows from a single page's text (date + amounts per segment)."""
        rows: List[Dict[str, Any]] = []
        prev_balance: Optional[float] = None
        date_matches = list(date_pattern.finditer(page_text))
        for i, m in enumerate(date_matches):
            tx_date = m.group(0)
            start, end = m.start(), date_matches[i + 1].start() if i + 1 < len(date_matches) else len(page_text)
            segment = page_text[start:end]
            amounts = [ParserUtils.clean_numeric(s) for s in amount_re.findall(segment)]
            desc = segment
            for x in date_pattern.findall(segment):
                desc = desc.replace(x, " ", 1)
            for x in amount_re.findall(desc):
                desc = desc.replace(x, " ", 1)
            desc = re.sub(r"\s+", " ", desc).strip() or "Transaction"
            debit, credit, balance = 0.0, 0.0, 0.0
            if len(amounts) >= 3:
                debit, credit, balance = amounts[0], amounts[1], amounts[2]
            elif len(amounts) == 2:
                a1, a2 = amounts[0], amounts[1]
                balance = a2
                if prev_balance is not None and a2 > prev_balance:
                    credit = a1
                else:
                    debit = a1
            elif len(amounts) == 1:
                balance = amounts[0]
            prev_balance = balance if balance else prev_balance
            rows.append({
                "Date": tx_date,
                "Description": desc[:500],
                "Debit": debit,
                "Credit": credit,
                "Balance": balance,
            })
        return rows

    def _extract_gtbank_from_text(self, full_text: str) -> Optional[pd.DataFrame]:
        """Parse GTBank from text: try line-by-line first, then split-by-date to catch all transactions."""
        date_re = re.compile(
            r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[-/\s]*\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
            re.IGNORECASE,
        )
        amount_re = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
        header_re = re.compile(
            r"ibank\.gtbank|Print\s*Date|Customer\s*Statement|Trans\s*Date|Value\s*Date|\d{1,2}:\d{2}",
            re.IGNORECASE,
        )

        def parse_segment(tx_date: str, segment: str, prev_bal: Optional[float]) -> tuple:
            amounts = [ParserUtils.clean_numeric(s) for s in amount_re.findall(segment)]
            desc = segment
            for x in date_re.findall(desc):
                desc = desc.replace(x, " ", 1)
            for x in amount_re.findall(desc):
                desc = desc.replace(x, " ", 1)
            desc = re.sub(r"\s+", " ", desc).strip() or "Transaction"
            debit, credit, balance = 0.0, 0.0, 0.0
            if len(amounts) >= 3:
                debit, credit, balance = amounts[0], amounts[1], amounts[2]
            elif len(amounts) == 2:
                a1, a2 = amounts[0], amounts[1]
                balance = a2
                if prev_bal is not None and a2 > prev_bal:
                    credit = a1
                else:
                    debit = a1
            elif len(amounts) == 1:
                balance = amounts[0]
            return debit, credit, balance, desc

        rows: List[Dict[str, Any]] = []
        prev_balance: Optional[float] = None
        pending: Optional[Dict[str, Any]] = None

        def flush_pending():
            nonlocal pending
            if pending:
                rows.append(pending)
                pending = None

        # Strategy 1: line-by-line (when PDF has one transaction per line)
        for line in full_text.splitlines():
            line = line.strip()
            if not line:
                continue
            if header_re.search(line) and not date_re.search(line):
                flush_pending()
                continue
            m = date_re.search(line)
            if not m:
                if pending and len(line) > 2:
                    pending["Description"] = (pending.get("Description") or "") + " " + line[:300]
                continue
            flush_pending()
            tx_date = m.group(1)
            debit, credit, balance, desc = parse_segment(tx_date, line, prev_balance)
            prev_balance = balance if balance else prev_balance
            pending = {"Date": tx_date, "Description": desc[:500], "Debit": debit, "Credit": credit, "Balance": balance}
        flush_pending()

        # Strategy 2: ALWAYS run for GTBank (split by date) and merge with Strategy 1 for max coverage
        date_matches = list(date_re.finditer(full_text))
        if len(date_matches) > len(rows):
            rows2: List[Dict[str, Any]] = []
            prev_balance = None
            for i, m in enumerate(date_matches):
                tx_date = m.group(1)
                start = m.start()
                end = date_matches[i + 1].start() if i + 1 < len(date_matches) else len(full_text)
                segment = full_text[start:end]
                if len(segment) > 50 and header_re.search(segment) and not amount_re.search(segment):
                    continue
                debit, credit, balance, desc = parse_segment(tx_date, segment, prev_balance)
                prev_balance = balance if balance else prev_balance
                rows2.append({
                    "Date": tx_date,
                    "Description": desc[:500],
                    "Debit": debit,
                    "Credit": credit,
                    "Balance": balance,
                })
            if len(rows2) > len(rows):
                print(f"[GTBank text] Strategy 2: {len(date_matches)} date matches -> {len(rows2)} rows (using as base)")
                rows = rows2
            else:
                # Merge both: add rows2 that aren't already in rows (by date+debit+credit)
                seen = {(r.get("Date"), r.get("Debit"), r.get("Credit")) for r in rows}
                for r in rows2:
                    key = (r.get("Date"), r.get("Debit"), r.get("Credit"))
                    if key not in seen:
                        seen.add(key)
                        rows.append(r)

        if not rows:
            return None
        return pd.DataFrame(rows)

    def _extract_gtbank_raw_lines(self, full_text: str) -> Optional[pd.DataFrame]:
        """Aggressive: every line that has a date and an amount -> one row. For ibank statements."""
        date_re = re.compile(
            r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[-/\s]*\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
            re.IGNORECASE,
        )
        amount_re = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
        header_re = re.compile(
            r"^Trans\s*Date|^Value\s*Date|^Debit\s*$|^Credit\s*$|ibank\.gtbank|Print\s*Date",
            re.IGNORECASE,
        )
        rows: List[Dict[str, Any]] = []
        prev_balance: Optional[float] = None
        for line in full_text.splitlines():
            line = line.strip()
            if len(line) < 15:
                continue
            if header_re.match(line) and not amount_re.search(line):
                continue
            m = date_re.search(line)
            if not m or not amount_re.search(line):
                continue
            tx_date = m.group(1)
            amounts = [ParserUtils.clean_numeric(s) for s in amount_re.findall(line)]
            desc = line
            for x in date_re.findall(desc):
                desc = desc.replace(x, " ", 1)
            for x in amount_re.findall(desc):
                desc = desc.replace(x, " ", 1)
            desc = re.sub(r"\s+", " ", desc).strip() or "Transaction"
            debit, credit, balance = 0.0, 0.0, 0.0
            if len(amounts) >= 3:
                debit, credit, balance = amounts[0], amounts[1], amounts[2]
            elif len(amounts) == 2:
                balance = amounts[1]
                if prev_balance is not None and amounts[1] > prev_balance:
                    credit = amounts[0]
                else:
                    debit = amounts[0]
            elif len(amounts) == 1:
                balance = amounts[0]
            prev_balance = balance if balance else prev_balance
            rows.append({
                "Date": tx_date,
                "Description": desc[:500],
                "Debit": debit,
                "Credit": credit,
                "Balance": balance,
            })
        if not rows:
            return None
        print(f"[GTBank raw lines] {len(rows)} rows from any line with date+amount")
        return pd.DataFrame(rows)

    def _extract_gtbank_from_words(self, content: bytes) -> Optional[pd.DataFrame]:
        """Extract GTBank transactions from word layout (all pages). One row per line that has date + amounts."""
        date_re = re.compile(
            r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[-/\s]+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*[-/\s]*\d{4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}|\d{1,2}/\d{1,2}/\d{2,4})",
            re.IGNORECASE,
        )
        amount_re = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d{2})")
        header_re = re.compile(
            r"ibank\.gtbank|Print\s*Date|Customer\s*Statement|Trans\s*Date|Value\s*Date|\d{1,2}:\d{2}",
            re.IGNORECASE,
        )
        rows: List[Dict[str, Any]] = []
        prev_balance: Optional[float] = None

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                words = page.extract_words(x_tolerance=3, y_tolerance=3)
                if not words:
                    continue
                lines_buckets: Dict[float, List[Any]] = {}
                for w in words:
                    bucket = round(w["top"] / 3) * 3
                    if bucket not in lines_buckets:
                        lines_buckets[bucket] = []
                    lines_buckets[bucket].append(w)
                for bucket in sorted(lines_buckets.keys()):
                    line_words = sorted(lines_buckets[bucket], key=lambda x: x["x0"])
                    line_text = " ".join([w["text"] for w in line_words])
                    if header_re.search(line_text) and not amount_re.search(line_text):
                        continue
                    # Date anywhere in line (first 20 words or full line)
                    search_region = " ".join([w["text"] for w in line_words[:20]]) if len(line_words) > 20 else line_text
                    m = date_re.search(search_region)
                    if not m:
                        continue
                    if not amount_re.search(line_text):
                        continue
                    tx_date = m.group(1)
                    amounts = [ParserUtils.clean_numeric(s) for s in amount_re.findall(line_text)]
                    desc = line_text
                    for x in date_re.findall(desc):
                        desc = desc.replace(x, " ", 1)
                    for x in amount_re.findall(desc):
                        desc = desc.replace(x, " ", 1)
                    desc = re.sub(r"\s+", " ", desc).strip() or "Transaction"
                    debit, credit, balance = 0.0, 0.0, 0.0
                    if len(amounts) >= 3:
                        debit, credit, balance = amounts[0], amounts[1], amounts[2]
                    elif len(amounts) == 2:
                        a1, a2 = amounts[0], amounts[1]
                        balance = a2
                        if prev_balance is not None and a2 > prev_balance:
                            credit = a1
                        else:
                            debit = a1
                    elif len(amounts) == 1:
                        balance = amounts[0]
                    prev_balance = balance if balance else prev_balance
                    rows.append({
                        "Date": tx_date,
                        "Description": desc[:500],
                        "Debit": debit,
                        "Credit": credit,
                        "Balance": balance,
                    })
        if not rows:
            return None
        print(f"[GTBank words] extracted {len(rows)} rows from word layout")
        return pd.DataFrame(rows)

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
            ("Date", ["date", "trans date", "value date", "transaction date"]),
            ("Description", ["description", "particulars", "narration", "details", "remarks"]),
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
