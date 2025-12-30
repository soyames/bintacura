import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.db import connections

def migrate_provider_data():
    render_db = 'frankfurt'
    aws_db = 'default'
    
    render_conn = connections[render_db]
    aws_conn = connections[aws_db]
    
    print("\n" + "="*70)
    print("MIGRATING PROVIDER DATA: Render → AWS")
    print("="*70 + "\n")
    
    # Migrate doctor_data
    print("Migrating doctor_data...")
    with render_conn.cursor() as render_cur:
        render_cur.execute("""
            SELECT id, specialization, license_number, years_of_experience,
                   qualifications, consultation_fee, bio, languages_spoken,
                   rating, total_reviews, total_consultations, 
                   is_available_for_telemedicine, participant_id
            FROM doctor_data
        """)
        doctors = render_cur.fetchall()
        
        if doctors:
            with aws_conn.cursor() as aws_cur:
                for doc in doctors:
                    try:
                        aws_cur.execute("""
                            INSERT INTO doctor_data 
                            (id, specialization, license_number, years_of_experience,
                             qualifications, consultation_fee, bio, languages_spoken,
                             rating, total_reviews, total_consultations,
                             is_available_for_telemedicine, participant_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, doc)
                        print(f"  ✓ Migrated doctor {doc[2]}")
                    except Exception as e:
                        print(f"  ✗ Failed doctor {doc[2]}: {e}")
            print(f"✅ Migrated {len(doctors)} doctors\n")
        else:
            print("  No doctors to migrate\n")
    
    # Migrate hospital_data
    print("Migrating hospital_data...")
    with render_conn.cursor() as render_cur:
        render_cur.execute("""
            SELECT id, hospital_name, registration_number, license_number,
                   hospital_type, bed_capacity, specialties, services_offered,
                   emergency_services, operating_hours, contact_person,
                   contact_phone, accreditation_status, accreditation_body,
                   accreditation_date, participant_id
            FROM hospital_data
        """)
        hospitals = render_cur.fetchall()
        
        if hospitals:
            with aws_conn.cursor() as aws_cur:
                for hosp in hospitals:
                    try:
                        aws_cur.execute("""
                            INSERT INTO hospital_data 
                            (id, hospital_name, registration_number, license_number,
                             hospital_type, bed_capacity, specialties, services_offered,
                             emergency_services, operating_hours, contact_person,
                             contact_phone, accreditation_status, accreditation_body,
                             accreditation_date, participant_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, hosp)
                        print(f"  ✓ Migrated hospital {hosp[1]}")
                    except Exception as e:
                        print(f"  ✗ Failed hospital {hosp[1]}: {e}")
            print(f"✅ Migrated {len(hospitals)} hospitals\n")
        else:
            print("  No hospitals to migrate\n")
    
    # Migrate insurance_company_data
    print("Migrating insurance_company_data...")
    with render_conn.cursor() as render_cur:
        render_cur.execute("""
            SELECT id, company_name, registration_number, license_number,
                   insurance_types, coverage_areas, contact_person, contact_phone,
                   accreditation_status, accreditation_body, accreditation_date,
                   participant_id
            FROM insurance_company_data
        """)
        insurance_companies = render_cur.fetchall()
        
        if insurance_companies:
            with aws_conn.cursor() as aws_cur:
                for ins in insurance_companies:
                    try:
                        aws_cur.execute("""
                            INSERT INTO insurance_company_data 
                            (id, company_name, registration_number, license_number,
                             insurance_types, coverage_areas, contact_person, contact_phone,
                             accreditation_status, accreditation_body, accreditation_date,
                             participant_id)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (id) DO NOTHING
                        """, ins)
                        print(f"  ✓ Migrated insurance {ins[1]}")
                    except Exception as e:
                        print(f"  ✗ Failed insurance {ins[1]}: {e}")
            print(f"✅ Migrated {len(insurance_companies)} insurance companies\n")
        else:
            print("  No insurance companies to migrate\n")
    
    print("="*70)
    print("PROVIDER DATA MIGRATION COMPLETE")
    print("="*70)

if __name__ == "__main__":
    migrate_provider_data()
