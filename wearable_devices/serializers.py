from rest_framework import serializers
from .models import WearableDevice, WearableData, WearableSyncLog


class WearableDeviceSerializer(serializers.ModelSerializer):
    device_type_display = serializers.CharField(source='get_device_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WearableDevice
        fields = [
            'id', 'device_type', 'device_type_display', 'device_name', 
            'device_id', 'status', 'status_display', 'last_sync', 
            'sync_frequency', 'auto_sync_enabled', 'data_types_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_sync', 'created_at', 'updated_at']


class WearableDataSerializer(serializers.ModelSerializer):
    data_type_display = serializers.CharField(source='get_data_type_display', read_only=True)
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    
    class Meta:
        model = WearableData
        fields = [
            'id', 'device', 'device_name', 'data_type', 'data_type_display',
            'timestamp', 'value', 'unit', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WearableSyncLogSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source='device.device_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = WearableSyncLog
        fields = [
            'id', 'device', 'device_name', 'sync_started_at', 
            'sync_completed_at', 'status', 'status_display',
            'records_fetched', 'records_stored', 'errors'
        ]
        read_only_fields = ['id', 'sync_started_at', 'sync_completed_at']


class WearableDataAggregateSerializer(serializers.Serializer):
    """Serializer for aggregated wearable data"""
    data_type = serializers.CharField()
    date = serializers.DateField()
    avg_value = serializers.FloatField()
    min_value = serializers.FloatField()
    max_value = serializers.FloatField()
    count = serializers.IntegerField()
    unit = serializers.CharField()
