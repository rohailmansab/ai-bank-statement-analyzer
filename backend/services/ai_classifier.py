import json
from typing import List, Dict, Any
from .ai_core import AICore
from .ai_prompts import PROMPT_DEPOSIT_CLASSIFICATION

class AIClassifier:
    """
    Advanced transaction classifier for Nigerian bank statements.
    """
    def __init__(self, ai_core: AICore):
        self.ai = ai_core

    async def classify_large_deposits(self, deposits: List[Dict], application_date: str) -> List[Dict]:
        """
        Classify a list of large deposits with visa-specific risk assessment.
        """
        if not deposits:
            return []

        # Prepare list for prompt
        deposits_list = "\n".join([
            f"- {d.get('Date')}: ₦{d.get('Credit', 0):,.2f} - {d.get('Description')}"
            for d in deposits
        ])

        prompt = PROMPT_DEPOSIT_CLASSIFICATION.format(
            deposits_list=deposits_list,
            application_date=application_date
        )

        result = await self.ai.call_ai(prompt)
        
        if not result:
            return deposits

        try:
            clean_result = result.replace("```json", "").replace("```", "").strip()
            classifications = json.loads(clean_result)
            
            # Merge classifications back into deposits
            # Assuming AI preserves the order or we match by date/amount
            for i, deposit in enumerate(deposits):
                if i < len(classifications):
                    deposit.update(classifications[i])
            
            return deposits
        except Exception as e:
            print(f"[AI CLASSIFIER ERROR] Failed to parse batch classification: {e}")
            return deposits

    async def classify_transaction(self, description: str) -> str:
        """
        Simple single-description classification (legacy support).
        """
        prompt = (
            "Classify the following bank transaction description into exactly ONE of these categories: "
            "Salary, Business Income, Loan, Gift, Refund, Transfer, Bills, Shopping, Investment, Misc. "
            "Return ONLY the category name and nothing else.\n\n"
            f"Description: {description}"
        )
        
        result = await self.ai.call_ai(prompt)
        if result:
            return result.strip()
        return "Misc"

