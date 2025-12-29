from django.db import migrations


def update_existing_configs(apps, schema_editor):
    """Update existing SystemConfiguration records to use USD"""
    SystemConfiguration = apps.get_model('core', 'SystemConfiguration')
    SystemConfiguration.objects.filter(
        default_consultation_currency='EUR'
    ).update(default_consultation_currency='USD')


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_update_currency_to_usd'),
    ]

    operations = [
        migrations.RunPython(update_existing_configs, migrations.RunPython.noop),
    ]
