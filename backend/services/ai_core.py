import os
import json
import asyncio
from typing import Optional, Any, Dict, List
import openai
from google import genai
from backend.config import OPENAI_API_KEY, GEMINI_API_KEY
from .ai_prompts import PROMPT_BANK_DETECTION

class AICore:
    """
    Centralized AI orchestration layer with retry logic and fallback.
    """
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        self.gemini_client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

    async def call_ai(self, prompt: str, system_instruction: str = "", model_preference: str = "gemini") -> Optional[str]:
        """
        Unified method to call AI with fallback.
        """
        print(f"[AI CORE] Calling {model_preference} model...")
        
        # Try Gemini first if preferred
        if model_preference == "gemini" and self.gemini_client:
            try:
                print(f"[AI CORE] Gemini prompt length: {len(prompt)}")
                response = self.gemini_client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt,
                    config={"system_instruction": system_instruction} if system_instruction else None
                )
                if response and hasattr(response, 'text'):
                    print(f"[AI CORE] Gemini success! Response length: {len(response.text)}")
                    return response.text.strip()
                else:
                    print(f"[AI CORE] Gemini returned empty response or invalid format: {response}")
            except Exception as e:
                print(f"[AI CORE ERROR] Gemini failed: {e}")
                # Fallback to OpenAI if Gemini fails

        # Fallback/Primary OpenAI
        if self.openai_client:
            try:
                print(f"[AI CORE] Falling back to OpenAI...")
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})

                response = self.openai_client.chat.completions.create(
                    model="gpt-4o",  # Prefer 4o for data extraction
                    messages=messages,
                    temperature=0
                )
                result = response.choices[0].message.content.strip()
                print(f"[AI CORE] OpenAI success! Response length: {len(result)}")
                return result
            except Exception as e:
                print(f"[AI CORE ERROR] OpenAI failed: {e}")

        return None

    async def extract_json(self, text: str, prompt_template: str) -> List[Dict[str, Any]]:
        """
        Helper to extract JSON using AI.
        """
        print(f"[AI EXTRACTION] Starting JSON extraction for {len(text)} chars of text...")
        prompt = prompt_template.replace("{pdf_text}", text)
        result = await self.call_ai(prompt)
        
        if not result:
            print("[AI EXTRACTION] AI returned None")
            return []

        try:
            # Clean possible markdown
            clean_result = result.replace("```json", "").replace("```", "").strip()
            print(f"[AI EXTRACTION] Cleaned JSON preview: {clean_result[:100]}...")
            data = json.loads(clean_result)
            if isinstance(data, list):
                print(f"[AI EXTRACTION] Successfully parsed {len(data)} transactions")
                return data
            else:
                print(f"[AI EXTRACTION] AI returned object instead of list: {type(data)}")
                # Try to find list within object
                for key, val in data.items():
                    if isinstance(val, list):
                        print(f"[AI EXTRACTION] Found list in key: {key}, count: {len(val)}")
                        return val
                return []
        except Exception as e:
            print(f"[AI CORE ERROR] JSON Parsing failed: {e}")
            print(f"[AI CORE ERROR] Raw content was: {result[:500]}...")
            return []

class BankDetector:
    """
    Service to identify Nigerian banks from statement text.
    """
    def __init__(self, ai_core: AICore):
        self.ai = ai_core

    async def detect_bank(self, header_text: str) -> str:
        """
        Detect bank name from header.
        """
        prompt = PROMPT_BANK_DETECTION.format(statement_header=header_text[:1000])
        bank = await self.ai.call_ai(prompt)
        
        if not bank:
            return "other"
            
        bank = bank.lower().strip()
        # Clean up common variations
        valid_banks = ['gtbank', 'uba', 'access', 'zenith', 'firstbank', 'ecobank', 'polaris', 'stanbic', 'fidelity', 'union']
        for vb in valid_banks:
            if vb in bank:
                return vb
                
        return "other"
