from .ai_core import AICore
from .ai_prompts import PROMPT_PROFESSIONAL_SUMMARY
from typing import Dict, Any

class ProfessionalSummarizer:
    """
    Service to generate visa-ready executive summaries using AI.
    """
    def __init__(self, ai_core: AICore):
        self.ai = ai_core

    async def generate_summary(self, 
                                 bank_name: str, 
                                 account_holder: str, 
                                 report: Dict[str, Any], 
                                 totals: Dict[str, float],
                                 classified_deposits_summary: str) -> str:
        """
        Generate a professional executive summary for visa officers.
        """
        # Use replace for all placeholders to avoid format() errors
        prompt = PROMPT_PROFESSIONAL_SUMMARY
        prompt = prompt.replace("{bank_name}", str(bank_name))
        prompt = prompt.replace("{account_holder}", str(account_holder))
        prompt = prompt.replace("{period_start}", str(report.get("metadata", {}).get("date_range", {}).get("start", "unknown")))
        prompt = prompt.replace("{period_end}", str(report.get("metadata", {}).get("date_range", {}).get("end", "unknown")))
        prompt = prompt.replace("{opening_balance:,.2f}", "0.00")
        prompt = prompt.replace("{closing_balance:,.2f}", f"{totals.get('total_income', 0.0) - totals.get('total_expense', 0.0):,.2f}")
        prompt = prompt.replace("{total_credits:,.2f}", f"{totals.get('total_income', 0.0):,.2f}")
        prompt = prompt.replace("{total_debits:,.2f}", f"{totals.get('total_expense', 0.0):,.2f}")
        prompt = prompt.replace("{avg_monthly_income:,.2f}", f"{totals.get('average_income', 0.0):,.2f}")
        prompt = prompt.replace("{classified_deposits_summary}", str(classified_deposits_summary))
        
        summary = await self.ai.call_ai(prompt)
        if summary and summary.strip():
            return summary.strip()
        # Rule-based fallback when AI is unavailable
        dr = report.get("date_range") or report.get("metadata", {}).get("date_range") or {}
        start = dr.get("start", "unknown")
        end = dr.get("end", "unknown")
        total_credits = totals.get("total_income") or totals.get("total_credit") or 0.0
        total_debits = totals.get("total_expense") or totals.get("total_debit") or 0.0
        n_tx = report.get("total_transactions", 0)
        return (
            f"This statement is for {account_holder} with {bank_name}, covering {start} to {end}. "
            f"Total credits: {total_credits:,.2f} NGN; total debits: {total_debits:,.2f} NGN; "
            f"transaction count: {n_tx}. "
            f"(Executive summary generated from statement data; AI was unavailable.)"
        )
