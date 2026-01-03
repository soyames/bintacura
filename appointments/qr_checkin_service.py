"""
QR Code Check-in Service for Appointments
"""
from django.utils import timezone
from django.conf import settings
from communication.models import Notification
import qrcode
from io import BytesIO
import base64
import json


class QRCodeCheckinService:
    """Handle QR code generation and check-in for appointments"""
    
    @staticmethod
    def generate_checkin_qr(appointment):
        """
        Generate QR code for appointment check-in
        
        Args:
            appointment: Appointment instance
            
        Returns:
            dict: QR code data including base64 image and check-in URL
        """
        try:
            # Create check-in payload
            checkin_data = {
                'appointment_uid': str(appointment.uid),
                'patient_name': appointment.patient.get_full_name(),
                'doctor_name': appointment.doctor.get_full_name() if appointment.doctor else 'N/A',
                'appointment_date': str(appointment.appointment_date),
                'appointment_time': str(appointment.appointment_time),
                'type': 'appointment_checkin'
            }
            
            # Create check-in URL
            base_url = getattr(settings, 'SITE_URL', 'https://bintacura.com')
            checkin_url = f"{base_url}/appointments/checkin/{appointment.uid}/"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(checkin_url)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            qr_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            return {
                'qr_code_base64': qr_base64,
                'qr_code_url': f"data:image/png;base64,{qr_base64}",
                'checkin_url': checkin_url,
                'checkin_data': checkin_data
            }
            
        except Exception as e:
            print(f"Error generating QR code: {str(e)}")
            return None
    
    @staticmethod
    def process_checkin(appointment_uid, checked_by=None):
        """
        Process check-in for an appointment using QR code
        
        Args:
            appointment_uid: UID of the appointment
            checked_by: User performing the check-in (staff member)
            
        Returns:
            dict: Check-in result with success status and message
        """
        from appointments.models import Appointment
        
        try:
            appointment = Appointment.objects.get(uid=appointment_uid)
        except Appointment.DoesNotExist:
            return {
                'success': False,
                'error': 'Rendez-vous non trouvé'
            }
        
        # Check if appointment is today
        if appointment.appointment_date != timezone.now().date():
            return {
                'success': False,
                'error': 'Ce rendez-vous n\'est pas prévu pour aujourd\'hui'
            }
        
        # Check if already checked in
        if appointment.checked_in_at:
            return {
                'success': False,
                'error': 'Patient déjà enregistré',
                'checked_in_at': appointment.checked_in_at
            }
        
        # Check if appointment is cancelled
        if appointment.status == 'cancelled':
            return {
                'success': False,
                'error': 'Ce rendez-vous a été annulé'
            }
        
        # Process check-in
        appointment.checked_in_at = timezone.now()
        if appointment.status == 'confirmed':
            appointment.status = 'in_progress'
        appointment.save()
        
        # Notify patient
        QRCodeCheckinService._notify_patient_checkin(appointment)
        
        # Notify doctor
        QRCodeCheckinService._notify_doctor_patient_arrived(appointment)
        
        return {
            'success': True,
            'message': 'Enregistrement réussi',
            'appointment': {
                'uid': str(appointment.uid),
                'patient_name': appointment.patient.get_full_name(),
                'doctor_name': appointment.doctor.get_full_name() if appointment.doctor else 'N/A',
                'appointment_time': str(appointment.appointment_time),
                'checked_in_at': appointment.checked_in_at.strftime('%H:%M')
            }
        }
    
    @staticmethod
    def _notify_patient_checkin(appointment):
        """Send check-in confirmation to patient"""
        message = f"""
        <h3>Enregistrement confirmé</h3>
        <p>Bonjour {appointment.patient.get_full_name()},</p>
        <p>Votre enregistrement a été effectué avec succès à <strong>{appointment.checked_in_at.strftime('%H:%M')}</strong>.</p>
        <p>Votre rendez-vous avec <strong>Dr. {appointment.doctor.get_full_name() if appointment.doctor else 'N/A'}</strong> 
        est prévu à <strong>{appointment.appointment_time.strftime('%H:%M')}</strong>.</p>
        <p>Veuillez patienter dans la salle d'attente. Vous serez appelé(e) bientôt.</p>
        <p>Merci,<br>L'équipe BINTACURA</p>
        """
        
        Notification.objects.create(
            user=appointment.patient,
            title="Enregistrement confirmé",
            message=message,
            notification_type='appointment',
            related_object_id=appointment.uid
        )
    
    @staticmethod
    def _notify_doctor_patient_arrived(appointment):
        """Notify doctor that patient has arrived"""
        if not appointment.doctor:
            return
            
        message = f"""
        <h3>Patient arrivé</h3>
        <p>Bonjour Dr. {appointment.doctor.get_full_name()},</p>
        <p><strong>{appointment.patient.get_full_name()}</strong> est arrivé(e) et a été enregistré(e) 
        à <strong>{appointment.checked_in_at.strftime('%H:%M')}</strong>.</p>
        <p>Rendez-vous prévu à <strong>{appointment.appointment_time.strftime('%H:%M')}</strong>.</p>
        <p>Type: <strong>{appointment.get_type_display()}</strong></p>
        <p>L'équipe BINTACURA</p>
        """
        
        Notification.objects.create(
            user=appointment.doctor,
            title="Patient arrivé",
            message=message,
            notification_type='appointment',
            related_object_id=appointment.uid
        )
    
    @staticmethod
    def get_checkin_stats(doctor=None, date=None):
        """
        Get check-in statistics for a doctor on a specific date
        
        Args:
            doctor: Participant instance (doctor)
            date: Date to check (defaults to today)
            
        Returns:
            dict: Statistics including total, checked-in, waiting, etc.
        """
        from appointments.models import Appointment
        from django.db.models import Count, Q
        
        if date is None:
            date = timezone.now().date()
        
        queryset = Appointment.objects.filter(appointment_date=date)
        
        if doctor:
            queryset = queryset.filter(doctor=doctor)
        
        stats = {
            'total_appointments': queryset.count(),
            'checked_in': queryset.filter(checked_in_at__isnull=False).count(),
            'not_checked_in': queryset.filter(
                checked_in_at__isnull=True,
                status__in=['confirmed', 'pending']
            ).count(),
            'in_progress': queryset.filter(status='in_progress').count(),
            'completed': queryset.filter(status='completed').count(),
            'no_show': queryset.filter(
                checked_in_at__isnull=True,
                appointment_time__lt=timezone.now().time(),
                status='confirmed'
            ).count()
        }
        
        return stats
