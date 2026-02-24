import pandas as pd
from typing import Dict, Any, Tuple

class DataValidator:
    """
    Production-grade validation layer.
    Ensures extracted data passes sanity checks before analysis.
    """
    
    @staticmethod
    def validate(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Main validation pipeline.
        Returns: (is_valid, validation_report)
        """
        if df.empty:
            return False, {"error": "DataFrame is empty"}
        
        report = {
            "total_transactions": len(df),
            "total_credit": float(df['Credit'].sum()),
            "total_debit": float(df['Debit'].sum()),
            "date_range": None,
            "months_found": 0,
            "issues": [],
            "confidence": "high"
        }
        
        # Validation 1: Check for reasonable totals
        if not DataValidator._validate_totals(df, report):
            report["issues"].append("Totals validation failed")
            report["confidence"] = "low"
        
        # Validation 2: Check date range
        if not DataValidator._validate_dates(df, report):
            report["issues"].append("Date validation failed")
            report["confidence"] = "medium"
        
        # Validation 3: Check for missing critical data
        if not DataValidator._validate_completeness(df, report):
            report["issues"].append("Data completeness check failed")
            report["confidence"] = "low"
        
        # Validation 4: Check for logical consistency
        if not DataValidator._validate_logic(df, report):
            report["issues"].append("Logical consistency check failed")
            report["confidence"] = "medium"
        
        is_valid = len(report["issues"]) == 0 or report["confidence"] != "low"
        
        return is_valid, report
    
    @staticmethod
    def _validate_totals(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        """Validate that totals are reasonable and realistic."""
        total_credit = report["total_credit"]
        total_debit = report["total_debit"]
        max_credit = float(df["Credit"].max()) if "Credit" in df.columns and len(df) else 0.0
        max_debit = float(df["Debit"].max()) if "Debit" in df.columns and len(df) else 0.0

        # Check 1: At least one of credit or debit should be non-zero
        if total_credit == 0 and total_debit == 0:
            print("[VALIDATION FAILED] Both credit and debit are zero")
            return False
        
        # Check 2: Totals should not be suspiciously small
        if len(df) > 10:  # If we have many transactions
            avg_transaction = (total_credit + total_debit) / len(df)
            if avg_transaction < 100:  # Less than 100 Naira average
                print(f"[VALIDATION FAILED] Average transaction ({avg_transaction}) is too small")
                return False
        
        # Check 3: If we have large balance values, credits/debits should also be large
        if 'Balance' in df.columns:
            max_balance = df['Balance'].abs().max()
            if max_balance > 100000 and (total_credit < 1000 or total_debit < 1000):
                print(f"[VALIDATION FAILED] Balance ({max_balance}) is large but totals are small")
                return False
        
        if len(df) >= 2:
            # For even small statements, at least one amount should be realistic (>1000)
            # This prevents picking up Day/Year values (e.g., 30 and 2026) as amounts
            if max_credit < 1000 and max_debit < 1000:
                print(f"[VALIDATION FAILED] Max amounts ({max_credit}, {max_debit}) are too small to be real transactions")
                return False
                
        if len(df) > 5:
            # At least one side should have realistic amounts (allow one column small, e.g. debit-heavy statement)
            if max_credit < 5000 and max_debit < 5000:
                print(f"[VALIDATION FAILED] Max credit ({max_credit}) and debit ({max_debit}) are both < 5,000 in {len(df)} rows")
                return False
        
        # Check 5: For many rows, at least one total should be non-trivial
        if len(df) > 10 and total_credit < 500 and total_debit < 500:
            print(f"[VALIDATION FAILED] Totals too small for {len(df)} transactions")
            return False
        
        return True
    
    @staticmethod
    def _validate_dates(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        """Validate date range and extract months. Always sets date_range/months_found when possible."""
        try:
            df = df.copy()
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            if df.empty:
                report["months_found"] = report.get("months_found", 0)
                return False
            
            min_date = df['Date'].min()
            max_date = df['Date'].max()
            
            report["date_range"] = {
                "start": min_date.strftime('%Y-%m-%d'),
                "end": max_date.strftime('%Y-%m-%d')
            }
            
            df['Month'] = df['Date'].dt.to_period('M')
            report["months_found"] = df['Month'].nunique()
            
            if report["months_found"] < 1:
                return False
            
            date_span_days = (max_date - min_date).days
            if date_span_days > 365 * 20:
                print(f"[VALIDATION FAILED] Date span ({date_span_days} days) is too large")
                return False
            if date_span_days > 365 * 10:
                print(f"[VALIDATION WARNING] Date span ({date_span_days} days) is large but accepting")
            
            from datetime import datetime
            current_year = datetime.now().year
            min_year = min_date.year
            max_year = max_date.year
            if min_year < current_year - 25 or max_year > current_year + 2:
                print(f"[VALIDATION WARNING] Years ({min_year}-{max_year}) unusual but accepting")
            
            return True
            
        except Exception as e:
            print(f"[VALIDATION ERROR] Date validation failed: {e}")
            report["months_found"] = report.get("months_found", 1)
            return False
    
    @staticmethod
    def _validate_completeness(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        """Check that we have complete data. Lenient for GTBank-style outputs."""
        if 'Description' not in df.columns:
            return True
        empty_descriptions = df['Description'].isna().sum() + (df['Description'].astype(str).str.strip() == '').sum()
        if empty_descriptions > len(df) * 0.85:  # Only fail if >85% empty (was 50%)
            return False
        
        rows_with_amounts = ((df['Credit'] > 0) | (df['Debit'] > 0)).sum()
        if rows_with_amounts < len(df) * 0.2:  # At least 20% have amounts (was 30%)
            return False
        
        return True
    
    @staticmethod
    def _validate_logic(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        """Check logical consistency and large deposit detection."""
        # Check 1: A transaction should not have both credit AND debit
        both_nonzero = ((df['Credit'] > 0) & (df['Debit'] > 0)).sum()
        if both_nonzero > len(df) * 0.1:  # More than 10% have both
            # This might be okay for some statement formats, so just warn
            pass
        
        # Check 2: Validate large deposit detection
        # If total credit is large, there should be at least some large deposits
        total_credit = df['Credit'].sum()
        max_credit = df['Credit'].max()
        
        if total_credit > 500000:  # If total credit is substantial
            if max_credit < 50000:
                print(f"[VALIDATION WARNING] Total credit is {total_credit} but max credit is only {max_credit}")
                print("[VALIDATION WARNING] Large deposits (>=50000) might not be detected correctly")
                # This is a warning, not a failure
        
        return True
    
    @staticmethod
    def should_retry_extraction(validation_report: Dict[str, Any]) -> bool:
        """Determine if extraction should be retried with fallback parser."""
        total_tx = validation_report.get("total_transactions", 0)
        total_credit = validation_report.get("total_credit", 0) or 0
        total_debit = validation_report.get("total_debit", 0) or 0
        
        # Accept if we have any usable data with real amounts (avoid rejecting gtbank-style output)
        if total_tx >= 5 and (total_credit > 0 or total_debit > 0):
            return False
        
        if validation_report.get("confidence") == "low":
            return True
        
        if total_tx <= 10:
            return True
        
        if total_credit == 0 and total_debit == 0:
            return True
        
        if validation_report.get("months_found", 0) == 0:
            return True
        
        return False
