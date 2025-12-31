"""
Participant Payment Method Models
==================================

Manages external payment accounts for participants (doctors, hospitals, pharmacies, insurance companies).

Participants with service roles link their bank accounts or mobile money accounts to receive payments.
When patients pay, money goes directly to these accounts via Fedapay gateway.

Note: "Provider" in comments refers to participants with non-patient roles (doctor, hospital, pharmacy, insurance).
      Models use Participant namespace - NO provider namespace.
"""

from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import uuid

from core.models import Participant
from core.hospital_staff_models import can_doctor_link_payment_account


class ParticipantPaymentMethod(models.Model):
    """
    External payment accounts linked by participants to receive payments.

    Flow:
    1. Participant (doctor/hospital/pharmacy/insurance) links bank account or mobile money
    2. Verification process (OTP for mobile money, micro-deposit for bank)
    3. Participant sets primary payment method
    4. When patients pay, money goes to this account via Fedapay
    """

    METHOD_TYPE_CHOICES = [
        ('bank_account', 'Compte Bancaire'),
        ('mobile_money', 'Mobile Money'),
    ]

    MOBILE_MONEY_PROVIDER_CHOICES = [
        ('mtn', 'MTN Mobile Money'),
        ('moov', 'Moov Money'),
        ('orange', 'Orange Money'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En Attente de Vérification'),
        ('active', 'Actif'),
        ('suspended', 'Suspendu'),
        ('rejected', 'Rejeté'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Participant (must be non-patient role)
    participant = models.ForeignKey(
        Participant,
        on_delete=models.CASCADE,
        related_name='linked_payment_accounts',  # Changed to avoid conflict with core.PaymentMethod
        limit_choices_to={'role__in': ['doctor', 'hospital', 'pharmacy', 'insurance', 'lab', 'imaging']},
        help_text='Participant fournisseur de services (médecin, hôpital, pharmacie, assurance)'
    )

    # Method type
    method_type = models.CharField(
        max_length=20,
        choices=METHOD_TYPE_CHOICES,
        help_text='Type de méthode de paiement'
    )

    # Bank account details
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Nom de la banque'
    )
    account_number = models.CharField(
        max_length=50,
        blank=True,
        help_text='Numéro de compte bancaire'
    )
    account_name = models.CharField(
        max_length=200,
        blank=True,
        help_text='Nom du titulaire du compte'
    )
    swift_code = models.CharField(
        max_length=20,
        blank=True,
        help_text='Code SWIFT/BIC (pour les virements internationaux)'
    )

    # Mobile money details
    mobile_money_provider = models.CharField(
        max_length=20,
        choices=MOBILE_MONEY_PROVIDER_CHOICES,
        blank=True,
        help_text='Fournisseur mobile money'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[1-9]\d{1,14}$',
                message='Numéro de téléphone invalide. Format: +22997000000'
            )
        ],
        help_text='Numéro de téléphone mobile money'
    )

    # Gateway integration
    gateway_provider = models.CharField(
        max_length=50,
        default='fedapay',
        help_text='Fournisseur de passerelle (Fedapay, etc.)'
    )
    gateway_account_id = models.CharField(
        max_length=100,
        blank=True,
        help_text='ID du compte dans la passerelle de paiement'
    )

    # Verification
    is_verified = models.BooleanField(
        default=False,
        help_text='Méthode de paiement vérifiée'
    )
    verification_code = models.CharField(
        max_length=10,
        blank=True,
        help_text='Code de vérification OTP'
    )
    verification_code_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Expiration du code de vérification'
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Date de vérification'
    )

    # Primary payment method
    is_primary = models.BooleanField(
        default=False,
        help_text='Méthode de paiement principale (utilisée par défaut)'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text='Statut de la méthode de paiement'
    )

    # Metadata
    rejection_reason = models.TextField(
        blank=True,
        help_text='Raison du rejet (si applicable)'
    )
    notes = models.TextField(
        blank=True,
        help_text='Notes administratives'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Données supplémentaires'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'participant_payment_methods'  # NOT provider_payment_methods
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=['participant', 'is_primary', 'status']),
            models.Index(fields=['participant', 'status']),
            models.Index(fields=['gateway_account_id']),
        ]
        constraints = [
            # Only one primary payment method per participant
            models.UniqueConstraint(
                fields=['participant'],
                condition=models.Q(is_primary=True, status='active'),
                name='unique_primary_payment_method_per_participant'
            )
        ]

    def __str__(self):
        if self.method_type == 'bank_account':
            return f"{self.participant.full_name} - {self.bank_name} (...{self.account_number[-4:] if self.account_number else 'N/A'})"
        else:
            return f"{self.participant.full_name} - {self.get_mobile_money_provider_display()} ({self.phone_number})"

    def clean(self):
        """Validate payment method data"""
        from django.core.exceptions import ValidationError

        # Hospital staff doctor validation - doctors who are hospital staff cannot link their own payment accounts
        if self.participant.role == 'doctor':
            if not can_doctor_link_payment_account(self.participant):
                raise ValidationError({
                    'participant': 'Les médecins qui sont personnel d\'hôpital ne peuvent pas lier leurs propres comptes de paiement. '
                                  'Les paiements sont gérés par l\'hôpital.'
                })

        # Bank account validation
        if self.method_type == 'bank_account':
            if not self.bank_name:
                raise ValidationError({'bank_name': 'Le nom de la banque est requis pour un compte bancaire'})
            if not self.account_number:
                raise ValidationError({'account_number': 'Le numéro de compte est requis'})
            if not self.account_name:
                raise ValidationError({'account_name': 'Le nom du titulaire du compte est requis'})

        # Mobile money validation
        elif self.method_type == 'mobile_money':
            if not self.mobile_money_provider:
                raise ValidationError({'mobile_money_provider': 'Le fournisseur mobile money est requis'})
            if not self.phone_number:
                raise ValidationError({'phone_number': 'Le numéro de téléphone est requis pour mobile money'})
            
            # Validate phone number format for FedaPay compatibility
            if not self.phone_number.startswith('+'):
                raise ValidationError({'phone_number': 'Le numéro de téléphone doit commencer par + (format international)'})
            
            # Ensure phone belongs to participant's country
            if hasattr(self.participant, 'country') and self.participant.country:
                from currency_converter.services import CurrencyConverterService
                phone_country = CurrencyConverterService.get_country_from_phone(self.phone_number)
                if phone_country and phone_country != self.participant.country:
                    raise ValidationError({
                        'phone_number': f'Le numéro de téléphone doit appartenir à votre pays ({self.participant.country})'
                    })

    def save(self, *args, **kwargs):
        # If setting as primary, remove primary flag from other methods
        if self.is_primary and self.status == 'active':
            ParticipantPaymentMethod.objects.filter(
                participant=self.participant,
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)

        super().save(*args, **kwargs)

    def get_masked_account_number(self):
        """Return masked account number for display"""
        if self.method_type == 'bank_account' and self.account_number:
            if len(self.account_number) > 4:
                return '*' * (len(self.account_number) - 4) + self.account_number[-4:]
            return self.account_number
        return None

    def get_display_name(self):
        """Get user-friendly display name"""
        if self.method_type == 'bank_account':
            return f"{self.bank_name} (...{self.account_number[-4:] if self.account_number and len(self.account_number) > 4 else 'N/A'})"
        else:
            return f"{self.get_mobile_money_provider_display()} ({self.phone_number})"


class PaymentMethodVerification(models.Model):
    """
    Tracks verification attempts for payment methods.

    For bank accounts: Micro-deposit verification
    For mobile money: OTP verification
    """

    VERIFICATION_TYPE_CHOICES = [
        ('micro_deposit', 'Micro-Dépôt Bancaire'),
        ('otp', 'Code OTP'),
    ]

    STATUS_CHOICES = [
        ('pending', 'En Attente'),
        ('verified', 'Vérifié'),
        ('failed', 'Échoué'),
        ('expired', 'Expiré'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_method = models.ForeignKey(
        ParticipantPaymentMethod,
        on_delete=models.CASCADE,
        related_name='verification_attempts'
    )

    verification_type = models.CharField(
        max_length=20,
        choices=VERIFICATION_TYPE_CHOICES
    )

    # OTP verification
    otp_code = models.CharField(
        max_length=10,
        blank=True,
        help_text='Code OTP envoyé'
    )
    otp_sent_at = models.DateTimeField(
        null=True,
        blank=True
    )
    otp_expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    # Micro-deposit verification
    deposit_amount_1 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Premier montant de micro-dépôt (en XOF)'
    )
    deposit_amount_2 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Deuxième montant de micro-dépôt (en XOF)'
    )
    deposit_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text='Référence de transaction du dépôt'
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    # Attempts
    attempt_count = models.IntegerField(
        default=0,
        help_text='Nombre de tentatives de vérification'
    )
    max_attempts = models.IntegerField(
        default=3,
        help_text='Nombre maximum de tentatives autorisées'
    )

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payment_method_verifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['status', 'otp_expires_at']),
        ]

    def __str__(self):
        return f"{self.payment_method} - {self.get_verification_type_display()} - {self.status}"

    def is_expired(self):
        """Check if verification has expired"""
        if self.verification_type == 'otp' and self.otp_expires_at:
            return timezone.now() > self.otp_expires_at
        return False

    def can_retry(self):
        """Check if user can retry verification"""
        return self.attempt_count < self.max_attempts and not self.is_expired()
