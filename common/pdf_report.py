import datetime
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _two_col_table(rows, col_widths=(200, 200)):
    t = Table(rows, colWidths=list(col_widths))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#1F2937")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    return t


def build_pdf_report(report_title, meta_text, sections, results_header=None, results_rows=None,
                      results_col_widths=(90, 90, 90, 100, 150)):
    """Generic equipment-agnostic protection evaluation report builder.

    sections: list of (heading, two_col_rows) tuples, each rendered as a titled
        Heading2 followed by a 2-column key/value table.
    results_header / results_rows: optional final "Evaluation Results" table
        (e.g. per-phase trip verdicts), styled distinctly from the spec tables.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor("#1E3A8A"))
    story.append(Paragraph(report_title, title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph(meta_text, styles['Normal']))
    story.append(Spacer(1, 15))

    for idx, (heading, rows) in enumerate(sections, start=1):
        story.append(Paragraph(f"<b>{idx}. {heading}</b>", styles['Heading2']))
        story.append(_two_col_table(rows))
        story.append(Spacer(1, 15))

    if results_header and results_rows is not None:
        story.append(Paragraph(f"<b>{len(sections) + 1}. Evaluation Results</b>", styles['Heading2']))
        results_data = [results_header] + results_rows
        t_results = Table(results_data, colWidths=list(results_col_widths))
        t_results.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E3A8A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(t_results)

    doc.build(story)
    buffer.seek(0)
    return buffer


def generate_generator_pdf_report(unit_name, relay_obj, evals, phases):
    """Generator (87G) report — output is identical to the original monolithic
    generate_pdf_report(), now built on top of the shared build_pdf_report()."""
    report_title = f"Generator Differential Protection (87G) Evaluation Report - {relay_obj.mode} Mode"
    meta_text = f"<b>Date/Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | <b>Configuration:</b> {unit_name}"

    generator_rows = [
        ["Parameter", "Value"],
        ["Generator Rating", f"{relay_obj.mva_rated} MVA"],
        ["Rated Voltage", f"{relay_obj.kv_rated} kV"],
        ["Rated Current (Pri)", f"{relay_obj.i_rated_pri:.2f} A"],
        ["Neutral CT Ratio", f"{relay_obj.ct_ratio_N:.0f}:{relay_obj.ct_secondary_rating:.0f}"],
        ["Terminal CT Ratio", f"{relay_obj.ct_ratio_T:.0f}:{relay_obj.ct_secondary_rating:.0f}"]
    ]

    if relay_obj.mode == "GENERATOR_LEGACY":
        relay_rows = [
            ["Parameter", "Value"],
            ["Relay Type", "GE CFD22B4A (GEK-34124)"],
            ["Target/Seal-in Pickup", f"{relay_obj.target_amps} A sec." if relay_obj.target_amps is not None else "N/A"],
            ["Equivalent Pickup", f"{relay_obj.i_pickup:.3f} pu"],
            ["Restraint Slope (GEK-34124E)", f"{relay_obj.s1*100:.1f} %"],
            ["Breakpoints / 2nd Slope / High-Set", "N/A - fixed by relay design"]
        ]
    else:
        has_unrestrained = relay_obj.i_unrestrained < 1e5
        relay_rows = [
            ["Parameter", "Value"],
            ["Relay Type", "GE G60 (Numerical)"],
            ["Pickup", f"{relay_obj.i_pickup:.3f} pu"],
            ["Slope 1", f"{relay_obj.s1*100:.0f} %"],
            ["Slope 2", f"{relay_obj.s2*100:.0f} %"],
            ["Break 1", f"{relay_obj.break_1:.2f} pu"],
            ["Break 2", f"{relay_obj.break_2:.2f} pu"],
            ["Unrestrained High-Set", f"{relay_obj.i_unrestrained:.2f} pu" if has_unrestrained else "Not enabled / unconfirmed"]
        ]

    results_header = ["Phase", "I_op [pu]", "I_rest [pu]", "Threshold [pu]", "Status"]
    results_rows = []
    for p in phases:
        e = evals[p]
        results_rows.append([p, f"{e['i_op_pu']:.3f}", f"{e['i_rest_pu']:.3f}", f"{e['i_threshold_pu']:.3f}", e['status']])

    return build_pdf_report(
        report_title, meta_text,
        sections=[("Generator Parameters", generator_rows), ("Relay Parameters", relay_rows)],
        results_header=results_header, results_rows=results_rows,
    )
