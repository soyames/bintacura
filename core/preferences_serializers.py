from rest_framework import serializers
from .preferences import ParticipantPreferences, EmergencyContact


class ParticipantPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for participant preferences."""
    
    class Meta:
        model = ParticipantPreferences
        fields = [
            'id',
            'theme',
            'font_size',
            'language',
            'enable_push_notifications',
            'enable_email_notifications',
            'enable_sms_notifications',
            'notify_appointment_confirmed',
            'notify_appointment_cancelled',
            'notify_appointment_reminder',
            'notify_prescription_ready',
            'notify_test_results',
            'notify_payment_received',
            'notify_payment_due',
            'notify_new_message',
            'notify_marketing',
            'appointment_reminder_time',
            'enable_two_factor_auth',
            'profile_visible_to_providers',
            'allow_anonymous_data_sharing',
            'enable_auto_backup',
            'blood_type',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate preference data."""
        # Ensure email notifications are enabled if appointment reminders are on
        if data.get('notify_appointment_reminder') and not data.get('enable_email_notifications', True):
            if not data.get('enable_sms_notifications', False):
                raise serializers.ValidationError(
                    "Please enable email or SMS notifications to receive appointment reminders."
                )
        return data


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Serializer for emergency contacts."""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id',
            'full_name',
            'relationship',
            'phone_number',
            'email',
            'is_primary',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Ensure only one primary contact per participant."""
        if data.get('is_primary'):
            participant = self.context.get('participant')
            if participant:
                # Check if another primary contact exists
                existing_primary = EmergencyContact.objects.filter(
                    participant=participant,
                    is_primary=True
                ).exclude(pk=self.instance.pk if self.instance else None).first()
                
                if existing_primary:
                    # Automatically set the old primary to False
                    existing_primary.is_primary = False
                    existing_primary.save()
        
        return data
