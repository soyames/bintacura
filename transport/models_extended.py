# Extended Transport Models for Ride-Sharing Integration and Real-time Features
from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from .models import TransportRequest


class RideShareProvider(models.Model):
    """
    Integration with ride-sharing services like Uber, Gozem, Bolt, etc.
    """
    PROVIDER_CHOICES = [
        ('uber', 'Uber'),
        ('gozem', 'Gozem'),
        ('bolt', 'Bolt'),
        ('yango', 'Yango'),
        ('internal', 'BINTACURA Internal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, choices=PROVIDER_CHOICES)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    # Service availability
    service_types_available = models.JSONField(default=list)  # ['standard', 'xl', 'ambulance', etc.]
    coverage_areas = models.JSONField(default=list)  # Geographic coverage

    # Performance metrics
    average_response_time = models.IntegerField(default=0, help_text="Average time to accept request in seconds")
    success_rate = models.FloatField(default=0.0, help_text="Percentage of successful trips")
    average_rating = models.FloatField(default=0.0)
    total_trips = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rideshare_providers'
        indexes = [
            models.Index(fields=['name', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_name_display()}"


class RideShareQuote(models.Model):
    """
    Quotes from different ride-sharing providers for a transport request
    """
    VEHICLE_TYPE_CHOICES = [
        ('economy', 'Economy'),
        ('comfort', 'Comfort'),
        ('xl', 'XL'),
        ('van', 'Van'),
        ('ambulance', 'Ambulance'),
        ('medical_van', 'Medical Van'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transport_request = models.ForeignKey('TransportRequest', on_delete=models.CASCADE, related_name='quotes')
    provider = models.ForeignKey(RideShareProvider, on_delete=models.CASCADE, related_name='quotes')

    # Quote details
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPE_CHOICES)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=2)
    surge_multiplier = models.FloatField(default=1.0)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')

    # Driver details (when available)
    driver_name = models.CharField(max_length=255, blank=True)
    driver_photo_url = models.URLField(blank=True)
    driver_rating = models.FloatField(null=True, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    driver_latitude = models.FloatField(null=True, blank=True)
    driver_longitude = models.FloatField(null=True, blank=True)

    # Vehicle details
    vehicle_make = models.CharField(max_length=100, blank=True)
    vehicle_model = models.CharField(max_length=100, blank=True)
    vehicle_color = models.CharField(max_length=50, blank=True)
    vehicle_plate = models.CharField(max_length=20, blank=True)
    vehicle_capacity = models.IntegerField(default=4)

    # Time estimates
    estimated_arrival_minutes = models.IntegerField(help_text="ETA for driver to reach pickup")
    estimated_trip_duration_minutes = models.IntegerField(help_text="Estimated trip duration")

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()

    # External reference
    provider_quote_id = models.CharField(max_length=255, blank=True, help_text="Quote ID from provider's system")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'rideshare_quotes'
        ordering = ['total_fare']  # Order by price, cheapest first
        indexes = [
            models.Index(fields=['transport_request', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.provider.name} - {self.vehicle_type} - {self.total_fare} {self.currency}"


class TransportChat(models.Model):
    """
    Real-time chat between patient and driver
    """
    SENDER_CHOICES = [
        ('patient', 'Patient'),
        ('driver', 'Driver'),
        ('system', 'System'),
    ]

    MESSAGE_TYPE_CHOICES = [
        ('text', 'Text'),
        ('location', 'Location'),
        ('image', 'Image'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transport_request = models.ForeignKey('TransportRequest', on_delete=models.CASCADE, related_name='chat_messages')
    quote = models.ForeignKey(RideShareQuote, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_messages')

    sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)
    sender = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transport_messages')

    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    message = models.TextField()

    # For location sharing
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    # For images
    image_url = models.URLField(blank=True)

    # Status
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'transport_chat'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['transport_request', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]

    def __str__(self):
        return f"{self.sender_type}: {self.message[:50]}"


class DriverLocation(models.Model):
    """
    Real-time tracking of driver location
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transport_request = models.ForeignKey('TransportRequest', on_delete=models.CASCADE, related_name='driver_locations')
    quote = models.ForeignKey(RideShareQuote, on_delete=models.CASCADE, related_name='driver_locations')

    latitude = models.FloatField()
    longitude = models.FloatField()
    heading = models.FloatField(null=True, blank=True, help_text="Direction in degrees")
    speed = models.FloatField(null=True, blank=True, help_text="Speed in km/h")
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")

    # Distance calculations
    distance_to_pickup = models.FloatField(null=True, blank=True, help_text="Distance to pickup in km")
    distance_to_dropoff = models.FloatField(null=True, blank=True, help_text="Distance to dropoff in km")
    estimated_arrival = models.DateTimeField(null=True, blank=True)

    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'driver_locations'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transport_request', '-timestamp']),
            models.Index(fields=['quote', '-timestamp']),
        ]

    def __str__(self):
        return f"Location at {self.timestamp}"


class HospitalTransportNotification(models.Model):
    """
    Notifications sent to hospitals about transport requests
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transport_request = models.ForeignKey('TransportRequest', on_delete=models.CASCADE, related_name='hospital_notifications')
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transport_notifications')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Response details
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)

    # If hospital provides their own transport
    can_provide_transport = models.BooleanField(default=False)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    proposed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'hospital_transport_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['transport_request']),
        ]

    def __str__(self):
        return f"Notification to {self.hospital.full_name} - {self.status}"

