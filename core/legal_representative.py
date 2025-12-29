"""
Legal Representative models for institutional participants.
Hospitals, Pharmacies, and Insurance Companies must have a legal representative.
"""
from django.db import models
from django.utils import timezone
import uuid


class LegalRepresentative(models.Model):
    """
    Legal representative information for institutional participants.
    Required for: Hospital, Pharmacy, Insurance Company
    """
    
    ID_TYPE_CHOICES = [
        ('passport', 'Passport'),
        ('national_id', 'National ID Card'),
        ('drivers_license', 'Driver\'s License'),
        ('other', 'Other Government ID'),
    ]
    
    POSITION_CHOICES = [
        ('ceo', 'Chief Executive Officer (CEO)'),
        ('director', 'Director'),
        ('general_manager', 'General Manager'),
        ('managing_director', 'Managing Director'),
        ('president', 'President'),
        ('vice_president', 'Vice President'),
        ('administrator', 'Administrator'),
        ('legal_officer', 'Legal Officer'),
        ('authorized_signatory', 'Authorized Signatory'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to participant (hospital, pharmacy, or insurance company)
    participant = models.OneToOneField(
        'Participant',
        on_delete=models.CASCADE,
        related_name='legal_representative',
        limit_choices_to={'role__in': ['hospital', 'pharmacy', 'insurance_company']}
    )
    
    # Personal Information
    full_name = models.CharField(
        max_length=255,
        help_text='Full legal name of the representative'
    )
    email = models.EmailField(
        help_text='Official email address of the representative'
    )
    phone_number = models.CharField(
        max_length=20,
        help_text='Direct phone number'
    )
    
    # Position/Title
    position = models.CharField(
        max_length=50,
        choices=POSITION_CHOICES,
        help_text='Official position in the organization'
    )
    position_other = models.CharField(
        max_length=100,
        blank=True,
        help_text='Specify if position is "Other"'
    )
    
    # Identification Documents
    id_type = models.CharField(
        max_length=20,
        choices=ID_TYPE_CHOICES,
        help_text='Type of identification document'
    )
    id_number = models.CharField(
        max_length=100,
        help_text='Identification document number'
    )
    id_expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text='Expiration date of ID document'
    )
    
    # Document Uploads
    id_document_front = models.FileField(
        upload_to='legal_representatives/id_documents/',
        help_text='Front side of ID document (passport, national ID, etc.)'
    )
    id_document_back = models.FileField(
        upload_to='legal_representatives/id_documents/',
        blank=True,
        help_text='Back side of ID document (if applicable)'
    )
    proof_of_position = models.FileField(
        upload_to='legal_representatives/proof_documents/',
        blank=True,
        help_text='Document proving position (appointment letter, board resolution, etc.)'
    )
    
    # Additional Information
    date_of_appointment = models.DateField(
        null=True,
        blank=True,
        help_text='Date appointed to current position'
    )
    authorization_scope = models.TextField(
        blank=True,
        help_text='Scope of authorization and signing authority'
    )
    
    # Verification Status
    is_verified = models.BooleanField(
        default=False,
        help_text='Whether the representative information has been verified by admin'
    )
    verified_by = models.ForeignKey(
        'Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_representatives'
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'legal_representatives'
        verbose_name = 'Legal Representative'
        verbose_name_plural = 'Legal Representatives'
    
    def __str__(self):
        return f"{self.full_name} - {self.participant.full_name}"
    
    def get_position_display_full(self):
        """Get full position display including 'other' specification"""
        if self.position == 'other' and self.position_other:
            return self.position_other
        return self.get_position_display()
    
    def is_id_expired(self):
        """Check if ID document is expired"""
        if self.id_expiry_date:
            from django.utils import timezone
            return self.id_expiry_date < timezone.now().date()
        return False
    
    @property
    def verification_status(self):
        """Get human-readable verification status"""
        if self.is_verified:
            return 'Verified'
        return 'Pending Verification'
