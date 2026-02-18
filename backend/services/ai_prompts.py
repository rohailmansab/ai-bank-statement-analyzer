"""
Universal AI Prompts for Nigerian Bank Statement Analysis.
"""

PROMPT_TRANSACTION_EXTRACTION = """You are an expert Nigerian bank statement parser. Extract ALL transactions.

🏦 SUPPORTED BANKS:
GTBank, UBA, Access Bank, Zenith, First Bank, Ecobank, Polaris, Stanbic IBTC, 
Fidelity, Union Bank, Sterling, Wema, FCMB, Heritage, Keystone, etc.

📋 NIGERIAN BANKING STANDARDS:

**DATE FORMATS:**
- "01-Sep-2025" (GTBank style)
- "01/09/2025" (UBA style)
- "2025-09-01" (Access style)
- "1 Sep 2025" (Zenith style)
- Convert ALL to: "YYYY-MM-DD"

**AMOUNT FORMATS:**
- "300,050.00" (with commas)
- "300050.00" (no commas)
- "₦300,050.00" (with Naira symbol)
- "(8,000.00)" (debit in brackets)
- "-8,000.00" (debit with minus)
- Clean to: 8000.00 (no symbols/commas)

**TRANSACTION TYPES:**

DEBIT (Money OUT) - Look for:
- "TRANSFER TO"
- "NIP TRANSFER"
- "NIBSS Instant Payment"
- "WITHDRAWAL"
- "POS PURCHASE"
- "ATM WITHDRAWAL"
- "CHARGES" / "COMMISSION" / "FEE"
- "VAT" / "STAMP DUTY"
- "AIRTIME" / "DATA"
- "BILL PAYMENT"
- Negative amounts or amounts in brackets

CREDIT (Money IN) - Look for:
- "TRANSFER FROM"
- "DEPOSIT"
- "SALARY CREDIT"
- "REVERSAL" / "REFUND"
- "INTEREST"
- "DIVIDEND"
- Positive amounts without minus/brackets

**DESCRIPTION HANDLING:**
- Multi-line descriptions → Merge into single line
- Remove extra whitespace
- Keep reference numbers
- Preserve sender/receiver names

🔍 EXTRACTION RULES:

1. **EVERY VISIBLE TRANSACTION:**
   Scan entire statement, don't skip any rows

2. **RUNNING BALANCE:**
   Extract balance column (rightmost number usually)

3. **DEBIT vs CREDIT:**
   Use keywords + amount position/format to determine

4. **REFERENCE NUMBERS:**
   Include transaction reference if visible

5. **CHARGES:**
   Include all fees (NIP charges, VAT, stamp duty) as separate transactions

6. **VALUE DATE:**
   If statement shows both transaction date and value date, include both

💾 OUTPUT FORMAT (STRICT JSON):
[
  {
    "date": "2025-09-02",
    "value_date": "2025-09-02",
    "description": "TRANSFER FROM OLAMIDE MUKAILA USMAN VIA OPAY",
    "debit": 0,
    "credit": 300050.00,
    "amount": 300050.00,
    "type": "credit",
    "balance": 304461.22,
    "reference": "10000425090203571",
    "channel": "OPAY"
  }
]

⚠️ CRITICAL RULES:
- Return ONLY raw JSON array (no ```json markdown)
- NO explanations or preamble
- NO invented data
- NO duplicate transactions
- If unsure about debit/credit, use description keywords

📄 BANK STATEMENT TEXT:
{pdf_text}

BEGIN EXTRACTION - JSON ONLY:"""

PROMPT_BANK_DETECTION = """Identify the Nigerian bank from this statement.

🏦 BANK SIGNATURES TO DETECT:

**GTBank (Guaranty Trust Bank):**
- "GTCO" / "Guaranty Trust Bank"
- "gtbank.com"
- Account format: 10 digits

**UBA (United Bank for Africa):**
- "United Bank for Africa" / "UBA"
- "ubagroup.com"
- Account format: 10 digits

**Access Bank:**
- "Access Bank Plc"
- "accessbankplc.com"
- Account format: 10 digits

**Zenith Bank:**
- "Zenith Bank Plc"
- "zenithbank.com"
- Account format: 10 digits

**First Bank:**
- "First Bank of Nigeria"
- "firstbanknigeria.com"
- Account format: 10 digits

🔍 DETECTION STRATEGY:
1. Check for bank name in header
2. Check for website/email domain
3. Check for logo text
4. Check account number format
5. Check statement layout/color references

📄 STATEMENT HEADER (First 1000 characters):
{statement_header}

💾 OUTPUT (SINGLE WORD ONLY):
Return just the bank identifier in lowercase (gtbank, uba, access, zenith, firstbank, ecobank, polaris, stanbic, fidelity, union, other).

RETURN ONE WORD ONLY:"""

PROMPT_DEPOSIT_CLASSIFICATION = """Classify these Nigerian bank deposits for visa application purposes.

🎯 CLASSIFICATION CATEGORIES:
1. Salary
2. Business Income
3. Investment Returns
4. Gift/Family Support
5. Loan ⚠️ RED FLAG
6. Property/Asset Sale
7. Refund/Reversal
8. Other

🔍 CLASSIFICATION LOGIC:
1. Check for patterns: Monthly = Salary, Multiple Sources = Business.
2. Analyze source: Company = Salary/Business, Individual + OPAY = Gift (usually).
3. Check amount: Round millions = Possible loan, Varied = Business.

💾 OUTPUT FORMAT (JSON):
[
  {{
    "date": "2025-09-02",
    "amount": 300050.00,
    "category": "Gift",
    "description": "...",
    "confidence": 0.75,
    "reasoning": "One-time transfer from individual via OPAY",
    "visa_risk": "low",
    "supporting_evidence": "No pattern of repayment",
    "recommendation": "Request affidavit"
  }}
]

📋 DEPOSITS TO CLASSIFY:
{deposits_list}

🕒 VISA APPLICATION DATE: {application_date}

BEGIN CLASSIFICATION - JSON ONLY:"""

PROMPT_ANOMALY_DETECTION = """Analyze this Nigerian bank statement for visa fraud red flags.

⚠️ COMMON FRAUD PATTERNS:
1. Balance Inflation (Large deposits just before application)
2. Circular Transfers (Money moving between applicant's family accounts)
3. Staged Deposits (Multiple round-number deposits)
4. Loan Disguised as Gift (Large deposit followed by equal repayments)

📊 STATEMENT DATA:
Period: {period_start} to {period_end}
Opening Balance: ₦{opening_balance:,.2f}
Closing Balance: ₦{closing_balance:,.2f}
Total Credits: ₦{total_credits:,.2f}

📋 TRANSACTIONS:
{transactions_json}

📅 VISA APPLICATION DATE: {application_date}

💾 OUTPUT FORMAT (JSON):
{{
  "overall_risk_score": 0.65,
  "risk_level": "medium",
  "verdict": "...",
  "red_flags": [
    {{
      "type": "balance_inflation",
      "severity": "high",
      "description": "...",
      "evidence": {{ "pattern": "Deposit -> Withdrawal" }},
      "impact_on_visa": "..."
    }}
  ],
  "positive_indicators": ["..."],
  "recommendations": ["..."]
}}

BEGIN ANALYSIS - JSON ONLY:"""

PROMPT_PROFESSIONAL_SUMMARY = """Generate professional bank statement analysis for visa application.

📊 STATEMENT OVERVIEW:
Bank: {bank_name}
Account Holder: {account_holder}
Period: {period_start} to {period_end}

💰 FINANCIAL SUMMARY:
Opening Balance: ₦{opening_balance:,.2f}
Closing Balance: ₦{closing_balance:,.2f}
Total Credits: ₦{total_credits:,.2f}
Total Debits: ₦{total_debits:,.2f}
Average Monthly Income: ₦{avg_monthly_income:,.2f}

📋 CLASSIFIED LARGE DEPOSITS:
{classified_deposits_summary}

🎯 WRITE (Professional tone for visa officer):
1. EXECUTIVE SUMMARY
2. INCOME ANALYSIS
3. EXPENDITURE ANALYSIS
4. SAVINGS CAPACITY
5. RED FLAGS & CONCERNS
6. POSITIVE INDICATORS
7. VISA OFFICER RECOMMENDATION

BEGIN SUMMARY:"""
