import pandas as pd
import re
from typing import Dict, Optional, Tuple
from datetime import datetime

class SmartColumnDetector:
    """
    Intelligent column detection for bank statements.
    Automatically identifies Date, Description, Credit, Debit, and Balance columns
    based on data patterns rather than fixed positions.
    """
    
    @staticmethod
    def detect_columns(df: pd.DataFrame) -> Dict[str, str]:
        """
        Detect column roles dynamically.
        Returns: {role: column_name} mapping
        """
        if df.empty:
            return {}
        
        detected = {
            'Date': None,
            'Description': None,
            'Credit': None,
            'Debit': None,
            'Balance': None
        }
        
        # Step 1: Detect Date column
        detected['Date'] = SmartColumnDetector._detect_date_column(df)
        
        # Step 2: Detect numeric columns (potential amount columns)
        numeric_cols = SmartColumnDetector._get_numeric_columns(df)
        print(f"[DEBUG] Numeric columns found: {numeric_cols}")
        
        # Step 3: Detect Credit and Debit columns by NAME first (High priority)
        credit_col_name, debit_col_name = SmartColumnDetector._detect_credit_debit_by_name(df, numeric_cols)
        detected['Credit'] = credit_col_name
        detected['Debit'] = debit_col_name
        print(f"[DEBUG] Name-based detection: Credit={detected['Credit']}, Debit={detected['Debit']}")
        
        # Step 4: Detect Balance column (From remaining numeric columns)
        remaining_numeric = [c for c in numeric_cols if c not in [detected['Credit'], detected['Debit']]]
        print(f"[DEBUG] Remaining for Balance: {remaining_numeric}")
        detected['Balance'] = SmartColumnDetector._detect_balance_column(df, remaining_numeric)
        
        # Step 5: If Credit or Debit still missing, detect by mutual exclusivity
        if not detected['Credit'] or not detected['Debit']:
            # Refresh candidates (excluding Balance)
            remaining_for_amt = [c for c in numeric_cols if c != detected['Balance']]
            print(f"[DEBUG] Missing one amount column. Candidates: {remaining_for_amt}")
            c_col, d_col = SmartColumnDetector._detect_credit_debit_by_pattern(
                df, remaining_for_amt, detected['Credit'], detected['Debit']
            )
            detected['Credit'] = c_col
            detected['Debit'] = d_col
            print(f"[DEBUG] After pattern detection: Credit={detected['Credit']}, Debit={detected['Debit']}")
        
        # Step 6: Detect Description column
        print(f"[DEBUG] Finalizing detection with detected dict: {detected}")
        detected['Description'] = SmartColumnDetector._detect_description_column(
            df, [detected['Date'], detected['Credit'], detected['Debit'], detected['Balance']]
        )
        
        return detected
    
    @staticmethod
    def _detect_date_column(df: pd.DataFrame) -> Optional[str]:
        """Find column with date-like values."""
        date_pattern = re.compile(
            r'\d{1,2}[-/\s](Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
            r'January|February|March|April|May|June|July|August|September|October|November|December|'
            r'\d{1,2})[-/\s]\d{2,4}',
            re.IGNORECASE
        )
        
        for col in df.columns:
            # Check if column values match date pattern
            sample = df[col].dropna().astype(str).head(20)
            if len(sample) == 0:
                continue
            
            matches = sum(1 for val in sample if date_pattern.search(str(val)))
            match_ratio = matches / len(sample)
            
            if match_ratio > 0.5:  # More than 50% look like dates
                return col
        
        return None
    
    @staticmethod
    def _get_numeric_columns(df: pd.DataFrame) -> list:
        """
        Get columns that contain numeric values.
        Uses two-pass approach:
        1. Find columns with max > 50,000 (primary money columns)
        2. If found, also include columns with max > 1,000 (secondary like debits)
        """
        numeric_cols = []
        potential_cols = []  # Columns with smaller values
        
        for col in df.columns:
            # Try to convert to numeric
            sample = df[col].dropna()
            if len(sample) == 0:
                continue
            
            # Clean and test conversion
            cleaned = sample.astype(str).str.replace(',', '').str.replace(' ', '').str.replace('₦', '').str.replace('NGN', '')
            
            try:
                numeric_values = pd.to_numeric(cleaned, errors='coerce').dropna()
                
                if len(numeric_values) == 0:
                    continue
                
                max_value = numeric_values.abs().max()
                
                # Primary money columns (>50k)
                if max_value > 50000:
                    print(f"[MONEY COLUMN DETECTED] {col}: max_value = {max_value:,.2f}")
                    numeric_cols.append(col)
                # Secondary money columns (>100 but <50k)
                elif max_value > 100:
                    print(f"[POTENTIAL MONEY COLUMN] {col}: max_value = {max_value:,.2f} (waiting for confirmation)")
                    potential_cols.append((col, max_value))
                elif max_value > 5:
                    print(f"[SMALL MONEY COLUMN] {col}: max_value = {max_value:,.2f} (likely debit/charge)")
                    potential_cols.append((col, max_value))
                else:
                    print(f"[REJECTED] {col}: max_value = {max_value:,.2f} (too small, likely index/line number)")
                    
            except (ValueError, TypeError):
                # Check if at least 70% are numeric
                numeric_count = 0
                valid_values = []
                
                for val in cleaned:
                    try:
                        num_val = float(val)
                        numeric_count += 1
                        valid_values.append(abs(num_val))
                    except:
                        pass
                
                if numeric_count / len(cleaned) > 0.7 and valid_values:
                    max_value = max(valid_values)
                    
                    if max_value > 50000:
                        print(f"[MONEY COLUMN DETECTED] {col}: max_value = {max_value:,.2f}")
                        numeric_cols.append(col)
                    elif max_value > 1000:
                        print(f"[POTENTIAL MONEY COLUMN] {col}: max_value = {max_value:,.2f} (waiting for confirmation)")
                        potential_cols.append((col, max_value))
                    else:
                        print(f"[REJECTED] {col}: max_value = {max_value:,.2f} (too small)")
        
        # If we found at least one large money column, include potential columns
        if numeric_cols and potential_cols:
            print(f"\n[CONFIRMATION] Found {len(numeric_cols)} large money columns, including {len(potential_cols)} potential columns")
            for col, max_val in potential_cols:
                print(f"[CONFIRMED] {col}: max_value = {max_val:,.2f} (likely debit/small transactions)")
                numeric_cols.append(col)
        elif potential_cols and not numeric_cols:
            print(f"\n[WARNING] No large columns found, but {len(potential_cols)} potential columns exist")
            # Include them anyway - might be a statement with only small transactions
            for col, max_val in potential_cols:
                print(f"[ACCEPTED] {col}: max_value = {max_val:,.2f}")
                numeric_cols.append(col)
        
        return numeric_cols
    
    @staticmethod
    def _detect_balance_column(df: pd.DataFrame, numeric_cols: list) -> Optional[str]:
        """
        Detect balance column.
        Balance characteristics:
        - Cumulative (changes gradually)
        - Rarely zero
        - Usually the largest absolute values
        - NEVER named 'credit' or 'debit'
        """
        if not numeric_cols:
            return None
        
        best_col = None
        best_score = -1
        
        # Priority 1: Check for column names containing 'balance', 'closing', 'bal'
        for col in numeric_cols:
            col_lower = str(col).lower()
            if any(kw in col_lower for kw in ['balance', 'closing', 'bal']):
                if not any(sw in col_lower for sw in ['credit', 'debit', 'inflow', 'outflow']):
                    print(f"[COLUMN NAMES] Picked {col} as Balance based on name")
                    return col

        for col in numeric_cols:
            col_lower = str(col).lower()
            # Skip columns that are clearly Credit or Debit
            if any(keyword in col_lower for keyword in ['credit', 'debit', 'inflow', 'outflow', 'deposit', 'withdrawal']):
                continue

            values = pd.to_numeric(
                df[col].astype(str).str.replace(',', '').str.replace(' ', ''),
                errors='coerce'
            ).dropna()
            
            if len(values) < 2:
                continue
            
            # Score based on:
            # 1. Non-zero ratio (balance rarely zero)
            non_zero_ratio = (values != 0).sum() / len(values)
            
            # 2. Gradual changes (not too volatile)
            changes = values.diff().abs()
            avg_change = changes.mean()
            avg_value = values.abs().mean()
            volatility = avg_change / avg_value if avg_value > 0 else 999
            
            # 3. Larger absolute values
            magnitude = values.abs().mean()
            
            # Combined score
            score = (non_zero_ratio * 0.4) + (min(1.0, 1.0 / (volatility + 0.1)) * 0.3) + (min(1.0, magnitude / 100000) * 0.3)
            
            if score > best_score:
                best_score = score
                best_col = col
        
        if best_col:
            print(f"[ALGORITHMIC DETECTION] Picked {best_col} as Balance (score: {best_score:.2f})")
        return best_col
    
    @staticmethod
    @staticmethod
    def _detect_credit_debit_by_name(df: pd.DataFrame, numeric_cols: list) -> Tuple[Optional[str], Optional[str]]:
        """
        High priority name-based detection.
        """
        credit_col = None
        debit_col = None
        
        for col in numeric_cols:
            col_lower = str(col).lower()
            if any(keyword in col_lower for keyword in ['credit', 'inflow', 'deposit', 'income']):
                if credit_col is None or ('credit' in col_lower and 'credit' not in str(credit_col).lower()):
                    credit_col = col
            elif any(keyword in col_lower for keyword in ['debit', 'outflow', 'withdrawal', 'expense']):
                if debit_col is None or ('debit' in col_lower and 'debit' not in str(debit_col).lower()):
                    debit_col = col
        
        # Cross-check: If they are the same, something is wrong
        if credit_col == debit_col:
            return None, None
            
        return credit_col, debit_col

    @staticmethod
    def _detect_credit_debit_by_pattern(df: pd.DataFrame, candidates: list, 
                                        existing_credit: Optional[str], 
                                        existing_debit: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """
        Fall back to mutual exclusivity if names didn't find BOTH.
        """
        credit_col = existing_credit
        debit_col = existing_debit
        
        if credit_col and debit_col:
            return credit_col, debit_col
            
        remaining = [c for c in candidates if c not in [credit_col, debit_col]]
        
        if not remaining:
            return credit_col, debit_col
            
        # If we have one but not the other, and only one candidate left
        if len(remaining) == 1:
            if credit_col and not debit_col:
                return credit_col, remaining[0]
            if debit_col and not credit_col:
                return remaining[0], debit_col
        
        # If we have neither, try to find the pair with best mutual exclusivity
        if not credit_col and not debit_col and len(remaining) >= 2:
            best_pair = (None, None)
            max_excl = -1
            
            for i, col1 in enumerate(remaining):
                for col2 in remaining[i+1:]:
                    v1 = pd.to_numeric(df[col1].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    v2 = pd.to_numeric(df[col2].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                    excl = ((v1 > 0) & (v2 == 0)).sum() + ((v2 > 0) & (v1 == 0)).sum()
                    if excl > max_excl:
                        max_excl = excl
                        best_pair = (col1, col2)
            
            return best_pair
            
        return credit_col, debit_col
    
    @staticmethod
    def _detect_description_column(df: pd.DataFrame, exclude_cols: list) -> Optional[str]:
        """
        Detect description column.
        Should be text-based and not a date or numeric column.
        """
        exclude_cols = [col for col in exclude_cols if col is not None]
        
        for col in df.columns:
            if col in exclude_cols:
                continue
            
            # Check if it's text-based
            sample = df[col].dropna().astype(str).head(20)
            if len(sample) == 0:
                continue
            
            # Should have some text (not just numbers)
            has_text = sum(1 for val in sample if re.search(r'[a-zA-Z]', str(val)))
            
            if has_text / len(sample) > 0.5:
                return col
        
        # Fallback: return first non-excluded column
        for col in df.columns:
            if col not in exclude_cols:
                return col
        
        return None
