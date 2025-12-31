from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class EmailService:  # Service class for Email operations
    @staticmethod
    def send_email(to_email, subject, template_name, context, participant=None, notification_type=None):
        """
        Send email respecting participant preferences.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_name: Template to use for email body
            context: Context data for template
            participant: Participant instance (optional, for preference checking)
            notification_type: Type of notification (optional, for preference checking)
        """
        # Check participant preferences before sending
        if participant and notification_type:
            from core.preferences_utils import should_send_notification
            if not should_send_notification(participant, notification_type, channel='email'):
                logger.info(f"Email skipped for {to_email} due to preferences: {notification_type}")
                return False
        
        try:
            html_content = render_to_string(template_name, context)

            email = EmailMultiAlternatives(
                subject=subject,
                body=html_content,
                from_email=settings.NO_REPLY_EMAIL,
                to=[to_email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Email envoyé à {to_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Erreur envoi email à {to_email}: {str(e)}")
            return False

    @staticmethod
    def send_appointment_confirmation(appointment):  # Send appointment confirmation
        context = {
            "patient_name": appointment.patient.full_name,
            "doctor_name": appointment.doctor.full_name if appointment.doctor else "",
            "date": appointment.appointment_date.strftime("%d/%m/%Y"),
            "time": appointment.appointment_time.strftime("%H:%M"),
            "appointment_id": str(appointment.id),
        }
        return EmailService.send_email(
            to_email=appointment.patient.email,
            subject="Confirmation de rendez-vous - BINTACURA",
            template_name="emails/appointment_confirmation.html",
            context=context,
            participant=appointment.patient,
            notification_type='appointment_confirmed',
        )

    @staticmethod
    def send_appointment_reminder(appointment):  # Send appointment reminder
        context = {
            "patient_name": appointment.patient.full_name,
            "doctor_name": appointment.doctor.full_name if appointment.doctor else "",
            "date": appointment.appointment_date.strftime("%d/%m/%Y"),
            "time": appointment.appointment_time.strftime("%H:%M"),
        }
        return EmailService.send_email(
            to_email=appointment.patient.email,
            subject="Rappel de rendez-vous - BINTACURA",
            template_name="emails/appointment_reminder.html",
            context=context,
            participant=appointment.patient,
            notification_type='appointment_reminder',
        )

    @staticmethod
    def send_password_reset(user, reset_link):  # Send password reset
        """
        Send password reset email using no-reply@bintacura.org
        """
        from django.core.mail import EmailMultiAlternatives
        from django.template.loader import render_to_string

        context = {
            "user_name": user.full_name,
            "reset_link": reset_link,
        }

        try:
            html_content = render_to_string("emails/password_reset.html", context)

            # Use NO_REPLY_EMAIL for password reset emails
            email = EmailMultiAlternatives(
                subject="Réinitialisation de mot de passe - BINTACURA",
                body=html_content,
                from_email=settings.NO_REPLY_EMAIL,  # Use no-reply email
                to=[user.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send()

            logger.info(f"Password reset email sent to {user.email}")
            return True
        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {str(e)}")
            return False

    @staticmethod
    def send_welcome_email(user):  # Send welcome email
        context = {
            "user_name": user.full_name,
            "role": user.get_role_display(),
        }
        return EmailService.send_email(
            to_email=user.email,
            subject="Bienvenue sur BINTACURA",
            template_name="emails/welcome.html",
            context=context,
        )

    @staticmethod
    def send_staff_credentials(recipient_email, staff_name, pharmacy_name, email, password, role):
        """Send staff credentials via email"""
        context = {
            "staff_name": staff_name,
            "pharmacy_name": pharmacy_name,
            "email": email,
            "password": password,
            "role": role,
            "login_url": f"{settings.BASE_URL}/auth/login/",
        }
        return EmailService.send_email(
            to_email=recipient_email,
            subject=f"Vos accès - {pharmacy_name}",
            template_name="emails/staff_credentials.html",
            context=context,
        )

    @staticmethod
    def send_insurance_claim_update(claim, status):  # Send insurance claim update
        context = {
            "patient_name": claim.patient.full_name,
            "claim_number": str(claim.id),
            "status": status,
            "amount": claim.claim_amount,
        }
        return EmailService.send_email(
            to_email=claim.patient.email,
            subject=f"Mise à jour de votre demande de remboursement - BINTACURA",
            template_name="emails/insurance_claim_update.html",
            context=context,
        )


email_service = EmailService()

