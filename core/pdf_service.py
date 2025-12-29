from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from io import BytesIO
from datetime import datetime


class PDFService:
    @staticmethod
    def generate_prescription_pdf(prescription):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#4CAF50"),
            spaceAfter=30,
        )

        elements.append(Paragraph("BINTACURA", title_style))
        elements.append(Paragraph("Ordonnance Médicale", styles["Heading2"]))
        elements.append(Spacer(1, 0.5 * cm))

        info_data = [
            ["Date:", prescription.issue_date.strftime("%d/%m/%Y")],
            ["Patient:", prescription.patient.full_name],
            ["Médecin:", prescription.doctor.full_name],
            ["Valide jusqu'au:", prescription.valid_until.strftime("%d/%m/%Y")],
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 1 * cm))

        elements.append(Paragraph("Médicaments prescrits:", styles["Heading3"]))
        elements.append(Spacer(1, 0.3 * cm))

        meds_data = [["Médicament", "Dosage", "Fréquence", "Durée"]]
        for item in prescription.items.all():
            meds_data.append(
                [
                    item.medication.name,
                    item.dosage,
                    item.get_frequency_display(),
                    f"{item.duration_days} jours",
                ]
            )

        meds_table = Table(meds_data, colWidths=[6 * cm, 3 * cm, 4 * cm, 3 * cm])
        meds_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4CAF50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(meds_table)

        if prescription.notes:
            elements.append(Spacer(1, 0.5 * cm))
            elements.append(
                Paragraph(f"<b>Notes:</b> {prescription.notes}", styles["Normal"])
            )

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_invoice_pdf(invoice):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#2196F3"),
            spaceAfter=30,
        )

        elements.append(Paragraph("BINTACURA", title_style))
        elements.append(
            Paragraph(f"Facture N° {invoice.invoice_number}", styles["Heading2"])
        )
        elements.append(Spacer(1, 0.5 * cm))

        info_data = [
            ["Date d'émission:", invoice.issue_date.strftime("%d/%m/%Y")],
            ["Date d'échéance:", invoice.due_date.strftime("%d/%m/%Y")],
            ["Patient:", invoice.patient.full_name],
            ["Assurance:", invoice.insurance_package.name],
        ]

        info_table = Table(info_data, colWidths=[5 * cm, 11 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 1 * cm))

        amount_data = [
            ["Description", "Montant"],
            [
                f"Prime d'assurance ({invoice.period_start.strftime('%d/%m/%Y')} - {invoice.period_end.strftime('%d/%m/%Y')})",
                f"{invoice.amount} FCFA",
            ],
            ["", ""],
            ["Total à payer", f"{invoice.amount} FCFA"],
        ]

        amount_table = Table(amount_data, colWidths=[12 * cm, 4 * cm])
        amount_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2196F3")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )
        elements.append(amount_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_health_record_pdf(record):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#9C27B0"),
            spaceAfter=30,
        )

        elements.append(Paragraph("BINTACURA", title_style))
        elements.append(Paragraph("Dossier Médical", styles["Heading2"]))
        elements.append(Spacer(1, 0.5 * cm))

        info_data = [
            ["Date:", record.record_date.strftime("%d/%m/%Y")],
            ["Patient:", record.patient.full_name],
            ["Médecin:", record.doctor.full_name if record.doctor else "N/A"],
            ["Type:", record.get_record_type_display()],
        ]

        info_table = Table(info_data, colWidths=[4 * cm, 12 * cm])
        info_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ]
            )
        )
        elements.append(info_table)
        elements.append(Spacer(1, 1 * cm))

        elements.append(Paragraph(f"<b>Titre:</b> {record.title}", styles["Normal"]))
        elements.append(Spacer(1, 0.3 * cm))
        elements.append(Paragraph(f"<b>Description:</b>", styles["Normal"]))
        elements.append(Paragraph(record.description, styles["Normal"]))

        doc.build(elements)
        buffer.seek(0)
        return buffer


pdf_service = PDFService()

