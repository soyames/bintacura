# Contributing to BintaCura

## 📋 Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Git Workflow & Commit Standards](#git-workflow--commit-standards)
3. [Database Standards & ACID Compliance](#database-standards--acid-compliance)
4. [Code Architecture](#code-architecture)
5. [Testing Requirements](#testing-requirements)
6. [Participant Role System](#participant-role-system)
7. [Common Tasks & Workflows](#common-tasks--workflows)

---

## 🛠️ Development Environment Setup

### Prerequisites

**Required Software:**
- **Python 3.10 or higher** - [Download](https://www.python.org/downloads/)
- **PostgreSQL 13+** - We use a **remote database hosted on Render**
- **Redis 6+** - For caching and task queue
- **Node.js 16+** - For frontend asset compilation
- **Git** - Version control

**Verify installations:**
```bash
python --version    # Should be 3.10+
psql --version      # Should be 13+
redis-server --version
node --version
git --version
```

### Database Configuration

**IMPORTANT:** We use a **centralized PostgreSQL database hosted on Render.com**

#### Database Access
- **Host:** Provided by team lead (DO NOT commit to repository)
- **Database:** `bintacura_production` (or staging database for testing)
- **Port:** 5432
- **SSL Mode:** Required

#### Getting Database Credentials

**Contact project owner to receive:**
1. Database connection URL
2. `.env` file with credentials
3. VPN access (if required)

**⚠️ SECURITY RULES (MANDATORY):**
- ❌ NEVER commit database credentials to Git
- ❌ NEVER commit `.env` file to repository  
- ❌ NEVER share passwords or API keys publicly
- ❌ NEVER include credentials in code comments
- ❌ NEVER commit any sensitive information
- ✅ Always use environment variables for sensitive data
- ✅ Add `.env` to `.gitignore` (already done)
- ✅ Contact project owner if you need credentials

### Project Setup

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/vitacare_django.git
cd vitacare_django

# 2. Create virtual environment
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment variables
# Contact project owner for .env file with database credentials
# NEVER commit .env file to Git!
# NEVER share credentials publicly!

# 5. Verify database connection
python manage.py check --database default

# 6. Check for migrations (DO NOT create new migrations yet!)
python manage.py showmigrations

# 7. Apply migrations if needed (rarely needed as DB is shared)
# Only run if explicitly told by team lead
# python manage.py migrate

# 8. Create your local superuser (ONLY if INSTANCE_TYPE=CLOUD in .env)
# For LOCAL instances, use: python manage.py request_admin
python manage.py createsuperuser

# 9. Run development server
python manage.py runserver

# 10. Visit http://localhost:8000
```

### IDE Setup (Recommended: VS Code or PyCharm)

**VS Code Extensions:**
- Python (Microsoft)
- Pylance
- Django
- GitLens
- PostgreSQL (for database queries)

**PyCharm:**
- Django support enabled
- PostgreSQL database connection configured

---

## 🔄 Git Workflow & Commit Standards

### ⚠️ STRICT COMMIT RULES

**Since this project is private and not under an organization, we enforce strict self-discipline:**

### Branching Strategy

```
main (production-ready)
  ├── develop (integration branch)
  │   ├── feature/pharmacy-counter-system
  │   ├── feature/appointment-notifications
  │   ├── bugfix/payment-currency-conversion
  │   └── hotfix/login-timeout-issue
```

### Branch Naming Convention

```bash
# Feature branches
feature/<issue-number>-<short-description>
feature/123-pharmacy-inventory

# Bug fixes
bugfix/<issue-number>-<short-description>
bugfix/456-payment-receipt-error

# Hot fixes (urgent production bugs)
hotfix/<issue-number>-<description>
hotfix/789-critical-auth-bypass

# Refactoring
refactor/<description>
refactor/payment-service-cleanup
```

### Commit Message Format (MANDATORY)

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic change)
- `refactor`: Code restructuring (no feature change)
- `test`: Adding/updating tests
- `chore`: Build process, dependencies
- `perf`: Performance improvements
- `security`: Security improvements

**Examples:**

```bash
# Good commits ✅
git commit -m "feat(pharmacy): add multi-counter payment system

- Implemented PharmacyCounter model with staff assignment
- Added counter-specific cash register tracking
- Updated payment flow to support counter selection
- All database changes are ACID compliant

Closes #145"

git commit -m "fix(appointments): resolve timezone conversion bug

- Fixed appointment time showing incorrect timezone
- Added proper UTC conversion in serializer
- Updated tests to verify timezone handling

Fixes #234"

git commit -m "docs(readme): update contribution guidelines

- Added database setup instructions
- Clarified commit message format
- Included ACID compliance checklist"

# Bad commits ❌
git commit -m "fixed stuff"
git commit -m "WIP"
git commit -m "asdf"
git commit -m "changes"
```

### Pull Request Process

1. **Create feature branch from `develop`**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/123-my-feature
```

2. **Make your changes with proper commits**
```bash
git add .
git commit -m "feat(module): detailed description..."
```

3. **Push to remote**
```bash
git push origin feature/123-my-feature
```

4. **Create Pull Request on GitHub**
- **Title:** Clear and descriptive
- **Description:** 
  - What changes were made
  - Why they were made
  - How to test
  - Screenshots (if UI changes)
  - Migration notes (if database changes)
  - Breaking changes (if any)

5. **Code Review Checklist**
- [ ] Code follows project style
- [ ] All tests pass
- [ ] Database changes are ACID compliant
- [ ] No sensitive data in commits
- [ ] Documentation updated
- [ ] No console.log or debug prints
- [ ] Migrations are idempotent

6. **Merge Requirements**
- Minimum 1 approval from team lead
- All CI/CD checks pass
- Conflicts resolved
- Up to date with develop branch

### Daily Workflow

```bash
# Morning: Start of day
git checkout develop
git pull origin develop
git checkout feature/my-feature
git merge develop  # Keep your branch up to date

# During work: Regular commits
git add <files>
git commit -m "feat(module): specific change"

# Before lunch/end of day: Push your work
git push origin feature/my-feature

# Before creating PR: Final cleanup
git fetch origin
git rebase origin/develop  # Optional: clean history
git push origin feature/my-feature --force-with-lease
```

---

## 🗄️ Database Standards & ACID Compliance

### ACID Properties (MANDATORY)

Our database MUST maintain ACID properties at all times:

#### **A - Atomicity**
Transactions must be all-or-nothing.

```python
# ✅ CORRECT - Using transaction
from django.db import transaction

@transaction.atomic
def create_appointment_with_payment(appointment_data, payment_data):
    """Both appointment and payment are created, or neither"""
    appointment = Appointment.objects.create(**appointment_data)
    payment = Payment.objects.create(
        appointment=appointment,
        **payment_data
    )
    return appointment

# ❌ WRONG - No transaction
def create_appointment_with_payment(appointment_data, payment_data):
    appointment = Appointment.objects.create(**appointment_data)
    # If this fails, appointment is still created (inconsistent state!)
    payment = Payment.objects.create(**payment_data)
```

#### **C - Consistency**
Database must always be in a valid state.

```python
# ✅ CORRECT - Validation ensures consistency
class PharmacyOrder(models.Model):
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def clean(self):
        if self.paid_amount > self.total_amount:
            raise ValidationError("Paid amount cannot exceed total")
        if self.total_amount < 0:
            raise ValidationError("Total amount must be positive")
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Always validate before save
        super().save(*args, **kwargs)
```

#### **I - Isolation**
Concurrent transactions must not interfere.

```python
# ✅ CORRECT - Using select_for_update to prevent race conditions
from django.db import transaction

@transaction.atomic
def process_pharmacy_sale(order_id, items):
    # Lock the inventory rows to prevent concurrent modifications
    inventory_items = PharmacyInventory.objects.select_for_update().filter(
        medication_id__in=[item['medication_id'] for item in items]
    )
    
    for inventory in inventory_items:
        item = next(i for i in items if i['medication_id'] == inventory.medication_id)
        if inventory.quantity < item['quantity']:
            raise ValueError(f"Insufficient stock for {inventory.medication.name}")
        inventory.quantity -= item['quantity']
        inventory.save()

# ❌ WRONG - Race condition possible
def process_pharmacy_sale(order_id, items):
    for item in items:
        inventory = PharmacyInventory.objects.get(medication_id=item['medication_id'])
        # Another transaction could modify this between get and save!
        inventory.quantity -= item['quantity']
        inventory.save()
```

#### **D - Durability**
Committed transactions must persist.

- Django handles this automatically with PostgreSQL
- Always use `transaction.atomic()` for critical operations
- Never catch and suppress database errors without logging

### Idempotency (CRITICAL)

All operations must be idempotent - calling them multiple times has the same effect as calling once.

```python
# ✅ CORRECT - Idempotent operation
def create_or_update_patient(patient_id, data):
    patient, created = Patient.objects.update_or_create(
        id=patient_id,
        defaults=data
    )
    return patient

# ✅ CORRECT - Idempotent with idempotency key
def process_payment(idempotency_key, payment_data):
    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing  # Already processed
    
    return Payment.objects.create(
        idempotency_key=idempotency_key,
        **payment_data
    )

# ❌ WRONG - Not idempotent
def add_item_to_cart(cart_id, item):
    cart = Cart.objects.get(id=cart_id)
    cart.items.add(item)  # Calling twice adds item twice!
```

### Migration Best Practices

```python
# ✅ CORRECT - Reversible migration
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='appointment',
            name='consultation_fee_usd',
            field=models.DecimalField(max_digits=10, decimal_places=2, null=True),
        ),
    ]
    
    # Always provide reverse operation
    def reverse_code(apps, schema_editor):
        # Migration reversal logic
        pass

# ✅ CORRECT - Data migration with transaction
def migrate_currency_data(apps, schema_editor):
    Payment = apps.get_model('payments', 'Payment')
    
    # Process in batches to avoid memory issues
    batch_size = 1000
    payments = Payment.objects.all()
    
    for i in range(0, payments.count(), batch_size):
        batch = payments[i:i+batch_size]
        for payment in batch:
            payment.amount_usd = convert_to_usd(payment.amount, payment.currency)
            payment.save()

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(migrate_currency_data, reverse_code=migrations.RunPython.noop),
    ]

# ❌ WRONG - Not idempotent
def bad_migration(apps, schema_editor):
    Payment = apps.get_model('payments', 'Payment')
    for payment in Payment.objects.all():
        # Running twice will double the amount!
        payment.amount *= 2
        payment.save()
```

### Database Query Best Practices

```python
# ✅ CORRECT - Efficient queries
# Use select_related for ForeignKey
appointments = Appointment.objects.select_related(
    'patient', 'doctor', 'hospital'
).filter(date=today)

# Use prefetch_related for ManyToMany
doctors = Doctor.objects.prefetch_related(
    'specializations', 'hospitals'
).all()

# Use only() to fetch specific fields
patients = Patient.objects.only('id', 'name', 'email').all()

# ❌ WRONG - N+1 query problem
appointments = Appointment.objects.filter(date=today)
for appointment in appointments:
    print(appointment.patient.name)  # Queries database for EACH appointment!
    print(appointment.doctor.name)    # Another query!
```

---

## 🏗️ Code Architecture

### SyncMixin - Offline-First Architecture

**What is SyncMixin?**

SyncMixin is an abstract model that provides offline-first synchronization capabilities. It allows local installations (hospitals, pharmacies) to operate independently and sync with the cloud.

**When to use SyncMixin:**

✅ **Use SyncMixin for:**
- Models that need to sync between local and cloud instances
- Critical business data (appointments, prescriptions, payments)
- Data created at multiple locations
- Models that need conflict resolution

❌ **Don't use SyncMixin for:**
- System configuration (single source of truth)
- Static reference data (countries, currencies)
- Temporary data (sessions, cache)
- Large binary data (use cloud storage instead)

**How to use SyncMixin:**

```python
from core.sync_mixin import SyncMixin

class Appointment(SyncMixin):
    """Appointments are created at hospitals and need to sync to cloud"""
    patient = models.ForeignKey('core.Participant', on_delete=models.PROTECT)
    doctor = models.ForeignKey('doctor.DoctorData', on_delete=models.PROTECT)
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20)
    
    class Meta:
        indexes = [
            models.Index(fields=['instance_id', 'updated_at']),  # For sync queries
        ]
```

**SyncMixin provides:**
- `id` - UUID (globally unique across all instances)
- `created_at` - When record was created
- `updated_at` - When record was last modified
- `version` - Version number for conflict detection
- `instance_id` - Which installation created this record
- `created_by_instance` - Original creator instance
- `deleted_at` - Soft delete timestamp
- `last_synced_at` - Last successful sync

**Sync Workflow:**

1. **Local instance creates record**
   - Assigns unique UUID
   - Sets `instance_id` to local instance
   - Sets `version = 1`

2. **Sync to cloud**
   - Local pushes changes to cloud API
   - Cloud checks for conflicts (version mismatch)
   - Cloud accepts or rejects based on conflict resolution rules

3. **Cloud distributes to other instances**
   - Other instances pull changes
   - Update their local database
   - Handle any conflicts

### Serializers - API Data Transformation

**Why we use serializers:**

Serializers handle the conversion between complex Python objects and JSON/XML for API responses.

```python
from rest_framework import serializers

class AppointmentSerializer(serializers.ModelSerializer):
    # Related fields
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    
    # Custom fields
    consultation_fee_formatted = serializers.SerializerMethodField()
    
    def get_consultation_fee_formatted(self, obj):
        return f"${obj.consultation_fee_usd:.2f}"
    
    # Validation
    def validate_appointment_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Cannot book appointments in the past")
        return value
    
    # Custom create logic
    def create(self, validated_data):
        # Add current instance_id
        validated_data['instance_id'] = settings.INSTANCE_ID
        return super().create(validated_data)
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment_date', 'status', 'consultation_fee_usd',
            'consultation_fee_formatted', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'instance_id']
```

**Serializer Best Practices:**

✅ **Always:**
- Validate input data
- Use `read_only=True` for computed fields
- Include related object details
- Handle currency conversion
- Add helpful error messages

❌ **Never:**
- Return sensitive data (passwords, tokens)
- Perform heavy operations in `get_*` methods
- Ignore validation errors
- Return None without handling

### Services - Business Logic Layer

**Why we separate services:**

Services contain reusable business logic separate from views and models.

```python
# appointments/services.py

class AppointmentService:
    """Business logic for appointment management"""
    
    @staticmethod
    @transaction.atomic
    def create_appointment(patient, doctor, appointment_date, **kwargs):
        """
        Create appointment with all necessary validations and side effects
        
        Returns: (Appointment, created: bool, errors: list)
        """
        errors = []
        
        # 1. Validate availability
        if not doctor.is_available(appointment_date):
            errors.append("Doctor is not available at this time")
        
        # 2. Check for conflicts
        conflicts = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=['SCHEDULED', 'IN_PROGRESS']
        ).exists()
        
        if conflicts:
            errors.append("Time slot already booked")
        
        if errors:
            return None, False, errors
        
        # 3. Create appointment
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            appointment_date=appointment_date,
            instance_id=settings.INSTANCE_ID,
            **kwargs
        )
        
        # 4. Side effects
        AppointmentService._send_confirmation(appointment)
        AppointmentService._update_queue(appointment)
        
        return appointment, True, []
    
    @staticmethod
    def _send_confirmation(appointment):
        """Send confirmation email/SMS"""
        # Implementation
        pass
    
    @staticmethod
    def _update_queue(appointment):
        """Update queue management system"""
        # Implementation
        pass
```

---

## 🧪 Testing Requirements

### Test Structure

```python
# tests/test_appointments.py

from django.test import TestCase
from django.utils import timezone
from appointments.services import AppointmentService
from appointments.models import Appointment

class AppointmentServiceTest(TestCase):
    
    def setUp(self):
        """Run before each test"""
        self.patient = PatientFactory()
        self.doctor = DoctorFactory()
        self.appointment_date = timezone.now() + timezone.timedelta(days=1)
    
    def test_create_appointment_success(self):
        """Test successful appointment creation"""
        appointment, created, errors = AppointmentService.create_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_date
        )
        
        self.assertTrue(created)
        self.assertEqual(len(errors), 0)
        self.assertIsNotNone(appointment)
        self.assertEqual(appointment.status, 'SCHEDULED')
    
    def test_create_appointment_with_conflict(self):
        """Test appointment creation with time conflict"""
        # Create existing appointment
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_date,
            status='SCHEDULED'
        )
        
        # Try to create conflicting appointment
        appointment, created, errors = AppointmentService.create_appointment(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_date
        )
        
        self.assertFalse(created)
        self.assertIn("Time slot already booked", errors)
    
    def tearDown(self):
        """Run after each test"""
        pass
```

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test appointments

# Run specific test class
python manage.py test appointments.tests.AppointmentServiceTest

# Run with coverage
pip install coverage
coverage run --source='.' manage.py test
coverage report
coverage html  # Generate HTML report
```

---

## 👥 Participant Role System

### ⚠️ CRITICAL: Understanding the Participant Model

**IMPORTANT:** BintaCura uses a **single unified User model** called `Participant` - NOT Django's default `User` model.

**DO NOT use `User` namespace anywhere in the code!**

### Why Participant Instead of User?

```python
# ❌ WRONG - Never import or use Django's User model
from django.contrib.auth.models import User  # DON'T DO THIS!

# ✅ CORRECT - Always use Participant
from core.models import Participant

# Create a new participant
participant = Participant.objects.create_user(
    email='patient@example.com',
    password='secure_password',
    role='PATIENT',
    first_name='John',
    last_name='Doe'
)
```

### Participant Model Structure

```python
# core/models.py
class Participant(AbstractBaseUser, PermissionsMixin):
    """
    Unified user model for all system participants.
    Replaces Django's default User model.
    
    DO NOT use 'User' anywhere - always use 'Participant'
    """
    email = models.EmailField(unique=True)  # Primary identifier
    phone_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # Role determines what this participant can do
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    
    # Instance tracking (for sync)
    instance_id = models.CharField(max_length=255, blank=True)
    
    USERNAME_FIELD = 'email'  # Login with email, not username
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    objects = ParticipantManager()
    
    class Meta:
        db_table = 'core_participant'
        verbose_name = 'Participant'
        verbose_name_plural = 'Participants'
```

### How to Reference Participant in Models

```python
# ✅ CORRECT - Use settings.AUTH_USER_MODEL
from django.conf import settings

class Appointment(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Points to Participant
        on_delete=models.PROTECT,
        related_name='appointments_as_patient'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='appointments_created'
    )

# ✅ CORRECT - Direct import for type hints
from core.models import Participant

def process_appointment(patient: Participant):
    """Process appointment for a participant"""
    pass

# ❌ WRONG - Never use User
from django.contrib.auth.models import User  # DON'T DO THIS!
```

### Participant Roles

BintaCura uses a **single unified User model** called `Participant` with different roles:

**Participant Roles:**
- `PATIENT` - Regular patients
- `DOCTOR` - Medical doctors
- `HOSPITAL_ADMIN` - Hospital administrators
- `PHARMACY_STAFF` - Pharmacy employees
- `PHARMACY_MANAGER` - Pharmacy managers
- `INSURANCE_AGENT` - Insurance company staff
- `TRANSPORT_DRIVER` - Ambulance drivers
- `FINANCE_STAFF` - Financial department staff
- `HR_STAFF` - Human resources staff
- `SUPERUSER` - System administrators (cloud only)

### Role Flow by Module

#### 1. **Patient Registration & Management**

**Files:**
- `patient/models.py` - Patient profile data
- `patient/views.py` - Patient-specific views
- `authentication/views.py` - Registration/login

**Flow:**
```
1. User registers → Creates Participant (role=PATIENT)
2. Fills patient profile → Creates Patient record
3. Can book appointments
4. Can view health records
5. Can make payments
```

**Important models:**
- `Participant` (core/models.py) - Base user
- `Patient` (patient/models.py) - Extended patient data

#### 2. **Appointment System**

**Files:**
- `appointments/models.py` - Appointment data model
- `appointments/services.py` - Business logic
- `appointments/views.py` - API endpoints
- `appointments/serializers.py` - Data transformation

**Flow:**
```
Patient Side:
1. Search for doctors
2. View available time slots
3. Book appointment
4. Receive confirmation
5. Pay consultation fee
6. Join appointment (in-person or telemedicine)

Doctor Side:
1. Set availability schedule
2. Receive appointment notifications
3. View patient history
4. Conduct consultation
5. Write prescription
6. Complete appointment

Hospital Admin:
1. Manage doctor schedules
2. View all appointments
3. Handle cancellations
4. Generate reports
```

**Database consistency:**
- Appointment status transitions must be sequential
- Cannot delete appointment with payment
- Must use `select_for_update()` when changing status

#### 3. **Pharmacy System**

**Files:**
- `pharmacy/models.py` - Inventory, orders, counters
- `pharmacy/payment_service.py` - Payment processing
- `pharmacy/counter_views.py` - Counter-specific operations
- `pharmacy/serializers.py` - API serialization

**Flow:**
```
Customer:
1. Upload prescription or walk-in
2. Pharmacy staff verifies prescription
3. Staff creates order with items
4. Customer pays at counter
5. Receives receipt and medications

Pharmacy Staff:
1. Login → Assigned to counter
2. Scan/enter prescription
3. Check inventory
4. Create order
5. Process payment (cash/mobile/insurance)
6. Print receipt
7. Dispense medications
8. Update inventory

Pharmacy Manager:
1. Manage inventory
2. Set prices
3. View sales reports
4. Manage staff assignments
5. Handle refunds/returns
```

**Database consistency:**
- Inventory must be locked with `select_for_update()`
- Cannot dispense without payment
- Stock cannot go negative
- All transactions must be atomic

#### 4. **Payment System**

**Files:**
- `payments/models.py` - Payment records, receipts
- `payments/services.py` - Payment processing
- `payments/fedapay_service.py` - Mobile money integration
- `currency_converter/services.py` - Currency conversion

**Flow:**
```
1. Service rendered (appointment, pharmacy order, etc.)
2. Payment request created
3. Customer chooses payment method:
   - Cash
   - Mobile Money (FedaPay)
   - Insurance
   - Bank transfer
4. Payment processed
5. Receipt generated (PDF + QR code)
6. Email/SMS sent to customer
7. Update service status to PAID
```

**Database consistency:**
- Payments must be idempotent (use idempotency_key)
- Amount in both local currency and USD
- Cannot delete payment, only refund
- All payment state changes must be logged

#### 5. **Insurance System**

**Files:**
- `insurance/models.py` - Policies, claims, coverage
- `insurance/services.py` - Claims processing
- `insurance/payment_service.py` - Insurance payments

**Flow:**
```
Patient:
1. Links insurance policy to account
2. Service is provided
3. Submits claim with documents
4. Pays copay/deductible
5. Insurance processes claim
6. Receives reimbursement

Insurance Agent:
1. Reviews submitted claims
2. Verifies coverage
3. Approves/rejects claim
4. Processes payment to provider
5. Updates claim status
```

#### 6. **Prescription System**

**Files:**
- `prescriptions/models.py` - Prescription data
- `prescriptions/services.py` - Prescription logic
- `prescriptions/tasks.py` - Background jobs (reminders)

**Flow:**
```
Doctor:
1. Creates prescription after consultation
2. Adds medications with dosage
3. Sets duration and refills
4. Sends electronically to pharmacy

Patient:
1. Receives prescription notification
2. Chooses pharmacy
3. Pharmacy fulfills prescription
4. Picks up medication

Pharmacy:
1. Receives electronic prescription
2. Checks inventory
3. Prepares medications
4. Notifies patient
5. Dispenses after payment
```

---

## 🐛 Common Tasks & Workflows

### Creating a New Feature

```bash
# 1. Create branch
git checkout develop
git pull origin develop
git checkout -b feature/123-new-feature

# 2. Create models (if needed)
# Edit app/models.py

# 3. Create migration
python manage.py makemigrations app_name --name descriptive_name

# 4. Review migration SQL (IMPORTANT!)
python manage.py sqlmigrate app_name 0001

# 5. Test migration on local
python manage.py migrate

# 6. Implement serializers
# Edit app/serializers.py

# 7. Implement services
# Edit app/services.py

# 8. Implement views
# Edit app/views.py

# 9. Add URLs
# Edit app/urls.py

# 10. Write tests
# Edit app/tests.py

# 11. Run tests
python manage.py test app_name

# 12. Manual testing
python manage.py runserver

# 13. Commit changes
git add .
git commit -m "feat(app): add new feature

- Detailed description
- What was changed
- Why it was changed

Closes #123"

# 14. Push and create PR
git push origin feature/123-new-feature
```

### Fixing Database Inconsistencies

```bash
# 1. Check for inconsistencies
python manage.py check

# 2. Check migrations
python manage.py showmigrations

# 3. If migrations out of sync
# DO NOT run makemigrations without team approval
# Contact team lead first

# 4. Check database state
python manage.py dbshell
# Then run SQL queries to inspect

# 5. Fix data issues with management command
# Create: core/management/commands/fix_data_issue.py

from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    help = 'Fix specific data issue'
    
    @transaction.atomic
    def handle(self, *args, **options):
        # Fix logic here
        pass

# 6. Run fix command
python manage.py fix_data_issue

# 7. Verify fix
python manage.py check
```

### Adding New Currency Support

```python
# 1. Edit currency_converter/models.py
# Add currency to CURRENCY_CHOICES

# 2. Create exchange rate
from currency_converter.models import ExchangeRate

ExchangeRate.objects.create(
    from_currency='XOF',
    to_currency='USD',
    rate=0.0017,  # Get current rate
    source='CENTRAL_BANK'
)

# 3. Update conversion service
# currency_converter/services.py already handles this

# 4. Test conversion
from currency_converter.services import CurrencyConverter

converter = CurrencyConverter()
usd_amount = converter.convert(1000, 'XOF', 'USD')
print(usd_amount)  # Should be ~1.70
```

### Debugging Common Issues

**Issue: "Unable to connect to database"**
```bash
# Check database is running
# Check .env file has correct credentials
# Test connection:
python manage.py dbshell
```

**Issue: "Migration conflicts"**
```bash
# Show migrations
python manage.py showmigrations

# Merge migrations (with team lead approval)
python manage.py makemigrations --merge
```

**Issue: "ImportError or ModuleNotFoundError"**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Check virtual environment is activated
which python  # Should show venv path
```

**Issue: "OperationalError: relation does not exist"**
```bash
# Run migrations
python manage.py migrate

# If still failing, check database directly
python manage.py dbshell
\dt  # List all tables
```

---

## 🔐 Security Best Practices (CRITICAL)

### NEVER Commit Sensitive Data

**Absolutely forbidden to commit:**
- ❌ Database passwords
- ❌ API keys (FedaPay, SendGrid, Twilio, etc.)
- ❌ SECRET_KEY
- ❌ JWT signing keys
- ❌ OAuth credentials
- ❌ Email/SMS service credentials
- ❌ Third-party service tokens
- ❌ Encryption keys
- ❌ Any `.env` file

### How to Handle Credentials

```python
# ✅ CORRECT - Use environment variables
from decouple import config

SECRET_KEY = config('SECRET_KEY')
DATABASE_PASSWORD = config('DB_PASSWORD')
FEDAPAY_API_KEY = config('FEDAPAY_API_KEY')

# ❌ WRONG - Hardcoded credentials
SECRET_KEY = 'my-secret-key-12345'  # NEVER DO THIS!
DATABASE_PASSWORD = 'password123'   # NEVER DO THIS!
```

### .gitignore Requirements

Ensure these are in `.gitignore`:
```
.env
.env.local
.env.production
*.key
*.pem
secrets/
credentials/
```

### If You Accidentally Commit Credentials

1. **DO NOT** just delete the file and commit again
2. **Immediately** notify the project owner
3. Credentials must be rotated/changed
4. Use `git filter-branch` or BFG Repo-Cleaner to remove from history
5. Force push to remote (requires team lead approval)

### Requesting Credentials

**To get development credentials:**
1. Contact project owner via email (not public channels)
2. Never request credentials in GitHub issues or comments
3. Never send credentials via unencrypted channels
4. Store credentials securely (password manager recommended)

---

## 📝 Documentation Standards

### Code Documentation

```python
def process_payment(payment_data: dict, idempotency_key: str) -> Payment:
    """
    Process a payment transaction with idempotency guarantee.
    
    Args:
        payment_data (dict): Payment information
            - amount (Decimal): Amount in USD
            - currency (str): Original currency code
            - payment_method (str): 'CASH', 'MOBILE_MONEY', 'INSURANCE'
            - participant_id (UUID): Payer identifier
        idempotency_key (str): Unique key to prevent duplicate charges
    
    Returns:
        Payment: Created or existing payment object
    
    Raises:
        ValidationError: If payment_data is invalid
        InsufficientFundsError: If mobile money payment fails
        
    Example:
        >>> payment_data = {
        ...     'amount': Decimal('50.00'),
        ...     'currency': 'USD',
        ...     'payment_method': 'CASH',
        ...     'participant_id': patient.id
        ... }
        >>> payment = process_payment(payment_data, 'unique-key-123')
    """
    pass
```

### API Documentation

We use **drf-spectacular** for automatic API documentation.

```python
from drf_spectacular.utils import extend_schema, OpenApiParameter

@extend_schema(
    summary="Create appointment",
    description="Book a new medical appointment with a doctor",
    parameters=[
        OpenApiParameter(
            name='doctor_id',
            type=str,
            description='UUID of the doctor'
        ),
    ],
    responses={
        201: AppointmentSerializer,
        400: "Validation error",
        409: "Time slot conflict"
    }
)
@api_view(['POST'])
def create_appointment(request):
    pass
```

---

## 🚨 Emergency Procedures

### Production Hotfix

```bash
# 1. Create hotfix branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# 2. Fix the issue
# 3. Test thoroughly
# 4. Commit
git commit -m "hotfix: fix critical production bug"

# 5. Merge to main AND develop
git checkout main
git merge hotfix/critical-bug-fix
git push origin main

git checkout develop
git merge hotfix/critical-bug-fix
git push origin develop

# 6. Delete hotfix branch
git branch -d hotfix/critical-bug-fix
git push origin --delete hotfix/critical-bug-fix

# 7. Notify team
```

### Rollback Procedure

```bash
# 1. Identify last good commit
git log

# 2. Revert specific commit
git revert <commit-hash>

# 3. Or reset to previous state (DANGEROUS!)
git reset --hard <commit-hash>
git push origin develop --force

# 4. Or rollback migration
python manage.py migrate app_name 0004  # Rollback to migration 0004
```

---

## 📚 Additional Resources

- **API Documentation:** http://localhost:8000/api/docs/
- **Admin Panel:** http://localhost:8000/admin/
- **Issue Tracker:** GitHub Issues

---

## ❓ Getting Help

1. **Check this documentation first**
2. **Search existing GitHub issues**
3. **Ask in team chat**
4. **Create detailed GitHub issue with:**
   - What you're trying to do
   - What you expected
   - What actually happened
   - Error messages (full traceback)
   - Your environment details
   - Steps to reproduce

---

# PARTICIPANT ROLE SYSTEM - COMPLETE ARCHITECTURE

## Date: 2025-12-27
## Status: ✅ CORRECTED AND CONSISTENT

---

## Core Principle

**The system uses `Participant` model with `participant.role` and `participant.uid`**

❌ **NEVER use**: `user` namespace, `provider` namespace  
✅ **ALWAYS use**: `participant` with explicit `role`

---

## Role Architecture

### 1. **Primary Roles** (`Participant.role`)

```python
ROLE_CHOICES = [
    ("patient", "Patient"),                          # ✅ Service consumer
    ("doctor", "Doctor"),                            # ✅ Independent doctor
    ("hospital", "Hospital"),                        # ✅ Hospital organization
    ("pharmacy", "Pharmacy"),                        # ✅ Pharmacy organization
    ("insurance_company", "Insurance Company"),      # ✅ Insurance organization
    ("admin", "Admin"),                              # ✅ Platform admin
    ("super_admin", "Super Admin"),                  # ✅ Platform super admin
    
    # ⚠️ DEPRECATED - Do NOT use these:
    ("hospital_staff", "Hospital Staff"),            # ❌ Use role='hospital' + staff_role
    ("pharmacy_staff", "Pharmacy Staff"),            # ❌ Use role='pharmacy' + staff_role
    ("insurance_company_staff", "Insurance Staff"),  # ❌ Use role='insurance_company' + staff_role
]
```

### 2. **Staff Roles** (`Participant.staff_role`)

Used to differentiate staff members from organization owners:

```python
STAFF_ROLE_CHOICES = [
    # Hospital staff roles
    ("doctor", "Doctor"),
    ("nurse", "Nurse"),
    ("receptionist", "Receptionist"),
    ("lab_technician", "Lab Technician"),
    ("administrator", "Administrator"),
    
    # Pharmacy staff roles
    ("pharmacist", "Pharmacist"),
    ("cashier", "Cashier"),
    ("inventory_clerk", "Inventory Clerk"),
    ("delivery_person", "Delivery Person"),
    ("manager", "Manager"),
    
    # Insurance company staff roles
    ("claims_processor", "Claims Processor"),
    ("underwriter", "Underwriter"),
    ("customer_service", "Customer Service"),
]
```

---

## Participant Types

### **Type 1: Service Consumers**
```python
# Patient
Participant {
    uid: UUID,
    role: "patient",
    staff_role: None,
    affiliated_provider_id: None
}

# Independent Doctor (not employed by hospital)
Participant {
    uid: UUID,
    role: "doctor",
    staff_role: None,
    affiliated_provider_id: None
}
```

### **Type 2: Service Providers (Organizations)**
```python
# Hospital Owner
Participant {
    uid: UUID,
    role: "hospital",
    staff_role: None,
    affiliated_provider_id: None
}

# Pharmacy Owner
Participant {
    uid: UUID,
    role: "pharmacy",
    staff_role: None,
    affiliated_provider_id: None
}

# Insurance Company Owner
Participant {
    uid: UUID,
    role: "insurance_company",
    staff_role: None,
    affiliated_provider_id: None
}
```

### **Type 3: Staff Members (Employees)**

#### Hospital Staff
```python
# Example: Hospital Nurse
Participant {
    uid: UUID,
    role: "hospital",                    # Same as owner!
    staff_role: "nurse",                 # Differentiates from owner
    affiliated_provider_id: <hospital_uid>,  # Links to employer
    employee_id: "EMP-NUR-123456"
}

# Example: Hospital Doctor (employed)
Participant {
    uid: UUID,
    role: "hospital",                    # Use hospital, not doctor
    staff_role: "doctor",                # Job role
    affiliated_provider_id: <hospital_uid>
}
```

#### Pharmacy Staff
```python
# Example: Pharmacy Cashier
Participant {
    uid: UUID,
    role: "pharmacy",                    # Same as owner!
    staff_role: "cashier",               # Differentiates from owner
    affiliated_provider_id: <pharmacy_uid>,  # Links to employer
    employee_id: "EMP-CAS-789012"
}
```

#### Insurance Staff
```python
# Example: Claims Processor
Participant {
    uid: UUID,
    role: "insurance_company",           # Same as owner!
    staff_role: "claims_processor",      # Differentiates from owner
    affiliated_provider_id: <insurance_uid>, # Links to employer
    employee_id: "EMP-CLM-345678"
}
```

---

## Three-Field System for Staff

**Every staff member MUST have all three fields set:**

1. ✅ `role` = Provider's role (hospital/pharmacy/insurance_company)
2. ✅ `staff_role` = Job role (nurse/cashier/claims_processor)
3. ✅ `affiliated_provider_id` = UUID of the employing organization

**Owner vs Staff Differentiation:**
- **Owner**: Has `role`, NO `staff_role`, NO `affiliated_provider_id`
- **Staff**: Has `role`, HAS `staff_role`, HAS `affiliated_provider_id`

---

## Staff Relationship Models

### HospitalStaff Model
```python
class HospitalStaff:
    staff_participant = ForeignKey(Participant)  # The employee
    hospital = ForeignKey(Participant)           # The hospital owner
    role = CharField()                           # Job role (from STAFF_ROLE_CHOICES)
    # Permissions...
```

### PharmacyStaff Model
```python
class PharmacyStaff:
    staff_participant = ForeignKey(Participant)  # The employee
    pharmacy = ForeignKey(Participant)           # The pharmacy owner
    role = CharField()                           # Job role
    # Permissions...
```

### InsuranceStaff Model
```python
class InsuranceStaff:
    staff_participant = ForeignKey(Participant)     # The employee
    insurance_company = ForeignKey(Participant)     # The insurance company owner
    staff_role = CharField()                        # Job role
    # Permissions...
```

---

## Authentication and Redirects

### Login Flow

```python
def redirect_to_dashboard(user):  # user is Participant instance
    user_role = user.role.lower()
    
    # Check if staff (has staff_role + affiliated_provider_id)
    if user.staff_role and user.affiliated_provider_id:
        # This is a STAFF MEMBER
        if user_role == "hospital":
            # Hospital staff - redirect based on staff_role
            return redirect(f"/hospital/staff/{user.staff_role}/dashboard/")
        
        elif user_role == "pharmacy":
            # Pharmacy staff - all go to counter
            return redirect("/pharmacy/staff/counter/")
        
        elif user_role == "insurance_company":
            # Insurance staff
            return redirect("/insurance/staff/dashboard/")
    
    # Not staff - redirect based on main role
    role_map = {
        "patient": "/patient/dashboard/",
        "doctor": "/doctor/dashboard/",
        "hospital": "/hospital/dashboard/",      # Hospital OWNER
        "pharmacy": "/pharmacy/dashboard/",      # Pharmacy OWNER
        "insurance_company": "/insurance/dashboard/",  # Insurance OWNER
    }
    return redirect(role_map.get(user_role, "/patient/dashboard/"))
```

### Access Control Patterns

```python
# View-level check
@login_required
def staff_only_view(request):
    participant = request.user  # request.user IS Participant instance
    
    # Check if staff (not owner)
    if not participant.staff_role or not participant.affiliated_provider_id:
        return redirect('/')  # Not staff
    
    # Staff logic here...

# Owner-only check
@login_required
def owner_only_view(request):
    participant = request.user
    
    # Check if owner (not staff)
    if participant.staff_role:
        return redirect('/')  # Has staff_role = is staff, not owner
    
    # Owner logic here...
```

---

## Database Queries

### Get All Staff for a Provider

```python
# Get all hospital staff
hospital = Participant.objects.get(uid=hospital_uid, role='hospital')
staff_members = Participant.objects.filter(
    role='hospital',
    affiliated_provider_id=hospital.uid,
    staff_role__isnull=False
)

# Get all pharmacy staff
pharmacy = Participant.objects.get(uid=pharmacy_uid, role='pharmacy')
staff_members = Participant.objects.filter(
    role='pharmacy',
    affiliated_provider_id=pharmacy.uid,
    staff_role__isnull=False
)
```

### Get Provider for Staff Member

```python
# Get hospital for staff member
staff = Participant.objects.get(uid=staff_uid)
if staff.staff_role and staff.affiliated_provider_id:
    hospital = Participant.objects.get(uid=staff.affiliated_provider_id)
```

### Helper Function for ViewSets

```python
def get_provider_id_for_participant(participant):
    """
    Returns provider ID for queries.
    - For staff: returns affiliated_provider_id
    - For owner: returns participant.uid
    """
    if participant.staff_role and participant.affiliated_provider_id:
        return participant.affiliated_provider_id  # Staff
    return participant.uid  # Owner
```

---

## Common Patterns

### Creating Staff Member

```python
# Hospital staff creation
staff_participant = Participant.objects.create(
    email='nurse@example.com',
    role='hospital',                          # NOT 'hospital_staff'
    staff_role='nurse',                       # Job role
    affiliated_provider_id=hospital.uid,      # Link to hospital
    employee_id='EMP-NUR-123456',
    is_active=True
)

HospitalStaff.objects.create(
    staff_participant=staff_participant,
    hospital=hospital,
    role='nurse',
    # permissions...
)
```

### Checking Staff vs Owner

```python
def is_staff(participant):
    """Check if participant is a staff member"""
    return bool(participant.staff_role and participant.affiliated_provider_id)

def is_owner(participant):
    """Check if participant is an organization owner"""
    return participant.role in ['hospital', 'pharmacy', 'insurance_company'] and not participant.staff_role
```

---

## Migration from Old System

If you have existing data with deprecated roles:

```python
# Migrate hospital_staff to hospital + staff_role
Participant.objects.filter(role='hospital_staff').update(role='hospital')

# Migrate pharmacy_staff to pharmacy + staff_role
Participant.objects.filter(role='pharmacy_staff').update(role='pharmacy')

# Migrate insurance_company_staff to insurance_company + staff_role
Participant.objects.filter(role='insurance_company_staff').update(role='insurance_company')
```

---

## Summary

### ✅ Correct Approach
```python
# Owner
participant.role = 'pharmacy'
participant.staff_role = None
participant.affiliated_provider_id = None

# Staff
participant.role = 'pharmacy'
participant.staff_role = 'cashier'
participant.affiliated_provider_id = <pharmacy_uuid>
```

### ❌ Deprecated Approach
```python
# Old way - DO NOT USE
participant.role = 'pharmacy_staff'  # Wrong!
```

### 🎯 Golden Rules

1. **Same base `role`** for owners and their staff
2. **Differentiate with `staff_role`** field
3. **Link with `affiliated_provider_id`**
4. **Use `participant.uid`** for identification
5. **Never use `user` or `provider` namespace**

---

**The system is now consistent and follows proper namespace conventions!** ✅

----

# Participant Role Task List
## Clear Task Lists for Each Module Flow

**Project:** BintaCura Healthcare Platform  
**Purpose:** Quick reference for developers working on different participant flows  
**Last Updated:** December 27, 2024

---

## 🎯 Overview

BintaCura uses a single unified user model (`Participant`) with role-based access control. Each role has specific responsibilities and workflows.

---

## 👤 Participant Roles

| Role | Code | Primary Module | Description |
|------|------|----------------|-------------|
| Patient | `PATIENT` | patient, appointments | End users seeking healthcare |
| Doctor | `DOCTOR` | doctor, appointments | Medical professionals |
| Hospital Admin | `HOSPITAL_ADMIN` | hospital, hr | Hospital management staff |
| Pharmacy Staff | `PHARMACY_STAFF` | pharmacy | Pharmacy counter staff |
| Pharmacy Manager | `PHARMACY_MANAGER` | pharmacy | Pharmacy management |
| Insurance Agent | `INSURANCE_AGENT` | insurance | Insurance company staff |
| Transport Driver | `TRANSPORT_DRIVER` | transport | Ambulance drivers |
| Finance Staff | `FINANCE_STAFF` | financial, payments | Financial operations |
| HR Staff | `HR_STAFF` | hr | Human resources |
| Superuser | `SUPERUSER` | All | System administrator (cloud only) |

---

## 📋 Task Lists by Role

### 1. PATIENT Tasks

#### Core Files:
- `patient/models.py` - Patient profile
- `patient/views.py` - Patient operations
- `appointments/views.py` - Appointment booking
- `payments/views.py` - Payment processing
- `health_records/views.py` - Medical records

#### User Stories & Tasks:

**Registration & Profile** ✅
- [ ] Register new account
- [ ] Verify email/phone
- [ ] Complete profile (medical history, allergies, emergency contact)
- [ ] Upload profile photo
- [ ] Link family members as dependents

**Appointment Booking** ✅
- [ ] Search doctors by specialty/location
- [ ] View doctor profiles and ratings
- [ ] Check available time slots
- [ ] Book appointment (in-person or telemedicine)
- [ ] Select appointment type (consultation, follow-up, emergency)
- [ ] Receive confirmation (email/SMS)
- [ ] Make payment (cash/mobile money/insurance)

**Before Appointment**
- [ ] View upcoming appointments
- [ ] Upload relevant documents (test results, previous prescriptions)
- [ ] Fill pre-consultation forms
- [ ] Request appointment rescheduling
- [ ] Cancel appointment (with valid reason)

**During Appointment**
- [ ] Check-in at hospital reception
- [ ] Join telemedicine video call (if virtual)
- [ ] Share symptoms and concerns
- [ ] Receive diagnosis
- [ ] Get prescription

**After Appointment**
- [ ] View consultation notes
- [ ] Download prescription
- [ ] Rate doctor
- [ ] Schedule follow-up if needed
- [ ] Access medical records

**Pharmacy Interaction**
- [ ] Find nearby pharmacies
- [ ] Upload prescription
- [ ] Check medication availability
- [ ] Order medications
- [ ] Choose delivery or pickup
- [ ] Make payment
- [ ] Track order status
- [ ] Receive medications

**Health Records Management**
- [ ] View complete medical history
- [ ] Access lab test results
- [ ] View imaging reports (X-rays, MRI, CT scans)
- [ ] Download health records (PDF)
- [ ] Share records with doctors
- [ ] Upload external documents

**Payments & Billing**
- [ ] View payment history
- [ ] Download invoices/receipts
- [ ] Set up payment methods (mobile money, bank)
- [ ] Submit insurance claims
- [ ] Track claim status
- [ ] View outstanding balances

**Inconsistencies to Watch:**
- ⚠️ Appointment status not updating after payment
- ⚠️ Duplicate appointments if user clicks "Book" multiple times
- ⚠️ Prescription not linking to appointment
- ⚠️ Payment confirmation delay

**Database Operations:**
```python
# Create patient account
participant = Participant.objects.create_user(
    email='patient@example.com',
    role='PATIENT',
    ...
)
patient_profile = Patient.objects.create(
    participant=participant,
    blood_group='O+',
    allergies=['Penicillin'],
    ...
)

# Book appointment (MUST be atomic)
@transaction.atomic
def book_appointment(patient, doctor, appointment_date):
    # Check availability
    if not doctor.is_available(appointment_date):
        raise ValidationError("Doctor not available")
    
    # Create appointment
    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        appointment_date=appointment_date,
        status='SCHEDULED',
        instance_id=settings.INSTANCE_ID
    )
    
    # Create payment record
    payment = Payment.objects.create(
        appointment=appointment,
        amount_usd=doctor.consultation_fee_usd,
        status='PENDING',
        idempotency_key=generate_idempotency_key()
    )
    
    return appointment
```

---

### 2. DOCTOR Tasks

#### Core Files:
- `doctor/models.py` - Doctor profile and services
- `appointments/views.py` - Appointment management
- `prescriptions/models.py` - Prescription writing
- `health_records/views.py` - Patient records access

#### User Stories & Tasks:

**Profile Management** ✅
- [ ] Complete professional profile
- [ ] Add specializations
- [ ] Upload credentials (license, certificates)
- [ ] Set consultation fees (different rates for appointment types)
- [ ] Link to affiliated hospitals
- [ ] Add biography and experience
- [ ] Upload professional photo

**Availability Management** ✅
- [ ] Set weekly schedule (recurring availability)
- [ ] Block specific dates (vacation, conferences)
- [ ] Set different schedules for different hospitals
- [ ] Configure appointment duration (15min, 30min, 1hr)
- [ ] Enable/disable telemedicine
- [ ] Set maximum daily appointments

**Appointment Management** ✅
- [ ] View daily schedule
- [ ] Receive new appointment notifications
- [ ] Access patient medical history before appointment
- [ ] Start consultation
- [ ] Join telemedicine video call
- [ ] Take consultation notes
- [ ] Update appointment status (in_progress, completed, cancelled)

**During Consultation**
- [ ] Review patient symptoms
- [ ] Access previous consultations
- [ ] View lab results and imaging
- [ ] Record diagnosis
- [ ] Write prescription
- [ ] Order lab tests
- [ ] Request imaging (X-ray, CT, MRI)
- [ ] Refer to specialist if needed
- [ ] Schedule follow-up appointment

**Prescription Writing** ✅
- [ ] Search medications from database
- [ ] Add medication with dosage instructions
- [ ] Set duration (7 days, 14 days, 30 days)
- [ ] Allow refills
- [ ] Add special instructions
- [ ] Send prescription electronically to pharmacy
- [ ] Print prescription

**Patient Records**
- [ ] Add consultation notes
- [ ] Update diagnosis
- [ ] View patient health trends
- [ ] Add to patient allergies list
- [ ] Mark patient as high-risk
- [ ] Export patient summary

**Financial Management**
- [ ] View earnings summary
- [ ] Track appointments completed
- [ ] Request payout
- [ ] View payment history
- [ ] Export financial reports

**Inconsistencies to Watch:**
- ⚠️ Availability slots not blocking after appointment booked
- ⚠️ Prescription not saving all medications
- ⚠️ Telemedicine link not generating
- ⚠️ Patient history showing wrong patient data (CRITICAL!)

**Database Operations:**
```python
# Create prescription (MUST be atomic and linked to appointment)
@transaction.atomic
def create_prescription(doctor, patient, appointment, medications):
    prescription = Prescription.objects.create(
        doctor=doctor,
        patient=patient,
        appointment=appointment,
        diagnosis=appointment.diagnosis,
        instance_id=settings.INSTANCE_ID
    )
    
    for med_data in medications:
        PrescriptionItem.objects.create(
            prescription=prescription,
            medication_id=med_data['medication_id'],
            dosage=med_data['dosage'],
            frequency=med_data['frequency'],
            duration_days=med_data['duration_days'],
            instructions=med_data['instructions']
        )
    
    # Notify patient
    send_prescription_notification(patient, prescription)
    
    return prescription
```

---

### 3. PHARMACY_STAFF Tasks

#### Core Files:
- `pharmacy/models.py` - Inventory, orders, counters
- `pharmacy/counter_views.py` - Counter operations
- `pharmacy/payment_service.py` - Payment processing
- `prescriptions/models.py` - Prescription fulfillment

#### User Stories & Tasks:

**Login & Counter Assignment** ✅
- [ ] Login to system
- [ ] Select/assign to counter
- [ ] Open cash register for shift
- [ ] Set starting cash amount
- [ ] View counter status

**Customer Service**
- [ ] Greet customer
- [ ] Scan prescription QR code (if electronic)
- [ ] Manually enter prescription (if paper)
- [ ] Verify prescription validity
- [ ] Check prescription not already fulfilled
- [ ] Verify doctor signature/license

**Order Creation** ✅
- [ ] Create new pharmacy order
- [ ] Link to prescription (if applicable)
- [ ] Search medications in inventory
- [ ] Check medication availability
- [ ] Add items to order
- [ ] Calculate total amount
- [ ] Apply discounts (if any)
- [ ] Check insurance coverage (if applicable)

**Inventory Check** ✅ (CRITICAL: Must prevent race conditions)
- [ ] Lock inventory items with `select_for_update()`
- [ ] Verify sufficient stock
- [ ] Reserve items for order
- [ ] Show alternatives if out of stock
- [ ] Notify manager if low stock

**Payment Processing** ✅
- [ ] Select payment method (cash, mobile money, insurance)
- [ ] Process cash payment
- [ ] Process mobile money payment
- [ ] Process insurance payment (copay/deductible)
- [ ] Handle split payments (cash + insurance)
- [ ] Generate receipt with QR code
- [ ] Print receipt
- [ ] Send receipt via email/SMS

**Dispensing Medications** ✅
- [ ] Verify payment completed
- [ ] Dispense medications
- [ ] Provide dosage instructions
- [ ] Counsel patient on usage
- [ ] Warn about side effects
- [ ] Check for drug interactions
- [ ] Mark prescription as fulfilled
- [ ] Update inventory (ATOMIC!)

**End of Shift**
- [ ] Close cash register
- [ ] Count cash
- [ ] Record closing amount
- [ ] Submit shift report
- [ ] Resolve discrepancies

**Inconsistencies to Watch:**
- ⚠️ Inventory going negative (CRITICAL!)
- ⚠️ Same item dispensed twice from different counters
- ⚠️ Payment not linking to order
- ⚠️ Receipt not generating
- ⚠️ Prescription fulfilled but inventory not updated

**Database Operations:**
```python
# Process pharmacy sale (MUST be ATOMIC and use locks)
@transaction.atomic
def process_pharmacy_sale(counter, prescription, items, payment_data):
    # CRITICAL: Lock inventory to prevent race conditions
    medication_ids = [item['medication_id'] for item in items]
    inventory_items = PharmacyInventory.objects.select_for_update().filter(
        pharmacy=counter.pharmacy,
        medication_id__in=medication_ids
    )
    
    # Verify stock availability
    inventory_dict = {inv.medication_id: inv for inv in inventory_items}
    for item in items:
        inventory = inventory_dict.get(item['medication_id'])
        if not inventory or inventory.quantity < item['quantity']:
            raise ValidationError(f"Insufficient stock for {item['medication_name']}")
    
    # Create order
    order = PharmacyOrder.objects.create(
        pharmacy=counter.pharmacy,
        counter=counter,
        prescription=prescription,
        served_by=counter.current_staff,
        total_amount_usd=calculate_total(items),
        status='PENDING',
        instance_id=settings.INSTANCE_ID
    )
    
    # Add order items
    for item in items:
        PharmacyOrderItem.objects.create(
            order=order,
            medication_id=item['medication_id'],
            quantity=item['quantity'],
            unit_price_usd=item['unit_price_usd']
        )
    
    # Process payment (with idempotency)
    payment = process_payment(
        order=order,
        payment_data=payment_data,
        idempotency_key=generate_idempotency_key()
    )
    
    # Update inventory (CRITICAL: Still inside transaction)
    for item in items:
        inventory = inventory_dict[item['medication_id']]
        inventory.quantity -= item['quantity']
        inventory.save()
        
        # Create stock movement record
        PharmacyStockMovement.objects.create(
            pharmacy=counter.pharmacy,
            medication_id=item['medication_id'],
            movement_type='SALE',
            quantity=-item['quantity'],
            order=order
        )
    
    # Mark prescription as fulfilled
    if prescription:
        prescription.status = 'FULFILLED'
        prescription.fulfilled_at = timezone.now()
        prescription.fulfilled_by = counter.current_staff
        prescription.save()
    
    # Update cash register
    if payment_data['method'] == 'CASH':
        counter.cash_register.current_balance += payment.amount_usd
        counter.cash_register.save()
    
    return order, payment
```

---

### 4. PHARMACY_MANAGER Tasks

#### Core Files:
- `pharmacy/models.py` - Pharmacy management
- `pharmacy/views.py` - Manager operations
- `hr/models.py` - Staff management

#### Tasks:

**Inventory Management** ✅
- [ ] Add new medications to inventory
- [ ] Set medication prices
- [ ] Update stock quantities
- [ ] Set reorder levels (low stock alerts)
- [ ] Create purchase orders to suppliers
- [ ] Receive and record deliveries
- [ ] Handle expired medications
- [ ] Perform stock audits

**Staff Management**
- [ ] Add pharmacy staff
- [ ] Assign staff to counters
- [ ] Set staff schedules
- [ ] View staff performance
- [ ] Handle staff permissions

**Counter Management** ✅
- [ ] Create/edit counters
- [ ] Assign cash registers
- [ ] View counter sales
- [ ] Reconcile cash registers
- [ ] Handle discrepancies

**Sales Reports**
- [ ] Daily sales report
- [ ] Monthly revenue report
- [ ] Top-selling medications
- [ ] Slow-moving stock
- [ ] Payment method breakdown
- [ ] Staff performance metrics

**Financial Operations**
- [ ] View total revenue
- [ ] Track expenses
- [ ] Generate profit/loss reports
- [ ] Handle refunds
- [ ] Manage discounts

---

### 5. HOSPITAL_ADMIN Tasks

#### Core Files:
- `hospital/models.py` - Hospital management
- `doctor/models.py` - Doctor affiliations
- `hr/models.py` - Staff management
- `appointments/views.py` - Appointment oversight

#### Tasks:

**Hospital Setup**
- [ ] Configure hospital profile
- [ ] Add departments
- [ ] Set operating hours
- [ ] Configure services offered
- [ ] Set consultation fees

**Doctor Management**
- [ ] Onboard new doctors
- [ ] Verify credentials
- [ ] Assign to departments
- [ ] Set doctor schedules
- [ ] Monitor doctor performance

**Staff Management**
- [ ] Add hospital staff (nurses, receptionists, etc.)
- [ ] Assign roles and permissions
- [ ] Manage staff schedules
- [ ] View staff attendance

**Bed Management**
- [ ] Add/edit bed records
- [ ] Assign beds to patients
- [ ] Track bed occupancy
- [ ] Mark beds for cleaning/maintenance

**Appointment Oversight**
- [ ] View all appointments
- [ ] Handle appointment conflicts
- [ ] Manage cancellations
- [ ] Override scheduling rules (emergency cases)

**Financial Reports**
- [ ] Daily revenue
- [ ] Doctor earnings
- [ ] Insurance claims
- [ ] Outstanding payments

---

### 6. INSURANCE_AGENT Tasks

#### Core Files:
- `insurance/models.py` - Policies and claims
- `insurance/services.py` - Claims processing
- `payments/views.py` - Payment processing

#### Tasks:

**Policy Management**
- [ ] Create insurance policies
- [ ] Set coverage details
- [ ] Define copay/deductible amounts
- [ ] Add covered services
- [ ] Link patients to policies

**Claims Processing**
- [ ] Review submitted claims
- [ ] Verify service eligibility
- [ ] Check policy coverage
- [ ] Request additional documents
- [ ] Approve/reject claims
- [ ] Calculate reimbursement amount
- [ ] Process payment to provider

**Provider Network**
- [ ] Add healthcare providers to network
- [ ] Set negotiated rates
- [ ] View provider claims history

---

## 🔍 Common Database Inconsistencies

### 1. **Inventory Going Negative** (CRITICAL!)
```python
# ❌ WRONG - Race condition
def dispense_medication(medication_id, quantity):
    inventory = PharmacyInventory.objects.get(medication_id=medication_id)
    # Another transaction could modify between get and save!
    inventory.quantity -= quantity
    inventory.save()

# ✅ CORRECT - Use select_for_update()
@transaction.atomic
def dispense_medication(medication_id, quantity):
    inventory = PharmacyInventory.objects.select_for_update().get(
        medication_id=medication_id
    )
    if inventory.quantity < quantity:
        raise ValidationError("Insufficient stock")
    inventory.quantity -= quantity
    inventory.save()
```

### 2. **Duplicate Payments**
```python
# ❌ WRONG - Can create duplicate payments
def process_payment(order_id, amount):
    return Payment.objects.create(order_id=order_id, amount=amount)

# ✅ CORRECT - Use idempotency key
def process_payment(order_id, amount, idempotency_key):
    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing
    return Payment.objects.create(
        order_id=order_id,
        amount=amount,
        idempotency_key=idempotency_key
    )
```

### 3. **Appointment Double Booking**
```python
# ✅ CORRECT - Check for conflicts before creating
@transaction.atomic
def book_appointment(doctor, appointment_date):
    existing = Appointment.objects.select_for_update().filter(
        doctor=doctor,
        appointment_date=appointment_date,
        status__in=['SCHEDULED', 'IN_PROGRESS']
    ).exists()
    
    if existing:
        raise ValidationError("Time slot already booked")
    
    return Appointment.objects.create(
        doctor=doctor,
        appointment_date=appointment_date,
        status='SCHEDULED'
    )
```

### 4. **Orphaned Records**
```python
# ✅ CORRECT - Use on_delete=PROTECT for critical relationships
class Payment(models.Model):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.PROTECT  # Cannot delete appointment with payment
    )

# ✅ CORRECT - Use soft delete with SyncMixin
class Appointment(SyncMixin):
    # SyncMixin provides deleted_at field
    pass

def delete_appointment(appointment_id):
    appointment = Appointment.objects.get(id=appointment_id)
    appointment.deleted_at = timezone.now()
    appointment.save()
```

---

## 🛠️ Developer Setup Checklist

### For Each New Developer:

- [ ] Install Python 3.10+
- [ ] Install PostgreSQL client tools
- [ ] Install Redis (for local testing)
- [ ] Install Node.js 16+
- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Receive `.env` file from team lead
- [ ] Test database connection
- [ ] Read CONTRIBUTING.md
- [ ] Understand ACID compliance requirements
- [ ] Understand SyncMixin usage
- [ ] Setup IDE (VS Code/PyCharm)
- [ ] Run development server
- [ ] Create test superuser (if INSTANCE_TYPE=CLOUD)

---

## 📞 Getting Help

**Stuck on a task?**
1. Check CONTRIBUTING.md
2. Search GitHub issues
3. Ask in team chat
4. Create detailed GitHub issue

**Database inconsistency found?**
1. Document the issue with examples
2. Create GitHub issue with "bug" label
3. DO NOT attempt to fix migrations without approval
4. Contact team lead immediately

---

**Last Updated:** December 27, 2024  
**Maintained By:** BintaCura Development Team


**Last Updated:** December 27, 2024
**Maintained By:** BintaCura Development Team
