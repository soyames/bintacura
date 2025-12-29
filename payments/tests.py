from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from core.models import Participant, Wallet, Transaction
from .models import FeeLedger, HealthTransaction, ProviderPayout
from datetime import date, timedelta


class FeeLedgerModelTest(TestCase):  # FeeLedgerModelTest class implementation
    def setUp(self):  # Setup
        self.provider = Participant.objects.create_user(
            email="provider@test.com", password="test123", role="doctor"
        )

    def test_create_fee_ledger(self):  # Test create fee ledger
        ledger = FeeLedger.objects.create(
            related_transaction_id="550e8400-e29b-41d4-a716-446655440000",
            provider=self.provider,
            provider_role="doctor",
            service_amount=10000,
            fee_amount=500,
            fee_percentage=5.0,
            payment_method="WALLET",
        )
        self.assertEqual(ledger.status, "UNCOLLECTED")
        self.assertEqual(ledger.fee_amount, 500)
        self.assertEqual(ledger.fee_percentage, 5.0)


class HealthTransactionModelTest(TestCase):  # HealthTransactionModelTest class implementation
    def setUp(self):  # Setup
        self.patient = Participant.objects.create_user(
            email="patient@test.com", password="test123", role="patient"
        )
        self.provider = Participant.objects.create_user(
            email="provider@test.com", password="test123", role="doctor"
        )
        patient_wallet = Wallet.objects.create(
            participant=self.patient, currency="XOF", balance=100000
        )
        provider_wallet = Wallet.objects.create(
            participant=self.provider, currency="XOF", balance=50000
        )

    def test_create_health_transaction(self):  # Test create health transaction
        patient_wallet = Wallet.objects.get(participant=self.patient)
        provider_wallet = Wallet.objects.get(participant=self.provider)
        patient_balance = patient_wallet.balance
        core_transaction = Transaction.objects.create(
            sender=self.patient,
            recipient=self.provider,
            wallet=patient_wallet,
            amount=5000,
            currency="XOF",
            transaction_type="CONSULTATION_PAYMENT",
            balance_before=patient_balance,
            balance_after=patient_balance - 5000,
        )
        health_tx = HealthTransaction.objects.create(
            transaction=core_transaction,
            patient=self.patient,
            provider=self.provider,
            service_description="Medical consultation",
        )
        self.assertEqual(health_tx.patient, self.patient)
        self.assertEqual(health_tx.provider, self.provider)


class ProviderPayoutModelTest(TestCase):  # ProviderPayoutModelTest class implementation
    def setUp(self):  # Setup
        self.provider = Participant.objects.create_user(
            email="provider@test.com", password="test123", role="doctor"
        )

    def test_create_payout(self):  # Test create payout
        payout = ProviderPayout.objects.create(
            provider=self.provider,
            amount=50000,
            currency="XOF",
            period_start=date.today() - timedelta(days=30),
            period_end=date.today(),
            transaction_count=10,
            total_fees_deducted=2500,
        )
        self.assertEqual(payout.status, "pending")
        self.assertEqual(payout.amount, 50000)
        self.assertEqual(payout.transaction_count, 10)
