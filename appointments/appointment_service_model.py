"""
Appointment Service Model
Links appointments to multiple additional services
"""
from django.db import models
from django.utils import timezone
import uuid


class AppointmentService(models.Model):
    """
    Many-to-many relationship between appointments and provider services
    Allows patients to add multiple services to an appointment
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        'Appointment',
        on_delete=models.CASCADE,
        related_name='appointment_services'
    )
    service = models.ForeignKey(
        'core.ProviderService',
        on_delete=models.CASCADE,
        related_name='service_appointments'
    )
    service_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price of service at time of booking"
    )
    quantity = models.IntegerField(default=1)
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="service_price * quantity"
    )
    created_at = models.DateTimeField(default=timezone.now)
    
    class Meta:  # Meta class implementation
        db_table = 'appointment_services'
        indexes = [
            models.Index(fields=['appointment']),
            models.Index(fields=['service']),
        ]
        unique_together = ['appointment', 'service']
    
    def __str__(self):  # Return string representation
        return f"{self.service.name} for Appointment {self.appointment.id}"
    
    def save(self, *args, **kwargs):  # Save
        # Calculate subtotal
        self.subtotal = self.service_price * self.quantity
        super().save(*args, **kwargs)
