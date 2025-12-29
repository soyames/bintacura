# Generated migration to rename user fields to participant

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('communication', '0002_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='communityconnection',
            old_name='from_user',
            new_name='from_participant',
        ),
        migrations.RenameField(
            model_name='communityconnection',
            old_name='to_user',
            new_name='to_participant',
        ),
        migrations.AlterUniqueTogether(
            name='communityconnection',
            unique_together={('from_participant', 'to_participant', 'connection_type')},
        ),
    ]
