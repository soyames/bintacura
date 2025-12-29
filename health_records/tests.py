from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Participant
from .models import HealthRecord
from datetime import date


class HealthRecordModelTest(TestCase):  # HealthRecordModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )

    def test_create_health_record(self):  # Test create health record
        record = HealthRecord.objects.create(
            created_by=self.doctor,
            assigned_to=self.patient,
            type="consultation",
            title="General Checkup",
            diagnosis="Annual health checkup",
            date_of_record=date.today(),
        )
        self.assertEqual(record.type, "consultation")
        self.assertEqual(record.assigned_to, self.patient)
        self.assertEqual(record.created_by, self.doctor)


class HealthRecordAPITest(APITestCase):  # HealthRecordAPITest class implementation
    def setUp(self):  # Setup
        self.client = APIClient()
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.client.force_authenticate(user=self.patient)

    def test_list_health_records(self):  # Test list health records
        url = reverse("health_records:record-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
