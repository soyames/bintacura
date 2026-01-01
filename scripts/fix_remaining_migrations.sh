#!/bin/bash

echo "🔧 Fixing ALL remaining migrations (including doctor)..."
echo "=========================================================="
echo ""

# Fake doctor migrations that are creating existing tables/columns
echo "🔄 Faking doctor migrations..."
python manage.py migrate doctor 0004_add_doctor_affiliation_model --fake
python manage.py migrate doctor 0005_alter_doctorservice_currency --fake
python manage.py migrate doctor 0006_remove_doctordata_affiliated_hospitals_and_more --fake
python manage.py migrate doctor 0007_set_default_consultation_fee --fake

echo ""
echo "🔄 Running all remaining migrations..."
python manage.py migrate

echo ""
echo "📋 Checking migration status..."
python manage.py showmigrations core doctor appointments

echo ""
echo "📋 Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat

echo ""
echo "✅ All done! Check payment functionality now."
