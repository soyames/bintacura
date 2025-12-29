from django.db import models
from django.core.validators import FileExtensionValidator
from django.utils import timezone


class Advertisement(models.Model):  # Manages advertisements displayed in patient dashboard carousel
    """
    Model for managing advertisements displayed in patient dashboard carousel
    """
    MEDIA_TYPE_CHOICES = [
        ('image', 'Image'),
        ('video', 'Video'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]

    # Basic Info
    title = models.CharField(max_length=200, help_text="Internal title for the ad (not displayed to users)")

    # Media
    media_type = models.CharField(max_length=10, choices=MEDIA_TYPE_CHOICES, default='image')
    image = models.ImageField(
        upload_to='ads/images/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp'])],
        help_text="Upload an image for the ad background"
    )
    video = models.FileField(
        upload_to='ads/videos/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['mp4', 'webm', 'ogg'])],
        help_text="Upload a video for the ad background"
    )

    # Content
    heading = models.CharField(max_length=150, help_text="Main heading displayed on the ad")
    subheading = models.CharField(max_length=200, blank=True, help_text="Subheading or description (optional)")

    # Call to Action Button
    button_text = models.CharField(max_length=50, default="Learn More", help_text="Text displayed on the button")
    button_link = models.URLField(max_length=500, help_text="URL the button links to (can be internal or external)")
    button_opens_new_tab = models.BooleanField(default=False, help_text="Open link in new tab")

    # Scheduling
    start_date = models.DateTimeField(default=timezone.now, help_text="When to start showing this ad")
    end_date = models.DateTimeField(null=True, blank=True, help_text="When to stop showing this ad (optional)")

    # Display Settings
    display_order = models.IntegerField(default=0, help_text="Order in carousel (lower numbers appear first)")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    # Analytics
    view_count = models.IntegerField(default=0, help_text="Number of times ad was displayed")
    click_count = models.IntegerField(default=0, help_text="Number of times button was clicked")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'core.Participant',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ads_created'
    )

    class Meta:  # Meta class implementation
        ordering = ['display_order', '-created_at']
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'

    def __str__(self):  # Return string representation
        return f"{self.title} ({self.get_status_display()})"

    def is_active(self):
        """Check if ad should be displayed based on status and dates"""
        if self.status != 'active':
            return False

        now = timezone.now()
        if self.start_date and now < self.start_date:
            return False

        if self.end_date and now > self.end_date:
            return False

        return True

    def get_media_url(self):
        """Get the URL of the media (image or video)"""
        if self.media_type == 'image' and self.image:
            return self.image.url
        elif self.media_type == 'video' and self.video:
            return self.video.url
        return None

    def increment_views(self):
        """Increment view count"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    def increment_clicks(self):
        """Increment click count"""
        self.click_count += 1
        self.save(update_fields=['click_count'])

    @property
    def click_through_rate(self):
        """Calculate click-through rate"""
        if self.view_count == 0:
            return 0
        return (self.click_count / self.view_count) * 100
