#!/bin/bash

echo "🔧 Fixing ALL remaining migration conflicts..."
echo "==============================================="
echo ""

# Fake migrations that try to add columns that already exist
migrations_to_fake=(
    "core.0030_participant_can_receive_payments_and_more"
    "core.0031_remove_refundrequest_refund_requ_provide_40b426_idx_and_more"
    "core.0032_add_refund_security_features"
    "core.0033_participant_rejection_reason_and_more"
)

for migration in "${migrations_to_fake[@]}"; do
    echo "🔄 Faking migration: $migration"
    python manage.py migrate ${migration%.*} ${migration##*.} --fake
    echo ""
done

echo "🔄 Running all remaining migrations..."
python manage.py migrate

echo ""
echo "✅ All migrations processed!"
echo ""
echo "📋 Restarting services..."
sudo systemctl restart bintacura
sudo systemctl restart bintacura-celery
sudo systemctl restart bintacura-celerybeat
sudo systemctl restart nginx

echo ""
echo "✅ All done! Services restarted."
