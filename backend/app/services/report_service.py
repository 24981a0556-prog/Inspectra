"""
ReportService — PDF inspection report generation using reportlab.

Generates a structured compliance report containing:
  - Inspection header and metadata
  - Product information
  - Submitted images list
  - Extracted declarations table
  - Quantity information
  - Rule validation results (Declaration + Measurement engines)
  - Potential violations / findings
  - Human verification summary
  - Final inspection decision

The report is saved to local storage and the path is returned.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_pdf(self, inspection_id: int) -> str:
        """
        Generate a PDF compliance report for the given inspection.
        Returns the file path (relative to LOCAL_UPLOAD_DIR).
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                HRFlowable, KeepTogether
            )
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        except ImportError:
            raise RuntimeError("reportlab is required for PDF generation. Run: pip install reportlab")

        from app.models.inspection import Inspection
        from app.models.ai_result import AIResult
        from app.models.evidence import Evidence
        from app.models.compliance_check import ComplianceCheck
        from app.core.config import settings

        # ── Load data ─────────────────────────────────────────────────────────
        inspection = (
            self.db.query(Inspection)
            .filter(Inspection.id == inspection_id)
            .first()
        )
        if not inspection:
            raise ValueError(f"Inspection {inspection_id} not found")

        ai_results = (
            self.db.query(AIResult)
            .filter(AIResult.inspection_id == inspection_id)
            .order_by(AIResult.created_at)
            .all()
        )
        evidences = (
            self.db.query(Evidence)
            .filter(Evidence.inspection_id == inspection_id)
            .order_by(Evidence.id)
            .all()
        )
        checks = (
            self.db.query(ComplianceCheck)
            .filter(ComplianceCheck.inspection_id == inspection_id)
            .order_by(ComplianceCheck.id)
            .all()
        )

        # ── Build PDF ─────────────────────────────────────────────────────────
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm,
        )

        styles = getSampleStyleSheet()
        story = []

        # Colors
        NAVY  = colors.HexColor("#1e3a5f")
        BLUE  = colors.HexColor("#1d4ed8")
        GREEN = colors.HexColor("#16a34a")
        RED   = colors.HexColor("#dc2626")
        AMBER = colors.HexColor("#d97706")
        GREY  = colors.HexColor("#64748b")
        LIGHT = colors.HexColor("#f8fafc")

        title_style   = ParagraphStyle("Title",  fontName="Helvetica-Bold", fontSize=20, textColor=NAVY,  spaceAfter=4, alignment=TA_CENTER)
        h1_style      = ParagraphStyle("H1",     fontName="Helvetica-Bold", fontSize=14, textColor=NAVY,  spaceBefore=12, spaceAfter=4)
        h2_style      = ParagraphStyle("H2",     fontName="Helvetica-Bold", fontSize=11, textColor=BLUE,  spaceBefore=8, spaceAfter=2)
        normal_style  = ParagraphStyle("Normal", fontName="Helvetica",      fontSize=9,  textColor=colors.black, spaceAfter=2)
        small_style   = ParagraphStyle("Small",  fontName="Helvetica",      fontSize=8,  textColor=GREY,   spaceAfter=1)
        mono_style    = ParagraphStyle("Mono",   fontName="Courier",        fontSize=9,  textColor=NAVY,   spaceAfter=2)
        center_style  = ParagraphStyle("Center", fontName="Helvetica",      fontSize=9,  alignment=TA_CENTER)

        def status_color(status: str):
            return {
                "PASS": GREEN,
                "FAIL": RED,
                "NEEDS_VERIFICATION": AMBER,
                "NOT_CHECKED": GREY,
                "NOT_APPLICABLE": GREY,
            }.get(status, GREY)

        # ── Header ────────────────────────────────────────────────────────────
        story.append(Paragraph("INSPECTRA", title_style))
        story.append(Paragraph("AI-Assisted Legal Metrology Inspection Report", center_style))
        story.append(Paragraph("Legal Metrology (Packaged Commodities) Rules, 2011", center_style))
        story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=8))

        if inspection.is_demo:
            demo_style = ParagraphStyle("Demo", fontName="Helvetica-Bold", fontSize=9,
                                        textColor=AMBER, alignment=TA_CENTER, spaceAfter=4)
            story.append(Paragraph("⚠ DEMO INSPECTION — Results are for demonstration purposes only", demo_style))

        # ── Inspection Metadata ───────────────────────────────────────────────
        story.append(Paragraph("Inspection Summary", h1_style))
        meta_data = [
            ["Inspection Number", inspection.inspection_number],
            ["Product", inspection.product.product_name if inspection.product else "—"],
            ["Category", inspection.product.category or "—" if inspection.product else "—"],
            ["Manufacturer", inspection.product.manufacturer or "—" if inspection.product else "—"],
            ["Inspector", inspection.inspector.name if inspection.inspector else "—"],
            ["Status", inspection.status.value],
            ["Created", _fmt_dt(inspection.created_at)],
            ["Analysis Started", _fmt_dt(inspection.started_at)],
        ]
        if inspection.final_decision:
            meta_data.append(["Final Decision", inspection.final_decision.value.replace("_", " ")])
        if inspection.finalized_at:
            meta_data.append(["Decision Date", _fmt_dt(inspection.finalized_at)])

        meta_table = Table(
            [[Paragraph(k, small_style), Paragraph(str(v), normal_style)] for k, v in meta_data],
            colWidths=[5*cm, 12*cm]
        )
        meta_table.setStyle(TableStyle([
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0,0), (0,-1), LIGHT),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Submitted Images ──────────────────────────────────────────────────
        story.append(Paragraph("Submitted Package Images", h1_style))
        img_data = [["#", "View Type", "Filename", "Uploaded"]]
        for i, img in enumerate(inspection.images, 1):
            img_data.append([
                str(i),
                img.view_type.value if hasattr(img.view_type, 'value') else str(img.view_type),
                img.original_filename or "—",
                _fmt_dt(img.created_at),
            ])
        if len(img_data) == 1:
            img_data.append(["—", "No images", "—", "—"])

        img_table = Table(img_data, colWidths=[1*cm, 3*cm, 8*cm, 5*cm])
        img_table.setStyle(_table_style(NAVY, LIGHT))
        story.append(img_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Extracted Declarations ────────────────────────────────────────────
        story.append(Paragraph("Extracted Declarations", h1_style))
        story.append(Paragraph("The following declarations were extracted by AI agents from the submitted package images. "
                                "These are structured observations — compliance is determined by the rule engines below.", small_style))
        story.append(Spacer(1, 0.2*cm))

        decl_result = next((r.result_json for r in ai_results if r.agent_type == "declaration_agent"), {})
        declarations = decl_result.get("declarations", []) if decl_result else []

        decl_data = [["Field", "Extracted Value", "Confidence", "Evidence Ref"]]
        evidence_by_field = {ev.field_name: ev for ev in evidences if ev.agent_type == "declaration_agent"}
        for decl in declarations:
            ev = evidence_by_field.get(decl.get("field"))
            decl_data.append([
                Paragraph(decl.get("display_name", decl.get("field", "—")), small_style),
                Paragraph(_truncate(decl.get("value", "—"), 60), normal_style),
                f"{decl.get('confidence', 0):.0%}" if decl.get("confidence") else "—",
                ev.evidence_ref_id if ev else "—",
            ])
        if len(decl_data) == 1:
            decl_data.append(["No declarations extracted", "—", "—", "—"])

        decl_table = Table(decl_data, colWidths=[4*cm, 8*cm, 2.5*cm, 2.5*cm])
        decl_table.setStyle(_table_style(NAVY, LIGHT))
        story.append(decl_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Quantity Information ──────────────────────────────────────────────
        story.append(Paragraph("Quantity Information", h1_style))
        qty_result = next((r.result_json for r in ai_results if r.agent_type == "quantity_agent"), {})
        primary_qty = qty_result.get("primary_quantity") if qty_result else None
        if primary_qty:
            qty_data = [
                ["Declared Value", primary_qty.get("raw_value", "—")],
                ["Numeric Value", str(primary_qty.get("numeric_value", "—"))],
                ["Unit", primary_qty.get("unit", "—")],
                ["Normalised Value", f"{primary_qty.get('normalized_value', '—')} {primary_qty.get('normalized_unit', '')}"],
                ["Confidence", f"{primary_qty.get('confidence', 0):.0%}"],
            ]
        else:
            qty_data = [["Net Quantity", "Not detected"]]

        qty_table = Table(
            [[Paragraph(k, small_style), Paragraph(str(v), normal_style)] for k, v in qty_data],
            colWidths=[5*cm, 12*cm]
        )
        qty_table.setStyle(TableStyle([
            ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0,0), (0,-1), LIGHT),
            ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",   (0,0), (-1,-1), 8),
            ("PADDING",    (0,0), (-1,-1), 4),
        ]))
        story.append(qty_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Rule Validation Results ───────────────────────────────────────────
        story.append(Paragraph("Rule Validation Results", h1_style))
        story.append(Paragraph("Results produced by deterministic rule engines. AI agents provide evidence; "
                                "rule engines apply the rules; human inspector makes the final decision.", small_style))
        story.append(Spacer(1, 0.2*cm))

        check_data = [["Rule ID", "Rule Name", "Engine", "Status", "Severity", "Reason"]]
        for check in checks:
            status_str = check.status.value if hasattr(check.status, 'value') else str(check.status)
            sev_str = check.severity.value if check.severity and hasattr(check.severity, 'value') else "—"
            check_data.append([
                Paragraph(check.rule_id, mono_style),
                Paragraph(check.rule_name or "—", small_style),
                check.engine_type or "—",
                Paragraph(status_str, ParagraphStyle("s", fontName="Helvetica-Bold", fontSize=8,
                                                       textColor=status_color(status_str))),
                sev_str,
                Paragraph(_truncate(check.message or "—", 80), small_style),
            ])
        if len(check_data) == 1:
            check_data.append(["—", "No checks run", "—", "—", "—", "—"])

        check_table = Table(check_data, colWidths=[3.5*cm, 3.5*cm, 2*cm, 2*cm, 1.8*cm, 4.2*cm])
        check_table.setStyle(_table_style(NAVY, LIGHT))
        story.append(check_table)
        story.append(Spacer(1, 0.4*cm))

        # ── Findings ─────────────────────────────────────────────────────────
        failing = [c for c in checks if c.status.value in ("FAIL", "NEEDS_VERIFICATION")]
        if failing:
            story.append(Paragraph("Potential Non-Compliance Findings", h1_style))
            story.append(Paragraph("The following findings require inspector attention. These are potential non-compliance "
                                    "observations — the final determination is made by the human inspector.", small_style))
            story.append(Spacer(1, 0.2*cm))
            for i, check in enumerate(failing, 1):
                status_str = check.status.value if hasattr(check.status, 'value') else str(check.status)
                sev_str = check.severity.value if check.severity and hasattr(check.severity, 'value') else "MEDIUM"
                finding_data = [
                    [f"Finding #{i} — {check.rule_id}", ""],
                    ["Rule", check.rule_name or "—"],
                    ["Status", status_str],
                    ["Severity", sev_str],
                    ["Reason", _truncate(check.message or "—", 120)],
                    ["Evidence", ", ".join(check.evidence_ref_ids or []) or "—"],
                    ["Human Review Required", "YES" if check.requires_human_review else "NO"],
                ]
                ft = Table(finding_data, colWidths=[4*cm, 13*cm])
                ft.setStyle(TableStyle([
                    ("SPAN",       (0,0), (1,0)),
                    ("BACKGROUND", (0,0), (1,0), RED if status_str == "FAIL" else AMBER),
                    ("TEXTCOLOR",  (0,0), (1,0), colors.white),
                    ("FONTNAME",   (0,0), (1,0), "Helvetica-Bold"),
                    ("FONTSIZE",   (0,0), (-1,-1), 8),
                    ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
                    ("PADDING",    (0,0), (-1,-1), 4),
                    ("BACKGROUND", (0,1), (0,-1), LIGHT),
                ]))
                story.append(ft)
                story.append(Spacer(1, 0.3*cm))

        # ── Human Verification ────────────────────────────────────────────────
        reviewed = [c for c in checks if c.human_reviewed]
        if reviewed:
            story.append(Paragraph("Human Verification", h1_style))
            rv_data = [["Rule ID", "Original", "Action", "Reviewer Comment"]]
            for c in reviewed:
                rv_data.append([
                    c.rule_id,
                    c.status.value if hasattr(c.status, 'value') else "—",
                    c.human_action or "—",
                    _truncate(c.human_comment or "—", 60),
                ])
            rv_table = Table(rv_data, colWidths=[4*cm, 2.5*cm, 4*cm, 6.5*cm])
            rv_table.setStyle(_table_style(NAVY, LIGHT))
            story.append(rv_table)
            story.append(Spacer(1, 0.4*cm))

        # ── Final Decision ────────────────────────────────────────────────────
        story.append(Paragraph("Final Inspection Decision", h1_style))
        if inspection.final_decision:
            fd_val = inspection.final_decision.value.replace("_", " ")
            fd_color = {"COMPLIANT": GREEN, "NON_COMPLIANT": RED}.get(
                inspection.final_decision.value, AMBER
            )
            fd_style = ParagraphStyle("FD", fontName="Helvetica-Bold", fontSize=14,
                                       textColor=fd_color, spaceBefore=4, spaceAfter=4)
            story.append(Paragraph(fd_val, fd_style))
            if inspection.final_decision_comment:
                story.append(Paragraph(f"Inspector comment: {inspection.final_decision_comment}", normal_style))
            if inspection.finalized_at and inspection.finalized_by:
                story.append(Paragraph(
                    f"Recorded by {inspection.finalized_by.name} on {_fmt_dt(inspection.finalized_at)}",
                    small_style
                ))
        else:
            story.append(Paragraph("No final decision recorded yet — human verification pending.", normal_style))

        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=GREY))
        story.append(Spacer(1, 0.2*cm))
        footer_text = (
            "This report is produced by the INSPECTRA prototype system. "
            "AI-extracted information is provided as structured observations to assist the human inspector. "
            "The final compliance determination is made exclusively by the authorised human inspector. "
            "This report does not constitute a legal regulatory determination."
        )
        story.append(Paragraph(footer_text, ParagraphStyle("footer", fontName="Helvetica",
                                                             fontSize=7, textColor=GREY, alignment=TA_CENTER)))
        story.append(Paragraph(f"Generated: {_fmt_dt(datetime.now(timezone.utc))} UTC  |  INSPECTRA v1.0", 
                                ParagraphStyle("gen", fontName="Helvetica", fontSize=7, textColor=GREY, alignment=TA_CENTER)))

        # ── Save PDF ──────────────────────────────────────────────────────────
        doc.build(story)
        pdf_bytes = buffer.getvalue()

        from app.core.config import settings
        report_dir = os.path.join(settings.LOCAL_UPLOAD_DIR, "reports")
        os.makedirs(report_dir, exist_ok=True)

        filename = f"report_inspection_{inspection_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(report_dir, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        logger.info("[ReportService] PDF saved: %s", filepath)
        return f"/uploads/reports/{filename}"


def _fmt_dt(dt) -> str:
    if not dt:
        return "—"
    try:
        return dt.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return str(dt)


def _truncate(text: str, max_len: int) -> str:
    return text[:max_len] + "…" if len(text) > max_len else text


def _table_style(header_color, row_color):
    from reportlab.platypus import TableStyle
    from reportlab.lib import colors
    return TableStyle([
        ("BACKGROUND", (0,0), (-1,0), header_color),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
        ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 8),
        ("GRID",       (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, row_color]),
        ("PADDING",    (0,0), (-1,-1), 4),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
    ])
