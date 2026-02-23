"""
Generate a formal PDF report in client-standard format.
Same layout for every statement; all figures from the report data (uploaded statement).
"""
import io
from typing import Dict, Any, List

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def _fmt_num(x: Any) -> str:
    if x is None:
        return "0.00"
    try:
        return f"{float(x):,.2f}"
    except (TypeError, ValueError):
        return str(x)


def _safe_html(s: str) -> str:
    """Escape for use inside reportlab Paragraph (XML-style)."""
    if not s:
        return ""
    s = str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_report_pdf(report: Dict[str, Any]) -> bytes:
    """
    Build a PDF report from the analysis result (client-style layout).
    All data comes from the report dict (uploaded statement only).
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is required for PDF export. Install with: pip install reportlab")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name="ReportTitle",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        name="SectionHead",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = styles["Normal"]
    small_style = ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, textColor=colors.gray)

    story = []

    # Title
    story.append(Paragraph("Financial Summary — Bank Statement Analysis", title_style))
    story.append(Spacer(1, 6))

    filename = _safe_html(report.get("filename") or "Statement")
    story.append(Paragraph(f"<b>Dataset:</b> {filename}", body_style))
    story.append(Paragraph("All calculations and figures are from this uploaded statement only.", small_style))
    story.append(Spacer(1, 14))

    # Summary section
    totals = report.get("totals") or {}
    avg_income = totals.get("average_income") or 0
    avg_expense = totals.get("average_expense") or 0
    disposable = avg_income - avg_expense

    summary_data = [
        ["Monthly Revenue (Average Inflow)", "Monthly Expenditure (Average Outflow)", "Capital Reserves (Disposable Balance)"],
        [f"₦ {_fmt_num(avg_income)}", f"₦ {_fmt_num(avg_expense)}", f"₦ {_fmt_num(disposable)}"],
    ]
    t1 = Table(summary_data, colWidths=[2 * inch, 2.2 * inch, 2.2 * inch])
    t1.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, 1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(Paragraph("Summary", heading_style))
    story.append(t1)
    story.append(Spacer(1, 14))

    # Monthly performance table
    story.append(Paragraph("Financial Summary: Monthly Performance", heading_style))
    monthly = report.get("monthly_summary") or []
    table_data = [["Transaction Period", "Income (Credits)", "Expenses (Debits)", "Net Liquidity"]]
    for row in monthly:
        inc = row.get("income") or 0
        exp = row.get("expenses") or 0
        net = inc - exp
        table_data.append([
            row.get("month", ""),
            f"₦ {_fmt_num(inc)}",
            f"₦ {_fmt_num(exp)}",
            f"₦ {_fmt_num(net)}",
        ])
    if len(table_data) == 1:
        table_data.append(["No monthly data", "-", "-", "-"])
    t2 = Table(table_data, colWidths=[1.8 * inch, 1.5 * inch, 1.5 * inch, 1.5 * inch])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Paragraph("Data verified by BSA Core Algorithm.", small_style))
    story.append(Spacer(1, 14))

    # Large / Unusual Deposits
    story.append(Paragraph("Large / Unusual Deposits", heading_style))
    large = report.get("large_deposits") or []
    if large:
        dep_data = [["Date", "Description", "Amount", "Category"]]
        for d in large:
            dep_data.append([
                d.get("Date", ""),
                (d.get("Description") or "")[:40] + ("..." if len(str(d.get("Description") or "")) > 40 else ""),
                f"₦ {_fmt_num(d.get('Amount') or d.get('Credit'))}",
                d.get("Category", ""),
            ])
        t3 = Table(dep_data, colWidths=[1.2 * inch, 2.5 * inch, 1.2 * inch, 1.2 * inch])
        t3.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(t3)
    else:
        story.append(Paragraph("No large/unusual deposits detected.", body_style))
    story.append(Spacer(1, 14))

    # Professional summary
    pro_summary = (report.get("professional_summary") or "").strip()
    if pro_summary:
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(_safe_html(pro_summary).replace("\n", "<br/>"), body_style))
        story.append(Spacer(1, 10))

    # Risk
    risk = report.get("risk_analysis") or {}
    verdict = risk.get("verdict") or risk.get("risk_level") or "—"
    story.append(Paragraph("Risk / Audit", heading_style))
    story.append(Paragraph(f"Verdict: {_safe_html(str(verdict))}", body_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("— End of Report —", small_style))
    doc.build(story)
    buf.seek(0)
    return buf.read()
