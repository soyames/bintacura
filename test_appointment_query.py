import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from appointments.models import Appointment
from core.models import Participant

# Get a patient
patient = Participant.objects.filter(role='patient').first()
print(f"Patient: {patient.email}")

# Try the query that's failing
try:
    appointments = Appointment.objects.filter(
        patient=patient
    ).select_related('doctor', 'hospital', 'service', 'beneficiary').order_by("-appointment_date", "-appointment_time")
    
    print(f"\n✅ Query successful! Found {appointments.count()} appointments")
    
    for appt in appointments[:3]:
        print(f"\nAppointment: {appt.id}")
        print(f"  Doctor: {appt.doctor}")
        print(f"  Hospital: {appt.hospital}")
        print(f"  Service: {appt.service}")
        print(f"  Date: {appt.appointment_date} {appt.appointment_time}")
        
except Exception as e:
    print(f"\n❌ Query failed: {e}")
    import traceback
    traceback.print_exc()
