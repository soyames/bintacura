from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.urls import reverse
from core.models import Participant
from .models import Appointment, Availability
from datetime import date, time, timedelta


class AppointmentModelTest(TestCase):  # AppointmentModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )
        self.appointment_date = date.today() + timedelta(days=1)

    def test_create_appointment(self):  # Test create appointment
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_date,
            appointment_time=time(10, 0),
            type="consultation",
            consultation_fee=5000,
        )
        self.assertEqual(appointment.status, "pending")
        self.assertEqual(appointment.payment_status, "pending")
        self.assertEqual(appointment.consultation_fee, 5000)

    def test_appointment_status_choices(self):  # Test appointment status choices
        appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=self.appointment_date,
            appointment_time=time(10, 0),
        )
        valid_statuses = [
            "pending",
            "confirmed",
            "completed",
            "cancelled",
            "rejected",
            "in_progress",
            "no_show",
        ]
        for stat in valid_statuses:
            appointment.status = stat
            appointment.save()
            self.assertEqual(appointment.status, stat)


class AvailabilityModelTest(TestCase):  # AvailabilityModelTest class implementation
    def setUp(self):  # Setup
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )

    def test_create_availability(self):  # Test create availability
        availability = Availability.objects.create(
            provider=self.doctor,
            weekday="monday",
            start_time=time(9, 0),
            end_time=time(17, 0),
            slot_duration=30,
        )
        self.assertTrue(availability.is_active)
        self.assertEqual(availability.slot_duration, 30)


class AppointmentAPITest(APITestCase):  # AppointmentAPITest class implementation
    def setUp(self):  # Setup
        self.client = APIClient()
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.doctor = Participant.objects.create_user(
            email="doctor@test.com", password="test123", role="doctor"
        )
        self.client.force_authenticate(user=self.patient)

    def test_list_appointments(self):  # Test list appointments
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date=date.today() + timedelta(days=1),
            appointment_time=time(10, 0),
        )
        url = reverse("appointments:appointment-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
