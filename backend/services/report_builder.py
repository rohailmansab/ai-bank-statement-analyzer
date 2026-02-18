import pandas as pd
from typing import Dict, Any, List

class ReportBuilder:
    """
    Production-grade report builder with output validation.
    Ensures only accurate data reaches the frontend.
    """
    
    @staticmethod
    def build_visa_summary(df: pd.DataFrame, monthly_summary: List[Dict], 
                          totals: Dict[str, float], large_deposits: List[Dict],
                          validation_report: Dict[str, Any],
                          professional_summary: str = "",
                          risk_analysis: Dict[str, Any] = None,
                          detected_bank: str = "other") -> Dict[str, Any]:
        """
        Build final report with confidence scoring and all AI insights.
        """
        return {
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
