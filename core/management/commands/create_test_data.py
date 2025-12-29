"""
Management command to create comprehensive test data for BintaCura.
Creates test users with dual roles (doctor+hospital staff, pharmacist+hospital staff),
departments, services, staff, and sample data for all participants.

Usage: python manage.py create_test_data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random

from core.models import Participant, Department
from doctor.models import DoctorData, DoctorAffiliation, DoctorService
from hospital.models import HospitalStaff, Bed, Department as HospitalDepartment
from pharmacy.models import PharmacyInventory, PharmacyStaff
from insurance.models import InsurancePackage, InsuranceStaff
from hr.models import Employee, Department as HRDepartment


class Command(BaseCommand):
    help = 'Create comprehensive test data for all participants'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Delete existing test data before creating new',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting test data creation...'))

        if options['clean']:
            self.clean_test_data()

        # Create participants
        hospital = self.create_test_hospital()
        pharmacy = self.create_test_pharmacy()
        insurance = self.create_test_insurance()

        # Create departments
        departments = self.create_hospital_departments(hospital)

        # Create dual-role users
        doctor_staff = self.create_doctor_hospital_staff(hospital, departments[0])
        pharmacist_staff = self.create_pharmacist_hospital_staff(hospital, departments[0])

        # Create additional test data
        self.create_hospital_beds(hospital, departments)
        self.create_hospital_staff(hospital, departments)
        self.create_doctor_services(doctor_staff)
        self.create_pharmacy_inventory(pharmacy)
        self.create_pharmacy_staff(pharmacy)
        self.create_insurance_packages(insurance)
        self.create_insurance_staff(insurance)

        self.stdout.write(self.style.SUCCESS('\n' + '='*70))
        self.stdout.write(self.style.SUCCESS('[SUCCESS] Test data created successfully!'))
        self.stdout.write(self.style.SUCCESS('='*70))
        self.stdout.write(self.style.SUCCESS('\n TEST ACCOUNTS CREATED:\n'))
        self.stdout.write(self.style.WARNING('1. Doctor + Hospital Staff (Dual Role):'))
        self.stdout.write(f'   Email: dr.staff@test.com')
        self.stdout.write(f'   Password: test123')
        self.stdout.write(f'   Role: Doctor (can also access hospital staff features)')
        self.stdout.write(self.style.WARNING('\n2. Pharmacist + Hospital Staff (Dual Role):'))
        self.stdout.write(f'   Email: pharm.staff@test.com')
        self.stdout.write(f'   Password: test123')
        self.stdout.write(f'   Role: Pharmacist (hospital pharmacy staff)')
        self.stdout.write(self.style.WARNING('\n3. Test Hospital:'))
        self.stdout.write(f'   Email: test.hospital@bintacura.com')
        self.stdout.write(f'   Password: test123')
        self.stdout.write(self.style.WARNING('\n4. Test Pharmacy:'))
        self.stdout.write(f'   Email: test.pharmacy@bintacura.com')
        self.stdout.write(f'   Password: test123')
        self.stdout.write(self.style.WARNING('\n5. Test Insurance:'))
        self.stdout.write(f'   Email: test.insurance@bintacura.com')
        self.stdout.write(f'   Password: test123')
        self.stdout.write(self.style.SUCCESS('\n' + '='*70 + '\n'))

    def clean_test_data(self):
        """Delete existing test data"""
        self.stdout.write('Cleaning existing test data...')

        # Delete test participants (cascade will handle related objects)
        Participant.objects.filter(email__contains='@test.com').delete()
        Participant.objects.filter(email__contains='test.hospital@bintacura.com').delete()
        Participant.objects.filter(email__contains='test.pharmacy@bintacura.com').delete()
        Participant.objects.filter(email__contains='test.insurance@bintacura.com').delete()

        self.stdout.write(self.style.SUCCESS('[OK] Cleaned existing test data'))

    def create_test_hospital(self):
        """Create a test hospital"""
        self.stdout.write('Creating test hospital...')

        hospital, created = Participant.objects.get_or_create(
            email='test.hospital@bintacura.com',
            defaults={
                'full_name': 'BintaCura Test Hospital',
                'role': 'hospital',
                'phone_number': '+22501234567',
                'password': make_password('test123'),
                'is_email_verified': True,
                'is_active': True,
                'address': '123 Medical Center Drive',
                'city': 'Cotonou',
                'country': 'Benin',
                'preferred_currency': 'XOF',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created hospital: {hospital.full_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'[WARN] Hospital already exists: {hospital.full_name}'))

        return hospital

    def create_test_pharmacy(self):
        """Create a test pharmacy"""
        self.stdout.write('Creating test pharmacy...')

        pharmacy, created = Participant.objects.get_or_create(
            email='test.pharmacy@bintacura.com',
            defaults={
                'full_name': 'BintaCura Test Pharmacy',
                'role': 'pharmacy',
                'phone_number': '+22501234568',
                'password': make_password('test123'),
                'is_email_verified': True,
                'is_active': True,
                'address': '456 Pharmacy Lane',
                'city': 'Cotonou',
                'country': 'Benin',
                'preferred_currency': 'XOF',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created pharmacy: {pharmacy.full_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'[WARN] Pharmacy already exists: {pharmacy.full_name}'))

        return pharmacy

    def create_test_insurance(self):
        """Create a test insurance company"""
        self.stdout.write('Creating test insurance company...')

        insurance, created = Participant.objects.get_or_create(
            email='test.insurance@bintacura.com',
            defaults={
                'full_name': 'BintaCura Test Insurance',
                'role': 'insurance_company',
                'phone_number': '+22501234569',
                'password': make_password('test123'),
                'is_email_verified': True,
                'is_active': True,
                'address': '789 Insurance Plaza',
                'city': 'Cotonou',
                'country': 'Benin',
                'preferred_currency': 'XOF',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'[OK] Created insurance: {insurance.full_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'[WARN] Insurance already exists: {insurance.full_name}'))

        return insurance

    def create_hospital_departments(self, hospital):
        """Create hospital departments"""
        self.stdout.write('Creating hospital departments...')

        dept_data = [
            {'name': 'Emergency', 'name_fr': 'Urgences', 'code': 'EMG'},
            {'name': 'Cardiology', 'name_fr': 'Cardiologie', 'code': 'CARD'},
            {'name': 'Pediatrics', 'name_fr': 'Pédiatrie', 'code': 'PED'},
            {'name': 'Surgery', 'name_fr': 'Chirurgie', 'code': 'SURG'},
            {'name': 'ICU', 'name_fr': 'Soins Intensifs', 'code': 'ICU'},
        ]

        departments = []
        for data in dept_data:
            dept, created = Department.objects.get_or_create(
                hospital=hospital,
                code=data['code'],
                defaults={
                    'name': data['name'],
                    'description': f'{data["name"]} Department',
                }
            )
            departments.append(dept)

            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Created department: {dept.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'  [WARN] Department exists: {dept.name}'))

        return departments

    def create_doctor_hospital_staff(self, hospital, department):
        """Create a doctor who is also hospital staff"""
        self.stdout.write('Creating doctor + hospital staff (dual role)...')

        # Create doctor participant
        doctor, created = Participant.objects.get_or_create(
            email='dr.staff@test.com',
            defaults={
                'full_name': 'Dr. Jean-Baptiste Kouassi',
                'role': 'doctor',
                'phone_number': '+22501234570',
                'password': make_password('test123'),
                'is_email_verified': True,
                'is_active': True,
                'address': '10 Medical Plaza',
                'city': 'Cotonou',
                'country': 'Benin',
                'preferred_currency': 'XOF',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created doctor participant: {doctor.full_name}'))

            # Create doctor data
            DoctorData.objects.create(
                participant=doctor,
                specialization='cardiology',
                license_number='MD-TEST-001',
                years_of_experience=10,
                qualifications=['MD', 'Cardiology Board Certified'],
                consultation_fee=5000,  # 50 USD in cents
                bio='Experienced cardiologist specializing in interventional cardiology',
                languages_spoken=['French', 'English'],
                is_available_for_telemedicine=True,
            )
            self.stdout.write(self.style.SUCCESS('  [OK] Created doctor profile'))
        else:
            self.stdout.write(self.style.WARNING(f'  [WARN] Doctor exists: {doctor.full_name}'))

        # Create hospital staff affiliation
        staff, staff_created = HospitalStaff.objects.get_or_create(
            hospital=hospital,
            staff_participant=doctor,
            defaults={
                'full_name': doctor.full_name,
                'email': doctor.email,
                'phone_number': doctor.phone_number,
                'role': 'doctor',
                'department': department,
                'employment_type': 'full_time',
                'is_active': True,
                'can_admit_patients': True,
                'can_discharge_patients': True,
                'can_prescribe': True,
                'can_view_all_records': True,
            }
        )

        if staff_created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created hospital staff profile for doctor'))

            # Create doctor affiliation
            DoctorAffiliation.objects.create(
                doctor=doctor,
                hospital=hospital,
                is_primary=True,
                is_locked=True,  # Locked because created by hospital
                is_active=True,
                department_id=department.uid,
            )
            self.stdout.write(self.style.SUCCESS('  [OK] Created doctor-hospital affiliation'))
        else:
            self.stdout.write(self.style.WARNING('  [WARN] Hospital staff profile exists'))

        return doctor

    def create_pharmacist_hospital_staff(self, hospital, department):
        """Create a pharmacist who is hospital staff"""
        self.stdout.write('Creating pharmacist + hospital staff (dual role)...')

        # Create pharmacist participant
        pharmacist, created = Participant.objects.get_or_create(
            email='pharm.staff@test.com',
            defaults={
                'full_name': 'Marie Akou',
                'role': 'pharmacy',
                'phone_number': '+22501234571',
                'password': make_password('test123'),
                'is_email_verified': True,
                'is_active': True,
                'address': '20 Pharmacy Street',
                'city': 'Cotonou',
                'country': 'Benin',
                'preferred_currency': 'XOF',
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created pharmacist participant: {pharmacist.full_name}'))
        else:
            self.stdout.write(self.style.WARNING(f'  [WARN] Pharmacist exists: {pharmacist.full_name}'))

        # Create hospital staff affiliation (hospital pharmacist)
        staff, staff_created = HospitalStaff.objects.get_or_create(
            hospital=hospital,
            staff_participant=pharmacist,
            defaults={
                'full_name': pharmacist.full_name,
                'email': pharmacist.email,
                'phone_number': pharmacist.phone_number,
                'role': 'pharmacist',
                'department': department,
                'employment_type': 'full_time',
                'is_active': True,
                'can_prescribe': False,
                'can_view_all_records': False,
            }
        )

        if staff_created:
            self.stdout.write(self.style.SUCCESS(f'  [OK] Created hospital staff profile for pharmacist'))
        else:
            self.stdout.write(self.style.WARNING('  [WARN] Hospital staff profile exists'))

        return pharmacist

    def create_hospital_beds(self, hospital, departments):
        """Create hospital beds"""
        self.stdout.write('Creating hospital beds...')

        bed_count = 0
        for dept in departments[:3]:  # Create beds for first 3 departments
            for i in range(1, 6):  # 5 beds per department
                bed, created = Bed.objects.get_or_create(
                    hospital=hospital,
                    bed_number=f'{dept.code}-{i:02d}',
                    defaults={
                        'department': dept,
                        'room_number': f'{dept.code}-R{(i-1)//2 + 1}',
                        'floor_number': str(random.randint(1, 5)),
                        'bed_type': random.choice(['standard', 'icu', 'private']),
                        'status': random.choice(['available', 'occupied', 'available', 'available']),
                        'has_oxygen': random.choice([True, False]),
                        'has_monitor': random.choice([True, False]),
                        'is_isolation': False,
                    }
                )
                if created:
                    bed_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {bed_count} beds'))

    def create_hospital_staff(self, hospital, departments):
        """Create additional hospital staff"""
        self.stdout.write('Creating additional hospital staff...')

        staff_data = [
            {'name': 'Nurse Ada', 'role': 'nurse', 'dept_idx': 0},
            {'name': 'Nurse Ibrahim', 'role': 'nurse', 'dept_idx': 1},
            {'name': 'Lab Tech Fatima', 'role': 'lab_technician', 'dept_idx': 2},
            {'name': 'Receptionist Amina', 'role': 'receptionist', 'dept_idx': 0},
        ]

        staff_count = 0
        for i, data in enumerate(staff_data, start=2):
            staff, created = HospitalStaff.objects.get_or_create(
                hospital=hospital,
                email=f'staff{i}@test.com',
                defaults={
                    'full_name': data['name'],
                    'phone_number': f'+2250123457{70+i}',
                    'role': data['role'],
                    'department': departments[data['dept_idx']],
                    'employment_type': 'full_time',
                    'is_active': True,
                }
            )
            if created:
                staff_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {staff_count} staff members'))

    def create_doctor_services(self, doctor):
        """Create services for the test doctor"""
        self.stdout.write('Creating doctor services...')

        services_data = [
            {
                'name': 'Cardiac Consultation',
                'category': 'consultation',
                'description': 'General cardiac health consultation',
                'price': 7500,  # 75 USD in cents
                'duration': 30,
            },
            {
                'name': 'ECG Test',
                'category': 'diagnostic',
                'description': 'Electrocardiogram test and analysis',
                'price': 5000,  # 50 USD in cents
                'duration': 45,
            },
            {
                'name': 'Stress Test',
                'category': 'diagnostic',
                'description': 'Cardiac stress test',
                'price': 15000,  # 150 USD in cents
                'duration': 60,
            },
        ]

        service_count = 0
        for data in services_data:
            service, created = DoctorService.objects.get_or_create(
                doctor=doctor,
                name=data['name'],
                defaults={
                    'category': data['category'],
                    'description': data['description'],
                    'price': data['price'],
                    'duration_minutes': data['duration'],
                    'is_available': True,
                    'is_active': True,
                }
            )
            if created:
                service_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {service_count} services'))

    def create_pharmacy_inventory(self, pharmacy):
        """Create pharmacy inventory items"""
        self.stdout.write('Creating pharmacy inventory...')

        medicines = [
            {'name': 'Paracetamol 500mg', 'category': 'pain_relief', 'price': 500, 'qty': 500},
            {'name': 'Amoxicillin 250mg', 'category': 'antibiotics', 'price': 1500, 'qty': 200},
            {'name': 'Ibuprofen 400mg', 'category': 'pain_relief', 'price': 800, 'qty': 300},
            {'name': 'Metformin 500mg', 'category': 'diabetes', 'price': 2000, 'qty': 150},
            {'name': 'Lisinopril 10mg', 'category': 'cardiovascular', 'price': 2500, 'qty': 100},
        ]

        item_count = 0
        for med in medicines:
            item, created = PharmacyInventory.objects.get_or_create(
                pharmacy=pharmacy,
                medicine_name=med['name'],
                defaults={
                    'category': med['category'],
                    'unit_price': med['price'],
                    'quantity_in_stock': med['qty'],
                    'reorder_level': 50,
                    'batch_number': f'BATCH-{random.randint(1000, 9999)}',
                    'expiry_date': date.today() + timedelta(days=365),
                    'requires_prescription': med['category'] in ['antibiotics', 'cardiovascular'],
                    'is_active': True,
                }
            )
            if created:
                item_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {item_count} inventory items'))

    def create_pharmacy_staff(self, pharmacy):
        """Create pharmacy staff"""
        self.stdout.write('Creating pharmacy staff...')

        staff_data = [
            {'name': 'Pharmacist Chief', 'role': 'pharmacist'},
            {'name': 'Pharmacy Assistant', 'role': 'pharmacy_assistant'},
            {'name': 'Cashier', 'role': 'cashier'},
        ]

        staff_count = 0
        for i, data in enumerate(staff_data, start=1):
            staff, created = PharmacyStaff.objects.get_or_create(
                pharmacy=pharmacy,
                email=f'pharm.staff{i}@test.com',
                defaults={
                    'full_name': data['name'],
                    'phone_number': f'+2250123458{i}',
                    'role': data['role'],
                    'is_active': True,
                }
            )
            if created:
                staff_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {staff_count} pharmacy staff'))

    def create_insurance_packages(self, insurance):
        """Create insurance packages"""
        self.stdout.write('Creating insurance packages...')

        packages = [
            {
                'name': 'Basic Coverage',
                'description': 'Basic health insurance coverage',
                'premium': 5000,  # 50 USD/month
                'coverage_limit': 100000,  # 1000 USD
                'copay': 1000,  # 10 USD
            },
            {
                'name': 'Standard Coverage',
                'description': 'Standard health insurance with dental',
                'premium': 10000,  # 100 USD/month
                'coverage_limit': 300000,  # 3000 USD
                'copay': 500,  # 5 USD
            },
            {
                'name': 'Premium Coverage',
                'description': 'Comprehensive health insurance',
                'premium': 20000,  # 200 USD/month
                'coverage_limit': 1000000,  # 10000 USD
                'copay': 0,  # No copay
            },
        ]

        package_count = 0
        for pkg in packages:
            package, created = InsurancePackage.objects.get_or_create(
                insurance_company=insurance,
                package_name=pkg['name'],
                defaults={
                    'description': pkg['description'],
                    'monthly_premium': pkg['premium'],
                    'annual_coverage_limit': pkg['coverage_limit'],
                    'copay_percentage': pkg['copay'],
                    'is_active': True,
                    'covers_consultations': True,
                    'covers_prescriptions': True,
                    'covers_hospitalization': True,
                }
            )
            if created:
                package_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {package_count} insurance packages'))

    def create_insurance_staff(self, insurance):
        """Create insurance staff"""
        self.stdout.write('Creating insurance staff...')

        staff_data = [
            {'name': 'Claims Manager', 'role': 'claims_manager'},
            {'name': 'Underwriter', 'role': 'underwriter'},
            {'name': 'Customer Service', 'role': 'customer_service'},
        ]

        staff_count = 0
        for i, data in enumerate(staff_data, start=1):
            staff, created = InsuranceStaff.objects.get_or_create(
                insurance_company=insurance,
                email=f'ins.staff{i}@test.com',
                defaults={
                    'full_name': data['name'],
                    'phone_number': f'+2250123459{i}',
                    'role': data['role'],
                    'is_active': True,
                }
            )
            if created:
                staff_count += 1

        self.stdout.write(self.style.SUCCESS(f'  [OK] Created {staff_count} insurance staff'))
