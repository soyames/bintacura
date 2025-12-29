from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from hospital.models import HospitalStaff
from pharmacy.models import PharmacyStaff


def get_staff_record(user):
    if not user.is_authenticated:
        return None

    if user.role == "hospital" and user.affiliated_provider_id:
        try:
            return HospitalStaff.objects.get(staff_participant=user, hospital_id=user.affiliated_provider_id, is_active=True)
        except HospitalStaff.DoesNotExist:
            return None

    elif user.role == "pharmacy" and user.affiliated_provider_id:
        try:
            return PharmacyStaff.objects.get(staff_participant=user, pharmacy_id=user.affiliated_provider_id, is_active=True)
        except PharmacyStaff.DoesNotExist:
            return None

    return None


def require_staff_role(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Vous devez être connecté.")
                return redirect("/auth/login/")

            staff_record = get_staff_record(request.user)

            if not staff_record:
                messages.error(request, "Accès refusé. Vous n'êtes pas un membre du personnel autorisé.")
                return redirect("/")

            if staff_record.role not in allowed_roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires pour accéder à cette page.")
                return redirect("/")

            request.staff_record = staff_record
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_hospital_staff(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Vous devez être connecté.")
                return redirect("/auth/login/")

            if request.user.role != "hospital" or not request.user.affiliated_provider_id:
                messages.error(request, "Accès refusé.")
                return redirect("/")

            try:
                staff_record = HospitalStaff.objects.get(
                    staff_participant=request.user,
                    hospital_id=request.user.affiliated_provider_id,
                    is_active=True
                )
            except HospitalStaff.DoesNotExist:
                messages.error(request, "Profil du personnel introuvable.")
                return redirect("/")

            if allowed_roles and staff_record.role not in allowed_roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                return redirect("/")

            request.staff_record = staff_record
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def require_pharmacy_staff(allowed_roles=None):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, "Vous devez être connecté.")
                return redirect("/auth/login/")

            if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
                messages.error(request, "Accès refusé.")
                return redirect("/")

            try:
                staff_record = PharmacyStaff.objects.get(
                    staff_participant=request.user,
                    pharmacy_id=request.user.affiliated_provider_id,
                    is_active=True
                )
            except PharmacyStaff.DoesNotExist:
                messages.error(request, "Profil du personnel introuvable.")
                return redirect("/")

            if allowed_roles and staff_record.role not in allowed_roles:
                messages.error(request, "Vous n'avez pas les permissions nécessaires.")
                return redirect("/")

            request.staff_record = staff_record
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator


def check_staff_permission(staff_record, permission):
    permission_map = {
        'can_admit_patients': 'can_admit_patients',
        'can_discharge_patients': 'can_discharge_patients',
        'can_prescribe': 'can_prescribe',
        'can_perform_surgery': 'can_perform_surgery',
        'can_manage_equipment': 'can_manage_equipment',
        'can_manage_staff': 'can_manage_staff',
        'can_view_all_records': 'can_view_all_records',
        'can_manage_inventory': 'can_manage_inventory',
        'can_process_orders': 'can_process_orders',
        'can_handle_sales': 'can_handle_sales',
    }

    permission_attr = permission_map.get(permission)
    if not permission_attr:
        return False

    return getattr(staff_record, permission_attr, False)


def require_permission(permission):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'staff_record') or not request.staff_record:
                messages.error(request, "Accès refusé.")
                return redirect("/")

            if not check_staff_permission(request.staff_record, permission):
                messages.error(request, "Vous n'avez pas la permission requise.")
                return redirect("/")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
