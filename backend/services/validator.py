import pandas as pd
from typing import Dict, Any, Tuple

class DataValidator:
    @staticmethod
    def validate(df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        if df.empty:
            return False, {"error": "DataFrame is empty"}

        if "Credit" not in df.columns:
            df["Credit"] = 0.0
        if "Debit" not in df.columns:
            df["Debit"] = 0.0

        max_credit = float(df["Credit"].max()) if not df["Credit"].empty else 0.0
        max_debit  = float(df["Debit"].max())  if not df["Debit"].empty  else 0.0

        report = {
            "total_transactions": len(df),
            "total_credit": float(df['Credit'].sum()),
            "total_debit": float(df['Debit'].sum()),
            "date_range": None,
            "months_found": 0,
            "issues": [],
            "confidence": "high",
            "_max_credit": max_credit,
            "_max_debit": max_debit,
        }
        
        if not DataValidator._validate_totals(df, report):
            report["issues"].append("Totals validation failed")
            report["confidence"] = "low"
        
        if not DataValidator._validate_dates(df, report):
            report["issues"].append("Date validation failed")
            report["confidence"] = "medium"
        
        if not DataValidator._validate_completeness(df, report):
            report["issues"].append("Data completeness check failed")
            report["confidence"] = "low"
        
        if not DataValidator._validate_logic(df, report):
            report["issues"].append("Logical consistency check failed")
            report["confidence"] = "medium"
        
        is_valid = len(report["issues"]) == 0 or report["confidence"] != "low"
        report.pop("_max_credit", None)
        report.pop("_max_debit", None)
        return is_valid, report
    
    @staticmethod
    def _validate_totals(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        total_credit = report.get("total_credit", 0.0)
        total_debit  = report.get("total_debit", 0.0)
        mc = report.get("_max_credit", 0.0)
        md = report.get("_max_debit", 0.0)

        if total_credit == 0 and total_debit == 0:
            print("[VALIDATION FAILED] Both credit and debit are zero")
            return False
        
        if len(df) > 10:
            avg_transaction = (total_credit + total_debit) / len(df)
            if avg_transaction < 100:
                print(f"[VALIDATION FAILED] Average transaction ({avg_transaction}) is too small")
                return False
        
        if 'Balance' in df.columns:
            max_balance = df['Balance'].abs().max()
            if max_balance > 100000 and (total_credit < 1000 or total_debit < 1000):
                print(f"[VALIDATION FAILED] Balance ({max_balance}) is large but totals are small")
                return False

        if len(df) >= 2:
            if mc < 1000 and md < 1000:
                print(f"[VALIDATION FAILED] Max amounts ({mc}, {md}) are too small to be real transactions")
                return False
                
        if len(df) > 5:
            if mc < 50000 and md < 50000:
                print(f"[VALIDATION FAILED] Max credit ({mc}) and debit ({md}) are both < 50,000 in {len(df)} rows")
                return False
        
        if total_credit < 1000 and len(df) > 5:
            print(f"[VALIDATION FAILED] Total credit ({total_credit}) is too small for {len(df)} transactions")
            return False
        
        return True
    
    @staticmethod
    def _validate_dates(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        try:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])
            
            if df.empty:
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
            if date_span_days > 365 * 10:
                return False
            
            from datetime import datetime
            current_year = datetime.now().year
            if min_date.year < current_year - 5 or max_date.year > current_year + 1:
                return False
            
            return True
            
        except Exception as e:
            print(f"[VALIDATION ERROR] Date validation failed: {e}")
            return False
    
    @staticmethod
    def _validate_completeness(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        empty_descriptions = df['Description'].isna().sum() + (df['Description'] == '').sum()
        if empty_descriptions > len(df) * 0.5:
            return False
        
        rows_with_amounts = ((df['Credit'] > 0) | (df['Debit'] > 0)).sum()
        if rows_with_amounts < len(df) * 0.3:
            return False
        
        return True
    
    @staticmethod
    def _validate_logic(df: pd.DataFrame, report: Dict[str, Any]) -> bool:
        total_credit = float(df['Credit'].sum()) if 'Credit' in df.columns else 0.0
        mx_c = float(df['Credit'].max()) if 'Credit' in df.columns and not df['Credit'].empty else 0.0
        if total_credit > 500000 and mx_c < 50000:
            print(f"[VALIDATION WARNING] Total credit is {total_credit} but max credit is only {mx_c}")
        return True
    
    @staticmethod
    def should_retry_extraction(validation_report: Dict[str, Any]) -> bool:
        if validation_report.get("confidence") == "low":
            return True
        if validation_report.get("total_credit", 0) == 0 and validation_report.get("total_debit", 0) == 0:
            return True
        if validation_report.get("months_found", 0) == 0:
            return True
        return False