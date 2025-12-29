from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Participant
from .models import InsurancePackage, PatientInsuranceCard, InsuranceClaim
from datetime import date, timedelta


class InsurancePackageModelTest(TestCase):  # InsurancePackageModelTest class implementation
    def setUp(self):  # Setup
        self.insurance_company = Participant.objects.create_user(
            email="insurance@test.com",
            password="test123",
            role="insurance_company",
        )

    def test_create_insurance_package(self):  # Test create insurance package
        package = InsurancePackage.objects.create(
            company=self.insurance_company,
            name="Basic Health Coverage",
            description="Basic healthcare package",
            package_type="individual",
            premium_amount=10000,
            max_coverage_amount=500000,
        )
        self.assertTrue(package.is_active)
        self.assertEqual(package.premium_amount, 10000)
        self.assertEqual(package.package_type, "individual")

    def test_package_types(self):  # Test package types
        package = InsurancePackage.objects.create(
            company=self.insurance_company,
            name="Family Coverage",
            description="Family healthcare package",
            package_type="family",
            premium_amount=25000,
        )
        self.assertEqual(package.package_type, "family")


class PatientInsuranceCardModelTest(TestCase):  # PatientInsuranceCardModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.insurance_company = Participant.objects.create_user(
            email="insurance@test.com",
            password="test123",
            role="insurance_company",
        )
        self.package = InsurancePackage.objects.create(
            company=self.insurance_company,
            name="Test Package",
            description="Test",
            premium_amount=10000,
        )

    def test_create_insurance_card(self):  # Test create insurance card
        card = PatientInsuranceCard.objects.create(
            patient=self.patient,
            insurance_package=self.package,
            card_number="CARD123456",
            policy_number="POL123456",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            coverage_start_date=date.today(),
            coverage_end_date=date.today() + timedelta(days=365),
        )
        self.assertEqual(card.status, "active")
        self.assertEqual(card.card_number, "CARD123456")

    def test_card_unique_number(self):  # Test card unique number
        PatientInsuranceCard.objects.create(
            patient=self.patient,
            insurance_package=self.package,
            card_number="UNIQUE123",
            policy_number="POL001",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            coverage_start_date=date.today(),
            coverage_end_date=date.today() + timedelta(days=365),
        )
        patient2 = Participant.objects.create_user(
            email="patient2@test.com", password="test123", role="patient"
        )
        with self.assertRaises(Exception):
            PatientInsuranceCard.objects.create(
                patient=patient2,
                insurance_package=self.package,
                card_number="UNIQUE123",
                policy_number="POL002",
                issue_date=date.today(),
                expiry_date=date.today() + timedelta(days=365),
                coverage_start_date=date.today(),
                coverage_end_date=date.today() + timedelta(days=365),
            )


class InsuranceClaimModelTest(TestCase):  # InsuranceClaimModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.insurance_company = Participant.objects.create_user(
            email="insurance@test.com",
            password="test123",
            role="insurance_company",
        )
        self.package = InsurancePackage.objects.create(
            company=self.insurance_company,
            name="Test Package",
            description="Test",
            premium_amount=10000,
        )
        self.card = PatientInsuranceCard.objects.create(
            patient=self.patient,
            insurance_package=self.package,
            card_number="CARD123",
            policy_number="POL123",
            issue_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            coverage_start_date=date.today(),
            coverage_end_date=date.today() + timedelta(days=365),
        )

    def test_create_claim(self):  # Test create claim
        claim = InsuranceClaim.objects.create(
            claim_number="CLM001",
            patient=self.patient,
            insurance_card=self.card,
            insurance_package=self.package,
            service_type="consultation",
            partner_name="Test Healthcare Partner",
            partner_id=self.patient.uid,
            service_date=date.today(),
            claimed_amount=5000,
        )
        self.assertEqual(claim.status, "submitted")
        self.assertEqual(claim.claimed_amount, 5000)
