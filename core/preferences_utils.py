"""
Utility functions for participant preferences.
"""
from .preferences import ParticipantPreferences
from django.db import transaction


def create_default_preferences(participant):
    """
    Create default preferences for a new participant.
    This should be called when a new participant registers.
    """
    with transaction.atomic():
        preferences, created = ParticipantPreferences.objects.get_or_create(
            participant=participant,
            defaults={
                'theme': 'light',
                'font_size': 'medium',
                'language': participant.preferred_language or 'fr',
                'enable_push_notifications': True,
                'enable_email_notifications': True,
                'enable_sms_notifications': False,
                'notify_appointment_confirmed': True,
                'notify_appointment_cancelled': True,
                'notify_appointment_reminder': True,
                'notify_prescription_ready': True,
                'notify_test_results': True,
                'notify_payment_received': True,
                'notify_payment_due': True,
                'notify_new_message': True,
                'notify_marketing': False,
                'appointment_reminder_time': 60,
                'enable_two_factor_auth': False,
                'profile_visible_to_providers': True,
                'allow_anonymous_data_sharing': False,
                'enable_auto_backup': True,
            }
        )
        return preferences


def get_or_create_preferences(participant):
    """
    Get participant preferences or create with defaults if not exists.
    """
    try:
        return participant.preferences
    except ParticipantPreferences.DoesNotExist:
        return create_default_preferences(participant)


def should_send_notification(participant, notification_type, channel='email'):
    """
    Check if a notification should be sent to a participant.
    
    Args:
        participant: Participant instance
        notification_type: Type of notification (e.g., 'appointment_confirmed')
        channel: Notification channel ('email', 'sms', or 'push')
    
    Returns:
        bool: True if notification should be sent, False otherwise
    """
    try:
        preferences = get_or_create_preferences(participant)
        
        if channel == 'email':
            return preferences.should_send_email_notification(notification_type)
        elif channel == 'sms':
            return preferences.should_send_sms_notification(notification_type)
        elif channel == 'push':
            return preferences.should_send_push_notification(notification_type)
        else:
            return False
            
    except Exception as e:
        # If there's an error, default to sending the notification
        # Log the error for debugging
        print(f"Error checking notification preferences: {e}")
        return True
