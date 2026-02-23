import pandas as pd
import re
from typing import Dict, Any, List

# Fixed report structure (client format): same sections and labels for every upload.
# All figures (totals, monthly_summary, large_deposits) are computed only from the uploaded statement.
REPORT_FORMAT_VERSION = "standard"
DATA_SOURCE_LABEL = "uploaded_statement"


def _safe_float(x: Any) -> float:
    """Ensure value is float for JSON (strip PDF artifacts like '& &5&,&7&0&8&')."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    s = re.sub(r"[^\d.\-\()]", "", s).replace(",", "").replace("(", "-").replace(")", "")
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


class ReportBuilder:
    """
    Builds reports in a fixed, client-standard format.
    Layout and section names are always the same; every number is derived
    solely from the uploaded bank statement (no mixing with other data).
    """
    
    @staticmethod
    def build_visa_summary(df: pd.DataFrame, monthly_summary: List[Dict], 
                          totals: Dict[str, float], large_deposits: List[Dict],
                          validation_report: Dict[str, Any],
                          professional_summary: str = "",
                          risk_analysis: Dict[str, Any] = None,
                          detected_bank: str = "other") -> Dict[str, Any]:
        """
        Build final report: fixed format, all calculations from the uploaded statement.
        Ensures all numeric fields are clean floats (no garbled strings) for PDF/JSON.
        """
        clean_totals = {
            "total_income": _safe_float(totals.get("total_income")),
            "total_expense": _safe_float(totals.get("total_expense")),
            "average_income": _safe_float(totals.get("average_income")),
            "average_expense": _safe_float(totals.get("average_expense")),
        }
        clean_monthly = [
            {
                "month": m.get("month", ""),
                "income": _safe_float(m.get("income")),
                "expenses": _safe_float(m.get("expenses")),
            }
            for m in (monthly_summary or [])
        ]
        clean_large = []
        for d in (large_deposits or []):
            clean_large.append({
                "Date": str(d.get("Date", ""))[:50],
                "Description": str(d.get("Description", ""))[:200],
                "Amount": _safe_float(d.get("Amount") or d.get("Credit")),
                "Category": str(d.get("Category", "")),
            })
        return {
            "report_format": REPORT_FORMAT_VERSION,
            "data_source": DATA_SOURCE_LABEL,
            "monthly_summary": clean_monthly,
            "totals": clean_totals,
            "large_deposits": clean_large,
            "professional_summary": professional_summary,
            "risk_analysis": risk_analysis or {},
            "detected_bank": detected_bank,
            "metadata": {
                "total_transactions": len(df),
                "date_range": validation_report.get("date_range"),
                "confidence": validation_report.get("confidence", "high"),
                "validation_issues": validation_report.get("issues", []),
                "parser_used": validation_report.get("parser_used", "unknown")
            }
        }
    
    @staticmethod
    def add_extraction_metadata(report: Dict[str, Any], parser_id: str, 
                                diagnostic_logs: List[str]) -> Dict[str, Any]:
        """
        Add extraction metadata for debugging and transparency.
        """
        report["extraction_status"] = {
            "status": "success",
            "parser_used": parser_id,
            "diagnostic_logs": diagnostic_logs[-5:] if len(diagnostic_logs) > 5 else diagnostic_logs
        }
        return report
