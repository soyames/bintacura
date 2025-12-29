from django.db import models
from django.utils import timezone
import uuid
from core.models import Participant
from core.mixins import SyncMixin

class TransportRequest(SyncMixin):  # Manages patient medical transport and ambulance requests
    TRANSPORT_TYPE_CHOICES = [
        ('ambulance', 'Ambulance'),
        ('medical_taxi', 'Medical Taxi'),
        ('wheelchair_transport', 'Wheelchair Transport'),
        ('stretcher_transport', 'Stretcher Transport'),
        ('regular_taxi', 'Regular Taxi'),
    ]
    
    URGENCY_CHOICES = [
        ('emergency', 'Emergency'),
        ('urgent', 'Urgent'),
        ('scheduled', 'Scheduled'),
        ('routine', 'Routine'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('driver_assigned', 'Driver Assigned'),
        ('en_route', 'En Route'),
        ('arrived', 'Arrived'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    request_number = models.CharField(max_length=50, unique=True)
    patient = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transport_requests')
    
    transport_type = models.CharField(max_length=50, choices=TRANSPORT_TYPE_CHOICES)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    pickup_address = models.TextField()
    pickup_latitude = models.FloatField(null=True, blank=True)
    pickup_longitude = models.FloatField(null=True, blank=True)
    
    dropoff_address = models.TextField()
    dropoff_latitude = models.FloatField(null=True, blank=True)
    dropoff_longitude = models.FloatField(null=True, blank=True)
    
    scheduled_pickup_time = models.DateTimeField()
    actual_pickup_time = models.DateTimeField(null=True, blank=True)
    actual_dropoff_time = models.DateTimeField(null=True, blank=True)
    
    driver_id = models.UUIDField(null=True, blank=True)
    driver_name = models.CharField(max_length=255, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    vehicle_number = models.CharField(max_length=50, blank=True)
    
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    payment_id = models.UUIDField(null=True, blank=True)
    
    patient_notes = models.TextField(blank=True)
    special_requirements = models.TextField(blank=True)
    medical_equipment_needed = models.JSONField(default=list, blank=True)
    
    companion_count = models.IntegerField(default=0)
    companion_names = models.JSONField(default=list, blank=True)
    
    estimated_distance = models.FloatField(null=True, blank=True)
    estimated_duration = models.IntegerField(null=True, blank=True)
    
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    rating = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    
    class Meta:  # Meta class implementation
        db_table = 'transport_requests'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['request_number']),
            models.Index(fields=['scheduled_pickup_time']),
            models.Index(fields=['status']),
        ]
    
    def save(self, *args, **kwargs):  # Save
        if not self.request_number:
            self.request_number = f"TR-{timezone.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    def __str__(self):  # Return string representation
        return f"{self.request_number} - {self.transport_type} - {self.status}"

class TransportProvider(SyncMixin):  # Stores information about transport service providers
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]
    
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    
    service_types = models.JSONField(default=list)
    coverage_areas = models.JSONField(default=list)
    operating_hours = models.JSONField(default=dict)
    
    base_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    per_km_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    rating = models.FloatField(default=0.0)
    total_trips = models.IntegerField(default=0)
    
    class Meta:  # Meta class implementation
        db_table = 'transport_providers'
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.name}"


class RideShareProvider(SyncMixin):  #  Integration with ride-sharing services (Uber, Gozem, Bolt)
    PROVIDER_CHOICES = [
        ('uber', 'Uber'),
        ('gozem', 'Gozem'),
        ('bolt', 'Bolt'),
        ('yango', 'Yango'),
        ('internal', 'BINTACURA Internal'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    name = models.CharField(max_length=100, choices=PROVIDER_CHOICES)
    api_key = models.CharField(max_length=255, blank=True)
    api_secret = models.CharField(max_length=255, blank=True)
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    service_types_available = models.JSONField(default=list)
    coverage_areas = models.JSONField(default=list)
    average_response_time = models.IntegerField(default=0)
    success_rate = models.FloatField(default=0.0)
    average_rating = models.FloatField(default=0.0)
    total_trips = models.IntegerField(default=0)

    class Meta:  # Meta class implementation
        db_table = 'rideshare_providers'
        indexes = [models.Index(fields=['name', 'is_active'])]

    def __str__(self):  # Return string representation
        return f"{self.get_name_display()}"


class RideShareQuote(SyncMixin):  # Quotes from ride-sharing providers for transport requests
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

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='quotes')
    provider = models.ForeignKey(RideShareProvider, on_delete=models.CASCADE, related_name='quotes')
    vehicle_type = models.CharField(max_length=50, choices=VEHICLE_TYPE_CHOICES)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2)
    distance_fare = models.DecimalField(max_digits=10, decimal_places=2)
    surge_multiplier = models.FloatField(default=1.0)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    driver_name = models.CharField(max_length=255, blank=True)
    driver_photo_url = models.URLField(blank=True)
    driver_rating = models.FloatField(null=True, blank=True)
    driver_phone = models.CharField(max_length=20, blank=True)
    driver_latitude = models.FloatField(null=True, blank=True)
    driver_longitude = models.FloatField(null=True, blank=True)
    vehicle_make = models.CharField(max_length=100, blank=True)
    vehicle_model = models.CharField(max_length=100, blank=True)
    vehicle_color = models.CharField(max_length=50, blank=True)
    vehicle_plate = models.CharField(max_length=20, blank=True)
    vehicle_capacity = models.IntegerField(default=4)
    estimated_arrival_minutes = models.IntegerField()
    estimated_trip_duration_minutes = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    expires_at = models.DateTimeField()
    provider_quote_id = models.CharField(max_length=255, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'rideshare_quotes'
        ordering = ['total_fare']
        indexes = [
            models.Index(fields=['transport_request', 'status']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.provider.name} - {self.vehicle_type} - {self.total_fare} {self.currency}"


class TransportChat(SyncMixin):  # Real-time chat between patient and driver
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

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='chat_messages')
    quote = models.ForeignKey(RideShareQuote, on_delete=models.CASCADE, null=True, blank=True, related_name='chat_messages')
    sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)
    sender = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transport_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='text')
    message = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    image_url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'transport_chat'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['transport_request', 'created_at']),
            models.Index(fields=['sender', 'is_read']),
        ]

    def __str__(self):  # Return string representation
        return f"{self.sender_type}: {self.message[:50]}"


class DriverLocation(SyncMixin):  # Real-time tracking of driver location
    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='driver_locations')
    quote = models.ForeignKey(RideShareQuote, on_delete=models.CASCADE, related_name='driver_locations')
    latitude = models.FloatField()
    longitude = models.FloatField()
    heading = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    accuracy = models.FloatField(null=True, blank=True)
    distance_to_pickup = models.FloatField(null=True, blank=True)
    distance_to_dropoff = models.FloatField(null=True, blank=True)
    estimated_arrival = models.DateTimeField(null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:  # Meta class implementation
        db_table = 'driver_locations'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['transport_request', '-timestamp']),
            models.Index(fields=['quote', '-timestamp']),
        ]

    def __str__(self):  # Return string representation
        return f"Location at {self.timestamp}"


class HospitalTransportNotification(SyncMixin):  # Notifications to hospitals about transport requests
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('viewed', 'Viewed'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    region_code = models.CharField(max_length=50, default="global", db_index=True)
    transport_request = models.ForeignKey(TransportRequest, on_delete=models.CASCADE, related_name='hospital_notifications')
    hospital = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='transport_notifications')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    responded_at = models.DateTimeField(null=True, blank=True)
    response_notes = models.TextField(blank=True)
    can_provide_transport = models.BooleanField(default=False)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    proposed_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:  # Meta class implementation
        db_table = 'hospital_transport_notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['hospital', 'status']),
            models.Index(fields=['transport_request']),
        ]

    def __str__(self):  # Return string representation
        return f"Notification to {self.hospital.full_name} - {self.status}"

