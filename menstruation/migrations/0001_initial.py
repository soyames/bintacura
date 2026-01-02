# Generated manually - Creating all menstruation tables fresh

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create MenstrualCycle table
        migrations.CreateModel(
            name='MenstrualCycle',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Global unique identifier', primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last modified')),
                ('version', models.IntegerField(default=1, help_text='Version number for conflict detection')),
                ('last_synced_at', models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True)),
                ('created_by_instance', models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record')),
                ('modified_by_instance', models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes')),
                ('deleted_at', models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True)),
                ('cycle_start_date', models.DateField(help_text='First day of menstruation')),
                ('cycle_end_date', models.DateField(blank=True, help_text='Last day of cycle (first day of next period)', null=True)),
                ('period_length', models.IntegerField(default=5, help_text='Number of days of active menstruation')),
                ('cycle_length', models.IntegerField(default=28, help_text='Total cycle length in days')),
                ('flow_intensity', models.CharField(blank=True, choices=[('light', 'Light'), ('medium', 'Medium'), ('heavy', 'Heavy'), ('spotting', 'Spotting')], max_length=20)),
                ('symptoms', models.JSONField(blank=True, default=list, help_text='List of symptoms experienced (cramps, headache, bloating, etc.)')),
                ('mood', models.CharField(blank=True, choices=[('happy', 'Happy'), ('normal', 'Normal'), ('irritable', 'Irritable'), ('sad', 'Sad'), ('anxious', 'Anxious'), ('tired', 'Tired')], max_length=50)),
                ('notes', models.TextField(blank=True, help_text='Personal notes about this cycle')),
                ('predicted_ovulation_date', models.DateField(blank=True, null=True)),
                ('predicted_next_period_date', models.DateField(blank=True, null=True)),
                ('predicted_fertile_window_start', models.DateField(blank=True, null=True)),
                ('predicted_fertile_window_end', models.DateField(blank=True, null=True)),
                ('is_active_cycle', models.BooleanField(default=True, help_text='Whether this is the current cycle')),
                ('patient', models.ForeignKey(limit_choices_to={'gender__in': ['female', 'feminin', 'f', 'F', 'Female']}, on_delete=django.db.models.deletion.CASCADE, related_name='menstrual_cycles', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'menstrual_cycles',
                'ordering': ['-cycle_start_date'],
            },
        ),
        
        # Create CycleSymptom table
        migrations.CreateModel(
            name='CycleSymptom',
            fields=[
                ('uid', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('symptom_type', models.CharField(choices=[('cramps', 'Cramps'), ('headache', 'Headache'), ('bloating', 'Bloating'), ('breast_tenderness', 'Breast Tenderness'), ('acne', 'Acne'), ('back_pain', 'Back Pain'), ('fatigue', 'Fatigue'), ('nausea', 'Nausea'), ('diarrhea', 'Diarrhea'), ('constipation', 'Constipation'), ('food_cravings', 'Food Cravings'), ('mood_swings', 'Mood Swings'), ('insomnia', 'Insomnia'), ('other', 'Other')], max_length=50)),
                ('severity', models.IntegerField(choices=[(1, 'Mild'), (2, 'Moderate'), (3, 'Severe')], default=1)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('cycle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_symptoms', to='menstruation.menstrualcycle')),
            ],
            options={
                'db_table': 'cycle_symptoms',
                'ordering': ['-date'],
            },
        ),
        
        # Create CycleReminder table
        migrations.CreateModel(
            name='CycleReminder',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Global unique identifier', primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False, help_text='When this record was created')),
                ('updated_at', models.DateTimeField(auto_now=True, help_text='When this record was last modified')),
                ('version', models.IntegerField(default=1, help_text='Version number for conflict detection')),
                ('last_synced_at', models.DateTimeField(blank=True, help_text='When this record was last synced with cloud', null=True)),
                ('created_by_instance', models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that created this record')),
                ('modified_by_instance', models.UUIDField(blank=True, default=uuid.uuid4, help_text='UUID of instance that last modified this record')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, help_text='Soft delete flag for sync purposes')),
                ('deleted_at', models.DateTimeField(blank=True, help_text='When this record was marked as deleted', null=True)),
                ('reminder_type', models.CharField(choices=[('period_starting', 'Period Starting Soon'), ('ovulation', 'Ovulation Day'), ('fertile_window', 'Fertile Window'), ('period_late', 'Period Late'), ('log_cycle', 'Log Your Cycle')], max_length=50)),
                ('reminder_date', models.DateField()),
                ('reminder_time', models.TimeField(default='08:00:00')),
                ('is_sent', models.BooleanField(default=False)),
                ('is_enabled', models.BooleanField(default=True)),
                ('message', models.TextField(blank=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cycle_reminders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'cycle_reminders',
                'ordering': ['reminder_date', 'reminder_time'],
            },
        ),
        
        # Add indexes
        migrations.AddIndex(
            model_name='menstrualcycle',
            index=models.Index(fields=['patient', 'cycle_start_date'], name='menstrual_c_patient_f12d6f_idx'),
        ),
        migrations.AddIndex(
            model_name='menstrualcycle',
            index=models.Index(fields=['patient', 'is_active_cycle'], name='menstrual_c_patient_0a819a_idx'),
        ),
        
        # Add unique constraint
        migrations.AlterUniqueTogether(
            name='cyclesymptom',
            unique_together={('cycle', 'date', 'symptom_type')},
        ),
    ]
