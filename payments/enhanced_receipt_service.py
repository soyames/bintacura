import os
import logging
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT, TA_JUSTIFY
from io import BytesIO
from datetime import datetime
import qrcode

logger = logging.getLogger(__name__)


class EnhancedReceiptService:
    
    @staticmethod
    def generate_invoice_receipt(receipt, service_transaction=None):
        """Generate comprehensive invoice receipt matching 001.AFRICA template structure"""
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=50,
            bottomMargin=50
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'CompanyTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#667eea'),
            spaceAfter=5,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        company_info_style = ParagraphStyle(
            'CompanyInfo',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#555555'),
            spaceAfter=3,
            alignment=TA_LEFT
        )
        
        invoice_header_style = ParagraphStyle(
            'InvoiceHeader',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceAfter=3,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        status_paid_style = ParagraphStyle(
            'StatusPaid',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#28a745'),
            spaceAfter=10,
            alignment=TA_RIGHT,
            fontName='Helvetica-Bold'
        )
        
        section_heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=8,
            fontName='Helvetica-Bold',
            borderPadding=(0, 0, 5, 0)
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#555555'),
            spaceAfter=4
        )
        
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo.png')
        header_data = []
        
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=1.2*inch, height=1.2*inch)
                company_details = Paragraph(
                    f"""
                    <b>BINTACURA</b><br/>
                    Healthcare Platform<br/>
                    RCCM: VTC/BJ/2024<br/>
                    IFU: {getattr(settings, 'COMPANY_IFU', 'N/A')}<br/>
                    Tel: {getattr(settings, 'COMPANY_PHONE', '+229 XX XX XX XX')}<br/>
                    <font size=8>{getattr(settings, 'COMPANY_ADDRESS', 'Cotonou, BENIN')}</font>
                    """,
                    company_info_style
                )
                invoice_info = Paragraph(
                    f"""
                    <b>Facture #{receipt.invoice_number or receipt.receipt_number}</b><br/>
                    <font color='#28a745' size=14><b>{receipt.get_payment_status_display()}</b></font>
                    """,
                    invoice_header_style
                )
                header_data = [[logo, company_details, invoice_info]]
            except:
                pass
        
        if not header_data:
            company_title = Paragraph("BINTACURA", title_style)
            company_subtitle = Paragraph("Healthcare Platform", company_info_style)
            invoice_title = Paragraph(f"Facture #{receipt.invoice_number or receipt.receipt_number}", invoice_header_style)
            status_para = Paragraph(receipt.get_payment_status_display(), status_paid_style)
            elements.append(company_title)
            elements.append(company_subtitle)
            elements.append(Spacer(1, 10))
            elements.append(invoice_title)
            elements.append(status_para)
        else:
            header_table = Table(header_data, colWidths=[1.5*inch, 2.5*inch, 2.5*inch])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'LEFT'),
                ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ]))
            elements.append(header_table)
        
        elements.append(Spacer(1, 20))
        
        billing_section_data = [
            [
                Paragraph("<b>Payer à</b>", section_heading_style),
                Paragraph("<b>Facturé à</b>", section_heading_style),
            ],
            [
                Paragraph(
                    f"""
                    <b>BINTACURA</b><br/>
                    Healthcare Platform<br/>
                    RCCM: VTC/BJ/2024<br/>
                    IFU: {getattr(settings, 'COMPANY_IFU', 'N/A')}<br/>
                    Tel: {getattr(settings, 'COMPANY_PHONE', '+229 XX XX XX XX')}<br/>
                    {getattr(settings, 'COMPANY_ADDRESS', 'Cotonou, BENIN')}
                    """,
                    normal_style
                ),
                Paragraph(
                    f"""
                    <b>{receipt.issued_to_name or receipt.issued_to.full_name or 'N/A'}</b><br/>
                    {receipt.issued_to.email}<br/>
                    {receipt.issued_to_address or receipt.issued_to.address or ''}<br/>
                    {receipt.issued_to_city or receipt.issued_to.city or ''}<br/>
                    {receipt.issued_to_country or receipt.issued_to.country or ''}
                    """,
                    normal_style
                ),
            ]
        ]
        
        billing_table = Table(billing_section_data, colWidths=[3*inch, 3*inch])
        billing_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(billing_table)
        elements.append(Spacer(1, 15))
        
        payment_info_data = [
            [
                Paragraph("<b>Mode de paiement</b>", section_heading_style),
                Paragraph("<b>Date de facturation</b>", section_heading_style),
            ],
            [
                Paragraph(
                    f"{receipt.payment_gateway or 'Stripe'} - {receipt.payment_method or 'Carte bancaire'}",
                    normal_style
                ),
                Paragraph(
                    (receipt.billing_date or receipt.issued_at).strftime("%d/%m/%Y"),
                    normal_style
                ),
            ]
        ]
        
        payment_info_table = Table(payment_info_data, colWidths=[3*inch, 3*inch])
        payment_info_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(payment_info_table)
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("<b>Items de la facture</b>", section_heading_style))
        elements.append(Spacer(1, 10))
        
        line_items_data = [
            [
                Paragraph("<b>Descriptif</b>", normal_style),
                Paragraph("<b>Montant</b>", normal_style)
            ]
        ]
        
        if receipt.line_items and len(receipt.line_items) > 0:
            for item in receipt.line_items:
                desc = item.get('description', 'Service')
                amount_fmt = EnhancedReceiptService._format_currency(
                    Decimal(str(item.get('amount', 0))),
                    receipt.currency
                )
                taxable = ' *' if item.get('taxable', False) else ''
                line_items_data.append([
                    Paragraph(f"{desc}{taxable}", normal_style),
                    Paragraph(amount_fmt, normal_style)
                ])
        else:
            service_desc = "Service de santé"
            if service_transaction:
                service_desc = service_transaction.service_description
            elif receipt.service_details:
                service_desc = receipt.service_details.get('description', 'Service de santé')
            
            amount_fmt = EnhancedReceiptService._format_currency(receipt.subtotal or receipt.amount, receipt.currency)
            line_items_data.append([
                Paragraph(f"{service_desc} *", normal_style),
                Paragraph(amount_fmt, normal_style)
            ])
        
        if receipt.platform_fee and receipt.platform_fee > 0:
            fee_fmt = EnhancedReceiptService._format_currency(receipt.platform_fee, receipt.currency)
            line_items_data.append([
                Paragraph("Frais de transaction (Plateforme)", normal_style),
                Paragraph(fee_fmt, normal_style)
            ])
        
        subtotal_fmt = EnhancedReceiptService._format_currency(receipt.subtotal or receipt.amount, receipt.currency)
        line_items_data.append([
            Paragraph("<b>Sous-total</b>", normal_style),
            Paragraph(f"<b>{subtotal_fmt}</b>", normal_style)
        ])
        
        if receipt.tax_amount and receipt.tax_amount > 0:
            tax_fmt = EnhancedReceiptService._format_currency(receipt.tax_amount, receipt.currency)
            line_items_data.append([
                Paragraph(f"{receipt.tax_rate}% TVA", normal_style),
                Paragraph(tax_fmt, normal_style)
            ])
        
        if receipt.discount_amount and receipt.discount_amount > 0:
            discount_fmt = EnhancedReceiptService._format_currency(receipt.discount_amount, receipt.currency)
            line_items_data.append([
                Paragraph("Crédit", normal_style),
                Paragraph(discount_fmt, normal_style)
            ])
        
        total_fmt = EnhancedReceiptService._format_currency(receipt.total_amount or receipt.amount, receipt.currency)
        line_items_data.append([
            Paragraph("<b>Total</b>", normal_style),
            Paragraph(f"<b>{total_fmt}</b>", normal_style)
        ])
        
        line_items_table = Table(line_items_data, colWidths=[4.5*inch, 1.5*inch])
        line_items_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#333333')),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#333333')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(line_items_table)
        elements.append(Spacer(1, 10))
        elements.append(Paragraph("<font size=8>* Indique un article taxable.</font>", normal_style))
        elements.append(Spacer(1, 20))
        
        if receipt.transaction_reference or receipt.gateway_transaction_id:
            elements.append(Paragraph("<b>Transactions</b>", section_heading_style))
            elements.append(Spacer(1, 10))
            
            transaction_data = [
                [
                    Paragraph("<b>Date de la transaction</b>", normal_style),
                    Paragraph("<b>Passerelle</b>", normal_style),
                    Paragraph("<b>Transaction #</b>", normal_style),
                    Paragraph("<b>Montant</b>", normal_style),
                ]
            ]
            
            payment_date = (receipt.payment_date or receipt.issued_at).strftime("%d/%m/%Y")
            gateway = receipt.payment_gateway or '-'
            txn_id = receipt.gateway_transaction_id or receipt.transaction_reference or '-'
            amount_fmt = EnhancedReceiptService._format_currency(receipt.total_amount or receipt.amount, receipt.currency)
            
            transaction_data.append([
                Paragraph(payment_date, normal_style),
                Paragraph(gateway, normal_style),
                Paragraph(txn_id, normal_style),
                Paragraph(amount_fmt, normal_style),
            ])
            
            if receipt.discount_amount and receipt.discount_amount > 0:
                discount_fmt = EnhancedReceiptService._format_currency(-receipt.discount_amount, receipt.currency)
                transaction_data.append([
                    Paragraph((receipt.issued_at + timezone.timedelta(days=1)).strftime("%d/%m/%Y"), normal_style),
                    Paragraph('-', normal_style),
                    Paragraph('', normal_style),
                    Paragraph(discount_fmt, normal_style),
                ])
            
            balance = (receipt.total_amount or receipt.amount) - (receipt.discount_amount or Decimal('0'))
            balance_fmt = EnhancedReceiptService._format_currency(balance, receipt.currency)
            transaction_data.append([
                Paragraph("<b>Solde</b>", normal_style),
                Paragraph('', normal_style),
                Paragraph('', normal_style),
                Paragraph(f"<b>{balance_fmt}</b>", normal_style),
            ])
            
            transaction_table = Table(transaction_data, colWidths=[1.3*inch, 1.5*inch, 2*inch, 1.2*inch])
            transaction_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#333333')),
                ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#333333')),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(transaction_table)
            elements.append(Spacer(1, 20))
        
        footer_text = f"""
        <para align=center>
        <font size=9 color='#888888'>
        Ce reçu a été généré automatiquement.<br/>
        Pour toute question, contactez support@BINTACURA.com<br/>
        Merci d'utiliser BINTACURA!
        </font>
        </para>
        """
        footer = Paragraph(footer_text, normal_style)
        elements.append(footer)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    @staticmethod
    def _format_currency(amount, currency='XOF'):
        """Format currency amounts properly"""
        if currency in ['XOF', 'CFA']:
            return f"{amount:,.2f}F CFA".replace(',', ' ')
        elif currency == 'USD':
            return f"${amount:,.2f}"
        elif currency == 'EUR':
            return f"€{amount:,.2f}"
        else:
            return f"{amount:,.2f} {currency}"
    
    @staticmethod
    def create_receipt_from_service_transaction(service_transaction):
        """Create PaymentReceipt from ServiceTransaction"""
        from .models import PaymentReceipt
        from .invoice_number_service import InvoiceNumberService
        
        service_provider_role = service_transaction.service_provider.role if service_transaction.service_provider else None
        
        receipt_number = InvoiceNumberService.generate_receipt_number()
        invoice_number, invoice_sequence = InvoiceNumberService.generate_invoice_number(service_provider_role)
        
        fee_details = service_transaction.fee_details if hasattr(service_transaction, 'fee_details') else None
        
        line_items = [{
            'description': service_transaction.service_description,
            'amount': str(service_transaction.amount),
            'taxable': True
        }]
        
        if fee_details:
            if fee_details.platform_fee_amount > 0:
                line_items.append({
                    'description': f'Transaction Fee ({service_transaction.get_payment_method_display()})',
                    'amount': str(fee_details.platform_fee_amount),
                    'taxable': False
                })
        
        if service_transaction.payment_method == 'onsite_cash':
            payment_status = 'PAID' if service_transaction.status == 'completed' else 'PENDING'
        else:
            payment_status = 'PAID' if service_transaction.status == 'completed' else 'PENDING'
        
        receipt = PaymentReceipt.objects.create(
            service_transaction=service_transaction,
            receipt_number=receipt_number,
            invoice_number=invoice_number,
            invoice_sequence=invoice_sequence,
            transaction_type='OTHER',
            payment_status=payment_status,
            issued_to=service_transaction.patient,
            issued_by=service_transaction.service_provider,
            issued_to_name=service_transaction.patient.full_name,
            issued_to_address=service_transaction.patient.address,
            issued_to_city=service_transaction.patient.city,
            issued_to_country=service_transaction.patient.country,
            subtotal=service_transaction.amount,
            tax_amount=fee_details.tax_amount if fee_details else Decimal('0'),
            tax_rate=Decimal('18.00'),
            platform_fee=fee_details.platform_fee_amount if fee_details else Decimal('0'),
            total_amount=service_transaction.amount,
            amount=service_transaction.amount,
            currency=service_transaction.currency,
            payment_method=service_transaction.payment_method,
            payment_gateway=service_transaction.gateway_transaction.gateway_provider if service_transaction.gateway_transaction else None,
            transaction_reference=service_transaction.transaction_ref,
            gateway_transaction_id=service_transaction.gateway_transaction.gateway_transaction_id if service_transaction.gateway_transaction else None,
            line_items=line_items,
            billing_date=service_transaction.created_at,
            payment_date=service_transaction.completed_at,
            service_details={
                'service_type': service_transaction.service_type,
                'service_id': str(service_transaction.service_id),
                'provider_name': service_transaction.service_provider.full_name,
                'provider_role': service_transaction.service_provider_role
            }
        )
        
        from .qr_service import QRCodeService
        QRCodeService.generate_invoice_qr_code(receipt)
        
        return receipt

