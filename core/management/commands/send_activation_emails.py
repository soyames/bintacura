"""
Management command to send activation emails to all unverified participants
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Participant
from authentication.email_service import send_verification_email
from authentication.tokens import generate_activation_code


class Command(BaseCommand):
    help = 'Send activation emails to all participants who have not verified their email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send to all participants regardless of verification status',
        )
        parser.add_argument(
            '--test-emails',
            nargs='+',
            default=['soyames@gmail.com', 'smartwork608@gmail.com'],
            help='Test emails to exclude (space-separated)',
        )

    def handle(self, *args, **options):
        force = options['force']
        test_emails = options['test_emails']
        
        self.stdout.write("="*70)
        self.stdout.write("SENDING ACTIVATION EMAILS")
        self.stdout.write("="*70)
        
        # Get participants who need activation
        if force:
            participants = Participant.objects.exclude(email__in=test_emails)
            self.stdout.write(f"\nForce mode: Sending to ALL participants except test emails")
        else:
            participants = Participant.objects.filter(
                is_email_verified=False
            ).exclude(email__in=test_emails)
            self.stdout.write(f"\nSending to unverified participants only (excluding test emails)")
        
        self.stdout.write(f"Test emails excluded: {', '.join(test_emails)}")
        self.stdout.write(f"Participants to process: {participants.count()}\n")
        
        if participants.count() == 0:
            self.stdout.write(self.style.WARNING("No participants need activation emails"))
            return
        
        sent = 0
        failed = 0
        
        for participant in participants:
            try:
                # Generate new activation code
                activation_code = generate_activation_code()
                participant.activation_code = activation_code
                participant.activation_code_created_at = timezone.now()
                participant.save()
                
                # Send verification email
                result = send_verification_email(participant, activation_code)
                
                if result:
                    sent += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ {participant.email} ({participant.role}) - Code: {activation_code}"
                        )
                    )
                else:
                    failed += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f"❌ {participant.email} - Failed to send"
                        )
                    )
                    
            except Exception as e:
                failed += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ {participant.email} - Error: {str(e)}"
                    )
                )
        
        # Summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*70)
        self.stdout.write(f"Total processed: {participants.count()}")
        self.stdout.write(self.style.SUCCESS(f"Successfully sent: {sent}"))
        if failed > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed}"))
        
        self.stdout.write("\nParticipants should check their email inbox and spam folder.")
        self.stdout.write("Email from: no-reply@bintacura.org")
        self.stdout.write("Subject: Vérification de votre compte - BINTACURA")
