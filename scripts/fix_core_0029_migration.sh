#!/bin/bash

echo "🔧 Fixing core.0029_fix_currency_defaults_to_xof migration..."
echo "=============================================================="
echo ""
echo "📋 This migration tries to add 'amount_xof' column"
echo "   but it already exists in the database"
echo ""

echo "🔄 Faking migration 0029..."
python manage.py migrate core 0029_fix_currency_defaults_to_xof --fake

echo ""
echo "🔄 Now running all remaining migrations..."
python manage.py migrate

echo ""
echo "✅ Done! Now restart services:"
echo "   sudo systemctl restart bintacura"
echo "   sudo systemctl restart bintacura-celery"
echo "   sudo systemctl restart bintacura-celerybeat"