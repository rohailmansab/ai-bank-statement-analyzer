import pandas as pd
from typing import Dict, Any

class AnalysisService:
    """
    Production-grade financial analysis service.
    Calculates accurate monthly summaries, averages, and detects large deposits.
    """
    
    @staticmethod
    def generate_monthly_summary(df: pd.DataFrame) -> list:
        """
        Generate monthly summary with proper month extraction from transaction dates.
        Returns: List of {month, income, expenses}
        """
        # Ensure Date is datetime
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        if df.empty:
            return []
        
        # Extract month from ACTUAL transaction dates (not headers)
        df['Month'] = df['Date'].dt.strftime('%B %Y')  # e.g., "September 2025"
        
        monthly_summary = df.groupby('Month', sort=False).agg({
            'Credit': 'sum',
            'Debit': 'sum'
        }).reset_index()
        
        # Sort by date to maintain chronological order
        df_with_month = df[['Month', 'Date']].drop_duplicates('Month')
        monthly_summary = monthly_summary.merge(df_with_month, on='Month')
        monthly_summary = monthly_summary.sort_values('Date')
        
        result = []
        for _, row in monthly_summary.iterrows():
            result.append({
                "month": row['Month'],
                "income": round(float(row['Credit']), 2),
                "expenses": round(float(row['Debit']), 2)
            })
        
        return result
    
    @staticmethod
    def calculate_totals_and_averages(df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate accurate totals and averages.
        Formula: average = total / number_of_months
        """
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        if df.empty:
            return {
                "total_income": 0.0,
                "total_expense": 0.0,
                "average_income": 0.0,
                "average_expense": 0.0
            }
        
        # Calculate totals
        total_income = float(df['Credit'].sum())
        total_expense = float(df['Debit'].sum())
        
        # Count unique months
        df['Month'] = df['Date'].dt.to_period('M')
        num_months = df['Month'].nunique()
        
        # Calculate averages
        average_income = total_income / num_months if num_months > 0 else 0
        average_expense = total_expense / num_months if num_months > 0 else 0
        
        return {
            "total_income": round(total_income, 2),
            "total_expense": round(total_expense, 2),
            "average_income": round(average_income, 2),
            "average_expense": round(average_expense, 2)
        }
    
    @staticmethod
    def detect_large_deposits(df: pd.DataFrame, threshold: float = 50000) -> list:
        """
        Detect large/unusual deposits (Credit >= threshold).
        Returns: List of {Date, Description, Amount, Category}
        """
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        
        # Filter credits >= threshold
        large_deposits = df[df['Credit'] >= threshold].copy()
        
        if large_deposits.empty:
            return []
        
        # Sort by date (most recent first)
        large_deposits = large_deposits.sort_values('Date', ascending=False)
        
        result = []
        for _, row in large_deposits.iterrows():
            result.append({
                "Date": row['Date'].strftime('%d/%b/%Y'),
                "Description": str(row['Description']),
                "Amount": float(row['Credit'])
            })
        
        return result
    
    @staticmethod
    def validate_analysis_output(monthly_summary: list, totals: Dict[str, float], 
                                 large_deposits: list, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Final sanity check before sending to frontend.
        Returns: {is_valid, issues, confidence}
        """
        issues = []
        confidence = "high"
        
        # Check 1: Monthly summary should not be empty if we have data
        if len(df) > 0 and len(monthly_summary) == 0:
            issues.append("Monthly summary is empty despite having transactions")
            confidence = "low"
        
        # Check 2: Averages should be reasonable
        if totals["total_income"] > 100000 and totals["average_income"] < 1000:
            issues.append("Average income suspiciously low compared to total")
            confidence = "low"
        
        # Check 3: Large deposits should exist if total credit is high
        if totals["total_income"] > 500000 and len(large_deposits) == 0:
            # This might be okay (many small deposits), so just medium confidence
            confidence = "medium"
        
        # Check 4: Totals should match sum of monthly summary
        if monthly_summary:
            summary_total_income = sum(m["income"] for m in monthly_summary)
            summary_total_expense = sum(m["expenses"] for m in monthly_summary)
            
            income_diff = abs(summary_total_income - totals["total_income"])
            expense_diff = abs(summary_total_expense - totals["total_expense"])
            
            # Allow 1% tolerance for rounding
            if income_diff > totals["total_income"] * 0.01:
                issues.append(f"Monthly summary income ({summary_total_income}) doesn't match total ({totals['total_income']})")
                confidence = "medium"
            
            if expense_diff > totals["total_expense"] * 0.01:
                issues.append(f"Monthly summary expenses ({summary_total_expense}) doesn't match total ({totals['total_expense']})")
                confidence = "medium"
        
        return {
            "is_valid": confidence != "low",
            "issues": issues,
            "confidence": confidence
        }
