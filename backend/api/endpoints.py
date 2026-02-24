from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from backend.services.analysis import AnalysisService
from backend.services.ai_classifier import AIClassifier
from backend.auth.jwt_handler import decode_access_token
from fastapi.security import OAuth2PasswordBearer
import pandas as pd
import os
from backend.services.parser_router import ParserRouter
from backend.services.report_builder import ReportBuilder

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload["sub"]

@router.post("/analyze-statement")
async def analyze_statement(file: UploadFile = File(...), user: str = Depends(get_current_user)):
    """
    Universal bank statement analyzer with production-grade AI insights.
    """
    content = await file.read()
    extension = os.path.splitext(file.filename)[1]
    
    try:
        # Step 1: Initialize AI Core and Parser
        parser = ParserRouter()
        
        # Step 2: EXTRACTION pipeline (Normalizes and Validates internally)
        df, validation_report = await parser.parse(content, file.filename, extension)
        
        # Fallback: only use AI extraction if USE_AI is on; otherwise try OCR and fail cleanly
        from backend.config import USE_AI
        if (df.empty or validation_report.get("confidence") == "failed") and USE_AI:
            print("[INFO] Standard parsing failed or low confidence, falling back to AI extraction...")
            df = await parser.parse_with_ai(content)
            if not df.empty:
                from backend.services.normalizer import DataNormalizer
                from backend.services.validator import DataValidator
                df = DataNormalizer.normalize_dataframe(df)
                is_valid, validation_report = DataValidator.validate(df)
                validation_report["parser_used"] = "universal_ai_parser"

        if df.empty:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not extract transactions. {validation_report.get('error', 'Please ensure the file is a clear bank statement.')}"
            )
        
        # Step 3: CORE ANALYSIS
        monthly_summary = AnalysisService.generate_monthly_summary(df)
        totals = AnalysisService.calculate_totals_and_averages(df)
        large_deposits = AnalysisService.detect_large_deposits(df, threshold=50000)
        
        # Step 4: AI ANALYSIS only when USE_AI is on; otherwise rule-based only (no Gemini/OpenAI)
        if USE_AI:
            from backend.services.ai_core import AICore
            from backend.services.ai_classifier import AIClassifier
            from backend.services.anomaly_detector import AnomalyDetector
            from backend.services.professional_summarizer import ProfessionalSummarizer
            ai_core = AICore()
            classifier = AIClassifier(ai_core)
            anomaly_detector = AnomalyDetector(ai_core)
            summarizer = ProfessionalSummarizer(ai_core)
            application_date = "2026-02-18"
            if large_deposits:
                large_deposits = await classifier.classify_large_deposits(large_deposits, application_date)
            df_dict = df.to_dict('records')
            anomalies = await anomaly_detector.detect_anomalies(df_dict, validation_report, application_date)
            classified_summary = "\n".join([f"- {d.get('Date')}: {d.get('Category')}" for d in large_deposits])
            professional_summary = await summarizer.generate_summary(
                parser.detected_bank, user, validation_report, totals, classified_summary
            )
        else:
            # No AI: rule-based executive summary and anomaly verdict only
            dr = validation_report.get("date_range") or {}
            start = dr.get("start", "unknown")
            end = dr.get("end", "unknown")
            total_credits = totals.get("total_income") or totals.get("total_credit") or 0.0
            total_debits = totals.get("total_expense") or totals.get("total_debit") or 0.0
            n_tx = validation_report.get("total_transactions", 0)
            professional_summary = (
                f"This statement is for {user} with {parser.detected_bank}, covering {start} to {end}. "
                f"Total credits: {total_credits:,.2f} NGN; total debits: {total_debits:,.2f} NGN; "
                f"transaction count: {n_tx}. (Analysis from statement data; no AI APIs used.)"
            )
            anomalies = {
                "overall_risk_score": 0.0,
                "risk_level": "low",
                "verdict": "Anomaly analysis not run (AI disabled). No red flags identified in the provided data.",
                "red_flags": [],
                "positive_indicators": [],
                "recommendations": [],
            }
            for d in large_deposits:
                d["Category"] = d.get("Category") or "—"
        
        extraction_metadata = getattr(parser, "_config_driven_metadata", None) or {}
        report = ReportBuilder.build_visa_summary(
            df, monthly_summary, totals, large_deposits, validation_report,
            professional_summary=professional_summary,
            risk_analysis=anomalies,
            detected_bank=parser.detected_bank,
            extraction_metadata=extraction_metadata,
        )
        
        # Add extraction metadata
        report = ReportBuilder.add_extraction_metadata(
            report, parser.used_parser, parser.logs
        )
        report["filename"] = file.filename
        
        return report
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail="Internal server error during analysis. Please check logs."
        )
