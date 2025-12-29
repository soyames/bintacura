# Generated migration for appointment fee structure changes

from django.db import migrations, models
import django.db.models.deletion
import uuid
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('appointments', '0001_initial'),
        ('core', '0001_initial'),
    ]

    operations = [
        # Add new fields to Appointment model
        migrations.AddField(
            model_name='appointment',
            name='additional_services_total',
            field=models.DecimalField(decimal_places=2, default=0, help_text='Total cost of additional services selected', max_digits=10),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='consultation_fee',
            field=models.IntegerField(default=0, help_text='Base consultation fee (system default)'),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='original_price',
            field=models.IntegerField(default=0, help_text='consultation_fee + additional_services_total'),
        ),
        migrations.AlterField(
            model_name='appointment',
            name='final_price',
            field=models.IntegerField(default=0, help_text='Total after discounts'),
        ),
        
        # Create AppointmentService model
        migrations.CreateModel(
            name='AppointmentService',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('service_price', models.DecimalField(decimal_places=2, help_text='Price of service at time of booking', max_digits=10)),
                ('quantity', models.IntegerField(default=1)),
                ('subtotal', models.DecimalField(decimal_places=2, help_text='service_price * quantity', max_digits=10)),
                ('created_at', models.DateTimeField(default=timezone.now)),
                ('appointment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='appointment_services', to='appointments.appointment')),
                ('service', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='service_appointments', to='core.providerservice')),
            ],
            options={
                'db_table': 'appointment_services',
                'indexes': [
                    models.Index(fields=['appointment'], name='appointment_idx'),
                    models.Index(fields=['service'], name='service_idx'),
                ],
                'unique_together': {('appointment', 'service')},
            },
        ),
        
        # Create SystemConfiguration model
        migrations.CreateModel(
            name='SystemConfiguration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('default_consultation_fee', models.DecimalField(decimal_places=2, default=5.00, help_text='Standard consultation fee for all appointments (base price)', max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('default_consultation_currency', models.CharField(default='EUR', help_text='Currency code for consultation fee (EUR, USD, XOF, etc.)', max_length=3)),
                ('platform_fee_percentage', models.DecimalField(decimal_places=2, default=1.00, help_text='Platform fee percentage (e.g., 1.00 for 1%)', max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('tax_percentage', models.DecimalField(decimal_places=2, default=18.00, help_text='Tax percentage applied to platform fee (e.g., 18.00 for 18%)', max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('wallet_topup_fee_percentage', models.DecimalField(decimal_places=2, default=0.00, help_text='Fee for wallet top-ups (0 = free)', max_digits=5, validators=[django.core.validators.MinValueValidator(0)])),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(default=timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='system_configs_created', to='core.participant')),
            ],
            options={
                'verbose_name': 'System Configuration',
                'verbose_name_plural': 'System Configuration',
                'db_table': 'system_configuration',
                'ordering': ['-created_at'],
            },
        ),
    ]
