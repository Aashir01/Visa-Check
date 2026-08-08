"""Branded PDF report generation.

The report is the deliverable an agency resells to its own client (§2), so it
has to survive being printed and handed over: the checklist version and date
appear on every page, findings carry their evidence, and the disclaimer
language never claims an approval outcome (§9).
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ..pipeline.doctypes import label_for

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#6B7280")
LINE = colors.HexColor("#E5E7EB")
CRITICAL = colors.HexColor("#B91C1C")
WARNING = colors.HexColor("#B45309")
INFO = colors.HexColor("#1D4ED8")
GOOD = colors.HexColor("#047857")

SEVERITY_COLOR = {"critical": CRITICAL, "warning": WARNING, "info": INFO}
SEVERITY_LABEL = {"critical": "CRITICAL", "warning": "WARNING", "info": "INFO"}
BAND_COLOR = {
    "low": GOOD,
    "moderate": colors.HexColor("#CA8A04"),
    "elevated": WARNING,
    "high": CRITICAL,
}


def _styles(accent: colors.Color) -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("t", parent=base["Title"], fontName="Helvetica-Bold",
                                fontSize=19, leading=23, textColor=INK, spaceAfter=2),
        "subtitle": ParagraphStyle("st", parent=base["Normal"], fontSize=9.5,
                                   leading=13, textColor=MUTED),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold",
                             fontSize=12.5, leading=16, textColor=accent,
                             spaceBefore=14, spaceAfter=6),
        "h3": ParagraphStyle("h3", parent=base["Heading3"], fontName="Helvetica-Bold",
                             fontSize=10.5, leading=14, textColor=INK, spaceAfter=3),
        "body": ParagraphStyle("b", parent=base["Normal"], fontSize=9.5, leading=13.5,
                               textColor=INK, alignment=TA_LEFT),
        "small": ParagraphStyle("s", parent=base["Normal"], fontSize=8, leading=11,
                                textColor=MUTED),
        "fix": ParagraphStyle("f", parent=base["Normal"], fontSize=9.5, leading=13.5,
                              textColor=INK, leftIndent=8),
        "banner": ParagraphStyle("bn", parent=base["Normal"], fontSize=9, leading=12.5,
                                 textColor=colors.HexColor("#7C2D12")),
        "score": ParagraphStyle("sc", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=42, leading=44, alignment=TA_CENTER),
        "scorelabel": ParagraphStyle("scl", parent=base["Normal"], fontSize=9,
                                     leading=12, alignment=TA_CENTER, textColor=MUTED),
    }


class ScoreBar(Flowable):
    """A 0-100 track with the score marked. Clearer in print than a gauge."""

    def __init__(self, score: int, width: float, colour: colors.Color):
        super().__init__()
        self.score = max(0, min(100, int(score)))
        self.width = width
        # Tall enough that the scale labels sit inside the flowable rather
        # than overlapping whatever follows it.
        self.height = 34
        self.colour = colour

    def draw(self):
        c = self.canv
        track_h = 7
        y = self.height - track_h - 6

        c.setFillColor(colors.HexColor("#F3F4F6"))
        c.roundRect(0, y, self.width, track_h, 3.5, stroke=0, fill=1)

        filled = self.width * self.score / 100.0
        c.setFillColor(self.colour)
        if filled > 0:
            c.roundRect(0, y, max(filled, 4), track_h, 3.5, stroke=0, fill=1)

        # Scale ticks.
        c.setFont("Helvetica", 6.5)
        c.setFillColor(MUTED)
        for value in (0, 40, 65, 85, 100):
            x = self.width * value / 100.0
            c.setStrokeColor(LINE)
            c.line(x, y - 3, x, y - 1)
            label = str(value)
            offset = 0 if value == 0 else (c.stringWidth(label, "Helvetica", 6.5)
                                           if value == 100 else
                                           c.stringWidth(label, "Helvetica", 6.5) / 2)
            c.drawString(x - offset, y - 11, label)


def _severity_chip(severity: str) -> Table:
    colour = SEVERITY_COLOR.get(severity, INFO)
    cell = Paragraph(
        f'<font color="{colour.hexval()}" size="7.5"><b>'
        f"{SEVERITY_LABEL.get(severity, severity.upper())}</b></font>",
        ParagraphStyle("chip", fontSize=7.5, leading=9.5),
    )
    t = Table([[cell]], colWidths=[19 * mm])
    t.setStyle(
        TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colour),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    return t


def _esc(text) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fmt_value(value) -> str:
    """Render an evidence value the way a reader expects to see it.

    Extracted amounts arrive as floats, so a balance would otherwise print as
    "552000.0" in the middle of a sentence about money.
    """
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        if float(value).is_integer():
            return f"{int(value):,}"
        return f"{value:,.2f}"
    return str(value)


def build_report_pdf(*, check, corridor, pack: dict, documents: list, brand: dict | None = None) -> bytes:
    brand = brand or {}
    brand_name = brand.get("name") or "VisaGuard"
    accent = colors.HexColor(brand.get("color") or "#1D4ED8")
    S = _styles(accent)

    buf = io.BytesIO()
    page_w, page_h = A4
    margin = 18 * mm
    content_w = page_w - 2 * margin

    version = pack.get("version", "unknown")
    generated = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M UTC")
    footer_note = (
        f"{brand_name} · Checklist: {_esc(pack.get('title', ''))} v{_esc(version)} · "
        f"Generated {generated} · Check {check.id[:8]}"
    )

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(margin, page_h - margin + 6, page_w - margin, page_h - margin + 6)
        canvas.line(margin, margin - 6, page_w - margin, margin - 6)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin, margin - 15, footer_note[:150])
        canvas.drawRightString(page_w - margin, margin - 15, f"Page {doc.page}")
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(accent)
        canvas.drawString(margin, page_h - margin + 10, brand_name.upper())
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawRightString(
            page_w - margin, page_h - margin + 10, "Document completeness report"
        )
        canvas.restoreState()

    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=margin, rightMargin=margin, topMargin=margin, bottomMargin=margin,
        title=f"Visa document check — {check.id[:8]}", author=brand_name,
    )
    doc.addPageTemplates([
        PageTemplate(
            id="main",
            frames=[Frame(margin, margin, content_w, page_h - 2 * margin, id="f")],
            onPage=decorate,
        )
    ])

    story: list = []
    issues = check.issues or []
    extraction = check.extraction or {}
    scoring = extraction.get("scoring") or {}
    passed = extraction.get("passed") or []

    # ---------------- header ----------------
    story.append(Paragraph("Visa document completeness report", S["title"]))
    story.append(Paragraph(
        f"{_esc(corridor.label)} &middot; applicant profile: "
        f"{_esc((check.applicant_profile or '').replace('_', ' '))}",
        S["subtitle"],
    ))
    story.append(Spacer(1, 3 * mm))

    meta = [
        ["Check reference", check.id[:12]],
        ["Checklist", f"{pack.get('title', '')} · version {version}"],
        ["Checklist dated", str(pack.get("effective_date", "—"))],
        ["Generated", generated],
    ]
    if extraction.get("travel_start") or extraction.get("travel_end"):
        meta.append([
            "Travel dates",
            f"{extraction.get('travel_start') or '?'} to "
            f"{extraction.get('travel_end') or '?'}"
            + (f" ({extraction['trip_days']} days)" if extraction.get("trip_days") else ""),
        ])
    meta.append(["Documents analysed", str(len(documents))])

    meta_table = Table(
        [[Paragraph(f"<b>{_esc(k)}</b>", S["small"]), Paragraph(_esc(v), S["small"])]
         for k, v in meta],
        colWidths=[38 * mm, content_w - 38 * mm],
    )
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)

    # ---------------- unverified banner ----------------
    if pack.get("unverified"):
        story.append(Spacer(1, 4 * mm))
        banner = Table(
            [[Paragraph(
                "<b>Draft checklist.</b> This report was produced against a rule pack "
                "that has not yet been verified against live casework. Treat the "
                "findings as a first pass and confirm every requirement with the "
                "relevant consulate or your adviser before submitting.",
                S["banner"],
            )]],
            colWidths=[content_w],
        )
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FEF3C7")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#F59E0B")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(banner)

    # ---------------- score ----------------
    story.append(Spacer(1, 6 * mm))
    band = check.risk_band or scoring.get("band") or "high"
    band_colour = BAND_COLOR.get(band, CRITICAL)
    score = check.risk_score if check.risk_score is not None else 0

    score_cell = [
        Paragraph(f'<font color="{band_colour.hexval()}">{score}</font>', S["score"]),
        Paragraph("out of 100", S["scorelabel"]),
    ]
    counts = scoring.get("counts", {})
    right_cell = [
        Paragraph(
            f'<font color="{band_colour.hexval()}"><b>'
            f'{_esc(scoring.get("band_label", band.title()))}</b></font>',
            S["h3"],
        ),
        Paragraph(_esc(scoring.get("band_message", "")), S["body"]),
        Spacer(1, 2 * mm),
        ScoreBar(score, content_w - 44 * mm, band_colour),
        Paragraph(
            f"{counts.get('critical', 0)} critical &middot; "
            f"{counts.get('warning', 0)} warning &middot; "
            f"{counts.get('info', 0)} informational &middot; "
            f"{len(passed)} checks passed",
            S["small"],
        ),
    ]
    score_table = Table([[score_cell, right_cell]], colWidths=[40 * mm, content_w - 40 * mm])
    score_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("LINEAFTER", (0, 0), (0, 0), 0.6, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(score_table)

    if check.summary:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(_esc(check.summary), S["body"]))

    # ---------------- issues ----------------
    if issues:
        story.append(Paragraph("Issues found", S["h2"]))
        for severity, heading in (
            ("critical", "Critical — fix before submitting"),
            ("warning", "Warnings — likely to cause questions or delay"),
            ("info", "Informational — worth improving"),
        ):
            group = [i for i in issues if i.get("severity") == severity]
            if not group:
                continue
            story.append(Paragraph(
                f'<font color="{SEVERITY_COLOR[severity].hexval()}">'
                f"<b>{_esc(heading)}</b></font>",
                S["h3"],
            ))
            story.append(Spacer(1, 1.5 * mm))
            for n, issue in enumerate(group, start=1):
                story.append(_issue_block(n, issue, content_w, S))
                story.append(Spacer(1, 3 * mm))
    else:
        story.append(Paragraph("Issues found", S["h2"]))
        story.append(Paragraph(
            "No issues were detected against this checklist. This is not a "
            "prediction of approval — it means that nothing on checklist "
            f"<b>{_esc(pack.get('title', ''))} v{_esc(version)}</b> was found "
            "missing or inconsistent in the documents supplied.",
            S["body"],
        ))

    # ---------------- passed ----------------
    if passed:
        story.append(PageBreak())
        story.append(Paragraph("Checks that passed", S["h2"]))
        story.append(Paragraph(
            "These requirements were verified against the documents you supplied.",
            S["small"],
        ))
        story.append(Spacer(1, 2 * mm))
        rows = [[Paragraph(
            f'<font color="{GOOD.hexval()}">✓</font>&nbsp; {_esc(p.get("title") or p.get("rule_id"))}',
            S["body"],
        )] for p in passed]
        table = Table(rows, colWidths=[content_w])
        table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(table)

    # ---------------- not evaluated ----------------
    skipped = extraction.get("skipped") or []
    if skipped:
        story.append(Paragraph("Checks that could not be run", S["h2"]))
        story.append(Paragraph(
            "These requirements could not be evaluated, because the document they "
            "depend on was missing or a needed field could not be read. "
            "<b>They have not passed</b> — they were not checked at all. Verify them "
            "yourself before submitting.",
            S["small"],
        ))
        story.append(Spacer(1, 2 * mm))
        rows = [[Paragraph(
            f'<font color="{MUTED.hexval()}">—</font>&nbsp; '
            f'{_esc(s.get("title") or s.get("rule_id"))}',
            S["body"],
        )] for s in skipped]
        table = Table(rows, colWidths=[content_w])
        table.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, LINE),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ]))
        story.append(table)

    # ---------------- documents ----------------
    story.append(Paragraph("Documents analysed", S["h2"]))
    header = [Paragraph(f"<b>{h}</b>", S["small"])
              for h in ("File", "Detected as", "Read quality")]
    rows = [header]
    for d in documents:
        conf = d.doc_type_confidence
        quality = "—"
        if conf is not None:
            quality = "high" if conf >= 0.75 else ("medium" if conf >= 0.5 else "low")
        if d.doc_type_source == "user":
            quality = "set by you"
        rows.append([
            Paragraph(_esc(d.filename[:60]), S["small"]),
            Paragraph(_esc(label_for(d.effective_type)), S["small"]),
            Paragraph(quality, S["small"]),
        ])
    doc_table = Table(rows, colWidths=[content_w * 0.46, content_w * 0.34, content_w * 0.20])
    doc_table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, LINE),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(doc_table)

    # ---------------- disclaimer ----------------
    story.append(Spacer(1, 8 * mm))
    disclaimer = Table(
        [[Paragraph(
            f"<b>Important.</b> {_esc(pack.get('disclaimer', ''))} "
            f"This report reflects checklist <b>{_esc(pack.get('title', ''))} "
            f"version {_esc(version)}</b>, dated {_esc(pack.get('effective_date', '—'))}. "
            "Consular requirements change without notice and vary between consulates "
            "and individual cases. No statement here should be read as a prediction "
            "of the outcome of any application. Uploaded documents are encrypted at "
            "rest and automatically deleted after the retention period.",
            S["small"],
        )]],
        colWidths=[content_w],
    )
    disclaimer.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F9FAFB")),
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(disclaimer)

    doc.build(story)
    return buf.getvalue()


def _issue_block(n: int, issue: dict, width: float, S: dict) -> KeepTogether:
    severity = issue.get("severity", "info")
    parts: list = [
        Table(
            [[
                _severity_chip(severity),
                Paragraph(f"<b>{n}. {_esc(issue.get('title'))}</b>", S["h3"]),
            ]],
            colWidths=[21 * mm, width - 21 * mm],
            style=TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]),
        ),
        Paragraph(_esc(issue.get("detail")), S["body"]),
    ]

    evidence = [e for e in (issue.get("evidence") or []) if e.get("value") is not None]
    if evidence:
        lines = []
        for e in evidence[:5]:
            source = e.get("document_label") or e.get("document_type") or "—"
            field = (e.get("field") or "").replace("_", " ")
            value = _fmt_value(e.get("value"))
            if e.get("currency"):
                value = f"{e['currency']} {value}"
            if len(value) > 120:
                value = value[:117] + "…"
            lines.append(f"{_esc(source)} &middot; {_esc(field)}: <b>{_esc(value)}</b>")
        parts.append(Spacer(1, 1.5 * mm))
        parts.append(Paragraph("Evidence: " + " &nbsp;|&nbsp; ".join(lines), S["small"]))

    if issue.get("fix"):
        parts.append(Spacer(1, 2 * mm))
        fix = Table(
            [[Paragraph(f"<b>How to fix:</b> {_esc(issue['fix'])}", S["fix"])]],
            colWidths=[width],
        )
        fix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
            ("LINEBEFORE", (0, 0), (0, -1), 2, GOOD),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        parts.append(fix)

    authority = issue.get("authority")
    if authority:
        label = {
            "law": "This is a legal requirement.",
            "member_state": "This figure is published by the destination state.",
            "official_guidance": "Based on published official guidance.",
            "heuristic": "This is our own guidance, not an official requirement.",
        }.get(authority)
        if label:
            src = (issue.get("sources") or [None])[0]
            parts.append(Spacer(1, 1.5 * mm))
            parts.append(Paragraph(
                _esc(label) + (f" Source: {_esc(src)}" if src else ""), S["small"]
            ))

    if float(issue.get("confidence", 1.0)) < 0.6:
        parts.append(Spacer(1, 1.5 * mm))
        parts.append(Paragraph(
            "This finding has lower confidence — please verify it yourself before "
            "acting on it.",
            S["small"],
        ))

    return KeepTogether(parts)
