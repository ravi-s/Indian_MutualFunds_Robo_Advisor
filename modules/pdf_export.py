# modules/pdf_export.py

import io
import logging
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER

import qrcode
import qrcode.constants


logger = logging.getLogger(__name__)


def generate_goal_pdf(
    goal_id: str,
    goal_name: str,
    goal_inputs: dict,
    projections: dict,
    goal_url: str | None = None,
) -> io.BytesIO:
    """
    Generate a professional PDF for a goal path.

    Args:
        goal_id: Unique goal identifier (from DB)
        goal_name: User-friendly name (e.g., "Medium Risk Goal")
        goal_inputs: dict with keys:
            - startingcorpus (float)
            - monthlysip (float)
            - horizonyears (int)
            - riskcategory (str)
        projections: dict from calculate_goal_projections with keys:
            - conservative (float)
            - expected (float)
            - best_case (float)
            - base_return (float)
            - adjusted_return (float)
            - confidence (str)
            - confidence_percentage (int)
            - volatility (float)
            - mean_reversion_applied (bool)
        goal_url: Optional URL for QR code (revisit link; can be empty for now)

    Returns:
        BytesIO object with PDF content (ready for download)
    """
    pdf_buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.75 * inch,
        title=f"Goal Path - {goal_name}",
    )

    elements: list = []
    styles = getSampleStyleSheet()

    # ----- Custom styles -----
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#208090"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )

    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#208090"),
        spaceAfter=8,
        fontName="Helvetica-Bold",
    )

    normal_style = ParagraphStyle(
        "CustomNormal",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        leading=12,
    )

    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.red,
        spaceAfter=4,
        leading=10,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )

    # ----- Title -----
    elements.append(Paragraph("📊 Your Investment Goal Path", title_style))
    elements.append(Spacer(1, 0.15 * inch))

    created_date = datetime.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Goal: {goal_name}", normal_style))
    elements.append(Paragraph(f"Goal ID: {goal_id}", normal_style))
    elements.append(Paragraph(f"Created: {created_date}", normal_style))
    elements.append(Spacer(1, 0.15 * inch))

    # ----- Goal Summary -----
    elements.append(Paragraph("Your Investment Plan", heading_style))

    horizon_years = goal_inputs.get("horizonyears", 0)
    goal_summary = [
        ["Parameter", "Value"],
        ["Starting Corpus", f"₹{goal_inputs.get('startingcorpus', 0):,.0f}"],
        ["Monthly SIP", f"₹{goal_inputs.get('monthlysip', 0):,.0f}"],
        ["Investment Horizon", f"{horizon_years} years"],
        ["Risk Category", goal_inputs.get("riskcategory", "N/A")],
    ]

    summary_table = Table(goal_summary, colWidths=[2.5 * inch, 2.5 * inch])
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#208090")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]
        )
    )
    elements.append(summary_table)
    elements.append(Spacer(1, 0.2 * inch))

    # ----- Projections -----
    elements.append(Paragraph("Your Projection Scenarios", heading_style))

    base_return = projections.get("base_return", 0.0)
    adjusted_return = projections.get("adjusted_return", 0.0)
    confidence_pct = projections.get("confidence_percentage", 50)

    # For conservative / best-case annual returns, you can adjust this later if needed
    conservative_return = max(base_return - 2.0, 0.0)
    best_case_return = base_return + 2.0

    proj_data = [
        [
            "Scenario",
            "Annual Return",
            f"Final Corpus (after {horizon_years} yrs)",
            "Confidence",
        ],
        [
            "Conservative",
            f"{conservative_return:.1f}%",
            f"₹{projections.get('conservative', 0):,.0f}",
            "—",
        ],
        [
            "Expected (Most Likely)",
            f"{adjusted_return:.1f}%",
            f"₹{projections.get('expected', 0):,.0f}",
            f"{confidence_pct}%",
        ],
        [
            "Best Case",
            f"{best_case_return:.1f}%",
            f"₹{projections.get('best_case', 0):,.0f}",
            "—",
        ],
    ]

    proj_table = Table(
        proj_data,
        colWidths=[1.5 * inch, 1.3 * inch, 1.9 * inch, 1.1 * inch],
    )
    proj_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#208090")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
            ]
        )
    )

    elements.append(proj_table)
    elements.append(Spacer(1, 0.2 * inch))

    # ----- Assumptions / Mean Reversion -----
    elements.append(Paragraph("How We Calculated This", heading_style))

    mean_reversion_text = "Yes ✓" if projections.get("mean_reversion_applied") else "No"
    volatility = projections.get("volatility", 0.0)

    assumptions_text = (
        f"Base Return (long-term historical average): {base_return:.1f}%<br/>"
        f"Adjusted Return (after mean reversion): {adjusted_return:.1f}%<br/>"
        f"Mean Reversion Applied: {mean_reversion_text}<br/>"
        f"Volatility: {volatility:.1f}%<br/><br/>"
        "These projections are based on historical averages for your risk category. "
        "They are reviewed periodically and updated based on current market conditions."
    )
    elements.append(Paragraph(assumptions_text, normal_style))
    # After proj_table
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(
        Paragraph(
            "🔍 <b>Note:</b> The confidence percentage applies to the "
            "<b>Expected (most likely)</b> scenario.",
            normal_style,
        )
    )
    elements.append(Spacer(1, 0.2 * inch))

    # ----- QR Code (optional) -----
    if goal_url:
        elements.append(Paragraph("Share or Revisit This Goal", heading_style))
        qr_image = generate_qr_code(goal_url)
        if qr_image is not None:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(qr_image)
            elements.append(Spacer(1, 0.15 * inch))

    # ----- Disclaimer -----
    disclaimer_text = (
        "⚠️ IMPORTANT DISCLAIMER<br/><br/>"
        "This tool is for educational and informational purposes only. "
        "It does NOT constitute investment advice.<br/><br/>"
        "Past performance is NO guarantee of future results. "
        "We are NOT SEBI-registered investment advisors.<br/><br/>"
        "Market conditions change, and actual returns may vary significantly from projections. "
        "Please consult a certified financial advisor before making any investment decisions."
    )
    elements.append(Spacer(1, 0.15 * inch))
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    # Build PDF
    doc.build(elements, onFirstPage=add_footer, onLaterPages=add_footer)
    pdf_buffer.seek(0)
    logger.info("Generated PDF for goal %s", goal_id)
    return pdf_buffer



def generate_qr_code(url: str) -> Image | None:
    """
    Generate QR code image from URL.

    Args:
        url: Goal share URL

    Returns:
        reportlab Image object or None on failure
    """
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=4,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        img_buffer = io.BytesIO()
        img.save(img_buffer, "PNG")
        img_buffer.seek(0)

        return Image(img_buffer, width=1.5 * inch, height=1.5 * inch)
    except Exception as e:
        logger.error("Error generating QR code: %s", e)
        return None
    
def add_footer(canvas, doc) -> None:
    """Add footer to each page."""
    canvas.saveState()
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p IST")

    footer_text = (
        f"Generated on {timestamp} | Mutual Fund Robo-Advisor Prototype | "
        "Comments, Questions or Feedback, email: sankarsana@duck.com"
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(4.25 * inch, 0.4 * inch, footer_text)
    canvas.restoreState()


