"""
System Configuration Model
Stores platform-wide settings including default consultation fee
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
import uuid


class SystemConfiguration(models.Model):
    """
    Platform-wide configuration settings
    Singleton pattern - only one active configuration at a time
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Default consultation fee (in USD - platform base currency)
    default_consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5.00,
        validators=[MinValueValidator(0)],
        help_text="Standard consultation fee for all appointments in USD (base price)"
    )
    
    default_consultation_currency = models.CharField(
        max_length=3,
        default='XOF',
        help_text="Base currency for consultation fee (XOF is platform default)"
    )
    
    # Fee structure
    platform_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        validators=[MinValueValidator(0)],
        help_text="Platform fee percentage (e.g., 1.00 for 1%)"
    )
    
    tax_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=18.00,
        validators=[MinValueValidator(0)],
        help_text="Tax percentage applied to platform fee (e.g., 18.00 for 18%)"
    )
    
    # Additional settings
    wallet_topup_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text="Fee for wallet top-ups (0 = free)"
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='system_configs_created'
    )
    
    class Meta:
        db_table = 'system_configuration'
        ordering = ['-created_at']
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configuration'
    
    def __str__(self):
        return f"System Config - Consultation: ${self.default_consultation_fee} {self.default_consultation_currency}"
    
    @classmethod
    def get_active_config(cls):
        """Get the active system configuration"""
        config = cls.objects.filter(is_active=True).first()
        if not config:
            # Create default configuration if none exists
            config = cls.objects.create(
                default_consultation_fee=5.00,
                default_consultation_currency='XOF',
                platform_fee_percentage=1.00,
                tax_percentage=18.00,
                wallet_topup_fee_percentage=0.00,
                is_active=True
            )
        return config
    
    @classmethod
    def get_default_consultation_fee(cls):
        """Get the default consultation fee"""
        config = cls.get_active_config()
        return config.default_consultation_fee
    
    @classmethod
    def get_consultation_currency(cls):
        """Get the consultation currency"""
        config = cls.get_active_config()
        return config.default_consultation_currency
    
    def save(self, *args, **kwargs):
        # Ensure only one active configuration
        if self.is_active:
            SystemConfiguration.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)
