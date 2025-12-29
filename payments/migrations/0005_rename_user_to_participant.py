from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0004_participantphone_participantgatewayaccount_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='paymentrequest',
            old_name='from_user',
            new_name='from_participant',
        ),
        migrations.RenameField(
            model_name='paymentrequest',
            old_name='to_user',
            new_name='to_participant',
        ),
        migrations.RenameField(
            model_name='transfer',
            old_name='from_user',
            new_name='from_participant',
        ),
        migrations.RenameField(
            model_name='transfer',
            old_name='to_user',
            new_name='to_participant',
        ),
    ]
