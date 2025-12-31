"""
Management command to verify and repair rating cache consistency.

Usage:
    python manage.py verify_rating_cache
    python manage.py verify_rating_cache --repair
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Avg
from core.models import Review, Participant
from hospital.models import HospitalData
from doctor.models import DoctorData


class Command(BaseCommand):
    help = 'Verify rating cache consistency and optionally repair inconsistencies'

    def add_arguments(self, parser):
        parser.add_argument(
            '--repair',
            action='store_true',
            help='Repair inconsistent ratings (not just report them)',
        )

    def handle(self, *args, **options):
        repair = options['repair']
        
        self.stdout.write(self.style.WARNING('Starting rating cache verification...\n'))
        
        inconsistencies_found = 0
        repairs_made = 0
        
        # Check hospitals
        self.stdout.write('Checking hospitals...')
        for hospital_data in HospitalData.objects.all():
            actual_rating = hospital_data.get_actual_rating()
            actual_reviews = hospital_data.get_actual_total_reviews()
            
            if (abs(hospital_data.rating - actual_rating) > 0.05 or 
                hospital_data.total_reviews != actual_reviews):
                inconsistencies_found += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {hospital_data.participant.full_name}: '
                        f'Cached={hospital_data.rating}/{hospital_data.total_reviews}, '
                        f'Actual={actual_rating}/{actual_reviews}'
                    )
                )
                
                if repair:
                    hospital_data.rating = actual_rating
                    hospital_data.total_reviews = actual_reviews
                    hospital_data.save(update_fields=['rating', 'total_reviews'])
                    repairs_made += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✅ Repaired'))
        
        # Check doctors
        self.stdout.write('\nChecking doctors...')
        for doctor_data in DoctorData.objects.all():
            approved_reviews = Review.objects.filter(
                reviewed_type='doctor',
                reviewed_id=doctor_data.participant.uid,
                is_approved=True
            )
            actual_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            actual_rating = round(actual_rating, 1) if actual_rating else 0.0
            actual_reviews = approved_reviews.count()
            
            if (abs(doctor_data.rating - actual_rating) > 0.05 or 
                doctor_data.total_reviews != actual_reviews):
                inconsistencies_found += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {doctor_data.participant.full_name}: '
                        f'Cached={doctor_data.rating}/{doctor_data.total_reviews}, '
                        f'Actual={actual_rating}/{actual_reviews}'
                    )
                )
                
                if repair:
                    doctor_data.rating = actual_rating
                    doctor_data.total_reviews = actual_reviews
                    doctor_data.save(update_fields=['rating', 'total_reviews'])
                    repairs_made += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✅ Repaired'))
        
        # Check pharmacies
        self.stdout.write('\nChecking pharmacies...')
        for pharmacy in Participant.objects.filter(role='pharmacy'):
            approved_reviews = Review.objects.filter(
                reviewed_type='pharmacy',
                reviewed_id=pharmacy.uid,
                is_approved=True
            )
            actual_rating = approved_reviews.aggregate(Avg('rating'))['rating__avg']
            actual_rating = round(actual_rating, 1) if actual_rating else 0.0
            actual_reviews = approved_reviews.count()
            
            if (abs(pharmacy.rating - actual_rating) > 0.05 or 
                pharmacy.total_reviews != actual_reviews):
                inconsistencies_found += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'  ❌ {pharmacy.full_name}: '
                        f'Cached={pharmacy.rating}/{pharmacy.total_reviews}, '
                        f'Actual={actual_rating}/{actual_reviews}'
                    )
                )
                
                if repair:
                    pharmacy.rating = actual_rating
                    pharmacy.total_reviews = actual_reviews
                    pharmacy.save(update_fields=['rating', 'total_reviews'])
                    repairs_made += 1
                    self.stdout.write(self.style.SUCCESS(f'    ✅ Repaired'))
        
        # Summary
        self.stdout.write('\n' + '='*60)
        if inconsistencies_found == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ All rating caches are consistent! No issues found.'
                )
            )
        else:
            if repair:
                self.stdout.write(
                    self.style.WARNING(
                        f'Found {inconsistencies_found} inconsistencies, '
                        f'repaired {repairs_made}.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'❌ Found {inconsistencies_found} inconsistencies. '
                        f'Run with --repair to fix them.'
                    )
                )
        self.stdout.write('='*60)
