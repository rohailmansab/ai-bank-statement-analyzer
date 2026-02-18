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
        
        # Fallback to AI if standard parsers fail or return poor results
        if df.empty or validation_report.get("confidence") == "failed":
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
        
        # Step 4: ADVANCED AI ANALYSIS
        from backend.services.ai_core import AICore
        from backend.services.ai_classifier import AIClassifier
        from backend.services.anomaly_detector import AnomalyDetector
        from backend.services.professional_summarizer import ProfessionalSummarizer
        
        ai_core = AICore()
        classifier = AIClassifier(ai_core)
        anomaly_detector = AnomalyDetector(ai_core)
        summarizer = ProfessionalSummarizer(ai_core)
        
        # Batch Classify Deposits
        application_date = "2026-02-18" # Should ideally come from request
        if large_deposits:
            large_deposits = await classifier.classify_large_deposits(large_deposits, application_date)
        
        # Risk & Anomaly Detection
        df_dict = df.to_dict('records')
        anomalies = await anomaly_detector.detect_anomalies(df_dict, validation_report, application_date)
        
        # Step 5: BUILD FINAL REPORT
        classified_summary = "\n".join([f"- {d.get('Date')}: {d.get('Category')}" for d in large_deposits])
        professional_summary = await summarizer.generate_summary(
            parser.detected_bank, user, validation_report, totals, classified_summary
        )
        
        report = ReportBuilder.build_visa_summary(
            df, monthly_summary, totals, large_deposits, validation_report,
            professional_summary=professional_summary,
            risk_analysis=anomalies,
            detected_bank=parser.detected_bank
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
