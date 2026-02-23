import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Body
from fastapi.responses import Response
from backend.services.analysis import AnalysisService
from backend.services.ai_classifier import AIClassifier
from backend.auth.jwt_handler import decode_access_token
from fastapi.security import OAuth2PasswordBearer
import pandas as pd
import os
from backend.services.parser_router import ParserRouter
from backend.services.report_builder import ReportBuilder
from backend.services.pdf_report import build_report_pdf

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
                from backend.services.parser_router import _build_report_from_df
                df = DataNormalizer.normalize_dataframe(df)
                validation_report = _build_report_from_df(df)
                validation_report["parser_used"] = "universal_ai_parser"

        if df.empty:
            raise HTTPException(
                status_code=400, 
                detail=f"Could not extract transactions. {validation_report.get('error', 'Please ensure the file is a clear bank statement.')}"
            )
        
        # Step 3: CORE ANALYSIS — all from uploaded statement only (output format is fixed; figures = this file)
        monthly_summary = AnalysisService.generate_monthly_summary(df)
        totals = AnalysisService.calculate_totals_and_averages(df)
        large_deposits = AnalysisService.detect_large_deposits(df, threshold=50000)
        
        # Step 4: ADVANCED AI ANALYSIS (classify first, then anomaly + summary in parallel)
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
        classified_summary = "\n".join([f"- {d.get('Date')}: {d.get('Category')}" for d in large_deposits])

        df_dict = df.to_dict('records')
        # Run anomaly detection and professional summary in parallel to save ~15–45s
        anomalies, professional_summary = await asyncio.gather(
            anomaly_detector.detect_anomalies(df_dict, validation_report, application_date),
            summarizer.generate_summary(
                parser.detected_bank, user, validation_report, totals, classified_summary
            ),
        )
        
        report = ReportBuilder.build_visa_summary(
            df, monthly_summary, totals, large_deposits, validation_report,
            professional_summary=professional_summary,
            risk_analysis=anomalies,
            detected_bank=parser.detected_bank
        )
        
        # Add extraction metadata (including config-driven key-values when available)
        report = ReportBuilder.add_extraction_metadata(
            report, parser.used_parser, parser.logs
        )
        key_values = getattr(parser, "_config_driven_metadata", None)
        if key_values:
            report.setdefault("metadata", {})["key_values"] = key_values
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


@router.post("/export-pdf")
async def export_pdf(report: dict = Body(...), user: str = Depends(get_current_user)):
    """
    Generate a PDF report in client-standard format from the analysis result.
    Same layout as the reference; all figures are from the report (uploaded statement).
    """
    try:
        pdf_bytes = build_report_pdf(report)
        raw_name = (report.get("filename") or "BSA_Report").strip()
        filename = "".join(c if c.isalnum() or c in "._-" else "_" for c in raw_name).replace(" ", "_") or "BSA_Report"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RuntimeError as e:
        if "reportlab" in str(e).lower():
            raise HTTPException(status_code=503, detail="PDF export unavailable. Install reportlab.")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Failed to generate PDF.")
