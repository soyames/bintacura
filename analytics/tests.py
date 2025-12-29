from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from core.models import Participant


class AnalyticsAPITest(APITestCase):  # AnalyticsAPITest class implementation
    def setUp(self):  # Setup
        self.client = APIClient()
        self.admin = Participant.objects.create_user(
            email="admin@test.com", password="test123", role="admin"
        )
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )

    def test_analytics_requires_auth(self):  # Test analytics requires auth
        response = self.client.get("/api/v1/analytics/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
