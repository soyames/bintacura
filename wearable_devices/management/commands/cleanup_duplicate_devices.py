from django.core.management.base import BaseCommand
from wearable_devices.models import WearableDevice
from django.db.models import Count


class Command(BaseCommand):
    help = 'Clean up duplicate wearable devices'

    def handle(self, *args, **options):
        duplicates = (
            WearableDevice.objects.values('patient', 'device_type')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_cleaned = 0
        for dup in duplicates:
            patient_id = dup['patient']
            device_type = dup['device_type']
            devices = WearableDevice.objects.filter(
                patient_id=patient_id,
                device_type=device_type
            ).order_by('-updated_at', '-created_at')
            keep = devices.first()
            to_delete = devices.exclude(id=keep.id)
            count = to_delete.count()
            if count > 0:
                self.stdout.write(f'Deleting {count} {device_type} devices')
                to_delete.delete()
                total_cleaned += count

        self.stdout.write(self.style.SUCCESS(f'Cleaned up {total_cleaned} devices'))
