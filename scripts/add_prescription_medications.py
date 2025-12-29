import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bintacura_backend.settings')
django.setup()

from prescriptions.models import Prescription, PrescriptionItem
from pharmacy.models import Medication
from core.models import Participant

prescription_id = '2ef1a9d6-41e3-4d4d-94eb-dfa7c0e7b09b'

try:
    prescription = Prescription.objects.get(id=prescription_id)
    print(f"Found prescription: {prescription.id}")
    print(f"Patient: {prescription.patient}")
    print(f"Doctor: {prescription.doctor if hasattr(prescription, 'doctor') else 'N/A'}")
    print(f"Created: {prescription.created_at}")
    
    # Check if doctor is properly linked
    if hasattr(prescription, 'doctor') and prescription.doctor:
        doctor = prescription.doctor
        print(f"Doctor details: {doctor.last_name}, Role: {doctor.role}")
    else:
        print("Doctor not properly linked!")
    
    # Get or create some test medications
    medications = []
    
    med_data = [
        {
            'name': 'Paracetamol 500mg',
            'generic_name': 'Paracetamol',
            'category': 'Analgesic',
            'description': 'Pain reliever and fever reducer',
            'dosage_form': 'tablet',
            'strength': '500mg'
        },
        {
            'name': 'Amoxicillin 250mg',
            'generic_name': 'Amoxicillin',
            'category': 'Antibiotic',
            'description': 'Antibiotic for bacterial infections',
            'dosage_form': 'capsule',
            'strength': '250mg'
        },
        {
            'name': 'Ibuprofen 400mg',
            'generic_name': 'Ibuprofen',
            'category': 'NSAID',
            'description': 'Anti-inflammatory and pain reliever',
            'dosage_form': 'tablet',
            'strength': '400mg'
        },
    ]
    
    for med_info in med_data:
        med, created = Medication.objects.get_or_create(
            name=med_info['name'],
            defaults={
                'generic_name': med_info['generic_name'],
                'category': med_info['category'],
                'description': med_info['description'],
                'dosage_forms': [med_info['dosage_form']],
                'strengths': [med_info['strength']],
                'requires_prescription': True
            }
        )
        medications.append(med)
        print(f"{'Created' if created else 'Found'} medication: {med.name}")
    
    # Add prescription items
    item_data = [
        {'dosage_form': 'tablet', 'strength': '500mg', 'quantity': 20, 'frequency': 'twice_daily', 'duration': 7, 'instructions': 'Take 1 tablet with water after meals'},
        {'dosage_form': 'capsule', 'strength': '250mg', 'quantity': 30, 'frequency': 'three_times_daily', 'duration': 10, 'instructions': 'Take 1 capsule with full glass of water'},
        {'dosage_form': 'tablet', 'strength': '400mg', 'quantity': 15, 'frequency': 'as_needed', 'duration': 5, 'instructions': 'Take 1 tablet as needed for pain, max 3 per day'},
    ]
    
    for i, med in enumerate(medications):
        item, created = PrescriptionItem.objects.get_or_create(
            prescription=prescription,
            medication=med,
            medication_name=med.name,
            defaults={
                'dosage': f'{item_data[i]["quantity"]} {item_data[i]["dosage_form"]}(s)',
                'dosage_form': item_data[i]['dosage_form'],
                'strength': item_data[i]['strength'],
                'quantity': item_data[i]['quantity'],
                'frequency': item_data[i]['frequency'],
                'duration_days': item_data[i]['duration'],
                'instructions': item_data[i]['instructions'],
                'route': 'oral',
                'timing': 'with_food' if i == 0 else 'with_water'
            }
        )
        print(f"{'Created' if created else 'Found'} prescription item: {med.name}")
    
    print(f"\n✅ Prescription {prescription_id} now has {prescription.items.count()} medications")
    
except Prescription.DoesNotExist:
    print(f"❌ Prescription {prescription_id} not found")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

