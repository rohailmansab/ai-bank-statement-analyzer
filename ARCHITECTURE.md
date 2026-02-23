# Bank Statement Analyzer – Architecture

This document describes the **multi-step, robust pipeline** used to parse diverse bank statement PDFs with minimal reliance on large AI prompts.

## Pipeline Overview

| Step | Action | Tools / Approach |
|------|--------|------------------|
| **1** | **Text & table extraction** | `pdfplumber` for native PDFs; optional **OCR** (`pytesseract` + `pdf2image`) for scanned documents |
| **2** | **Rule-based parsing** | Config-driven parser first (bank detection + JSON config), then heuristic parsers (table, text, word, GTBank multiline, summary table) |
| **3** | **Data cleaning & normalization** | `DataNormalizer`: column detection, amount/date cleaning, deduplication |
| **4** | **Targeted AI** | AI used only for **categorization** (e.g. large deposits, risk), not for full-document extraction |
| **5** | **Fallback** | Full-document AI extraction only when all rule-based parsers fail |

## Key Components

- **`backend/config/bank_formats/`** – JSON configs per bank (e.g. `gtbank.json`, `uba.json`, `default.json`). Each config defines:
  - `keywords` for rule-based bank detection
  - `key_value_patterns` (regex) for account number, opening/closing balance, statement period
  - `table_column_mapping` (PDF header → standard field: Date, Description, Credit, Debit, Balance)
  - `date_formats` and `amount_cleanup` hints
- **`bank_config.py`** – Loads configs, `detect_bank_from_text()`, `extract_key_values()` for metadata
- **`parser_config_driven.py`** – Uses selected bank config for key-value extraction and table column mapping
- **`pdf_extractor.py`** – Central extraction (text + tables via pdfplumber); optional `extract_text_via_ocr()` for scanned PDFs
- **`parser_router.py`** – Orchestrates: config-driven → summary/table/text/word/multiline parsers; OCR when no text; AI only as last resort

## Adding a New Bank Format

1. Add a new JSON file under `backend/config/bank_formats/`, e.g. `access.json`.
2. Set `bank_id`, `name`, `keywords` (for detection), `key_value_patterns`, `table_column_mapping`, and `date_formats` as needed.
3. No code changes required; the config-driven parser and router will pick it up.

## Optional OCR (Scanned PDFs)

- If the PDF has no or very little extractable text, the router attempts OCR via `pytesseract` and `pdf2image`.
- Install: Tesseract on the system, and `pip install pytesseract pdf2image`.
- OCR output is then parsed with the same line-based logic as the text parser.

## AI Usage

- **Normal path**: AI is used only for **targeted** tasks (e.g. categorizing large deposits, risk/anomaly detection, professional summary).
- **Fallback path**: When every rule-based parser fails or returns low-confidence results, the system can fall back to sending a truncated extract to an LLM for transaction extraction (kept within token limits).
