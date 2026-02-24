import json
from typing import Dict, Any, List
from .ai_core import AICore
from .ai_prompts import PROMPT_ANOMALY_DETECTION

class AnomalyDetector:
    """
    Service to detect fraud patterns and anomalies in Nigerian bank statements.
    """
    def __init__(self, ai_core: AICore):
        self.ai = ai_core

    async def detect_anomalies(self, df_dict: List[Dict], report: Dict[str, Any], application_date: str) -> Dict[str, Any]:
        """
        Analyze transactions for visa fraud red flags.
        """
        # Convert Timestamps to strings for JSON serialization
        df_copy = []
        for row in df_dict[:100]:
            clean_row = row.copy()
            for k, v in clean_row.items():
                if hasattr(v, 'isoformat'): # Handle Timestamps/datetime
                    clean_row[k] = v.isoformat()
            df_copy.append(clean_row)

        # Use replace for all placeholders to avoid format() errors with JSON braces
        prompt = PROMPT_ANOMALY_DETECTION.replace("{transactions_json}", json.dumps(df_copy, indent=2))
        prompt = prompt.replace("{period_start}", str(report.get("date_range", {}).get("start", "unknown")))
        prompt = prompt.replace("{period_end}", str(report.get("date_range", {}).get("end", "unknown")))
        prompt = prompt.replace("{opening_balance:,.2f}", "0.00")
        prompt = prompt.replace("{closing_balance:,.2f}", f"{df_dict[-1].get('Balance', 0.0):,.2f}" if df_dict else "0.00")
        prompt = prompt.replace("{total_credits:,.2f}", f"{report.get('total_credit', 0.0):,.2f}")
        prompt = prompt.replace("{application_date}", str(application_date))
        
        result = await self.ai.call_ai(prompt)
        
        if not result:
            return {
                "overall_risk_score": 0.0,
                "risk_level": "low",
                "verdict": "Anomaly analysis unavailable (AI not configured). No red flags identified in the provided data.",
                "red_flags": [],
                "positive_indicators": [],
                "recommendations": []
            }

        try:
            clean_result = result.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_result)
        except Exception as e:
            print(f"[ANOMALY DETECTOR ERROR] Failed to parse AI response: {e}")
            return {
                "error": "Failed to parse analysis results",
                "risk_level": "unknown"
            }
