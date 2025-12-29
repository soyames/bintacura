from django.conf import settings
import logging

logger = logging.getLogger(__name__)

try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio module not installed. SMS functionality will be disabled.")


class SMSService:  # Service class for SMS operations
    def __init__(self):  # Initialize instance
        self.account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        self.auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        self.from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)

        if TWILIO_AVAILABLE and all(
            [self.account_sid, self.auth_token, self.from_number]
        ):
            self.client = Client(self.account_sid, self.auth_token)
        else:
            self.client = None
            if not TWILIO_AVAILABLE:
                logger.warning("Twilio module not available")
            else:
                logger.warning("Twilio credentials not configured")

    def send_sms(self, to_number, message):  # Send sms
        if not self.client:
            logger.error("SMS service not initialized")
            return False

        try:
            message = self.client.messages.create(
                body=message, from_=self.from_number, to=to_number
            )
            logger.info(f"SMS sent successfully: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            return False

    def send_appointment_reminder(self, appointment):  # Send appointment reminder
        patient_phone = appointment.patient.phone
        if not patient_phone:
            return False

        message = f"Rappel: Rendez-vous le {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')} avec {appointment.doctor.full_name if appointment.doctor else appointment.hospital.name}. BINTACURA"
        return self.send_sms(patient_phone, message)

    def send_appointment_confirmation(self, appointment):  # Send appointment confirmation
        patient_phone = appointment.patient.phone
        if not patient_phone:
            return False

        message = f"Votre rendez-vous a été confirmé pour le {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')}. BINTACURA"
        return self.send_sms(patient_phone, message)

    def send_appointment_cancellation(self, appointment):  # Send appointment cancellation
        patient_phone = appointment.patient.phone
        if not patient_phone:
            return False

        message = f"Votre rendez-vous du {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')} a été annulé. BINTACURA"
        return self.send_sms(patient_phone, message)

    def send_prescription_ready(self, prescription):  # Send prescription ready
        patient_phone = prescription.patient.phone
        if not patient_phone:
            return False

        message = f"Votre ordonnance est prête à être retirée à {prescription.pharmacy.name}. BINTACURA"
        return self.send_sms(patient_phone, message)


sms_service = SMSService()

