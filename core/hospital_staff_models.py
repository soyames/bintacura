"""
Hospital Staff Affiliation Models
==================================

Manages doctor-hospital staff relationships with ERP business rules.

Business Rules:
1. Doctors can create their own account OR be added as staff by a hospital
2. If added as staff by hospital → doctor CANNOT affiliate with other hospitals
3. Hospital staff doctors → Hospital handles ALL payments and claims (doctor cannot manage themselves)
4. Independent doctors → Can affiliate to hospital later
5. Affiliated doctors → Hospital handles payments (same as staff doctors)

Payment Routing:
- Independent doctor (no affiliation): Money goes to doctor's linked payment account
- Hospital staff doctor: Money goes to hospital's linked payment account
- Affiliated doctor: Money goes to hospital's linked payment account
"""

from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
import uuid

from core.models import Participant


class HospitalStaffAffiliation(models.Model):
    """
    Tracks doctor-hospital staff relationships.

    When a doctor is hospital staff:
    - ALL payments for their consultations go to the hospital
    - Hospital manages claims, invoices, and financial records
    - Doctor cannot link their own payment accounts
    - Doctor cannot affiliate with other hospitals
    """

    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('terminated', 'Terminé'),
    ]

    AFFILIATION_TYPE_CHOICES = [
        ('staff', 'Personnel'),  # Hospital added doctor as staff
        ('affiliated', 'Affilié'),  # Doctor affiliated themselves to hospital
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Doctor (must have role='doctor')
    doctor = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='staff_affiliation_records',  # Changed to avoid conflict with doctor.DoctorAffiliation
        limit_choices_to={'role': 'doctor'},
        help_text='Médecin affilié'
    )

    # Hospital (must have role='hospital')
    hospital = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='employed_staff_doctors',  # More specific name
        limit_choices_to={'role': 'hospital'},
        help_text='Hôpital employeur'
    )

    # Affiliation type
    affiliation_type = models.CharField(
        max_length=20,
        choices=AFFILIATION_TYPE_CHOICES,
        help_text='Type d\'affiliation'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text='Statut de l\'affiliation'
    )

    # Employment details (for staff)
    employment_start_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date de début d\'emploi'
    )
    employment_end_date = models.DateField(
        null=True,
        blank=True,
        help_text='Date de fin d\'emploi'
    )
    job_title = models.CharField(
        max_length=200,
        blank=True,
        help_text='Titre du poste'
    )
    department = models.CharField(
        max_length=200,
        blank=True,
        help_text='Département'
    )

    # Permissions
    can_manage_own_payments = models.BooleanField(
        default=False,
        help_text='Le médecin peut-il gérer ses propres paiements ? (Non si personnel)'
    )
    can_manage_own_claims = models.BooleanField(
        default=False,
        help_text='Le médecin peut-il gérer ses propres réclamations ? (Non si personnel)'
    )

    # Contract details
    contract_document = models.FileField(
        upload_to='hospital_contracts/%Y/%m/',
        blank=True,
        null=True,
        help_text='Document de contrat'
    )
    notes = models.TextField(
        blank=True,
        help_text='Notes'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_staff_affiliations',
        help_text='Créé par (admin hôpital ou médecin)'
    )

    class Meta:
        db_table = 'hospital_staff_affiliations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['affiliation_type', 'status']),
        ]
        constraints = [
            # A doctor can only have ONE active staff affiliation (enforces one-hospital rule)
            models.UniqueConstraint(
                fields=['doctor'],
                condition=models.Q(affiliation_type='staff', status='active'),
                name='unique_active_staff_per_doctor'
            )
        ]

    def __str__(self):
        return f"Dr. {self.doctor.full_name} - {self.hospital.full_name} ({self.get_affiliation_type_display()})"

    def clean(self):
        """Validate affiliation rules"""
        # Rule 1: Doctor must have role='doctor'
        if self.doctor.role != 'doctor':
            raise ValidationError({'doctor': 'Le participant doit avoir le rôle "doctor"'})

        # Rule 2: Hospital must have role='hospital'
        if self.hospital.role != 'hospital':
            raise ValidationError({'hospital': 'Le participant doit avoir le rôle "hospital"'})

        # Rule 3: If affiliation_type is 'staff', doctor cannot have other active staff affiliations
        if self.affiliation_type == 'staff' and self.status == 'active':
            existing_staff = HospitalStaffAffiliation.objects.filter(
                doctor=self.doctor,
                affiliation_type='staff',
                status='active'
            ).exclude(id=self.id)

            if existing_staff.exists():
                raise ValidationError({
                    'doctor': f'Le médecin est déjà personnel à {existing_staff.first().hospital.full_name}. '
                              f'Un médecin ne peut être personnel qu\'à un seul hôpital.'
                })

        # Rule 4: If affiliation_type is 'staff', set permissions to False (hospital manages everything)
        if self.affiliation_type == 'staff':
            self.can_manage_own_payments = False
            self.can_manage_own_claims = False

        # Rule 5: If affiliation_type is 'affiliated', hospital also manages payments
        # (per business rule: payments for affiliated doctors go through hospital system)
        elif self.affiliation_type == 'affiliated':
            self.can_manage_own_payments = False  # Hospital manages payments
            self.can_manage_own_claims = True      # Doctor can still view/manage claims

    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation
        super().save(*args, **kwargs)

    def get_payment_recipient(self):
        """
        Determine who receives payments for this doctor's consultations.

        Returns:
            Participant: Hospital for both staff and affiliated doctors (if active)

        Business Rule:
            When patients pay for services rendered by doctors who are staff OR affiliated,
            the payment goes through the hospital payment system (not individual doctor).
        """
        if self.status == 'active':
            return self.hospital  # Hospital receives payments for ALL active affiliations
        else:
            return self.doctor  # Inactive affiliation, pay doctor directly

    def is_active_staff(self):
        """Check if this is an active staff relationship"""
        return self.affiliation_type == 'staff' and self.status == 'active'

    def can_affiliate_to_other_hospital(self):
        """Check if doctor can affiliate to another hospital"""
        # If already staff, cannot affiliate to other hospitals
        if self.is_active_staff():
            return False
        return True


class StaffPermission(models.Model):
    """
    Granular permissions for hospital staff members.

    For future use: More detailed permission management.
    """

    PERMISSION_CHOICES = [
        ('view_patients', 'Voir les Patients'),
        ('manage_appointments', 'Gérer les Rendez-vous'),
        ('manage_prescriptions', 'Gérer les Prescriptions'),
        ('view_financial', 'Voir les Finances'),
        ('manage_financial', 'Gérer les Finances'),
        ('manage_claims', 'Gérer les Réclamations'),
        ('view_reports', 'Voir les Rapports'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    affiliation = models.ForeignKey(
        HospitalStaffAffiliation,
        on_delete=models.CASCADE,
        related_name='permissions'
    )
    permission = models.CharField(
        max_length=50,
        choices=PERMISSION_CHOICES
    )
    granted = models.BooleanField(
        default=True,
        help_text='Permission accordée'
    )
    granted_at = models.DateTimeField(default=timezone.now)
    granted_by = models.ForeignKey(
        Participant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_permissions'
    )

    class Meta:
        db_table = 'hospital_staff_permissions'  # Changed to avoid conflict with core.StaffPermissions
        unique_together = ['affiliation', 'permission']

    def __str__(self):
        return f"{self.affiliation.doctor.full_name} - {self.get_permission_display()}"


# Helper functions

def get_doctor_payment_recipient(doctor, hospital=None):
    """
    Get the participant who should receive payments for a doctor's consultations.

    Args:
        doctor: Participant with role='doctor'
        hospital: Optional - Participant with role='hospital' (context where service was rendered)

    Returns:
        Participant: Hospital if doctor has active affiliation to that specific hospital,
                    otherwise the doctor themselves

    Business Rule:
        Payments for services rendered by doctors who are staff OR affiliated to a hospital
        go through that hospital's payment system (not individual doctor).

    Note:
        If hospital parameter is provided, checks for affiliation to THAT specific hospital.
        If hospital is not provided, returns first active affiliation (for backward compatibility).
    """
    # If hospital context is provided, check for affiliation to THAT specific hospital
    if hospital:
        active_affiliation = HospitalStaffAffiliation.objects.filter(
            doctor=doctor,
            hospital=hospital,
            status='active'
        ).first()

        if active_affiliation:
            return hospital  # Hospital receives payment for service rendered there
        else:
            return doctor  # Doctor is not affiliated with this hospital, pays doctor directly

    # Backward compatibility: If no hospital context, check for ANY active affiliation
    else:
        active_affiliation = HospitalStaffAffiliation.objects.filter(
            doctor=doctor,
            status='active'
        ).first()

        if active_affiliation:
            return active_affiliation.hospital  # Hospital receives payment
        else:
            return doctor  # Independent doctor receives payment directly


def can_doctor_link_payment_account(doctor):
    """
    Check if a doctor can link their own payment account.

    Args:
        doctor: Participant with role='doctor'

    Returns:
        bool: False if doctor has ANY active hospital affiliation (staff or affiliated),
              True if doctor is independent

    Business Rule:
        Doctors who are staff OR affiliated to a hospital cannot link their own payment accounts.
        Payments are managed by the hospital.
    """
    # Doctors with ANY active hospital affiliation cannot link their own payment accounts
    has_active_affiliation = HospitalStaffAffiliation.objects.filter(
        doctor=doctor,
        status='active'
    ).exists()

    return not has_active_affiliation  # Can link only if independent (no active affiliation)


def can_doctor_affiliate_to_hospital(doctor, hospital):
    """
    Check if a doctor can affiliate to a specific hospital.

    Args:
        doctor: Participant with role='doctor'
        hospital: Participant with role='hospital'

    Returns:
        tuple: (bool, str) - (can_affiliate, reason)
    """
    # Check if already staff at another hospital
    existing_staff = HospitalStaffAffiliation.objects.filter(
        doctor=doctor,
        affiliation_type='staff',
        status='active'
    ).exclude(hospital=hospital).first()

    if existing_staff:
        return False, f"Le médecin est déjà personnel à {existing_staff.hospital.full_name}"

    return True, "Peut s'affilier"
