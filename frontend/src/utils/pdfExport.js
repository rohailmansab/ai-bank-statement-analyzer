/**
 * Client-side PDF export so it works without server reportlab.
 * Same layout as backend: Summary, Monthly Performance, Large Deposits, Executive Summary, Risk.
 * Uses plain ASCII numbers and sanitized text so jsPDF/autoTable never mangles output.
 */
import { jsPDF } from 'jspdf';
import { autoTable } from 'jspdf-autotable';

/** Strip any non-numeric chars so we get a parseable number (fixes "& &5&,&7&0&8&" style garbage). */
function toNumber(x) {
  if (x == null || x === '') return 0;
  if (typeof x === 'number' && !Number.isNaN(x)) return x;
  const str = String(x).trim().replace(/[^\d.\-\()]/g, '').replace(/,/g, '');
  const n = parseFloat(str.replace(/\(([^)]*)\)/, '-$1'));
  return Number.isNaN(n) ? 0 : n;
}

/** Format number as plain ASCII "1,234.56" (no unicode) so PDF never garbles it. */
function fmtNum(x) {
  const n = toNumber(x);
  const fixed = Math.abs(n).toFixed(2);
  const [intPart, decPart] = fixed.split('.');
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const combined = (n < 0 ? '-' : '') + withCommas + '.' + decPart;
  return combined;
}

/** Sanitize string for PDF table cell: remove & and other chars that break jsPDF. */
function sanitizeCell(s) {
  if (s == null) return '';
  return String(s)
    .replace(/&/g, '')
    .replace(/[\x00-\x08\x0b\x0c\x0e-\x1f]/g, '')
    .trim()
    .substring(0, 80);
}

export function buildReportPdf(report) {
  const doc = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' });
  const pageW = doc.internal.pageSize.getWidth();
  let y = 18;

  doc.setFontSize(16);
  doc.setFont(undefined, 'bold');
  doc.text('Financial Summary — Bank Statement Analysis', pageW / 2, y, { align: 'center' });
  y += 10;

  doc.setFontSize(10);
  doc.setFont(undefined, 'normal');
  const filename = report?.filename || 'Statement';
  doc.text(`Dataset: ${filename}`, 14, y);
  y += 6;
  doc.setFontSize(8);
  doc.setTextColor(100, 100, 100);
  doc.text('All calculations and figures are from this uploaded statement only.', 14, y);
  doc.setTextColor(0, 0, 0);
  y += 12;

  const totals = report?.totals || {};
  const avgIncome = totals.average_income ?? 0;
  const avgExpense = totals.average_expense ?? 0;
  const disposable = avgIncome - avgExpense;

  doc.setFontSize(11);
  doc.setFont(undefined, 'bold');
  doc.text('Summary', 14, y);
  y += 8;

  autoTable(doc, {
    startY: y,
    head: [['Monthly Revenue (Avg Inflow)', 'Monthly Expenditure (Avg Outflow)', 'Capital Reserves']],
    body: [[`NGN ${fmtNum(avgIncome)}`, `NGN ${fmtNum(avgExpense)}`, `NGN ${fmtNum(disposable)}`]],
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59], fontSize: 9 },
    bodyStyles: { fontSize: 10 },
    margin: { left: 14 },
  });
  y = doc.lastAutoTable.finalY + 14;

  doc.setFont(undefined, 'bold');
  doc.text('Financial Summary: Monthly Performance', 14, y);
  y += 8;

  const monthly = report?.monthly_summary || [];
  const tableData = monthly.map((row) => [
    sanitizeCell(row.month),
    `NGN ${fmtNum(row.income)}`,
    `NGN ${fmtNum(row.expenses)}`,
    `NGN ${fmtNum((row.income ?? 0) - (row.expenses ?? 0))}`,
  ]);
  if (tableData.length === 0) tableData.push(['No monthly data', '-', '-', '-']);

  autoTable(doc, {
    startY: y,
    head: [['Transaction Period', 'Income (Credits)', 'Expenses (Debits)', 'Net Liquidity']],
    body: tableData,
    theme: 'grid',
    headStyles: { fillColor: [30, 41, 59], fontSize: 9 },
    bodyStyles: { fontSize: 9 },
    margin: { left: 14 },
  });
  y = doc.lastAutoTable.finalY + 8;
  doc.setFontSize(8);
  doc.setFont(undefined, 'normal');
  doc.setTextColor(100, 100, 100);
  doc.text('Data verified by BSA Core Algorithm.', 14, y);
  doc.setTextColor(0, 0, 0);
  y += 14;

  doc.setFontSize(11);
  doc.setFont(undefined, 'bold');
  doc.text('Large / Unusual Deposits', 14, y);
  y += 8;

  const large = report?.large_deposits || [];
  if (large.length > 0) {
    const depData = large.map((d) => [
      sanitizeCell(d.Date),
      sanitizeCell((d.Description || '').substring(0, 35)),
      `NGN ${fmtNum(d.Amount ?? d.Credit)}`,
      sanitizeCell(d.Category),
    ]);
    autoTable(doc, {
      startY: y,
      head: [['Date', 'Description', 'Amount', 'Category']],
      body: depData,
      theme: 'grid',
      headStyles: { fillColor: [30, 41, 59], fontSize: 9 },
      bodyStyles: { fontSize: 9 },
      margin: { left: 14 },
    });
    y = doc.lastAutoTable.finalY + 14;
  } else {
    doc.setFont(undefined, 'normal');
    doc.text('No large/unusual deposits detected.', 14, y);
    y += 14;
  }

  const summary = (report?.professional_summary || '').trim();
  if (summary) {
    doc.setFont(undefined, 'bold');
    doc.text('Executive Summary', 14, y);
    y += 8;
    doc.setFont(undefined, 'normal');
    doc.setFontSize(10);
    const lines = doc.splitTextToSize(summary, pageW - 28);
    doc.text(lines, 14, y);
    y += lines.length * 5 + 10;
  }

  const risk = report?.risk_analysis || {};
  const verdict = risk.verdict || risk.risk_level || '—';
  doc.setFont(undefined, 'bold');
  doc.text('Risk / Audit', 14, y);
  y += 8;
  doc.setFont(undefined, 'normal');
  doc.text(`Verdict: ${verdict}`, 14, y);

  return doc;
}

export function downloadReportAsPdf(report, filename = 'BSA_Report.pdf') {
  const doc = buildReportPdf(report);
  const name = (filename || 'BSA_Report').replace(/\s+/g, '_');
  doc.save(name.endsWith('.pdf') ? name : `${name}.pdf`);
}
