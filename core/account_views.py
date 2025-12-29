from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse
import json


@login_required
def sessions_view(request):
    """View for managing active sessions"""
    # Get current session key
    current_session_key = request.session.session_key
    
    # In a full implementation, you would fetch all sessions from database
    # For now, we'll just show the current session
    sessions = [{
        'session_key': current_session_key[:10] + '...' if current_session_key else 'N/A',
        'device': request.META.get('HTTP_USER_AGENT', 'Unknown')[:80],
        'ip_address': request.META.get('REMOTE_ADDR', 'Unknown'),
        'last_activity': timezone.now(),
        'is_current': True
    }]
    
    context = {
        'sessions': sessions,
        'total_sessions': len(sessions)
    }
    
    return render(request, 'account/sessions.html', context)


@login_required
def export_data_view(request):
    """
    Export user data as JSON - GDPR compliant
    ISSUE-PAT-057: Enhanced to include ALL user data
    """
    from core.preferences_utils import get_or_create_preferences
    from patient.models import DependentProfile
    from appointments.models import Appointment
    from payments.models import PaymentReceipt, Transaction
    from prescriptions.models import Prescription

    user = request.user
    preferences = get_or_create_preferences(user)

    # Prepare comprehensive data export
    data = {
        'profile': {
            'uid': str(user.uid),
            'email': user.email,
            'full_name': user.full_name,
            'phone_number': user.phone_number,
            'role': user.role,
            'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None,
            'gender': user.gender,
            'address': user.address,
            'city': user.city,
            'country': user.country,
            'date_joined': str(user.created_at),
            'profile_picture_url': user.profile_picture_url,
        },
        'preferences': {
            'theme': preferences.theme,
            'language': preferences.language,
            'font_size': preferences.font_size,
            'email_notifications': preferences.enable_email_notifications,
            'sms_notifications': preferences.enable_sms_notifications,
            'push_notifications': preferences.enable_push_notifications,
        },
        'export_date': str(timezone.now()),
    }

    # Add role-specific data
    if user.role == 'patient':
        # Patient-specific data
        if hasattr(user, 'patient_data'):
            patient_data = user.patient_data
            data['patient_data'] = {
                'blood_type': patient_data.blood_type,
                'allergies': patient_data.allergies,
                'chronic_conditions': patient_data.chronic_conditions,
                'current_medications': patient_data.current_medications,
                'medical_history': patient_data.medical_history,
                'height': patient_data.height,
                'weight': patient_data.weight,
            }

        # Dependents - ISSUE-PAT-058
        dependents = DependentProfile.objects.filter(patient=user)
        data['dependents'] = [
            {
                'full_name': dep.full_name,
                'date_of_birth': str(dep.date_of_birth),
                'gender': dep.gender,
                'relationship': dep.relationship,
                'blood_type': dep.blood_type,
                'allergies': dep.allergies,
            }
            for dep in dependents
        ]

        # Appointments
        appointments = Appointment.objects.filter(patient=user)
        data['appointments'] = [
            {
                'date': str(apt.appointment_date),
                'type': apt.appointment_type,
                'status': apt.status,
                'doctor': apt.doctor.full_name if apt.doctor else None,
            }
            for apt in appointments
        ]

        # Prescriptions
        prescriptions = Prescription.objects.filter(patient=user)
        data['prescriptions'] = [
            {
                'date': str(pres.created_at),
                'doctor': pres.doctor.full_name if pres.doctor else None,
                'medications': [item.medication.name for item in pres.prescription_items.all()],
            }
            for pres in prescriptions
        ]

    # Payment data - ISSUE-PAT-057: Include payment receipts
    try:
        receipts = PaymentReceipt.objects.filter(participant=user)
        data['payment_receipts'] = [
            {
                'receipt_number': receipt.receipt_number,
                'date': str(receipt.created_at),
                'amount': float(receipt.amount),
                'currency': receipt.currency,
                'payment_method': receipt.payment_method,
                'description': receipt.description,
            }
            for receipt in receipts
        ]
    except:
        data['payment_receipts'] = []

    # Transaction history
    try:
        if hasattr(user, 'core_wallet'):
            transactions = Transaction.objects.filter(wallet=user.core_wallet)
            data['transactions'] = [
                {
                    'date': str(trans.created_at),
                    'type': trans.transaction_type,
                    'amount': float(trans.amount),
                    'currency': trans.currency,
                    'status': trans.status,
                    'description': trans.description,
                }
                for trans in transactions[:100]  # Limit to last 100
            ]
    except:
        data['transactions'] = []

    # Create JSON response
    response = HttpResponse(
        json.dumps(data, indent=2, ensure_ascii=False),
        content_type='application/json; charset=utf-8'
    )
    response['Content-Disposition'] = f'attachment; filename="BINTACURA_data_{user.uid}.json"'

    return response


@login_required
def emergency_contacts_view(request):
    """View for managing emergency contacts"""
    from .preferences import EmergencyContact
    
    contacts = EmergencyContact.objects.filter(participant=request.user)
    
    if request.method == 'POST':
        # Handle adding new contact
        full_name = request.POST.get('full_name')
        relationship = request.POST.get('relationship')
        phone_number = request.POST.get('phone_number')
        email = request.POST.get('email', '')
        is_primary = request.POST.get('is_primary') == 'on'
        
        if full_name and relationship and phone_number:
            # If this is primary, unset other primary contacts
            if is_primary:
                EmergencyContact.objects.filter(
                    participant=request.user,
                    is_primary=True
                ).update(is_primary=False)
            
            EmergencyContact.objects.create(
                participant=request.user,
                full_name=full_name,
                relationship=relationship,
                phone_number=phone_number,
                email=email,
                is_primary=is_primary
            )
            
            messages.success(request, 'Contact d\'urgence ajouté avec succès!')
            return redirect('account:emergency_contacts')
        else:
            messages.error(request, 'Veuillez remplir tous les champs requis.')
    
    context = {
        'contacts': contacts,
    }
    
    return render(request, 'account/emergency_contacts.html', context)


@login_required
def deactivate_account_view(request):
    """Deactivate user account (soft delete)"""
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation')

        if confirmation == 'DÉSACTIVER':
            user = request.user
            user.is_active = False
            user.save()

            from django.contrib.auth import logout
            logout(request)

            messages.success(request, 'Votre compte a été désactivé. Contactez le support pour le réactiver.')
            return redirect('/')
        else:
            messages.error(request, 'Confirmation incorrecte. Tapez "DÉSACTIVER" pour confirmer.')

    return render(request, 'account/deactivate.html')


@login_required
def delete_account_permanently_view(request):
    """
    Permanently delete user account - GDPR Right to be Forgotten
    ISSUE-PAT-056: Hard delete implementation for GDPR compliance
    ISSUE-PAT-058: Cascades to dependent profiles
    ISSUE-PAT-059: Sends confirmation email
    """
    if request.method == 'POST':
        confirmation = request.POST.get('confirmation')
        password = request.POST.get('password')

        # Verify password for security
        if not request.user.check_password(password):
            messages.error(request, 'Mot de passe incorrect.')
            return render(request, 'account/delete_permanently.html')

        if confirmation == 'SUPPRIMER DÉFINITIVEMENT':
            from django.contrib.auth import logout
            from communication.notification_service import NotificationService
            from patient.models import DependentProfile

            user = request.user
            user_email = user.email
            user_name = user.full_name

            try:
                # ISSUE-PAT-059: Send confirmation email BEFORE deletion
                try:
                    NotificationService.send_account_deletion_confirmation(user)
                except Exception as e:
                    # Log but don't fail if email fails
                    print(f"Failed to send deletion email: {str(e)}")

                # ISSUE-PAT-058: Delete dependent profiles (cascades automatically via on_delete=CASCADE)
                # But we'll explicitly handle for logging
                if user.role == 'patient':
                    dependent_count = DependentProfile.objects.filter(patient=user).count()
                    DependentProfile.objects.filter(patient=user).delete()
                    print(f"Deleted {dependent_count} dependent profiles for user {user.uid}")

                # Log the deletion for audit purposes before deleting
                from core.models import AuditLog
                try:
                    AuditLog.objects.create(
                        action="account_permanent_deletion",
                        participant=None,  # Will be None after deletion
                        description=f"User {user_name} ({user_email}) permanently deleted their account (GDPR)",
                        ip_address=request.META.get('REMOTE_ADDR', 'Unknown'),
                        user_agent=request.META.get('HTTP_USER_AGENT', 'Unknown')[:200]
                    )
                except:
                    pass

                # Logout first
                logout(request)

                # HARD DELETE - This will cascade to all related models with on_delete=CASCADE
                user.delete()

                messages.success(
                    request,
                    'Votre compte a été définitivement supprimé. Un email de confirmation vous a été envoyé.'
                )
                return redirect('/')

            except Exception as e:
                messages.error(request, f'Erreur lors de la suppression: {str(e)}')
                return render(request, 'account/delete_permanently.html')
        else:
            messages.error(request, 'Confirmation incorrecte. Tapez "SUPPRIMER DÉFINITIVEMENT" pour confirmer.')

    return render(request, 'account/delete_permanently.html')

