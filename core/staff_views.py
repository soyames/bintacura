from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.contrib import messages
from .staff_permissions import require_hospital_staff, require_pharmacy_staff
from hospital.models import HospitalStaff, Admission, Bed
from pharmacy.models import PharmacyStaff
from appointments.models import Appointment
from core.models import Participant, Department
from django.utils import timezone
from django.db.models import Q, Count


class ReceptionistDashboardView(TemplateView):
    template_name = "hospital/staff/receptionist_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated receptionist before allowing access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='receptionist'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil réceptionniste introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):  # Loads receptionist dashboard with today's appointments and pending admissions
        context = super().get_context_data(**kwargs)
        staff = self.request.staff_record
        hospital_id = self.request.user.affiliated_provider_id

        today = timezone.now().date()

        context['today_appointments'] = Appointment.objects.filter(
            provider_id=hospital_id,
            appointment_date=today,
            status__in=['pending', 'confirmed']
        ).select_related('patient', 'doctor').order_by('appointment_time')[:10]

        context['pending_appointments'] = Appointment.objects.filter(
            provider_id=hospital_id,
            status='pending'
        ).select_related('patient', 'doctor').order_by('appointment_date', 'appointment_time')[:10]

        context['total_appointments_today'] = Appointment.objects.filter(
            provider_id=hospital_id,
            appointment_date=today
        ).count()

        context['pending_admissions'] = Admission.objects.filter(
            hospital_id=hospital_id,
            status='pending'
        ).select_related('patient', 'department').order_by('-created_at')[:5]

        context['available_beds'] = Bed.objects.filter(
            hospital_id=hospital_id,
            status='available'
        ).count()

        context['doctors'] = HospitalStaff.objects.filter(
            hospital_id=hospital_id,
            role='doctor',
            is_active=True
        ).order_by('full_name')

        context['departments'] = Department.objects.filter(
            hospital_id=hospital_id,
            is_active=True
        ).order_by('name')

        return context


class ReceptionistAppointmentsView(TemplateView):
    template_name = "hospital/staff/receptionist_appointments.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies receptionist authentication before viewing appointments
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='receptionist'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil réceptionniste introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = self.request.user.affiliated_provider_id

        context['appointments'] = Appointment.objects.filter(
            provider_id=hospital_id
        ).select_related('patient', 'doctor').order_by('-appointment_date', '-appointment_time')[:50]

        context['doctors'] = HospitalStaff.objects.filter(
            hospital_id=hospital_id,
            role='doctor',
            is_active=True
        ).order_by('full_name')

        return context


class ReceptionistPatientsView(TemplateView):
    template_name = "hospital/staff/receptionist_patients.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='receptionist'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil réceptionniste introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = self.request.user.affiliated_provider_id

        context['recent_patients'] = Participant.objects.filter(
            role='patient',
            hospital_admissions__hospital_id=hospital_id
        ).distinct().order_by('-created_at')[:20]

        return context


class NurseDashboardView(TemplateView):
    template_name = "hospital/staff/nurse_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated nurse before allowing access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='nurse'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil infirmier(ère) introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        staff = self.request.staff_record
        hospital_id = self.request.user.affiliated_provider_id

        if staff.department:
            context['my_patients'] = Admission.objects.filter(
                hospital_id=hospital_id,
                department=staff.department,
                status='admitted'
            ).select_related('patient', 'bed', 'admitting_doctor').order_by('admission_date')
        else:
            context['my_patients'] = Admission.objects.filter(
                hospital_id=hospital_id,
                status='admitted'
            ).select_related('patient', 'bed', 'admitting_doctor').order_by('admission_date')[:20]

        context['pending_tasks'] = []

        return context


class LabTechnicianDashboardView(TemplateView):
    template_name = "hospital/staff/lab_technician_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated lab technician before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='lab_technician'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil technicien de laboratoire introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_tests'] = []
        context['completed_today'] = 0
        return context


class HospitalPharmacistDashboardView(TemplateView):
    template_name = "hospital/staff/pharmacist_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated hospital pharmacist before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='pharmacist'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil pharmacien introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pending_prescriptions'] = []
        return context


class HospitalAdministratorDashboardView(TemplateView):
    template_name = "hospital/staff/administrator_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated hospital administrator before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "hospital" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = HospitalStaff.objects.get(
                participant=request.user,
                hospital_id=request.user.affiliated_provider_id,
                is_active=True,
                role='administrator'
            )
            request.staff_record = staff_record
        except HospitalStaff.DoesNotExist:
            messages.error(request, "Profil administrateur introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hospital_id = self.request.user.affiliated_provider_id

        context['total_staff'] = HospitalStaff.objects.filter(
            hospital_id=hospital_id,
            is_active=True
        ).count()

        context['total_departments'] = Department.objects.filter(
            hospital_id=hospital_id,
            is_active=True
        ).count()

        context['total_beds'] = Bed.objects.filter(
            hospital_id=hospital_id
        ).count()

        context['available_beds'] = Bed.objects.filter(
            hospital_id=hospital_id,
            status='available'
        ).count()

        return context


class PharmacyStaffPharmacistDashboardView(TemplateView):
    template_name = "pharmacy/staff/pharmacist_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated pharmacy pharmacist before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = PharmacyStaff.objects.get(
                participant=request.user,
                pharmacy_id=request.user.affiliated_provider_id,
                is_active=True,
                role='pharmacist'
            )
            request.staff_record = staff_record
        except PharmacyStaff.DoesNotExist:
            messages.error(request, "Profil pharmacien introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyOrder
        pharmacy_id = self.request.user.affiliated_provider_id

        context['pending_orders'] = PharmacyOrder.objects.filter(
            pharmacy_id=pharmacy_id,
            status__in=['pending', 'confirmed', 'processing']
        ).select_related('patient', 'prescription').order_by('-order_date')[:10]

        context['ready_orders'] = PharmacyOrder.objects.filter(
            pharmacy_id=pharmacy_id,
            status='ready'
        ).select_related('patient').order_by('-ready_date')[:10]

        return context


class PharmacyCashierDashboardView(TemplateView):
    template_name = "pharmacy/staff/cashier_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated pharmacy cashier before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = PharmacyStaff.objects.get(
                participant=request.user,
                pharmacy_id=request.user.affiliated_provider_id,
                is_active=True,
                role='cashier'
            )
            request.staff_record = staff_record
        except PharmacyStaff.DoesNotExist:
            messages.error(request, "Profil caissier introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacySale
        pharmacy_id = self.request.user.affiliated_provider_id

        today = timezone.now().date()
        context['today_sales'] = PharmacySale.objects.filter(
            pharmacy_id=pharmacy_id,
            sale_date__date=today,
            cashier=self.request.user
        ).order_by('-sale_date')[:20]

        context['today_revenue'] = sum(sale.final_amount for sale in context['today_sales'])

        return context


class PharmacyInventoryClerkDashboardView(TemplateView):
    template_name = "pharmacy/staff/inventory_clerk_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated inventory clerk before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = PharmacyStaff.objects.get(
                participant=request.user,
                pharmacy_id=request.user.affiliated_provider_id,
                is_active=True,
                role='inventory_clerk'
            )
            request.staff_record = staff_record
        except PharmacyStaff.DoesNotExist:
            messages.error(request, "Profil gestionnaire d'inventaire introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyInventory
        pharmacy_id = self.request.user.affiliated_provider_id

        context['low_stock_items'] = PharmacyInventory.objects.filter(
            pharmacy_id=pharmacy_id,
            quantity_in_stock__lte=models.F('reorder_level')
        ).select_related('medication').order_by('quantity_in_stock')[:20]

        context['expiring_soon'] = PharmacyInventory.objects.filter(
            pharmacy_id=pharmacy_id,
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30),
            expiry_date__gte=timezone.now().date()
        ).select_related('medication').order_by('expiry_date')[:20]

        return context


class PharmacyDeliveryDashboardView(TemplateView):
    template_name = "pharmacy/staff/delivery_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated delivery person before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = PharmacyStaff.objects.get(
                participant=request.user,
                pharmacy_id=request.user.affiliated_provider_id,
                is_active=True,
                role='delivery_person'
            )
            request.staff_record = staff_record
        except PharmacyStaff.DoesNotExist:
            messages.error(request, "Profil livreur introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacyOrder
        pharmacy_id = self.request.user.affiliated_provider_id

        context['pending_deliveries'] = PharmacyOrder.objects.filter(
            pharmacy_id=pharmacy_id,
            delivery_method='delivery',
            status='ready'
        ).select_related('patient').order_by('-ready_date')[:20]

        return context


class PharmacyManagerDashboardView(TemplateView):
    template_name = "pharmacy/staff/manager_dashboard.html"

    def dispatch(self, request, *args, **kwargs):  # Verifies user is authenticated pharmacy manager before access
        if not request.user.is_authenticated:
            messages.error(request, "Vous devez être connecté.")
            return redirect("/auth/login/")

        if request.user.role != "pharmacy" or not request.user.affiliated_provider_id:
            messages.error(request, "Accès refusé.")
            return redirect("/")

        try:
            staff_record = PharmacyStaff.objects.get(
                participant=request.user,
                pharmacy_id=request.user.affiliated_provider_id,
                is_active=True,
                role='manager'
            )
            request.staff_record = staff_record
        except PharmacyStaff.DoesNotExist:
            messages.error(request, "Profil gestionnaire introuvable.")
            return redirect("/")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from pharmacy.models import PharmacySale, PharmacyOrder
        pharmacy_id = self.request.user.affiliated_provider_id

        today = timezone.now().date()
        context['today_sales'] = PharmacySale.objects.filter(
            pharmacy_id=pharmacy_id,
            sale_date__date=today
        ).count()

        context['today_revenue'] = PharmacySale.objects.filter(
            pharmacy_id=pharmacy_id,
            sale_date__date=today
        ).aggregate(total=models.Sum('final_amount'))['total'] or 0

        context['pending_orders'] = PharmacyOrder.objects.filter(
            pharmacy_id=pharmacy_id,
            status__in=['pending', 'confirmed', 'processing']
        ).count()

        context['staff_count'] = PharmacyStaff.objects.filter(
            pharmacy_id=pharmacy_id,
            is_active=True
        ).count()

        return context

