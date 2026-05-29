import io
import os
from datetime import datetime

from database.models import get_summary_stats, get_camera_analytics, query_detections, get_analytics_data

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
        PageBreak,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_pdf():
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed. Run: cd backend && pip install --user --break-system-packages reportlab")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        "ReportTitle", parent=styles["Title"],
        fontSize=22, leading=28, spaceAfter=6, textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle", parent=styles["Normal"],
        fontSize=11, leading=14, textColor=colors.HexColor("#64748b"), spaceAfter=20,
    )
    heading_style = ParagraphStyle(
        "SectionHeading", parent=styles["Heading2"],
        fontSize=14, leading=18, textColor=colors.HexColor("#1e293b"),
        spaceBefore=16, spaceAfter=8, borderPadding=(0, 0, 4, 0),
    )
    normal = styles["Normal"]

    elements.append(Paragraph("AquaVision", title_style))
    elements.append(Paragraph("AI-Powered Bottle Inspection Report", subtitle_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal))
    elements.append(Spacer(1, 12))

    stats = get_summary_stats()
    total = stats["total_bottles"]
    passed = stats["passed_bottles"]
    defective = stats["defective_bottles"]
    accuracy = stats["detection_accuracy"]

    summary_data = [
        ["Metric", "Value"],
        ["Total Bottles Inspected", str(total)],
        ["Passed", str(passed)],
        ["Defective", str(defective)],
        ["Detection Accuracy", f"{accuracy}%"],
    ]
    summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(Paragraph("Inspection Summary", heading_style))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    d = Drawing(400, 200)

    pie = Pie()
    pie.x = 50
    pie.y = 20
    pie.width = 150
    pie.height = 150
    pie.data = [passed, defective]
    pie.labels = [f"Passed ({passed})", f"Defective ({defective})"]
    pie.slices[0].fillColor = colors.HexColor("#10b981")
    pie.slices[1].fillColor = colors.HexColor("#ef4444")
    pie.slices[0].fontColor = colors.white
    pie.slices[1].fontColor = colors.white
    d.add(pie)

    bar = VerticalBarChart()
    bar.x = 230
    bar.y = 30
    bar.width = 160
    bar.height = 140
    bar.data = [[passed, defective]]
    bar.categoryAxis.categoryNames = ["Passed", "Defective"]
    bar.categoryAxis.labels.fontSize = 9
    bar.valueAxis.valueMin = 0
    bar.valueAxis.valueMax = max(total * 1.2, 10)
    bar.bars[0].fillColor = colors.HexColor("#0ea5e9")
    bar.bars[0].strokeColor = None
    d.add(bar)

    elements.append(Paragraph("Pass / Fail Distribution", heading_style))
    elements.append(d)
    elements.append(Spacer(1, 12))

    camera_stats = get_camera_analytics()
    if camera_stats:
        cam_data = [["Camera", "Total", "Passed", "Rejected", "Accuracy"]]
        for c in camera_stats:
            cam_data.append([
                c["camera"], str(c["total_bottles"]), str(c["passed_bottles"]),
                str(c["rejected_bottles"]), f'{c["accuracy"]}%'
            ])
        cam_table = Table(cam_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        cam_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(Paragraph("Camera Analytics", heading_style))
        elements.append(cam_table)

    analytics = get_analytics_data()
    if analytics.get("daily"):
        trend_data = [["Date", "Passed", "Defective"]]
        for d_entry in analytics["daily"][-14:]:
            trend_data.append([d_entry["date"], d_entry["passed"], d_entry["defective"]])

        trend_table = Table(trend_data, colWidths=[1.2*inch, 1*inch, 1*inch])
        trend_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0ea5e9")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(Paragraph("Recent Daily Trends (Last 14 Days)", heading_style))
        elements.append(trend_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer
