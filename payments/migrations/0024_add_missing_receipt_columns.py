"""
Add missing columns to payment_receipts table
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0023_fix_currency_defaults_to_xof'),
        ('core', '0033_participant_rejection_reason_and_more'),
    ]

    operations = [
        # Add missing FK columns
        migrations.AddField(
            model_name='paymentreceipt',
            name='transaction',
            field=models.OneToOneField(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='receipt', to='core.transaction'
            ),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_to',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='receipts', to='core.participant',
                default='00000000-0000-0000-0000-000000000000'
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_by',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                related_name='issued_receipts', to='core.participant'
            ),
        ),
        
        # Add string fields
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_to_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_to_address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_to_city',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_to_country',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='invoice_number',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='invoice_sequence',
            field=models.IntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='transaction_type',
            field=models.CharField(
                choices=[
                    ('APPOINTMENT', 'Appointment Payment'),
                    ('PRESCRIPTION', 'Prescription Purchase'),
                    ('CONSULTATION', 'Consultation Fee'),
                    ('WALLET_DEPOSIT', 'Wallet Deposit'),
                    ('WALLET_WITHDRAWAL', 'Wallet Withdrawal'),
                    ('INSURANCE_CLAIM', 'Insurance Claim'),
                    ('TRANSPORT', 'Transport Service'),
                    ('PHARMACY', 'Pharmacy Purchase'),
                    ('HOSPITAL_SERVICE', 'Hospital Service'),
                    ('LAB_TEST', 'Laboratory Test'),
                    ('OTHER', 'Other'),
                ],
                default='OTHER', max_length=30
            ),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='payment_status',
            field=models.CharField(
                choices=[
                    ('PAID', 'Paid'),
                    ('PENDING', 'Pending'),
                    ('FAILED', 'Failed'),
                    ('REFUNDED', 'Refunded'),
                ],
                default='PAID', max_length=20
            ),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='transaction_reference',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='payment_gateway',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='gateway_transaction_id',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='pdf_url',
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='pdf_file',
            field=models.FileField(blank=True, null=True, upload_to='receipts/'),
        ),
        
        # Add decimal fields
        migrations.AddField(
            model_name='paymentreceipt',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='tax_rate',
            field=models.DecimalField(decimal_places=4, default=0, max_digits=6),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='tax_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='discount_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='platform_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='total_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        
        # Add datetime fields
        migrations.AddField(
            model_name='paymentreceipt',
            name='issued_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='payment_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='billing_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='reminder_sent',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='reminded_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        
        # Add JSON fields
        migrations.AddField(
            model_name='paymentreceipt',
            name='line_items',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name='paymentreceipt',
            name='service_details',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
