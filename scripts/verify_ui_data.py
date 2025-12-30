#!/usr/bin/env python
"""
Verify that all provider data is properly set up for UI display
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config')
django.setup()

from django.db import connections

def verify_ui_data():
    print('\n' + '='*70)
    print('UI DATA VERIFICATION - AWS DATABASE')
    print('='*70 + '\n')
    
    with connections['default'].cursor() as c:
        # Check doctors
        c.execute('''
            SELECT p.uid, p.full_name, p.email, COUNT(ds.id) as services_count
            FROM participants p
            LEFT JOIN doctor_services ds ON ds.doctor_id = p.uid
            WHERE p.role = 'doctor' AND p.is_active = true
            GROUP BY p.uid, p.full_name, p.email
            ORDER BY p.full_name
        ''')
        doctors = c.fetchall()
        print(f'DOCTORS ({len(doctors)} active - should be visible in appointment booking):')
        for uid, name, email, services in doctors:
            display_name = name or email
            print(f'  ✓ {display_name} - {services} services')
        
        # Check hospitals
        c.execute('''
            SELECT p.uid, p.full_name, p.email, hd.id as has_data
            FROM participants p
            LEFT JOIN hospital_data hd ON hd.participant_id = p.uid
            WHERE p.role = 'hospital' AND p.is_active = true
            ORDER BY p.full_name
        ''')
        hospitals = c.fetchall()
        print(f'\nHOSPITALS ({len(hospitals)} active - should be visible in hospital booking):')
        for uid, name, email, has_data in hospitals:
            display_name = name or email
            status = '✓' if has_data else '✗ MISSING hospital_data'
            print(f'  {status} {display_name}')
        
        # Check pharmacies
        c.execute('''
            SELECT p.uid, p.full_name, p.email
            FROM participants p
            WHERE p.role = 'pharmacy' AND p.is_active = true
            ORDER BY p.full_name
        ''')
        pharmacies = c.fetchall()
        print(f'\nPHARMACIES ({len(pharmacies)} active - should be visible):')
        for uid, name, email in pharmacies:
            display_name = name or email
            print(f'  ✓ {display_name}')
        
        # Check insurance companies
        c.execute('''
            SELECT p.uid, p.full_name, p.email, COUNT(ip.id) as packages
            FROM participants p
            LEFT JOIN insurance_packages ip ON ip.company_id = p.uid
            WHERE p.role = 'insurance_company' AND p.is_active = true
            GROUP BY p.uid, p.full_name, p.email
            ORDER BY p.full_name
        ''')
        insurers = c.fetchall()
        print(f'\nINSURANCE COMPANIES ({len(insurers)} active - should be visible):')
        for uid, name, email, packages in insurers:
            display_name = name or email
            print(f'  ✓ {display_name} - {packages} packages')
        
        # Check patients
        c.execute('''
            SELECT COUNT(*) FROM participants 
            WHERE role = 'patient' AND is_active = true
        ''')
        patient_count = c.fetchone()[0]
        print(f'\nPATIENTS: {patient_count} active (including test accounts)')
        
        # Check system configuration
        c.execute('''
            SELECT key, value FROM system_configuration 
            WHERE key IN ('DEFAULT_CONSULTATION_FEE_XOF', 'DEFAULT_CURRENCY')
            ORDER BY key
        ''')
        print('\nSYSTEM DEFAULTS:')
        for key, value in c.fetchall():
            print(f'  {key}: {value}')
    
    print('\n' + '='*70)
    print('VERIFICATION COMPLETE')
    print('='*70 + '\n')

if __name__ == '__main__':
    verify_ui_data()
