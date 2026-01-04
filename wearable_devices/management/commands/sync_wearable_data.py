from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from wearable_devices.models import WearableDevice
from wearable_devices.services import GoogleFitService, FitbitService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync data from all active wearable devices'

    def add_arguments(self, parser):
        parser.add_argument(
            '--device-id',
            type=str,
            help='Sync only a specific device by ID',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to sync (default: 7)',
        )

    def handle(self, *args, **options):
        device_id = options.get('device_id')
        days = options.get('days')
        
        if device_id:
            devices = WearableDevice.objects.filter(id=device_id, status='active')
            if not devices.exists():
                self.stdout.write(self.style.ERROR(f'Device {device_id} not found or not active'))
                return
        else:
            devices = WearableDevice.objects.filter(status='active', auto_sync_enabled=True)
        
        self.stdout.write(f'Found {devices.count()} device(s) to sync')
        
        synced_count = 0
        failed_count = 0
        
        for device in devices:
            try:
                self.stdout.write(f'Syncing {device.device_name} ({device.get_device_type_display()}) for patient {device.patient.get_full_name()}...')
                
                # Determine service based on device type
                if device.device_type == 'google_fit':
                    service = GoogleFitService(device)
                elif device.device_type == 'fitbit':
                    service = FitbitService(device)
                else:
                    self.stdout.write(self.style.WARNING(f'  Sync not implemented for {device.get_device_type_display()}'))
                    continue
                
                # Calculate date range
                end_date = timezone.now()
                start_date = device.last_sync or (end_date - timedelta(days=days))
                
                # Sync data
                sync_log = service.sync_data(start_date=start_date, end_date=end_date)
                
                if sync_log.status == 'success':
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Synced {sync_log.records_stored} records'))
                    synced_count += 1
                else:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Partial sync: {sync_log.records_stored} records'))
                    failed_count += 1
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Failed: {str(e)}'))
                logger.error(f'Error syncing device {device.id}: {str(e)}', exc_info=True)
                failed_count += 1
        
        # Summary
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Sync completed: {synced_count} successful, {failed_count} failed'))
