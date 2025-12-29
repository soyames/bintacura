from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Participant
from .models import Medication, Prescription, PrescriptionItem
from datetime import date, timedelta


class MedicationModelTest(TestCase):  # MedicationModelTest class implementation
    def test_create_medication(self):  # Test create medication
        medication = Medication.objects.create(
            name="Aspirin",
            generic_name="Acetylsalicylic acid",
            category="Pain reliever",
            description="Common pain reliever",
        )
        self.assertEqual(medication.name, "Aspirin")
        self.assertTrue(medication.requires_prescription)
        self.assertFalse(medication.is_controlled_substance)


class PrescriptionModelTest(TestCase):  # PrescriptionModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )

    def test_create_prescription(self):  # Test create prescription
        prescription = Prescription.objects.create(
            user=self.patient,
            doctor=self.doctor,
            issue_date=date.today(),
            valid_until=date.today() + timedelta(days=30),
            type="regular",
            diagnosis="Common cold",
        )
        self.assertEqual(prescription.status, "active")
        self.assertEqual(prescription.max_refills, 0)
        self.assertEqual(prescription.refills_used, 0)

    def test_prescription_refills(self):  # Test prescription refills
        prescription = Prescription.objects.create(
            user=self.patient,
            doctor=self.doctor,
            issue_date=date.today(),
            valid_until=date.today() + timedelta(days=30),
            max_refills=3,
        )
        self.assertEqual(prescription.max_refills, 3)
        prescription.refills_used = 1
        prescription.save()
        self.assertEqual(prescription.refills_used, 1)


class PrescriptionItemModelTest(TestCase):  # PrescriptionItemModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )
        self.medication = Medication.objects.create(
            name="Amoxicillin", category="Antibiotic"
        )
        self.prescription = Prescription.objects.create(
            user=self.patient,
            doctor=self.doctor,
            issue_date=date.today(),
            valid_until=date.today() + timedelta(days=30),
        )

    def test_create_prescription_item(self):  # Test create prescription item
        item = PrescriptionItem.objects.create(
            prescription=self.prescription,
            medication=self.medication,
            dosage="500mg",
            frequency="twice_daily",
            duration_days=7,
            quantity=14,
        )
        self.assertEqual(item.dosage, "500mg")
        self.assertEqual(item.duration_days, 7)
