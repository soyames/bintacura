"""
Service layer for managing substitute practitioners
"""
from django.db import transaction
from django.utils import timezone
from communication.models import Notification
from .models import Appointment


class SubstituteService:
    """Handle substitute doctor assignments and notifications"""
    
    SUBSTITUTE_REASONS = {
        'vacation': 'Congé / Vacances',
        'sick_leave': 'Congé Maladie',
        'emergency': 'Urgence',
        'conference': 'Conférence / Formation',
        'other': 'Autre'
    }
    
    @staticmethod
    @transaction.atomic
    def assign_substitute(appointment, substitute_doctor, reason, assigned_by):
        """
        Assign a substitute doctor to an appointment
        
        Args:
            appointment: Appointment instance
            substitute_doctor: Doctor instance (substitute)
            reason: Reason for substitution
            assigned_by: User who assigned the substitute
        """
        if not appointment.doctor:
            raise ValueError("L'appointment doit avoir un médecin assigné")
        
        if appointment.doctor == substitute_doctor:
            raise ValueError("Le médecin remplaçant ne peut pas être le même que le médecin original")
        
        # Update appointment
        original_doctor = appointment.doctor
        appointment.substitute_doctor = substitute_doctor
        appointment.substitute_reason = reason
        appointment.substitute_notification_sent = False
        appointment.save()
        
        # Notify patient
        SubstituteService._notify_patient(appointment, original_doctor, substitute_doctor, reason)
        
        # Notify substitute doctor
        SubstituteService._notify_substitute(appointment, original_doctor)
        
        appointment.substitute_notification_sent = True
        appointment.save()
        
        return appointment
    
    @staticmethod
    def _notify_patient(appointment, original_doctor, substitute_doctor, reason):
        """Send notification to patient about substitute"""
        reason_text = SubstituteService.SUBSTITUTE_REASONS.get(reason, reason)
        
        message = f"""
        <h3>Changement de praticien</h3>
        <p>Bonjour {appointment.patient.user.get_full_name()},</p>
        <p>Nous vous informons que votre rendez-vous prévu le <strong>{appointment.appointment_date.strftime('%d/%m/%Y à %H:%M')}</strong> 
        avec <strong>Dr. {original_doctor.user.get_full_name()}</strong> sera assuré par un médecin remplaçant.</p>
        
        <div style="background: #f0f9ff; padding: 15px; border-left: 4px solid #0284c7; margin: 15px 0;">
            <p><strong>Médecin remplaçant:</strong> Dr. {substitute_doctor.user.get_full_name()}</p>
            <p><strong>Spécialité:</strong> {substitute_doctor.specialty or 'Médecine Générale'}</p>
            <p><strong>Raison:</strong> {reason_text}</p>
        </div>
        
        <p>Le rendez-vous reste confirmé à la même date et heure. Le médecin remplaçant aura accès à votre dossier médical.</p>
        <p>Si vous préférez reporter votre rendez-vous, vous pouvez nous contacter ou modifier votre réservation depuis votre espace patient.</p>
        
        <p>Cordialement,<br>L'équipe BINTACURA</p>
        """
        
        Notification.objects.create(
            user=appointment.patient.user,
            title="Médecin remplaçant assigné",
            message=message,
            notification_type='appointment',
            related_object_id=appointment.uid
        )
    
    @staticmethod
    def _notify_substitute(appointment, original_doctor):
        """Send notification to substitute doctor"""
        message = f"""
        <h3>Nouveau remplacement</h3>
        <p>Bonjour Dr. {appointment.substitute_doctor.user.get_full_name()},</p>
        <p>Vous avez été désigné comme médecin remplaçant pour le rendez-vous suivant :</p>
        
        <div style="background: #f0fdf4; padding: 15px; border-left: 4px solid #10b981; margin: 15px 0;">
            <p><strong>Patient:</strong> {appointment.patient.user.get_full_name()}</p>
            <p><strong>Date:</strong> {appointment.appointment_date.strftime('%d/%m/%Y à %H:%M')}</p>
            <p><strong>Type:</strong> {appointment.get_appointment_type_display()}</p>
            <p><strong>Médecin original:</strong> Dr. {original_doctor.user.get_full_name()}</p>
        </div>
        
        <p>Vous avez accès au dossier médical du patient depuis votre tableau de bord.</p>
        
        <p>Cordialement,<br>L'équipe BINTACURA</p>
        """
        
        Notification.objects.create(
            user=appointment.substitute_doctor.user,
            title="Remplacement assigné",
            message=message,
            notification_type='appointment',
            related_object_id=appointment.uid
        )
    
    @staticmethod
    def cancel_substitute(appointment):
        """Cancel substitute assignment and revert to original doctor"""
        if not appointment.substitute_doctor:
            raise ValueError("Aucun médecin remplaçant assigné")
        
        substitute = appointment.substitute_doctor
        appointment.substitute_doctor = None
        appointment.substitute_reason = None
        appointment.substitute_notification_sent = False
        appointment.save()
        
        # Notify patient
        message = f"""
        <h3>Annulation du remplacement</h3>
        <p>Bonjour {appointment.patient.user.get_full_name()},</p>
        <p>Nous vous informons que le remplacement pour votre rendez-vous du 
        <strong>{appointment.appointment_date.strftime('%d/%m/%Y à %H:%M')}</strong> a été annulé.</p>
        <p>Votre rendez-vous sera assuré par <strong>Dr. {appointment.doctor.user.get_full_name()}</strong> comme prévu initialement.</p>
        <p>Cordialement,<br>L'équipe BINTACURA</p>
        """
        
        Notification.objects.create(
            user=appointment.patient.user,
            title="Annulation du remplacement",
            message=message,
            notification_type='appointment',
            related_object_id=appointment.uid
        )
        
        return appointment
