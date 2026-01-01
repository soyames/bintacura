#!/bin/bash

echo "🔧 Faking core.0028_delete_providerservice migration..."
echo "======================================================"
echo ""

echo "📋 This migration tries to delete a table that doesn't exist"
echo "   We'll fake it to mark it as applied without running it"
echo ""

echo "🚀 Faking migration 0028..."
python manage.py migrate core 0028_delete_providerservice --fake

echo ""
echo "📋 Running all remaining migrations..."
python manage.py migrate

echo ""
echo "✅ Migration fix complete!"
echo ""
echo "📋 Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat

echo ""
echo "✅ All done! Services restarted."