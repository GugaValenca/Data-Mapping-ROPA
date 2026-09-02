"""CSV and PDF export of the Record of Processing Activities (ROPA).

Both exports operate on whatever queryset the dashboard's current filters
produced (see `views._filtered_activities`), so "export what I'm looking
at" and "export the full ROPA" are the same code path — the caller just
passes an unfiltered queryset for the latter.
"""

import csv
from xml.sax.saxutils import escape as xml_escape

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone

from .models import ProcessingActivity

EXPORT_BASENAME = "Data-Mapping-ROPA-Export"

COLUMN_HEADERS = [
    "Activity",
    "Department",
    "Purpose",
    "Data categories",
    "Sensitive data?",
    "Legal basis",
    "Recipients",
    "International transfer?",
    "Retention period",
    "Retention justification",
    "High risk flag",
]


def _row_for(activity: ProcessingActivity) -> list[str]:
    categories = ", ".join(c.name for c in activity.data_categories.all())
    recipients = ", ".join(r.name for r in activity.recipients.all())
    return [
        activity.name,
        activity.department,
        activity.purpose,
        categories,
        "Yes" if activity.involves_sensitive_data else "No",
        activity.legal_basis.name if activity.legal_basis else "UNDEFINED",
        recipients or "—",
        "Yes" if activity.involves_international_transfer else "No",
        activity.retention_period.duration_label if activity.retention_period else "UNDEFINED",
        activity.retention_period.justification if activity.retention_period else "",
        "HIGH RISK" if activity.is_high_risk else "",
    ]


def export_csv(activities) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    timestamp = timezone.now().strftime("%Y%m%d")
    response["Content-Disposition"] = (
        f'attachment; filename="{EXPORT_BASENAME}-{timestamp}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow([f"{settings.SITE_TITLE} — Record of Processing Activities"])
    writer.writerow([f"Generated {timezone.now().strftime('%Y-%m-%d %H:%M')}"])
    writer.writerow([])
    writer.writerow(COLUMN_HEADERS)
    for activity in activities:
        writer.writerow(_row_for(activity))

    return response


def export_pdf(activities) -> HttpResponse:
    # Imported lazily so the app still runs (dashboard, CSV export, admin)
    # if reportlab isn't installed in a given environment; only the PDF
    # export route pays the import cost / failure.
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    generated_at = timezone.now()
    response = HttpResponse(content_type="application/pdf")
    timestamp = generated_at.strftime("%Y%m%d")
    response["Content-Disposition"] = (
        f'attachment; filename="{EXPORT_BASENAME}-{timestamp}.pdf"'
    )

    doc = SimpleDocTemplate(
        response,
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.4 * inch,
        title=f"{settings.SITE_TITLE} Export",
    )

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    meta_style = styles["Normal"]
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=7.5, leading=9.5)
    risk_cell_style = ParagraphStyle(
        "riskCell", parent=cell_style, textColor=colors.HexColor("#B3261E")
    )

    elements = [
        Paragraph(f"{settings.SITE_TITLE}", title_style),
        Paragraph("Record of Processing Activities (ROPA)", styles["Heading2"]),
        Paragraph(
            f"Generated {generated_at.strftime('%Y-%m-%d %H:%M')} &mdash; "
            f"{len(activities)} activit{'y' if len(activities) == 1 else 'ies'} included",
            meta_style,
        ),
        Spacer(1, 0.15 * inch),
    ]

    # reportlab's Paragraph parses its text as a small XML-like markup
    # language (it's how <b>...</b> below produces bold headers), so any
    # value that isn't hardcoded markup we wrote ourselves has to be
    # escaped first — otherwise a stray "<" or "&" in a free-text field
    # (activity name, purpose, retention justification, all editable in
    # admin) gets silently swallowed or reinterpreted as a tag instead of
    # showing up in the exported document.
    header_row = [Paragraph(f"<b>{h}</b>", cell_style) for h in COLUMN_HEADERS]
    table_data = [header_row]
    row_is_high_risk = []
    for activity in activities:
        style = risk_cell_style if activity.is_high_risk else cell_style
        table_data.append(
            [Paragraph(xml_escape(str(value)), style) for value in _row_for(activity)]
        )
        row_is_high_risk.append(activity.is_high_risk)

    # Landscape letter minus margins leaves 10.2" of printable width
    # (11" - 0.4" - 0.4"); these widths sum to 10.1" so every column,
    # including the first and last, stays fully inside the page instead
    # of being clipped at the edges.
    col_widths = [
        1.0 * inch,
        0.8 * inch,
        1.3 * inch,
        1.15 * inch,
        0.5 * inch,
        0.85 * inch,
        1.15 * inch,
        0.5 * inch,
        1.0 * inch,
        1.3 * inch,
        0.55 * inch,
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table_style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2A44")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F6F8")]),
    ]
    for idx, is_high_risk in enumerate(row_is_high_risk, start=1):
        if is_high_risk:
            table_style_commands.append(
                ("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#FBE9E7"))
            )
    table.setStyle(TableStyle(table_style_commands))
    elements.append(table)

    elements.append(Spacer(1, 0.2 * inch))
    elements.append(
        Paragraph(
            "Sample data belongs to a fictional company, for demonstration "
            "purposes. Retention periods shown are illustrative placeholders "
            "pending legal verification, not confirmed legal requirements.",
            ParagraphStyle(
                "footnote", parent=styles["Normal"], fontSize=7, textColor=colors.grey
            ),
        )
    )

    doc.build(elements)
    return response
