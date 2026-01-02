from rest_framework import serializers
from .models import MenstrualCycle, CycleSymptom, CycleReminder
from core.models import Participant


class CycleSymptomSerializer(serializers.ModelSerializer):
    """Serializer for daily symptom tracking"""
    
    class Meta:
        model = CycleSymptom
        fields = [
            'uid', 'cycle', 'date', 'symptom_type', 'severity',
            'notes', 'created_at'
        ]
        read_only_fields = ['uid', 'created_at']


class MenstrualCycleSerializer(serializers.ModelSerializer):
    """Serializer for menstrual cycle tracking"""
    daily_symptoms = CycleSymptomSerializer(many=True, read_only=True)
    cycle_day = serializers.SerializerMethodField()
    is_fertile = serializers.SerializerMethodField()
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = MenstrualCycle
        fields = [
            'uid', 'patient', 'patient_name',
            'cycle_start_date', 'cycle_end_date',
            'period_length', 'cycle_length',
            'flow_intensity', 'symptoms', 'mood', 'notes',
            'predicted_ovulation_date', 'predicted_next_period_date',
            'predicted_fertile_window_start', 'predicted_fertile_window_end',
            'is_active_cycle', 'cycle_day', 'is_fertile',
            'daily_symptoms', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uid', 'created_at', 'updated_at',
            'predicted_ovulation_date', 'predicted_next_period_date',
            'predicted_fertile_window_start', 'predicted_fertile_window_end'
        ]
    
    def get_cycle_day(self, obj):
        """Get current day of cycle"""
        return obj.get_cycle_day()
    
    def get_is_fertile(self, obj):
        """Check if in fertile window"""
        return obj.is_in_fertile_window()


class CycleReminderSerializer(serializers.ModelSerializer):
    """Serializer for cycle reminders"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    
    class Meta:
        model = CycleReminder
        fields = [
            'uid', 'patient', 'patient_name',
            'reminder_type', 'reminder_date', 'reminder_time',
            'is_sent', 'is_enabled', 'message',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['uid', 'created_at', 'updated_at', 'is_sent']


class CycleStatsSerializer(serializers.Serializer):
    """Serializer for cycle statistics"""
    average_cycle_length = serializers.IntegerField()
    average_period_length = serializers.IntegerField()
    total_cycles = serializers.IntegerField()
    last_period_date = serializers.DateField()
    next_predicted_period = serializers.DateField()
    common_symptoms = serializers.ListField()
