"""
Management command to audit views for N+1 query problems.

Usage:
    python manage.py audit_queries
    python manage.py audit_queries --app appointments
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db.models import Prefetch
import ast
import os


class Command(BaseCommand):
    help = 'Audit views for potential N+1 query problems'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app',
            type=str,
            help='Specific app to audit (e.g., appointments, payments)',
        )

    def handle(self, *args, **options):
        target_app = options.get('app')
        
        self.stdout.write(self.style.WARNING('Starting N+1 Query Audit...\n'))
        
        findings = []
        
        # Get all installed apps
        if target_app:
            app_configs = [apps.get_app_config(target_app)]
        else:
            app_configs = [app for app in apps.get_app_configs() 
                          if not app.name.startswith('django.')]
        
        for app_config in app_configs:
            app_path = app_config.path
            views_file = os.path.join(app_path, 'views.py')
            
            if os.path.exists(views_file):
                self.stdout.write(f'\nChecking {app_config.name}/views.py...')
                issues = self._check_file_for_n_plus_one(views_file, app_config.name)
                findings.extend(issues)
        
        # Print summary
        self.stdout.write('\n' + '='*70)
        if findings:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  Found {len(findings)} potential N+1 query issues:\n'
                )
            )
            for finding in findings:
                self.stdout.write(
                    self.style.ERROR(f"  • {finding['file']}:{finding['line']}")
                )
                self.stdout.write(f"    {finding['issue']}")
                self.stdout.write(
                    self.style.SUCCESS(f"    Fix: {finding['fix']}\n")
                )
        else:
            self.stdout.write(
                self.style.SUCCESS('\n✅ No obvious N+1 query issues found!')
            )
        
        self.stdout.write('='*70 + '\n')
        
        # Print optimization patterns
        self._print_optimization_guide()
    
    def _check_file_for_n_plus_one(self, filepath, app_name):
        """Check a Python file for common N+1 query patterns"""
        issues = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for .all() followed by attribute access in loop
                if '.objects.all()' in line_stripped or '.objects.filter(' in line_stripped:
                    # Look ahead for potential N+1 in next 20 lines
                    for j in range(i, min(i+20, len(lines))):
                        next_line = lines[j].strip()
                        if 'for ' in next_line and ' in ' in next_line:
                            # Found a loop, check if it accesses foreign keys
                            for k in range(j, min(j+10, len(lines))):
                                check_line = lines[k].strip()
                                if '.get(' in check_line or 'ForeignKey' in check_line:
                                    issues.append({
                                        'file': f'{app_name}/views.py',
                                        'line': i,
                                        'issue': 'Potential N+1: Query followed by loop with FK access',
                                        'fix': 'Use select_related() for ForeignKey or prefetch_related() for ManyToMany'
                                    })
                                    break
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error reading {filepath}: {str(e)}')
            )
        
        return issues
    
    def _print_optimization_guide(self):
        """Print query optimization guide"""
        self.stdout.write('\n' + self.style.WARNING('QUERY OPTIMIZATION PATTERNS:'))
        self.stdout.write('\n1️⃣  select_related() - For ForeignKey and OneToOne')
        self.stdout.write('   Use when accessing related objects via ForeignKey')
        self.stdout.write(self.style.SUCCESS('''
   # Bad (N+1 queries)
   appointments = Appointment.objects.all()
   for apt in appointments:
       print(apt.doctor.name)  # Separate query for each doctor!
   
   # Good (1 query with JOIN)
   appointments = Appointment.objects.select_related('doctor').all()
   for apt in appointments:
       print(apt.doctor.name)  # No extra query!
'''))
        
        self.stdout.write('\n2️⃣  prefetch_related() - For ManyToMany and Reverse ForeignKey')
        self.stdout.write('   Use when accessing reverse relationships or M2M')
        self.stdout.write(self.style.SUCCESS('''
   # Bad (N+1 queries)
   doctors = Participant.objects.filter(role='doctor')
   for doctor in doctors:
       print(doctor.doctor_appointments.count())  # Query per doctor!
   
   # Good (2 queries total)
   doctors = Participant.objects.filter(role='doctor')\\
       .prefetch_related('doctor_appointments')
   for doctor in doctors:
       print(doctor.doctor_appointments.count())  # No extra query!
'''))
        
        self.stdout.write('\n3️⃣  Nested prefetch_related() with Prefetch()')
        self.stdout.write('   For filtering prefetched data')
        self.stdout.write(self.style.SUCCESS('''
   from django.db.models import Prefetch
   
   # Only prefetch confirmed appointments
   doctors = Participant.objects.filter(role='doctor')\\
       .prefetch_related(
           Prefetch(
               'doctor_appointments',
               queryset=Appointment.objects.filter(status='confirmed')
           )
       )
'''))
        
        self.stdout.write('\n4️⃣  only() and defer() - Load only needed fields')
        self.stdout.write('   Reduce data transfer when you need few fields')
        self.stdout.write(self.style.SUCCESS('''
   # Only load specific fields
   appointments = Appointment.objects.only('id', 'status', 'appointment_date')
   
   # Defer loading heavy fields
   participants = Participant.objects.defer('profile_picture', 'bio')
'''))
        
        self.stdout.write('\n5️⃣  annotate() and aggregate() - Database-level calculations')
        self.stdout.write('   Let the database do the math')
        self.stdout.write(self.style.SUCCESS('''
   from django.db.models import Count, Avg
   
   # Bad (N queries)
   for doctor in doctors:
       count = doctor.doctor_appointments.count()  # Query each time!
   
   # Good (1 query with aggregation)
   doctors = Participant.objects.filter(role='doctor')\\
       .annotate(appointment_count=Count('doctor_appointments'))
'''))
        
        self.stdout.write('\n' + '='*70 + '\n')
