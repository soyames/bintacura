from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.conf import settings
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import *
from .serializers import *
from .tokens import email_verification_token, generate_activation_code
from .email_service import send_verification_email
from .forms import LoginForm, RegistrationForm
from core.models import Participant
from communication.notification_service import NotificationService
from communication.email_service import EmailService
from django.contrib.auth.tokens import PasswordResetTokenGenerator
import re
import unicodedata


def login_view(request):  # Login view
    if request.user.is_authenticated:
        return redirect_to_dashboard(request.user)

    if request.method == "POST":
        form = LoginForm(request.POST)

        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            user = authenticate(request, username=email, password=password)

            if user is not None:
                auth_login(request, user)

                if user.is_superuser or (hasattr(user, "role") and user.role == "super_admin"):
                    return redirect("/superadmin/dashboard/")

                messages.success(request, f"Bienvenue {user.full_name}!")
                return redirect_to_dashboard(user)
            else:
                messages.error(request, "Email ou mot de passe incorrect.")
        else:
            # hCaptcha validation failed or form errors
            if 'hcaptcha' in form.errors:
                messages.error(request, "Veuillez compléter la vérification hCaptcha.")
            else:
                messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
    else:
        form = LoginForm()

    return render(request, "authentication/login.html", {'form': form})


def redirect_to_dashboard(user):  # Redirect to dashboard
    user_role = user.role.lower() if hasattr(user, "role") and user.role else "patient"

    # Handle hospital staff (role='hospital' + has staff_role + has affiliated_provider_id)
    if user_role == "hospital" and user.affiliated_provider_id and user.staff_role:
        staff_role = user.staff_role.lower()
        role_dashboard_map = {
            "receptionist": "/hospital/staff/receptionist/dashboard/",
            "nurse": "/hospital/staff/nurse/dashboard/",
            "lab_technician": "/hospital/staff/lab-technician/dashboard/",
            "pharmacist": "/hospital/staff/pharmacist/dashboard/",
            "doctor": "/doctor/dashboard/",
            "administrator": "/hospital/staff/administrator/dashboard/",
        }
        return redirect(role_dashboard_map.get(staff_role, "/hospital/dashboard/"))
    
    # Handle pharmacy staff (role='pharmacy' + has staff_role + has affiliated_provider_id)
    if user_role == "pharmacy" and user.staff_role and user.affiliated_provider_id:
        return redirect("/pharmacy/staff/counter/")
    
    # Handle insurance company staff (role='insurance_company' + has staff_role + has affiliated_provider_id)
    if user_role == "insurance_company" and user.staff_role and user.affiliated_provider_id:
        return redirect("/insurance/staff/dashboard/")

    # Default role-based redirects for owners and regular users
    role_map = {
        "patient": "/patient/dashboard/",
        "doctor": "/doctor/dashboard/",
        "hospital": "/hospital/dashboard/",  # Hospital OWNER (no staff_role)
        "pharmacy": "/pharmacy/dashboard/",  # Pharmacy OWNER (no staff_role)
        "insurance": "/insurance/dashboard/",
        "insurance_company": "/insurance/dashboard/",  # Insurance OWNER (no staff_role)
        "lab": "/hospital/dashboard/",
        "admin": "/superadmin/dashboard/",
        "super_admin": "/superadmin/dashboard/",
    }

    return redirect(role_map.get(user_role, "/patient/dashboard/"))


def validate_name_field(name, field_label):  # Validate name field
    if not name or not name.strip():
        return None, f"{field_label} est requis."

    name = name.strip().upper()

    normalized = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )

    if not re.match(r'^[A-Z\s\-]+$', normalized):
        return None, f"{field_label} ne doit contenir que des lettres, espaces et tirets (sans chiffres ni caractères spéciaux)."

    return normalized.upper(), None


def detect_language_from_request(request):
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if accept_language:
        supported_languages = dict(settings.LANGUAGES)
        languages = []
        
        for lang_entry in accept_language.split(','):
            parts = lang_entry.strip().split(';')
            lang_code = parts[0].strip().lower()[:2]
            
            try:
                quality = 1.0
                if len(parts) > 1 and parts[1].strip().startswith('q='):
                    quality = float(parts[1].strip()[2:])
                languages.append((lang_code, quality))
            except (ValueError, IndexError):
                continue
        
        languages.sort(key=lambda x: x[1], reverse=True)
        
        for lang_code, _ in languages:
            if lang_code in supported_languages:
                return lang_code
    
    return settings.LANGUAGE_CODE



def register_view(request):  # Register view
    if request.method == "POST":
        form = RegistrationForm(request.POST)

        # First validate the form (includes hCaptcha validation)
        if not form.is_valid():
            if 'hcaptcha' in form.errors:
                messages.error(request, "Veuillez compléter la vérification hCaptcha.")
            else:
                messages.error(request, "Veuillez corriger les erreurs dans le formulaire.")
            return render(request, "authentication/register.html", {'form': form})

        # Extract validated data from form
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        first_name = form.cleaned_data.get('first_name', '')
        last_name = form.cleaned_data['last_name']
        phone_number = form.cleaned_data['phone_number'].strip()
        country_code = form.cleaned_data['country_code'].strip()
        role = form.cleaned_data.get('role', 'patient')

        # For pharmacy, insurance_company, and hospital, firstname is not required
        organization_roles = ["pharmacy", "insurance_company", "hospital"]
        
        if role not in organization_roles:
            first_name_clean, first_name_error = validate_name_field(first_name, "Prénom")
            if first_name_error:
                messages.error(request, first_name_error)
                return render(request, "authentication/register.html")
        else:
            # For organizations, firstname can be empty
            if first_name.strip():
                first_name_clean, first_name_error = validate_name_field(first_name, "Prénom")
                if first_name_error:
                    messages.error(request, first_name_error)
                    return render(request, "authentication/register.html")
            else:
                first_name_clean = ""

        last_name_clean, last_name_error = validate_name_field(last_name, "Nom de famille")
        if last_name_error:
            messages.error(request, last_name_error)
            return render(request, "authentication/register.html")

        first_name_formatted = first_name_clean.upper() if first_name_clean else ""
        last_name_formatted = last_name_clean.upper()
        full_name = f"{first_name_formatted} {last_name_formatted}".strip()

        existing_participant = Participant.objects.filter(email=email).first()
        if existing_participant:
            existing_role = existing_participant.role
            role_names = {
                'patient': 'patient',
                'doctor': 'médecin',
                'hospital': 'hôpital',
                'pharmacy': 'pharmacie',
                'insurance_company': "compagnie d'assurance"
            }
            existing_role_name = role_names.get(existing_role, existing_role)
            messages.error(request, f"Cet email est déjà utilisé pour un compte {existing_role_name}. Chaque email ne peut être utilisé qu'une seule fois sur la plateforme.")
            return render(request, "authentication/register.html")

        existing_user = Participant.objects.filter(
            full_name__iexact=full_name
        ).exclude(email=email).first()

        if existing_user:
            messages.error(request, "Une personne avec ce nom et prénom est déjà enregistrée avec un email différent. La même personne ne peut pas avoir plusieurs adresses email.")
            return render(request, "authentication/register.html")

        if not country_code:
            messages.error(request, "Veuillez sélectionner votre pays.")
            return render(request, "authentication/register.html")

        if not phone_number:
            messages.error(request, "Le numéro de téléphone est requis pour les paiements mobiles.")
            return render(request, "authentication/register.html")

        country_phone_codes = {
            'BJ': '+229', 'TG': '+228', 'CI': '+225', 'SN': '+221',
            'ML': '+223', 'NE': '+227', 'BF': '+226', 'GH': '+233',
            'NG': '+234', 'CM': '+237', 'FR': '+33', 'US': '+1', 'CA': '+1'
        }

        phone_code = country_phone_codes.get(country_code)
        if not phone_code:
            messages.error(request, "Code pays invalide.")
            return render(request, "authentication/register.html")

        phone_number_clean = ''.join(filter(str.isdigit, phone_number))
        formatted_phone = f"{phone_code}{phone_number_clean}"
        
        detected_language = detect_language_from_request(request)

        try:
            user = Participant.objects.create_participant(
                email=email,
                password=password,
                full_name=full_name,
                phone_number=formatted_phone,
                country=country_code,
                role=role,
                is_active=False,
                is_email_verified=False,
                preferred_language=detected_language,
            )

            # Try to initiate phone verification, but don't fail registration if it fails
            try:
                from payments.services.phone_verification_service import PhoneVerificationService
                PhoneVerificationService.initiate_phone_verification(
                    participant=user,
                    phone_number=formatted_phone,
                    country_code=country_code,
                    is_primary=True
                )
            except Exception as phone_error:
                # Log error but continue with registration
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Phone verification error for {email}: {str(phone_error)}")

            request.session["pending_user_id"] = str(user.uid)
            request.session["pending_user_email"] = user.email
            request.session["pending_user_role"] = user.role

            return render(
                request,
                "authentication/terms_acceptance.html",
                {"user": user, "full_name": full_name, "email": email, "role": role},
            )
        except Exception as e:
            messages.error(request, f"Erreur lors de la création du compte: {str(e)}")
            form = RegistrationForm(request.POST)
            return render(request, "authentication/register.html", {'form': form})
    else:
        form = RegistrationForm()

    return render(request, "authentication/register.html", {'form': form})


def accept_terms(request):  # Accept terms
    if request.method == "POST":
        user_id = request.session.get("pending_user_id")

        if not user_id:
            messages.error(
                request, "Session expirée. Veuillez vous inscrire à nouveau."
            )
            return redirect("authentication:register")

        try:
            user = Participant.objects.get(uid=user_id)
            user.is_active = True
            user.terms_accepted = True
            user.terms_accepted_at = timezone.now()
            user.save()

            # Create role-specific data
            create_role_specific_data(user)

            # Generate and send email verification
            activation_code = generate_activation_code()
            user.activation_code = activation_code
            user.activation_code_created_at = timezone.now()
            user.save()

            # Send verification email
            send_verification_email(user, activation_code)

            request.session.pop("pending_user_id", None)
            request.session.pop("pending_user_email", None)
            request.session.pop("pending_user_role", None)

            auth_login(request, user)

            NotificationService.send_welcome_notification(user)
            NotificationService.send_terms_accepted_notification(user)

            messages.warning(
                request,
                f"Bienvenue {user.full_name}! Un email de vérification a été envoyé à {user.email}. "
                "Veuillez vérifier votre email pour accéder à toutes les fonctionnalités.",
            )

            return redirect_to_dashboard(user)

        except Participant.DoesNotExist:
            messages.error(request, "Utilisateur non trouvé.")
            return redirect("authentication:register")

    return redirect("authentication:register")


def decline_terms(request):  # Decline terms
    if request.method == "POST":
        user_id = request.session.get("pending_user_id")

        if user_id:
            try:
                user = Participant.objects.get(uid=user_id)
                user.delete()

                request.session.pop("pending_user_id", None)
                request.session.pop("pending_user_email", None)
                request.session.pop("pending_user_role", None)

                messages.info(
                    request,
                    "Votre compte a été supprimé car vous n'avez pas accepté les conditions d'utilisation.",
                )
            except Participant.DoesNotExist:
                pass

        return redirect("/")


def logout_view(request):  # Logout view
    auth_logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect("authentication:login")


def verify_email_page(request):  # Verify email page
    return render(request, "authentication/verify_email.html")


def verify_email_with_code(request):  # Verify email with code
    if request.method == "POST":
        email = request.POST.get("email")
        code = request.POST.get("code")

        try:
            user = Participant.objects.get(email=email, activation_code=code)

            code_age = timezone.now() - user.activation_code_created_at
            if code_age.total_seconds() > 86400:
                messages.error(
                    request,
                    "Le code d'activation a expiré. Veuillez demander un nouveau code.",
                )
                return render(request, "authentication/verify_email.html")

            user.is_email_verified = True
            user.activation_code = ""
            user.save()
            
            # Create role-specific data when email is verified
            create_role_specific_data(user)

            messages.success(
                request,
                "Email vérifié avec succès! Vous pouvez maintenant vous connecter.",
            )
            return redirect("authentication:login")
        except Participant.DoesNotExist:
            messages.error(request, "Email ou code d'activation invalide.")

    return render(request, "authentication/verify_email.html")


def verify_email_with_link(request, uidb64, token):  # Verify email with link
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Participant.objects.get(uid=uid)
    except (TypeError, ValueError, OverflowError, Participant.DoesNotExist):
        user = None

    if user is not None and email_verification_token.check_token(user, token):
        user.is_email_verified = True
        user.activation_code = ""
        user.save()
        
        # Create role-specific data when email is verified
        create_role_specific_data(user)
        
        messages.success(
            request, "Email vérifié avec succès! Vous pouvez maintenant vous connecter."
        )
        return redirect("authentication:login")
    else:
        messages.error(request, "Le lien de vérification est invalide ou a expiré.")
        return redirect("authentication:verify_email_page")


def resend_verification_email(request):  # Resend verification email
    if request.method == "POST":
        email = request.POST.get("email")

        try:
            user = Participant.objects.get(email=email, is_email_verified=False)

            activation_code = generate_activation_code()
            user.activation_code = activation_code
            user.activation_code_created_at = timezone.now()
            user.save()

            send_verification_email(user, activation_code)

            messages.success(request, "Email de vérification renvoyé avec succès!")
        except Participant.DoesNotExist:
            messages.error(request, "Aucun compte non vérifié trouvé avec cet email.")

    return render(request, "authentication/verify_email.html")


def create_role_specific_data(user):
    """Create role-specific data for newly registered users"""
    from doctor.models import DoctorData
    from patient.models import PatientData
    from hospital.models import HospitalData
    from core.models import Wallet
    from django.conf import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        if user.role == 'doctor':
            if not hasattr(user, 'doctor_data'):
                default_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
                consultation_fee_cents = default_fee_xof * 100
                
                DoctorData.objects.create(
                    participant=user,
                    specialization='general_practice',
                    license_number=f'DOC{str(user.uid)[:8].upper()}',
                    years_of_experience=0,
                    consultation_fee=consultation_fee_cents,
                    rating=5.0,
                    is_available_for_telemedicine=False
                )
                logger.info(f"Created DoctorData for {user.email}")
        
        elif user.role == 'hospital':
            if not hasattr(user, 'hospital_data'):
                default_fee_xof = getattr(settings, 'DEFAULT_CONSULTATION_FEE_XOF', 3500)
                consultation_fee_cents = default_fee_xof * 100
                
                HospitalData.objects.create(
                    participant=user,
                    license_number=f'HOSP{str(user.uid)[:8].upper()}',
                    consultation_fee=consultation_fee_cents,
                    bed_capacity=0,
                    rating=5.0,
                )
                logger.info(f"Created HospitalData for {user.email}")
        
        elif user.role == 'patient':
            if not hasattr(user, 'patient_data'):
                PatientData.objects.create(
                    participant=user
                )
                logger.info(f"Created PatientData for {user.email}")
        
        # Create wallet for all users except super_admin
        if user.role not in ['super_admin', 'admin']:
            if not Wallet.objects.filter(participant=user).exists():
                Wallet.objects.create(
                    participant=user,
                    balance=0,
                    currency=user.preferred_currency or 'XOF'
                )
                logger.info(f"Created Wallet for {user.email}")
    except Exception as e:
        logger.error(f"Error creating role-specific data for {user.email} (role: {user.role}): {str(e)}")
        raise
    
    except Exception as e:
        # Log the error but don't fail the registration
        print(f"Error creating role-specific data for {user.email}: {str(e)}")


def change_password_view(request):
    """View for changing password"""
    if not request.user.is_authenticated:
        return redirect('authentication:login')
    
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if not old_password or not new_password or not confirm_password:
            messages.error(request, 'Tous les champs sont requis.')
            return render(request, 'authentication/change_password.html')
        
        # Check if old password is correct
        if not request.user.check_password(old_password):
            messages.error(request, 'Mot de passe actuel incorrect.')
            return render(request, 'authentication/change_password.html')
        
        # Check if new passwords match
        if new_password != confirm_password:
            messages.error(request, 'Les nouveaux mots de passe ne correspondent pas.')
            return render(request, 'authentication/change_password.html')
        
        # Check password strength
        if len(new_password) < 8:
            messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
            return render(request, 'authentication/change_password.html')
        
        # Change password
        request.user.set_password(new_password)
        request.user.save()
        
        # Update session to prevent logout
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        
        messages.success(request, 'Mot de passe modifié avec succès!')
        return redirect_to_dashboard(request.user)
    
    return render(request, 'authentication/change_password.html')


def sessions_view(request):
    """View for managing active sessions"""
    if not request.user.is_authenticated:
        return redirect('authentication:login')

    # Get current session key
    current_session_key = request.session.session_key

    # In a full implementation, you would fetch all sessions from database
    # For now, we'll just show the current session
    sessions = [{
        'session_key': current_session_key[:10] + '...',
        'device': request.META.get('HTTP_USER_AGENT', 'Unknown')[:50],
        'ip_address': request.META.get('REMOTE_ADDR', 'Unknown'),
        'last_activity': timezone.now(),
        'is_current': True
    }]

    return render(request, 'authentication/sessions.html', {'sessions': sessions})


# Password reset token generator
password_reset_token = PasswordResetTokenGenerator()


def password_reset_request_view(request):
    """View for requesting password reset - sends email with reset link"""
    if request.user.is_authenticated:
        return redirect_to_dashboard(request.user)

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()

        if not email:
            messages.error(request, 'Veuillez entrer votre adresse email.')
            return render(request, 'authentication/password_reset_request.html')

        try:
            user = Participant.objects.get(email=email)

            # Generate password reset token and link
            token = password_reset_token.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.uid))

            # Build reset link
            reset_link = request.build_absolute_uri(
                f'/auth/reset-password/{uidb64}/{token}/'
            )

            # Send password reset email using no-reply email
            EmailService.send_password_reset(user, reset_link)

            messages.success(
                request,
                'Un email de réinitialisation a été envoyé à votre adresse. '
                'Veuillez vérifier votre boîte de réception et suivre les instructions.'
            )
            return redirect('authentication:login')

        except Participant.DoesNotExist:
            # Don't reveal if email exists or not (security)
            messages.success(
                request,
                'Si un compte existe avec cet email, un lien de réinitialisation a été envoyé.'
            )
            return redirect('authentication:login')

    return render(request, 'authentication/password_reset_request.html')


def password_reset_confirm_view(request, uidb64, token):
    """View for confirming password reset with new password"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Participant.objects.get(uid=uid)
    except (TypeError, ValueError, OverflowError, Participant.DoesNotExist):
        user = None

    # Verify token is valid
    if user is None or not password_reset_token.check_token(user, token):
        messages.error(
            request,
            'Le lien de réinitialisation est invalide ou a expiré. '
            'Veuillez demander un nouveau lien.'
        )
        return redirect('authentication:password_reset_request')

    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not new_password or not confirm_password:
            messages.error(request, 'Tous les champs sont requis.')
            return render(request, 'authentication/password_reset_confirm.html', {
                'uidb64': uidb64,
                'token': token
            })

        # Check if passwords match
        if new_password != confirm_password:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
            return render(request, 'authentication/password_reset_confirm.html', {
                'uidb64': uidb64,
                'token': token
            })

        # Check password strength
        if len(new_password) < 8:
            messages.error(request, 'Le mot de passe doit contenir au moins 8 caractères.')
            return render(request, 'authentication/password_reset_confirm.html', {
                'uidb64': uidb64,
                'token': token
            })

        # Set new password
        user.set_password(new_password)
        user.save()

        messages.success(
            request,
            'Votre mot de passe a été réinitialisé avec succès! '
            'Vous pouvez maintenant vous connecter avec votre nouveau mot de passe.'
        )
        return redirect('authentication:login')

    return render(request, 'authentication/password_reset_confirm.html', {
        'uidb64': uidb64,
        'token': token,
        'user': user
    })

