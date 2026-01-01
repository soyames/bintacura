import os
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO
from datetime import datetime
from qrcode_generator.services import QRCodeService

logger = logging.getLogger(__name__)


class ReceiptPDFService:
    """Service for generating PDF receipts for transactions"""
    
    @staticmethod
    def generate_transaction_receipt(transaction, receipt_number=None):
        """
        Generate a PDF receipt for a transaction
        
        Args:
            transaction: CoreTransaction or FedaPayTransaction instance
            receipt_number: Optional receipt number
            
        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        
        # Create PDF document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Container for PDF elements
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=6
        )
        
        # Header/Logo
        title = Paragraph("BINTACURA", title_style)
        elements.append(title)
        
        subtitle = Paragraph("Healthcare Platform", normal_style)
        elements.append(subtitle)
        elements.append(Spacer(1, 20))
        
        # Receipt title
        receipt_title = Paragraph("PAYMENT RECEIPT", heading_style)
        elements.append(receipt_title)
        elements.append(Spacer(1, 20))
        
        # Receipt details
        if receipt_number:
            receipt_no = Paragraph(f"<b>Receipt No:</b> {receipt_number}", normal_style)
            elements.append(receipt_no)
        
        # Transaction reference
        if hasattr(transaction, 'transaction_ref'):
            txn_ref = transaction.transaction_ref
        elif hasattr(transaction, 'fedapay_reference'):
            txn_ref = transaction.fedapay_reference
        else:
            txn_ref = f"TXN-{transaction.id}"
        
        ref_para = Paragraph(f"<b>Transaction Reference:</b> {txn_ref}", normal_style)
        elements.append(ref_para)
        
        # Date
        created_date = transaction.created_at.strftime("%B %d, %Y %I:%M %p")
        date_para = Paragraph(f"<b>Date:</b> {created_date}", normal_style)
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Participant information
        if hasattr(transaction, 'wallet'):
            participant = transaction.wallet.participant
        elif hasattr(transaction, 'participant'):
            participant = transaction.participant
        else:
            participant = None
        
        if participant:
            elements.append(Paragraph("<b>Customer Information</b>", heading_style))
            
            customer_data = [
                ["Name:", participant.full_name or "N/A"],
                ["Email:", participant.email],
                ["Phone:", participant.phone_number or "N/A"],
            ]
            
            customer_table = Table(customer_data, colWidths=[2*inch, 4*inch])
            customer_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(customer_table)
            elements.append(Spacer(1, 20))
        
        # Transaction details
        elements.append(Paragraph("<b>Transaction Details</b>", heading_style))
        
        # Get transaction type
        if hasattr(transaction, 'transaction_type'):
            txn_type = transaction.get_transaction_type_display() if hasattr(transaction, 'get_transaction_type_display') else transaction.transaction_type
        else:
            txn_type = "Payment"
        
        # Get status
        if hasattr(transaction, 'status'):
            txn_status = transaction.get_status_display() if hasattr(transaction, 'get_status_display') else transaction.status
        else:
            txn_status = "Completed"
        
        # Get description
        description = getattr(transaction, 'description', 'Payment transaction')
        
        transaction_data = [
            ["Type:", txn_type],
            ["Description:", description],
            ["Status:", txn_status],
            ["Amount:", f"{transaction.amount} {transaction.currency}"],
        ]
        
        # Add fees if available
        if hasattr(transaction, 'fees') and transaction.fees:
            transaction_data.append(["Fees:", f"{transaction.fees} {transaction.currency}"])
        
        # Add payment method if available
        if hasattr(transaction, 'payment_method') and transaction.payment_method:
            payment_method = transaction.get_payment_method_display() if hasattr(transaction, 'get_payment_method_display') else transaction.payment_method
            transaction_data.append(["Payment Method:", payment_method])
        
        transaction_table = Table(transaction_data, colWidths=[2*inch, 4*inch])
        transaction_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(transaction_table)
        elements.append(Spacer(1, 30))
        
        # Total amount box
        total_data = [
            ["TOTAL AMOUNT", f"{transaction.amount} {transaction.currency}"]
        ]
        
        total_table = Table(total_data, colWidths=[3*inch, 3*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#667eea')),
        ]))
        
        elements.append(total_table)
        elements.append(Spacer(1, 40))
        
        # Footer
        footer_text = """
        <para align=center>
        <font size=9 color='#888888'>
        This is an automatically generated receipt.<br/>
        For questions, contact support@BINTACURA.com<br/>
        Thank you for using BINTACURA!
        </font>
        </para>
        """
        
        footer = Paragraph(footer_text, normal_style)
        elements.append(footer)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def save_receipt_to_file(transaction, receipt_number=None, file_path=None):
        """
        Generate and save a PDF receipt to file
        
        Args:
            transaction: Transaction instance
            receipt_number: Receipt number
            file_path: Optional custom file path
            
        Returns:
            File path where PDF was saved
        """
        if not file_path:
            # Create receipts directory if it doesn't exist
            receipts_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
            os.makedirs(receipts_dir, exist_ok=True)
            
            # Generate file name
            timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"receipt_{receipt_number or transaction.id}_{timestamp}.pdf"
            file_path = os.path.join(receipts_dir, file_name)
        
        # Generate PDF
        pdf_buffer = ReceiptPDFService.generate_transaction_receipt(
            transaction,
            receipt_number
        )
        
        # Save to file
        with open(file_path, 'wb') as f:
            f.write(pdf_buffer.getvalue())
        
        logger.info(f"Receipt saved to {file_path}")
        return file_path
    
    @staticmethod
    def generate_appointment_receipt(appointment, queue_entry=None, transaction=None):
        """
        Generate appointment receipt with QR code and queue information
        
        Args:
            appointment: Appointment instance
            queue_entry: AppointmentQueue instance (optional)
            transaction: Payment transaction (optional)
        
        Returns:
            BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#007bff'),
            spaceAfter=10,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=6
        )
        
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
                logo.hAlign = 'CENTER'
                elements.append(logo)
                elements.append(Spacer(1, 10))
            except:
                title = Paragraph("BINTACURA", title_style)
                elements.append(title)
        else:
            title = Paragraph("BINTACURA", title_style)
            elements.append(title)
        
        subtitle = Paragraph("Healthcare Platform", subtitle_style)
        elements.append(subtitle)
        elements.append(Spacer(1, 10))
        
        receipt_title = Paragraph("APPOINTMENT CONFIRMATION", heading_style)
        elements.append(receipt_title)
        elements.append(Spacer(1, 15))
        
        receipt_number = f"APT-{appointment.uid}"
        if queue_entry:
            receipt_number = f"APT-{queue_entry.queue_number}-{str(appointment.uid)[:8]}"
        
        receipt_no = Paragraph(f"<b>Confirmation No:</b> {receipt_number}", normal_style)
        elements.append(receipt_no)
        
        date_para = Paragraph(f"<b>Booked On:</b> {timezone.now().strftime('%B %d, %Y %I:%M %p')}", normal_style)
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        if queue_entry:
            queue_box_data = [[
                f"Queue Number: {queue_entry.queue_number}",
                f"Estimated Wait: {queue_entry.estimated_wait_time or 0} min"
            ]]
            
            queue_table = Table(queue_box_data, colWidths=[3*inch, 2.5*inch])
            queue_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#007bff')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.white),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 14),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 15),
                ('GRID', (0, 0), (-1, -1), 1, colors.white),
            ]))
            
            elements.append(queue_table)
            elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Patient Information</b>", heading_style))
        
        patient_data = [
            ["Name:", appointment.patient.full_name or "N/A"],
            ["Email:", appointment.patient.email],
            ["Phone:", appointment.patient.phone_number or "N/A"],
        ]
        
        patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
        patient_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(patient_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Appointment Details</b>", heading_style))
        
        doctor_name = appointment.doctor.full_name if appointment.doctor else "N/A"
        appointment_data = [
            ["Doctor:", f"Dr. {doctor_name}"],
            ["Date:", appointment.appointment_date.strftime("%B %d, %Y")],
            ["Time:", appointment.appointment_time.strftime("%I:%M %p") if appointment.appointment_time else "N/A"],
            ["Type:", appointment.get_type_display() if hasattr(appointment, 'get_type_display') else appointment.type],
            ["Reason:", appointment.reason or "General Consultation"],
        ]
        
        appointment_table = Table(appointment_data, colWidths=[2*inch, 4*inch])
        appointment_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(appointment_table)
        elements.append(Spacer(1, 20))
        
        if transaction:
            elements.append(Paragraph("<b>Payment Details</b>", heading_style))
            
            payment_method = "Cash (Pay On-site)" if transaction.payment_method == 'cash' else transaction.get_payment_method_display() if hasattr(transaction, 'get_payment_method_display') else transaction.payment_method
            
            payment_data = [
                ["Amount:", f"{transaction.amount} {transaction.currency}"],
                ["Payment Method:", payment_method],
                ["Status:", "Pending (Pay on arrival)" if transaction.payment_method == 'cash' else "Paid"],
                ["Reference:", transaction.transaction_ref],
            ]
            
            payment_table = Table(payment_data, colWidths=[2*inch, 4*inch])
            payment_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            
            elements.append(payment_table)
            elements.append(Spacer(1, 20))
        
        # Generate QR code using payments QR service
        from payments.qr_service import QRCodeService as PaymentQRService
        qr_data = f"BINTACURA-APT:{appointment.uid}:{receipt_number}:{appointment.patient.uid}"
        qr_image_base64 = PaymentQRService.generate_qr_code_image(qr_data)
        
        if qr_image_base64 and qr_image_base64.startswith('data:image/png;base64,'):
            import base64
            qr_image_data = base64.b64decode(qr_image_base64.split(',')[1])
            qr_buffer = BytesIO(qr_image_data)
            qr_image = Image(qr_buffer, width=1.5*inch, height=1.5*inch)
        else:
            qr_image = Paragraph("<i>QR code unavailable</i>", styles['Normal'])
        qr_image.hAlign = 'CENTER'
        
        elements.append(Spacer(1, 10))
        qr_label = Paragraph("<b>Scan QR Code for Verification</b>", subtitle_style)
        elements.append(qr_label)
        elements.append(qr_image)
        elements.append(Spacer(1, 20))
        
        footer_text = f"""
        <para align=center>
        <font size=9 color='#999999'>
        Please arrive 15 minutes before your appointment time.<br/>
        Present this receipt at the reception desk.<br/>
        {'Cash payment will be collected upon arrival.<br/>' if transaction and transaction.payment_method == 'cash' else ''}
        For any changes or cancellations, contact us at {settings.CONTACT_EMAIL}<br/>
        <b>Thank you for choosing BINTACURA!</b>
        </font>
        </para>
        """
        
        footer = Paragraph(footer_text, normal_style)
        elements.append(footer)
        
        doc.build(elements)

        buffer.seek(0)
        return buffer

    @staticmethod
    def generate_service_transaction_receipt(service_transaction, receipt_number=None):
        """
        Generate a PDF receipt for a ServiceTransaction with currency conversion

        Args:
            service_transaction: ServiceTransaction instance
            receipt_number: Optional receipt number

        Returns:
            BytesIO buffer containing the PDF
        """
        from currency_converter.services import CurrencyConverterService

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )

        elements = []
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#333333'),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )

        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#555555'),
            spaceAfter=6
        )

        title = Paragraph("BINTACURA", title_style)
        elements.append(title)

        subtitle = Paragraph("Healthcare Platform", normal_style)
        elements.append(subtitle)
        elements.append(Spacer(1, 20))

        receipt_title = Paragraph("PAYMENT RECEIPT", heading_style)
        elements.append(receipt_title)
        elements.append(Spacer(1, 20))

        if receipt_number:
            receipt_no = Paragraph(f"<b>Receipt No:</b> {receipt_number}", normal_style)
            elements.append(receipt_no)

        ref_para = Paragraph(f"<b>Transaction Reference:</b> {service_transaction.transaction_ref}", normal_style)
        elements.append(ref_para)

        created_date = service_transaction.created_at.strftime("%B %d, %Y %I:%M %p")
        date_para = Paragraph(f"<b>Date:</b> {created_date}", normal_style)
        elements.append(date_para)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Patient Information</b>", heading_style))

        customer_data = [
            ["Name:", service_transaction.patient.full_name or "N/A"],
            ["Email:", service_transaction.patient.email],
            ["Phone:", service_transaction.patient.phone_number or "N/A"],
        ]

        customer_table = Table(customer_data, colWidths=[2*inch, 4*inch])
        customer_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(customer_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Service Provider Information</b>", heading_style))

        provider_data = [
            ["Name:", service_transaction.service_provider.full_name or "N/A"],
            ["Type:", service_transaction.service_provider_role.title()],
            ["Email:", service_transaction.service_provider.email],
        ]

        provider_table = Table(provider_data, colWidths=[2*inch, 4*inch])
        provider_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(provider_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Service Details</b>", heading_style))

        service_name = service_transaction.service_catalog_item.service_name if service_transaction.service_catalog_item else "Custom Service"

        service_data = [
            ["Service:", service_name],
            ["Type:", service_transaction.get_service_type_display()],
            ["Description:", service_transaction.service_description],
            ["Payment Method:", service_transaction.get_payment_method_display()],
            ["Status:", service_transaction.get_status_display()],
        ]

        service_table = Table(service_data, colWidths=[2*inch, 4*inch])
        service_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(service_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph("<b>Payment Breakdown</b>", heading_style))

        amount_formatted = CurrencyConverterService.format_amount(service_transaction.amount, service_transaction.currency)

        breakdown_data = [
            ["Service Amount:", amount_formatted],
        ]

        if hasattr(service_transaction, 'fee_details') and service_transaction.fee_details:
            fee_details = service_transaction.fee_details
            platform_fee_formatted = CurrencyConverterService.format_amount(fee_details.platform_fee_amount, service_transaction.currency)
            tax_formatted = CurrencyConverterService.format_amount(fee_details.tax_amount, service_transaction.currency)
            net_amount_formatted = CurrencyConverterService.format_amount(fee_details.net_amount_to_provider, service_transaction.currency)

            breakdown_data.extend([
                ["Platform Fee (1%):", platform_fee_formatted],
                ["Tax (18%):", tax_formatted],
                ["Net to Provider:", net_amount_formatted],
            ])

        if service_transaction.currency != 'USD':
            try:
                usd_amount = CurrencyConverterService.convert_currency(
                    service_transaction.amount,
                    service_transaction.currency,
                    'USD'
                )
                usd_formatted = CurrencyConverterService.format_amount(usd_amount, 'USD')
                breakdown_data.append(["Equivalent (USD):", usd_formatted])
            except:
                pass

        breakdown_table = Table(breakdown_data, colWidths=[2*inch, 4*inch])
        breakdown_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#555555')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(breakdown_table)
        elements.append(Spacer(1, 30))

        total_data = [
            ["TOTAL AMOUNT", amount_formatted]
        ]

        total_table = Table(total_data, colWidths=[3*inch, 3*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#667eea')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#667eea')),
        ]))

        elements.append(total_table)
        elements.append(Spacer(1, 40))

        footer_text = """
        <para align=center>
        <font size=9 color='#888888'>
        This is an automatically generated receipt.<br/>
        For questions, contact support@BINTACURA.com<br/>
        Thank you for using BINTACURA!
        </font>
        </para>
        """

        footer = Paragraph(footer_text, normal_style)
        elements.append(footer)

        doc.build(elements)

        buffer.seek(0)
        return buffer

