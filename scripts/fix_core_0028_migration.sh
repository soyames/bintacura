#!/bin/bash

echo "🔧 Faking core.0028_delete_providerservice migration..."
echo "========================================================="
echo ""

echo "📋 This migration tries to delete 'participant_services' table"
echo "   but the table doesn't exist (already deleted or never created)"
echo ""

echo "🔄 Faking migration 0028..."
python manage.py migrate core 0028_delete_providerservice --fake

echo ""
echo "🔄 Now running all remaining migrations..."
python manage.py migrate

echo ""
echo "✅ Done! Now restart services:"
echo "   sudo systemctl restart bintacura"
echo "   sudo systemctl restart bintacura-celery"
echo "   sudo systemctl restart bintacura-celerybeat"
