# ============================================================
# REPORT GENERATOR - MindEase
# Generates PDF emotional health reports for clinical use
# Privacy-focused: NO chat messages included, only statistics
# ============================================================

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import io


def generate_user_report(
    user_name,
    user_email,
    period_label,
    total_sessions,
    emotion_stats,
    sentiment_stats,
    stress_stats,
    crisis_count,
    top_emotion,
    output_path
):
    """
    Generates a privacy-safe PDF emotional health report
    for a single user, suitable for sharing with a doctor.

    NOTE: This function does NOT take or print any chat
    messages - only aggregated statistics - to protect
    user privacy.
    """

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch
    )

    styles = getSampleStyleSheet()
    elements = []

    # ---- Custom Styles ----
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#7C9E8A'),
        spaceAfter=4,
        alignment=TA_CENTER
    )

    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6B6B6B'),
        alignment=TA_CENTER,
        spaceAfter=16
    )

    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#2C2C2C'),
        spaceBefore=14,
        spaceAfter=8
    )

    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2C2C2C'),
        leading=15
    )

    note_style = ParagraphStyle(
        'NoteStyle',
        parent=styles['Normal'],
        fontSize=8.5,
        textColor=colors.HexColor('#6B6B6B'),
        leading=12
    )

    # ============================================================
    # HEADER
    # ============================================================
    elements.append(Paragraph("MindEase", title_style))
    elements.append(Paragraph(
        "AI-Powered Emotional Wellness Report",
        subtitle_style
    ))
    elements.append(HRFlowable(
        width="100%", thickness=1,
        color=colors.HexColor('#E8E3DA')
    ))
    elements.append(Spacer(1, 16))

    # ============================================================
    # PATIENT INFO
    # ============================================================
    elements.append(Paragraph("Patient Information", section_style))

    info_data = [
        ["Name:",            user_name],
        ["Email:",           user_email],
        ["Report Period:",   period_label],
        ["Generated On:",    datetime.now().strftime('%d %B %Y, %I:%M %p')],
        ["Total Sessions:",  str(total_sessions)],
    ]

    info_table = Table(info_data, colWidths=[1.6 * inch, 4.5 * inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',  (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2C2C2C')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING',    (0, 0), (-1, -1), 2),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    # ============================================================
    # CRISIS ALERT (if applicable)
    # ============================================================
    if crisis_count > 0:
        crisis_style = ParagraphStyle(
            'CrisisStyle',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#C0675A'),
            backColor=colors.HexColor('#FDF0EE'),
            borderColor=colors.HexColor('#EDD5D2'),
            borderWidth=1,
            borderPadding=10,
            leading=14
        )
        elements.append(Paragraph(
            f"<b>⚠ Clinical Alert:</b> {crisis_count} session(s) during this "
            f"period showed signs consistent with crisis-level distress "
            f"(e.g. expressions of hopelessness or self-harm ideation). "
            f"Immediate professional evaluation is strongly recommended.",
            crisis_style
        ))
        elements.append(Spacer(1, 14))

    # ============================================================
    # EMOTIONAL SUMMARY
    # ============================================================
    elements.append(Paragraph("Emotional Summary", section_style))

    dominant_sentiment = "Neutral"
    if sentiment_stats:
        dominant_sentiment = max(sentiment_stats, key=sentiment_stats.get)

    summary_data = [
        ["Most Frequent Emotion", top_emotion.capitalize() if top_emotion else "N/A"],
        ["Overall Sentiment Trend", dominant_sentiment],
        ["High Stress Sessions", str(stress_stats.get('High', 0))],
        ["Moderate Stress Sessions", str(stress_stats.get('Moderate', 0))],
        ["Low Stress Sessions", str(stress_stats.get('Low', 0))],
    ]

    summary_table = Table(summary_data, colWidths=[2.8 * inch, 3.3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), colors.HexColor('#F8F4EE')),
        ('FONTNAME',     (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0, 0), (-1, -1), 9.5),
        ('TEXTCOLOR',    (0, 0), (-1, -1), colors.HexColor('#2C2C2C')),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 8),
        ('TOPPADDING',   (0, 0), (-1, -1), 8),
        ('GRID',         (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E3DA')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 14))

    # ============================================================
    # EMOTION BREAKDOWN TABLE
    # ============================================================
    elements.append(Paragraph("Emotion Breakdown", section_style))

    emotion_table_data = [["Emotion", "Sessions", "Percentage"]]
    for emotion, count in emotion_stats:
        pct = (count / total_sessions * 100) if total_sessions > 0 else 0
        emotion_table_data.append([
            emotion.capitalize(),
            str(count),
            f"{pct:.1f}%"
        ])

    emotion_table = Table(
        emotion_table_data,
        colWidths=[2.5 * inch, 1.8 * inch, 1.8 * inch]
    )
    emotion_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#7C9E8A')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9.5),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E3DA')),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F4EE')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
    ]))
    elements.append(emotion_table)
    elements.append(Spacer(1, 14))

    # ============================================================
    # SENTIMENT BREAKDOWN
    # ============================================================
    elements.append(Paragraph("Sentiment Distribution", section_style))

    sentiment_table_data = [["Sentiment", "Sessions", "Percentage"]]
    for sentiment_label in ["Positive", "Neutral", "Negative"]:
        count = sentiment_stats.get(sentiment_label, 0)
        pct = (count / total_sessions * 100) if total_sessions > 0 else 0
        sentiment_table_data.append([
            sentiment_label,
            str(count),
            f"{pct:.1f}%"
        ])

    sentiment_table = Table(
        sentiment_table_data,
        colWidths=[2.5 * inch, 1.8 * inch, 1.8 * inch]
    )
    sentiment_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), colors.HexColor('#2C2C2C')),
        ('TEXTCOLOR',     (0, 0), (-1, 0), colors.white),
        ('FONTNAME',      (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE',      (0, 0), (-1, -1), 9.5),
        ('ALIGN',         (1, 0), (-1, -1), 'CENTER'),
        ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E3DA')),
        ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F4EE')]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
    ]))
    elements.append(sentiment_table)
    elements.append(Spacer(1, 16))

    # ============================================================
    # CLINICAL RECOMMENDATION
    # ============================================================
    elements.append(Paragraph("Clinical Observations", section_style))

    high_stress_count = stress_stats.get('High', 0)
    total = total_sessions if total_sessions > 0 else 1
    high_stress_pct = (high_stress_count / total) * 100

    if crisis_count > 0:
        recommendation = (
            "This individual has shown indicators consistent with "
            "crisis-level emotional distress during the reporting period. "
            "Immediate professional consultation is strongly advised."
        )
    elif high_stress_pct >= 40:
        recommendation = (
            "This individual has experienced elevated stress levels in a "
            "significant proportion of sessions. Professional counselling "
            "support is recommended to address underlying concerns."
        )
    elif dominant_sentiment == "Negative":
        recommendation = (
            "This individual's overall emotional sentiment trends negative "
            "during this period. Continued monitoring and supportive "
            "conversation with a mental health professional may be beneficial."
        )
    else:
        recommendation = (
            "This individual's emotional indicators are within a generally "
            "stable range for this period. Continued self-monitoring through "
            "MindEase is encouraged."
        )

    elements.append(Paragraph(recommendation, normal_style))
    elements.append(Spacer(1, 16))

    # ============================================================
    # EMERGENCY RESOURCES
    # ============================================================
    elements.append(Paragraph("Emergency Resources", section_style))
    elements.append(Paragraph(
        "<b>iCall Helpline:</b> 9152987821 &nbsp;&nbsp;|&nbsp;&nbsp; "
        "<b>Vandrevala Foundation:</b> 1860-2662-345 (24/7)",
        normal_style
    ))
    elements.append(Spacer(1, 20))

    # ============================================================
    # DISCLAIMER FOOTER
    # ============================================================
    elements.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor('#E8E3DA')
    ))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "This report was generated by MindEase, an AI-powered emotional "
        "wellness assistant, based on aggregated emotion and sentiment "
        "analysis of the user's conversations. Individual chat messages "
        "are not included in this report to protect user privacy. "
        "This report is intended to support, not replace, clinical "
        "judgment. It is not a medical diagnosis.",
        note_style
    ))

    doc.build(elements)
    return output_path