from .models import Notification
import logging

logger = logging.getLogger(__name__)


class NotificationService:  # Service class for Notification operations
    @staticmethod
    def create_notification(
        recipient,
        notification_type,
        title,
        message,
        action_url="",
        metadata=None,
    ):
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            metadata=metadata or {},
        )

        NotificationService.send_realtime_notification(recipient.uid, notification)

        return notification

    @staticmethod
    def send_realtime_notification(user_id, notification):  # Send realtime notification
        # Real-time notification via Django Channels is disabled.
        logger.info(
            f"Real-time notification would be sent to user {user_id}: {notification}"
        )

    @staticmethod
    def notify_appointment_created(appointment):  # Notify appointment created
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type="appointment",
            title="Nouveau rendez-vous",
            message=f"Votre rendez-vous a été créé pour le {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')}",
            action_url=f"/patient/appointments/{appointment.id}",
            metadata={"appointment_id": str(appointment.id)},
        )

        if appointment.doctor:
            NotificationService.create_notification(
                recipient=appointment.doctor,
                notification_type="appointment",
                title="Nouveau rendez-vous",
                message=f"Nouveau rendez-vous avec {appointment.patient.full_name} le {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')}",
                action_url=f"/doctor/appointments/{appointment.id}",
                metadata={"appointment_id": str(appointment.id)},
            )

        if appointment.hospital:
            NotificationService.create_notification(
                recipient=appointment.hospital,
                notification_type="appointment",
                title="Nouveau rendez-vous",
                message=f"Nouveau rendez-vous avec {appointment.patient.full_name} le {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')}",
                action_url=f"/hospital/appointments/{appointment.id}",
                metadata={"appointment_id": str(appointment.id)},
            )

    @staticmethod
    def notify_appointment_confirmed(appointment):  # Notify appointment confirmed
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type="appointment",
            title="Rendez-vous confirmé",
            message=f"Votre rendez-vous du {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')} a été confirmé",
            action_url=f"/patient/appointments/{appointment.id}",
            metadata={"appointment_id": str(appointment.id)},
        )

    @staticmethod
    def notify_appointment_cancelled(appointment):  # Notify appointment cancelled
        NotificationService.create_notification(
            recipient=appointment.patient,
            notification_type="appointment",
            title="Rendez-vous annulé",
            message=f"Votre rendez-vous du {appointment.appointment_date.strftime('%d/%m/%Y')} à {appointment.appointment_time.strftime('%H:%M')} a été annulé",
            action_url="/patient/appointments/",
            metadata={"appointment_id": str(appointment.id)},
        )

        if appointment.doctor:
            NotificationService.create_notification(
                recipient=appointment.doctor,
                notification_type="appointment",
                title="Rendez-vous annulé",
                message=f"Rendez-vous avec {appointment.patient.full_name} du {appointment.appointment_date.strftime('%d/%m/%Y')} annulé",
                action_url="/doctor/appointments/",
                metadata={"appointment_id": str(appointment.id)},
            )

    @staticmethod
    def notify_prescription_ready(prescription):  # Notify prescription ready
        NotificationService.create_notification(
            recipient=prescription.patient,
            notification_type="prescription",
            title="Ordonnance prête",
            message=f"Votre ordonnance est prête à être retirée à {prescription.pharmacy.name}",
            action_url=f"/patient/prescriptions/{prescription.id}",
            metadata={"prescription_id": str(prescription.id)},
        )

    @staticmethod
    def send_welcome_notification(user):  # Send welcome notification
        role_messages = {
            "patient": "Bienvenue sur BINTACURA! Vous pouvez maintenant prendre des rendez-vous, consulter vos dossiers médicaux et bien plus encore.",
            "doctor": "Bienvenue sur BINTACURA! Votre espace professionnel est prêt. Vous pouvez gérer vos consultations et patients.",
            "hospital": "Bienvenue sur BINTACURA! Votre établissement est maintenant en ligne. Gérez vos services et votre équipe.",
            "pharmacy": "Bienvenue sur BINTACURA! Votre pharmacie est connectée. Gérez les ordonnances et les stocks.",
            "insurance_company": "Bienvenue sur BINTACURA! Gérez les demandes de remboursement et les polices d'assurance.",
        }

        message = role_messages.get(
            user.role, "Bienvenue sur BINTACURA! Votre compte a été activé avec succès."
        )
        dashboard_url = f"/{user.role}/dashboard/"

        return NotificationService.create_notification(
            recipient=user,
            notification_type="system",
            title=f"Bienvenue {user.full_name}!",
            message=message,
            action_url=dashboard_url,
            metadata={"welcome": True, "first_login": True},
        )

    @staticmethod
    def send_terms_accepted_notification(user):  # Send terms accepted notification
        return NotificationService.create_notification(
            recipient=user,
            notification_type="system",
            title="Compte activé",
            message="Vous avez accepté les conditions d'utilisation de BINTACURA. Votre compte est maintenant actif! Explorez toutes nos fonctionnalités.",
            action_url=f"/{user.role}/dashboard/",
            metadata={"terms_accepted": True},
        )

    @staticmethod
    def send_account_deletion_confirmation(user):
        """
        Send account deletion confirmation email
        ISSUE-PAT-059: Confirmation email after account deletion
        """
        from django.core.mail import send_mail
        from django.conf import settings

        subject = "Confirmation de suppression de compte BINTACURA"
        message = f"""
Bonjour {user.full_name},

Nous confirmons que votre compte BINTACURA a été définitivement supprimé conformément à votre demande.

Détails de la suppression:
- Email: {user.email}
- Date: {Notification.objects.model._meta.get_field('created_at').auto_now_add}
- Type: Suppression permanente (GDPR - Droit à l'oubli)

Toutes vos données personnelles, y compris:
- Informations de profil
- Historique des rendez-vous
- Ordonnances
- Données de paiement
- Profils de dépendants

ont été définitivement supprimées de nos systèmes.

Si vous n'avez pas effectué cette action, veuillez contacter immédiatement notre service support à {settings.CONTACT_EMAIL}.

Merci d'avoir utilisé BINTACURA.

Cordialement,
L'équipe BINTACURA
        """

        try:
            send_mail(
                subject,
                message,
                settings.NO_REPLY_EMAIL,
                [user.email],
                fail_silently=False,
            )
            logger.info(f"Account deletion confirmation email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send deletion confirmation email to {user.email}: {str(e)}")
            raise
    
    @staticmethod
    def send_sms(phone_number, message):
        """Send SMS notification"""
        try:
            from communication.sms_service import sms_service
            return sms_service.send_sms(phone_number, message)
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False


notification_service = NotificationService()

