# Generated manually on 2024-12-30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('hospital', '0006_remove_bed_is_ibintation_bed_is_isolation'),
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HospitalData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('license_number', models.CharField(max_length=100, unique=True)),
                ('bed_capacity', models.IntegerField(default=0)),
                ('consultation_fee', models.IntegerField(default=0, help_text='Consultation fee in XOF cents')),
                ('emergency_services', models.BooleanField(default=False)),
                ('has_icu', models.BooleanField(default=False)),
                ('has_maternity', models.BooleanField(default=False)),
                ('has_laboratory', models.BooleanField(default=False)),
                ('has_pharmacy', models.BooleanField(default=False)),
                ('has_ambulance', models.BooleanField(default=False)),
                ('specialties', models.JSONField(default=list)),
                ('operating_hours', models.JSONField(default=dict)),
                ('rating', models.FloatField(default=0.0)),
                ('total_reviews', models.IntegerField(default=0)),
                ('participant', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='hospital_data', to='core.participant')),
            ],
            options={
                'db_table': 'hospital_data',
            },
        ),
    ]
