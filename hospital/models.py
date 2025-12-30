from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant, Department
from core.mixins import SyncMixin


class HospitalStaff(SyncMixin):  # Manages hospital staff members with roles and permissions
    ROLE_CHOICES = [
        ('administrator', 'Administrateur'),
        ('doctor', 'Médecin'),
        ('nurse', 'Infirmier(ère)'),
        ('surgeon', 'Chirurgien'),
        ('anesthesiologist', 'Anesthésiste'),
        ('radiologist', 'Radiologue'),
        ('lab_technician', 'Technicien de laboratoire'),
        ('pharmacist', 'Pharmacien'),
        ('receptionist', 'Réceptionniste'),
        ('janitor', 'Agent d\'entretien'),
        ('security', 'Sécurité'),
        ('it_staff', 'Personnel IT'),
    ]

    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Temps plein'),
        ('part_time', 'Temps partiel'),
        ('contract', 'Contractuel'),
        ('intern', 'Stagiaire'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_staff_members')
    staff_participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_staff_profile', null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff_members')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    license_number = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=255, blank=True)
    hire_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    can_admit_patients = models.BooleanField(default=False)
    can_discharge_patients = models.BooleanField(default=False)
    can_prescribe = models.BooleanField(default=False)
    can_perform_surgery = models.BooleanField(default=False)
    can_manage_equipment = models.BooleanField(default=False)
    can_manage_staff = models.BooleanField(default=False)
    can_view_all_records = models.BooleanField(default=False)
    shift_schedule = models.CharField(max_length=50, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_staff'
        indexes = [
            models.Index(fields=['hospital', 'is_active']),
            models.Index(fields=['department']),
            models.Index(fields=['role']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.full_name} - {self.get_role_display()}"


class Bed(SyncMixin):  # Represents hospital beds with status and equipment details
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('occupied', 'Occupé'),
        ('maintenance', 'En maintenance'),
        ('reserved', 'Réservé'),
    ]

    TYPE_CHOICES = [
        ('standard', 'Standard'),
        ('icu', 'Soins intensifs'),
        ('private', 'Privé'),
        ('semi_private', 'Semi-privé'),
        ('pediatric', 'Pédiatrique'),
        ('maternity', 'Maternité'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='beds')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='beds')
    bed_number = models.CharField(max_length=20)
    room_number = models.CharField(max_length=20)
    floor_number = models.CharField(max_length=10)
    bed_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='standard')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    has_oxygen = models.BooleanField(default=False)
    has_monitor = models.BooleanField(default=False)
    is_isolation = models.BooleanField(default=False)  # Fixed typo from is_iBINTAtion
    last_cleaned = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_beds'
        unique_together = [['hospital', 'bed_number']]
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['department', 'status']),
        ]

    def __str__(self):  # Return string representation
        return f"Lit {self.bed_number} - {self.room_number}"


class Admission(SyncMixin):  # Tracks patient hospital admissions and treatment details
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('admitted', 'Admis'),
        ('discharged', 'Sorti'),
        ('transferred', 'Transféré'),
        ('deceased', 'Décédé'),
    ]

    ADMISSION_TYPE_CHOICES = [
        ('emergency', 'Urgence'),
        ('scheduled', 'Programmé'),
        ('outpatient', 'Ambulatoire'),
        ('observation', 'Observation'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    admission_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='admissions')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_admissions')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, blank=True, related_name='admissions')
    admitting_doctor = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, related_name='admitted_patients')
    admission_type = models.CharField(max_length=20, choices=ADMISSION_TYPE_CHOICES, default='scheduled')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    chief_complaint = models.TextField()
    diagnosis = models.TextField(blank=True)
    treatment_plan = models.TextField(blank=True)
    admission_date = models.DateTimeField(default=timezone.now)
    expected_discharge_date = models.DateField(null=True, blank=True)
    actual_discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_summary = models.TextField(blank=True)
    discharge_instructions = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    total_cost = models.IntegerField(default=0)  # XOF cents
    insurance_coverage = models.IntegerField(default=0)  # XOF cents
    patient_responsibility = models.IntegerField(default=0)  # XOF cents
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_admissions'
        ordering = ['-admission_date']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['admission_number']),
            models.Index(fields=['admission_date']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.admission_number} - {self.patient.full_name}"


class DepartmentTask(SyncMixin):  # Manages tasks assigned to hospital department staff
    PRIORITY_CHOICES = [
        ('low', 'Basse'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminée'),
        ('cancelled', 'Annulée'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    description = models.TextField()
    assigned_to = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, related_name='created_tasks')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'department_tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['department', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['priority']),
        ]

    def __str__(self):  # Return string representation
        return self.title


class HospitalBill(SyncMixin):  # Stores hospital billing information and payment status
    STATUS_CHOICES = [
        ('draft', 'Brouillon'),
        ('pending', 'En attente'),
        ('partially_paid', 'Partiellement payé'),
        ('paid', 'Payé'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulé'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    bill_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_bills')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_hospital_bills')
    admission = models.ForeignKey(Admission, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    total_amount = models.IntegerField(default=0)  # XOF cents
    discount_amount = models.IntegerField(default=0)  # XOF cents
    tax_amount = models.IntegerField(default=0)  # XOF cents
    insurance_coverage = models.IntegerField(default=0)  # XOF cents
    amount_paid = models.IntegerField(default=0)  # XOF cents
    balance_due = models.IntegerField(default=0)  # XOF cents
    due_date = models.DateField(null=True, blank=True)
    billing_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_bills'
        ordering = ['-billing_date']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['bill_number']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.bill_number} - {self.patient.full_name}"


class BillItem(SyncMixin):  # Represents individual line items on hospital bills
    ITEM_TYPE_CHOICES = [
        ('consultation', 'Consultation'),
        ('procedure', 'Procédure'),
        ('medication', 'Médicament'),
        ('room_charge', 'Frais de chambre'),
        ('lab_test', 'Test laboratoire'),
        ('imaging', 'Imagerie'),
        ('surgery', 'Chirurgie'),
        ('equipment', 'Équipement'),
        ('other', 'Autre'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    bill = models.ForeignKey(HospitalBill, on_delete=models.CASCADE, related_name='items')
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    description = models.CharField(max_length=255)
    quantity = models.IntegerField(default=1)
    unit_price = models.IntegerField()  # XOF cents
    total_price = models.IntegerField()  # XOF cents
    date_of_service = models.DateField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'hospital_bill_items'

    def __str__(self):  # Return string representation
        # Amounts stored in XOF cents - display formatted
        return f"{self.description} - ${self.total_price/100:.2f}"


class Payment(SyncMixin):  # Records payments received for hospital bills
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Espèces'),
        ('card', 'Carte'),
        ('mobile_money', 'Mobile Money'),
        ('bank_transfer', 'Virement bancaire'),
        ('insurance', 'Assurance'),
        ('check', 'Chèque'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    payment_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='received_payments')
    bill = models.ForeignKey(HospitalBill, on_delete=models.CASCADE, related_name='payments')
    amount = models.IntegerField()  # XOF cents
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_ref = models.CharField(max_length=100, blank=True)
    payment_date = models.DateTimeField(default=timezone.now)
    received_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='received_payments')
    notes = models.TextField(blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_payments'
        ordering = ['-payment_date']
        indexes = [
            models.Index(fields=['hospital', 'payment_date']),
            models.Index(fields=['bill']),
            models.Index(fields=['payment_number']),
        ]

    def __str__(self):  # Return string representation
        # Amount stored in XOF cents - display formatted
        return f"{self.payment_number} - ${self.amount/100:.2f}"


# ============================================================================
# EMERGENCY DEPARTMENT MODELS - ISSUE-HSP-030, HSP-031, HSP-032
# ============================================================================

class EmergencyVisit(SyncMixin):
    """
    Tracks Emergency Department patient visits with triage and status tracking.
    Addresses ISSUE-HSP-030: Emergency Department integration
    """
    STATUS_CHOICES = [
        ('waiting', 'En attente au triage'),
        ('triaged', 'Trié'),
        ('in_treatment', 'En traitement'),
        ('observation', 'En observation'),
        ('admitted', 'Admis à l\'hôpital'),
        ('discharged', 'Sorti'),
        ('left_ama', 'Parti contre avis médical'),
        ('transferred', 'Transféré'),
        ('deceased', 'Décédé'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    ed_number = models.CharField(max_length=50, unique=True, help_text="Unique ED visit number")
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_ed_visits')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_ed_visits')

    # Arrival information
    arrival_time = models.DateTimeField(default=timezone.now)
    arrival_mode = models.CharField(max_length=50, choices=[
        ('ambulance', 'Ambulance'),
        ('walk_in', 'Arrivée par ses propres moyens'),
        ('police', 'Police'),
        ('helicopter', 'Hélicoptère'),
    ], default='walk_in')

    # Clinical information
    chief_complaint = models.TextField(help_text="Main reason for ED visit")
    initial_vitals = models.TextField(blank=True, help_text="Initial vital signs (JSON format)")

    # Triage (linked to TriageAssessment model)
    triage_time = models.DateTimeField(null=True, blank=True)

    # Treatment tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    assigned_doctor = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='ed_patients')
    assigned_nurse = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='ed_nursing_patients')
    ed_bed_number = models.CharField(max_length=20, blank=True, help_text="ED bed/room location")

    # Timestamps for performance metrics (ISSUE-HSP-032)
    doctor_first_contact_time = models.DateTimeField(null=True, blank=True, help_text="Door-to-doctor time")
    treatment_start_time = models.DateTimeField(null=True, blank=True)
    disposition_time = models.DateTimeField(null=True, blank=True, help_text="When disposition decision made")
    departure_time = models.DateTimeField(null=True, blank=True)

    # Disposition
    disposition = models.CharField(max_length=50, blank=True, help_text="Final disposition (admitted, discharged, etc.)")
    discharge_diagnosis = models.TextField(blank=True)
    discharge_instructions = models.TextField(blank=True)

    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_instructions = models.TextField(blank=True)

    # Linked admission if patient admitted to hospital
    admission = models.ForeignKey(Admission, on_delete=models.SET_NULL, null=True, blank=True, related_name='ed_visit')

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'emergency_visits'
        ordering = ['-arrival_time']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['ed_number']),
            models.Index(fields=['arrival_time']),
            models.Index(fields=['status', 'arrival_time']),
        ]

    def __str__(self):
        return f"ED {self.ed_number} - {self.patient.full_name}"

    def get_wait_time_minutes(self):
        """Calculate wait time from arrival to doctor contact"""
        if self.doctor_first_contact_time and self.arrival_time:
            delta = self.doctor_first_contact_time - self.arrival_time
            return int(delta.total_seconds() / 60)
        return None

    def get_total_ed_time_minutes(self):
        """Calculate total time in ED"""
        if self.departure_time and self.arrival_time:
            delta = self.departure_time - self.arrival_time
            return int(delta.total_seconds() / 60)
        return None


class TriageAssessment(SyncMixin):
    """
    Emergency Severity Index (ESI) triage system.
    Addresses ISSUE-HSP-031: Triage protocols
    """
    ESI_LEVEL_CHOICES = [
        ('1', 'ESI 1 - Critique (immédiat)'),
        ('2', 'ESI 2 - Urgence (10 minutes)'),
        ('3', 'ESI 3 - Urgent (30 minutes)'),
        ('4', 'ESI 4 - Moins urgent (60 minutes)'),
        ('5', 'ESI 5 - Non urgent (120 minutes)'),
    ]

    COLOR_CODE_CHOICES = [
        ('red', 'Rouge - Critique'),
        ('orange', 'Orange - Urgence'),
        ('yellow', 'Jaune - Urgent'),
        ('green', 'Vert - Moins urgent'),
        ('blue', 'Bleu - Non urgent'),
    ]

    ed_visit = models.OneToOneField(EmergencyVisit, on_delete=models.CASCADE, related_name='triage')

    # Triage nurse and time
    triage_nurse = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, related_name='triage_assessments')
    triage_time = models.DateTimeField(default=timezone.now)

    # ESI level and color code
    esi_level = models.CharField(max_length=1, choices=ESI_LEVEL_CHOICES, help_text="Emergency Severity Index")
    color_code = models.CharField(max_length=10, choices=COLOR_CODE_CHOICES)

    # Vital signs
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    heart_rate = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)  # Medical accuracy needed
    oxygen_saturation = models.IntegerField(null=True, blank=True)
    pain_score = models.IntegerField(null=True, blank=True, help_text="0-10 pain scale")

    # Assessment
    chief_complaint = models.TextField()
    resource_needs = models.TextField(blank=True, help_text="Estimated resource needs (labs, imaging, etc.)")

    # Re-triage tracking
    is_re_triage = models.BooleanField(default=False)
    previous_esi_level = models.CharField(max_length=1, blank=True)
    re_triage_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'triage_assessments'
        ordering = ['-triage_time']
        indexes = [
            models.Index(fields=['esi_level']),
            models.Index(fields=['triage_time']),
        ]

    def __str__(self):
        return f"Triage ESI-{self.esi_level} - {self.ed_visit.ed_number}"


# ============================================================================
# ICU/CRITICAL CARE MODELS - ISSUE-HSP-021
# ============================================================================

class ICUAdmission(SyncMixin):
    """
    Intensive Care Unit admission tracking with severity scoring.
    Addresses ISSUE-HSP-021: ICU/Critical Care system
    """
    STATUS_CHOICES = [
        ('active', 'Actif en soins intensifs'),
        ('transferred_out', 'Transféré hors soins intensifs'),
        ('discharged', 'Sorti'),
        ('deceased', 'Décédé'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    icu_admission_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_icu_admissions')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_icu_admissions')
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='icu_admissions')

    # ICU details
    icu_bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True, related_name='icu_patients')
    attending_physician = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, related_name='icu_patients')

    # Admission information
    icu_admission_time = models.DateTimeField(default=timezone.now)
    admission_source = models.CharField(max_length=50, choices=[
        ('ed', 'Service d\'urgence'),
        ('or', 'Salle d\'opération'),
        ('ward', 'Service hospitalier'),
        ('transfer', 'Transfert externe'),
    ])
    admission_diagnosis = models.TextField()

    # Severity scores (can be updated daily)
    apache_score = models.IntegerField(null=True, blank=True, help_text="APACHE II score (0-71)")
    sofa_score = models.IntegerField(null=True, blank=True, help_text="SOFA score (0-24)")
    gcs_score = models.IntegerField(null=True, blank=True, help_text="Glasgow Coma Scale (3-15)")

    # Support systems
    mechanical_ventilation = models.BooleanField(default=False)
    vasopressor_support = models.BooleanField(default=False)
    renal_replacement = models.BooleanField(default=False)
    ecmo = models.BooleanField(default=False, help_text="Extracorporeal membrane oxygenation")

    # Status and discharge
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    icu_discharge_time = models.DateTimeField(null=True, blank=True)
    icu_length_of_stay_hours = models.IntegerField(null=True, blank=True)
    discharge_destination = models.CharField(max_length=50, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'icu_admissions'
        ordering = ['-icu_admission_time']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['icu_admission_number']),
        ]

    def __str__(self):
        return f"ICU {self.icu_admission_number} - {self.patient.full_name}"


# ============================================================================
# OPERATING ROOM MODELS - ISSUE-HSP-033, HSP-034, HSP-035
# ============================================================================

class OperatingRoom(SyncMixin):
    """
    Operating room inventory and status.
    Addresses ISSUE-HSP-033: Operating room management
    """
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('occupied', 'Occupé'),
        ('cleaning', 'En nettoyage'),
        ('maintenance', 'En maintenance'),
        ('reserved', 'Réservé'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='operating_rooms')
    or_number = models.CharField(max_length=20, help_text="Operating room number")
    or_name = models.CharField(max_length=100)
    floor_number = models.CharField(max_length=10)

    # Capabilities
    or_type = models.CharField(max_length=50, choices=[
        ('general', 'Chirurgie générale'),
        ('cardiac', 'Chirurgie cardiaque'),
        ('neuro', 'Neurochirurgie'),
        ('ortho', 'Orthopédie'),
        ('pediatric', 'Pédiatrie'),
        ('trauma', 'Traumatologie'),
    ])
    has_laparoscopy = models.BooleanField(default=False)
    has_robotic_surgery = models.BooleanField(default=False)
    has_c_arm = models.BooleanField(default=False)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_surgery = models.ForeignKey('SurgerySchedule', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_or')

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'operating_rooms'
        unique_together = [['hospital', 'or_number']]
        indexes = [
            models.Index(fields=['hospital', 'status']),
        ]

    def __str__(self):
        return f"{self.or_name} ({self.or_number})"


class SurgerySchedule(SyncMixin):
    """
    Surgery scheduling and tracking system.
    Addresses ISSUE-HSP-033: OR scheduling, ISSUE-HSP-034: Surgical team coordination
    """
    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('confirmed', 'Confirmé'),
        ('patient_arrived', 'Patient arrivé'),
        ('in_pre_op', 'En pré-opératoire'),
        ('in_surgery', 'En cours de chirurgie'),
        ('in_pacu', 'En salle de réveil'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('postponed', 'Reporté'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    surgery_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_surgeries')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_surgeries')
    admission = models.ForeignKey(Admission, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries')

    # Scheduling
    operating_room = models.ForeignKey(OperatingRoom, on_delete=models.PROTECT, related_name='scheduled_surgeries')
    scheduled_date = models.DateField()
    scheduled_start_time = models.TimeField()
    estimated_duration_minutes = models.IntegerField()
    scheduled_end_time = models.TimeField(null=True, blank=True)

    # Surgery details
    procedure_name = models.CharField(max_length=255)
    procedure_code = models.CharField(max_length=50, blank=True, help_text="CPT or ICD-10-PCS code")
    procedure_category = models.CharField(max_length=50, choices=[
        ('elective', 'Électif'),
        ('urgent', 'Urgent'),
        ('emergency', 'Urgence'),
    ], default='elective')
    surgery_type = models.CharField(max_length=100, blank=True)

    # Surgical team (ISSUE-HSP-034)
    primary_surgeon = models.ForeignKey(HospitalStaff, on_delete=models.PROTECT, related_name='surgeries_as_primary')
    assistant_surgeon = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries_as_assistant')
    anesthesiologist = models.ForeignKey(HospitalStaff, on_delete=models.PROTECT, related_name='surgeries_as_anesthesiologist')
    scrub_nurse = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries_as_scrub_nurse')
    circulating_nurse = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='surgeries_as_circulating_nurse')

    # Equipment and supplies needed
    special_equipment = models.TextField(blank=True, help_text="Special equipment requirements")
    implants_needed = models.TextField(blank=True)

    # Actual times
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    actual_duration_minutes = models.IntegerField(null=True, blank=True)

    # Pre-op and post-op
    pre_op_checklist_complete = models.BooleanField(default=False)
    consent_signed = models.BooleanField(default=False)
    surgical_site_marked = models.BooleanField(default=False)

    # Post-op
    estimated_blood_loss_ml = models.IntegerField(null=True, blank=True)
    complications = models.TextField(blank=True)
    post_op_destination = models.CharField(max_length=50, blank=True, help_text="ICU, Ward, PACU, etc.")
    post_op_orders = models.TextField(blank=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    cancellation_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'surgery_schedules'
        ordering = ['scheduled_date', 'scheduled_start_time']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['operating_room', 'scheduled_date']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['primary_surgeon', 'scheduled_date']),
        ]

    def __str__(self):
        return f"{self.surgery_number} - {self.procedure_name}"


# ============================================================================
# STAFF MANAGEMENT MODELS - ISSUE-HSP-013, HSP-014, HSP-016
# ============================================================================

class StaffShift(SyncMixin):
    """
    Staff shift scheduling and management.
    Addresses ISSUE-HSP-013: Shift management system
    """
    SHIFT_TYPE_CHOICES = [
        ('day', 'Jour (7h-15h)'),
        ('evening', 'Soir (15h-23h)'),
        ('night', 'Nuit (23h-7h)'),
        ('day_12h', 'Jour 12h (7h-19h)'),
        ('night_12h', 'Nuit 12h (19h-7h)'),
        ('custom', 'Personnalisé'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('confirmed', 'Confirmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('no_show', 'Absent'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='staff_shifts')
    staff = models.ForeignKey(HospitalStaff, on_delete=models.CASCADE, related_name='shifts')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='shifts')

    # Shift details
    shift_date = models.DateField()
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()

    # Actual times (for attendance tracking)
    actual_clock_in = models.DateTimeField(null=True, blank=True)
    actual_clock_out = models.DateTimeField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    is_overtime = models.BooleanField(default=False)

    # Notes
    notes = models.TextField(blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        db_table = 'staff_shifts'
        ordering = ['shift_date', 'start_time']
        indexes = [
            models.Index(fields=['hospital', 'shift_date']),
            models.Index(fields=['staff', 'shift_date']),
            models.Index(fields=['department', 'shift_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.staff.full_name} - {self.shift_date} {self.get_shift_type_display()}"


class OnCallSchedule(SyncMixin):
    """
    On-call rotation scheduling for hospital staff.
    Addresses ISSUE-HSP-014: On-call scheduling
    """
    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('active', 'Actif'),
        ('called_in', 'Appelé'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='oncall_schedules')
    staff = models.ForeignKey(HospitalStaff, on_delete=models.CASCADE, related_name='oncall_shifts')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='oncall_schedules')

    # On-call period
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    # Priority and backup
    priority = models.CharField(max_length=20, choices=[
        ('primary', 'Principal'),
        ('backup', 'Remplaçant'),
    ], default='primary')
    backup_staff = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='backup_oncall_shifts')

    # Contact information
    contact_phone = models.CharField(max_length=20)
    response_time_minutes = models.IntegerField(default=30, help_text="Expected response time in minutes")

    # Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    was_called = models.BooleanField(default=False)
    call_time = models.DateTimeField(null=True, blank=True)
    response_time_actual = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'oncall_schedules'
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['hospital', 'start_datetime']),
            models.Index(fields=['staff', 'start_datetime']),
            models.Index(fields=['department', 'start_datetime']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.staff.full_name} - On-call {self.start_datetime.date()}"


class StaffCredential(SyncMixin):
    """
    Medical license and certification tracking for staff.
    Addresses ISSUE-HSP-016: Credentialing system
    """
    CREDENTIAL_TYPE_CHOICES = [
        ('medical_license', 'Licence médicale'),
        ('nursing_license', 'Licence infirmière'),
        ('board_certification', 'Certification du conseil'),
        ('specialty_certification', 'Certification de spécialité'),
        ('cpr_bls', 'RCR/BLS'),
        ('acls', 'ACLS'),
        ('pals', 'PALS'),
        ('other', 'Autre'),
    ]

    STATUS_CHOICES = [
        ('active', 'Actif'),
        ('expired', 'Expiré'),
        ('pending_renewal', 'En attente de renouvellement'),
        ('suspended', 'Suspendu'),
        ('revoked', 'Révoqué'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    staff = models.ForeignKey(HospitalStaff, on_delete=models.CASCADE, related_name='credentials')

    # Credential details
    credential_type = models.CharField(max_length=50, choices=CREDENTIAL_TYPE_CHOICES)
    credential_name = models.CharField(max_length=255)
    issuing_organization = models.CharField(max_length=255)
    credential_number = models.CharField(max_length=100)

    # Dates
    issue_date = models.DateField()
    expiration_date = models.DateField()
    verification_date = models.DateField(null=True, blank=True)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_credentials')

    # Document
    document_file = models.FileField(upload_to='staff_credentials/%Y/%m/', blank=True)

    # Alerts
    expiration_alert_sent = models.BooleanField(default=False)
    days_before_expiration_alert = models.IntegerField(default=90)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'staff_credentials'
        ordering = ['expiration_date']
        indexes = [
            models.Index(fields=['staff', 'status']),
            models.Index(fields=['credential_type']),
            models.Index(fields=['expiration_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.staff.full_name} - {self.get_credential_type_display()}"

    def is_expiring_soon(self):
        """Check if credential is expiring within the alert threshold"""
        from datetime import date, timedelta
        if self.expiration_date:
            alert_date = date.today() + timedelta(days=self.days_before_expiration_alert)
            return self.expiration_date <= alert_date
        return False


# ============================================================================
# CLINICAL ORDERS MODELS - ISSUE-HSP-071, HSP-040, HSP-037
# ============================================================================

class PhysicianOrder(SyncMixin):
    """
    Computerized Physician Order Entry (CPOE) system.
    Addresses ISSUE-HSP-071: CPOE implementation
    """
    ORDER_TYPE_CHOICES = [
        ('medication', 'Médicament'),
        ('lab', 'Laboratoire'),
        ('imaging', 'Imagerie'),
        ('procedure', 'Procédure'),
        ('diet', 'Régime alimentaire'),
        ('nursing', 'Soins infirmiers'),
        ('consult', 'Consultation'),
        ('therapy', 'Thérapie'),
        ('other', 'Autre'),
    ]

    PRIORITY_CHOICES = [
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('stat', 'STAT (immédiat)'),
        ('asap', 'Dès que possible'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('acknowledged', 'Accusé de réception'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('discontinued', 'Interrompu'),
        ('on_hold', 'En suspens'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    order_number = models.CharField(max_length=50, unique=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_physician_orders')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_physician_orders')
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='orders')

    # Order details
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    order_description = models.TextField()
    clinical_indication = models.TextField(blank=True)

    # Priority (ISSUE-HSP-037: STAT orders)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='routine')

    # Ordering physician
    ordering_physician = models.ForeignKey(HospitalStaff, on_delete=models.PROTECT, related_name='orders_created')
    order_datetime = models.DateTimeField(default=timezone.now)

    # Drug interaction checking (for medication orders)
    drug_interaction_checked = models.BooleanField(default=False)
    drug_interaction_warnings = models.TextField(blank=True)

    # Execution
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    acknowledged_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_acknowledged')
    acknowledged_datetime = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_completed')
    completed_datetime = models.DateTimeField(null=True, blank=True)

    # Cancellation
    cancelled_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders_cancelled')
    cancellation_reason = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'physician_orders'
        ordering = ['-order_datetime']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['admission']),
            models.Index(fields=['order_number']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['order_type', 'status']),
        ]

    def __str__(self):
        return f"{self.order_number} - {self.get_order_type_display()}"


class CriticalValueAlert(SyncMixin):
    """
    Critical laboratory value alerting system.
    Addresses ISSUE-HSP-040: Critical value alerting
    """
    ALERT_TYPE_CHOICES = [
        ('critical_high', 'Critique élevé'),
        ('critical_low', 'Critique bas'),
        ('panic', 'Panique'),
        ('abnormal', 'Anormal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('notified', 'Notifié'),
        ('acknowledged', 'Accusé de réception'),
        ('action_taken', 'Action entreprise'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='hospital_critical_alerts')
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='patient_critical_alerts')
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='critical_alerts')

    # Lab test information
    test_name = models.CharField(max_length=255)
    result_value = models.CharField(max_length=100)
    normal_range = models.CharField(max_length=100)
    unit_of_measure = models.CharField(max_length=50)

    # Alert details
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Bas'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('critical', 'Critique'),
    ])

    # Timestamps
    result_datetime = models.DateTimeField()
    alert_created = models.DateTimeField(default=timezone.now)

    # Notification
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notified_physician = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='critical_alerts_received')
    notification_datetime = models.DateTimeField(null=True, blank=True)
    notification_method = models.CharField(max_length=50, blank=True, help_text="Email, SMS, Phone, etc.")

    # Acknowledgment
    acknowledged_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='critical_alerts_acknowledged')
    acknowledged_datetime = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'critical_value_alerts'
        ordering = ['-alert_created']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['status', 'alert_created']),
            models.Index(fields=['alert_type']),
        ]

    def __str__(self):
        return f"ALERT: {self.test_name} = {self.result_value} for {self.patient.full_name}"


# ============================================================================
# EQUIPMENT MAINTENANCE MODEL - ISSUE-HSP-041
# ============================================================================

class EquipmentMaintenance(SyncMixin):
    """
    Preventive maintenance scheduling and tracking for medical equipment.
    Addresses ISSUE-HSP-041: Preventive maintenance system
    """
    MAINTENANCE_TYPE_CHOICES = [
        ('preventive', 'Préventif'),
        ('corrective', 'Correctif'),
        ('calibration', 'Étalonnage'),
        ('inspection', 'Inspection'),
    ]

    STATUS_CHOICES = [
        ('scheduled', 'Programmé'),
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('cancelled', 'Annulé'),
        ('overdue', 'En retard'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='equipment_maintenance')

    # Equipment details (simplified - could link to Equipment model if exists)
    equipment_name = models.CharField(max_length=255)
    equipment_serial_number = models.CharField(max_length=100)
    equipment_location = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='equipment_maintenance')

    # Maintenance details
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    maintenance_number = models.CharField(max_length=50, unique=True)
    scheduled_date = models.DateField()
    completed_date = models.DateField(null=True, blank=True)

    # Personnel
    performed_by = models.CharField(max_length=255, blank=True, help_text="Technician name or company")
    supervised_by = models.ForeignKey(HospitalStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='supervised_maintenance')

    # Results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    maintenance_passed = models.BooleanField(null=True, blank=True)
    findings = models.TextField(blank=True)
    corrective_actions = models.TextField(blank=True)

    # Next maintenance
    next_maintenance_due = models.DateField(null=True, blank=True)
    maintenance_frequency_days = models.IntegerField(default=365, help_text="Days between maintenance")

    # Cost - Changed from DecimalField to IntegerField (XOF cents)
    maintenance_cost = models.IntegerField(default=0)  # XOF cents

    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'equipment_maintenance'
        ordering = ['-scheduled_date']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['scheduled_date']),
            models.Index(fields=['equipment_serial_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.maintenance_number} - {self.equipment_name}"

