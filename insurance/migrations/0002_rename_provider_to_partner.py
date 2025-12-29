from django.db import migrations


def rename_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE insurance_claims RENAME COLUMN provider_name TO partner_name;')
        cursor.execute('ALTER TABLE insurance_claims RENAME COLUMN provider_id TO partner_id;')


def reverse_rename_columns(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute('ALTER TABLE insurance_claims RENAME COLUMN partner_name TO provider_name;')
        cursor.execute('ALTER TABLE insurance_claims RENAME COLUMN partner_id TO provider_id;')


class Migration(migrations.Migration):

    dependencies = [
        ('insurance', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(rename_columns, reverse_rename_columns),
    ]
