from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from core.models import AdminPermissions, StaffPermissions


def require_permissions(*required_permissions):  # Decorator to enforce permission requirements for views
    def decorator(view_func):  # Inner decorator that wraps the view function
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):  # Check user permissions before executing view
            user = request.user

            if not user.is_authenticated:
                return JsonResponse({"error": "Non authentifié"}, status=401)

            if user.role == "super_admin":
                return view_func(request, *args, **kwargs)

            if user.role == "admin":
                try:
                    permissions = user.admin_permissions
                    for perm in required_permissions:
                        if not getattr(permissions, perm, False):
                            return JsonResponse(
                                {"error": "Permission refusée"}, status=403
                            )
                    return view_func(request, *args, **kwargs)
                except AdminPermissions.DoesNotExist:
                    return JsonResponse(
                        {"error": "Permissions non configurées"}, status=403
                    )

            if user.staff_role in ["doctor", "nurse", "receptionist", "pharmacist"]:
                try:
                    permissions = user.staff_permissions
                    for perm in required_permissions:
                        if not getattr(permissions, perm, False):
                            return JsonResponse(
                                {"error": "Permission refusée"}, status=403
                            )
                    return view_func(request, *args, **kwargs)
                except StaffPermissions.DoesNotExist:
                    return JsonResponse(
                        {"error": "Permissions non configurées"}, status=403
                    )

            return JsonResponse({"error": "Rôle non autorisé"}, status=403)

        return wrapper

    return decorator


def require_role(*allowed_roles):  # Decorator to restrict view access to specific user roles
    def decorator(view_func):  # Inner decorator that wraps the view function
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):  # Check user role before executing view
            user = request.user

            if not user.is_authenticated:
                return JsonResponse({"error": "Non authentifié"}, status=401)

            if user.role not in allowed_roles:
                return JsonResponse(
                    {"error": "Rôle non autorisé pour cette action"}, status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def role_required(required_role):
    """
    Decorator to restrict view access to a specific participant role.
    Redirects non-authenticated users to login with friendly French messages.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Veuillez vous connecter pour accéder à cette page")
                return redirect('authentication:login')
            
            participant = request.user.participant if hasattr(request.user, 'participant') else None
            
            if not participant or participant.role != required_role:
                messages.error(request, f"Accès refusé. Cette page est réservée aux {required_role}s")
                return redirect('core:home')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_own_resource(resource_param="pk"):  # Decorator to ensure users can only access their own resources
    def decorator(view_func):  # Inner decorator that wraps the view function
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):  # Verify resource ownership before executing view
            user = request.user

            if not user.is_authenticated:
                return JsonResponse({"error": "Non authentifié"}, status=401)

            if user.role in ["super_admin", "admin"]:
                return view_func(request, *args, **kwargs)

            resource_id = kwargs.get(resource_param)
            if str(user.uid) != str(resource_id):
                return JsonResponse(
                    {"error": "Accès refusé à cette ressource"}, status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def email_verification_required(view_func):
    """
    Decorator to require email verification for specific views.

    This decorator restricts access to views that require verified email addresses.
    Unverified users will be redirected to the verification page with a warning message.

    Usage:
        @email_verification_required
        def book_appointment(request):
            # Only verified participants can book appointments
            ...

    Features requiring verification:
    - Booking appointments
    - Making payments
    - Accessing medical records
    - Submitting insurance claims
    - Communicating with healthcare providers
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if participant is authenticated
        if not request.user.is_authenticated:
            return redirect('authentication:login')

        # Check if participant's email is verified
        if not request.user.is_email_verified:
            messages.warning(
                request,
                "⚠️ Vérification requise : Vous devez vérifier votre adresse email "
                "pour accéder à cette fonctionnalité. Un email de vérification "
                "vous a été envoyé lors de votre inscription."
            )
            return redirect('authentication:verify_email_page')

        # Participant is verified, proceed with the view
        return view_func(request, *args, **kwargs)

    return wrapper


def check_participant_verified(participant):
    """
    Utility function to check if a participant's email is verified.

    Args:
        participant: Participant instance

    Returns:
        bool: True if email is verified, False otherwise
    """
    if not participant:
        return False

    return participant.is_email_verified


def get_verification_status_context(participant):
    """
    Get verification status information for templates.

    Args:
        participant: Participant instance

    Returns:
        dict: Context dictionary with verification status for use in templates
    """
    return {
        'is_email_verified': participant.is_email_verified if participant else False,
        'needs_verification': not participant.is_email_verified if participant else True,
        'verification_email': participant.email if participant else '',
        'verification_message': (
            'Votre email est vérifié ✓' if participant and participant.is_email_verified
            else 'Vérifiez votre email pour accéder à toutes les fonctionnalités'
        )
    }
