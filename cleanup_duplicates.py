#!/usr/bin/env python
"""Clean up duplicate disconnected wearable devices"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from wearable_devices.models import WearableDevice
from django.db.models import Count

def cleanup_duplicates():
    """Remove duplicate disconnected devices, keeping only one per patient/device_type"""
    
    # Find patients with multiple disconnected devices of the same type
    duplicates = (
        WearableDevice.objects
        .filter(status='disconnected')
        .values('patient', 'device_type')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    
    print(f"Found {len(duplicates)} sets of duplicates")
    
    total_deleted = 0
    for dup in duplicates:
        patient_id = dup['patient']
        device_type = dup['device_type']
        count = dup['count']
        
        # Get all disconnected devices for this patient/type
        devices = WearableDevice.objects.filter(
            patient_id=patient_id,
            device_type=device_type,
            status='disconnected'
        ).order_by('-created_at')
        
        # Keep the most recent one, delete the rest
        devices_to_delete = devices[1:]
        deleted = len(devices_to_delete)
        
        print(f"Patient {patient_id}, {device_type}: Keeping 1, deleting {deleted}")
        
        for device in devices_to_delete:
            device.delete()
            total_deleted += 1
    
    print(f"\nTotal devices deleted: {total_deleted}")
    
    # Show remaining devices
    remaining = WearableDevice.objects.all().count()
    print(f"Remaining devices: {remaining}")

if __name__ == '__main__':
    cleanup_duplicates()
