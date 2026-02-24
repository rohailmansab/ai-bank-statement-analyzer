import pandas as pd
from typing import Dict, Any, List


class ReportBuilder:
    """
    Production-grade report builder. Output matches document spec:
    account_holder, account_details, statement_summary, transactions + AI insights.
    """

    @staticmethod
    def _safe_float(x: Any) -> float:
        try:
            if x is None or (isinstance(x, float) and pd.isna(x)):
                return 0.0
            s = str(x).replace(",", "").replace(" ", "")
            return float(s)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _transactions_list(df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Build list of transactions: date, description, debit, credit, balance."""
        out = []
        for _, row in df.iterrows():
            date_val = row.get("Date")
            if pd.isna(date_val):
                continue
            date_str = date_val.strftime("%Y-%m-%d") if hasattr(date_val, "strftime") else str(date_val)
            out.append({
                "date": date_str,
                "description": str(row.get("Description", "") or "").strip(),
                "debit": ReportBuilder._safe_float(row.get("Debit")),
                "credit": ReportBuilder._safe_float(row.get("Credit")),
                "balance": ReportBuilder._safe_float(row.get("Balance")) if "Balance" in row else None,
            })
        return out

    @staticmethod
    def build_visa_summary(
        df: pd.DataFrame,
        monthly_summary: List[Dict],
        totals: Dict[str, float],
        large_deposits: List[Dict],
        validation_report: Dict[str, Any],
        professional_summary: str = "",
        risk_analysis: Dict[str, Any] = None,
        detected_bank: str = "other",
        extraction_metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Build final report: account_holder, account_details, statement_summary,
        transactions (document spec) plus monthly_summary, totals, AI insights.
        """
        extraction_metadata = extraction_metadata or {}
        total_credit = totals.get("total_income") or totals.get("total_credit") or 0.0
        total_debit = totals.get("total_expense") or totals.get("total_debit") or 0.0
        if extraction_metadata.get("total_credit") is not None:
            total_credit = ReportBuilder._safe_float(extraction_metadata.get("total_credit"))
        if extraction_metadata.get("total_debit") is not None:
            total_debit = ReportBuilder._safe_float(extraction_metadata.get("total_debit"))

        account_holder = {
            "name": extraction_metadata.get("account_holder") or extraction_metadata.get("account_name") or "",
            "address": extraction_metadata.get("address") or "",
        }
        account_details = {
            "account_number": extraction_metadata.get("account_number") or "",
            "currency": extraction_metadata.get("currency") or "NGN",
            "period": extraction_metadata.get("period") or extraction_metadata.get("statement_period") or "",
        }
        statement_summary = {
            "period": extraction_metadata.get("period") or extraction_metadata.get("statement_period") or "",
            "opening_balance": ReportBuilder._safe_float(extraction_metadata.get("opening_balance")),
            "closing_balance": ReportBuilder._safe_float(extraction_metadata.get("closing_balance")),
            "total_debit": total_debit,
            "total_credit": total_credit,
        }
        transactions = ReportBuilder._transactions_list(df)

        return {
            "account_holder": account_holder,
            "account_details": account_details,
            "statement_summary": statement_summary,
            "transactions": transactions,
            "monthly_summary": monthly_summary,
            "totals": totals,
            "large_deposits": large_deposits,
            "professional_summary": professional_summary,
            "risk_analysis": risk_analysis or {},
            "detected_bank": detected_bank,
            "metadata": {
                "total_transactions": len(df),
                "date_range": validation_report.get("date_range"),
                "confidence": validation_report.get("confidence", "high"),
                "validation_issues": validation_report.get("issues", []),
                "parser_used": validation_report.get("parser_used", "unknown"),
            },
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
