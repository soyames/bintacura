#!/usr/bin/env bash
# =============================================================================
# VITACARE - HEALTH CHECK SCRIPT FOR PRODUCTION
# =============================================================================
# Quick script to verify all production systems are working
# Run before deploying to check everything is configured correctly
# =============================================================================

echo "🏥 VitaCare Production Health Check"
echo "===================================="
echo ""

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Virtual environment not activated!"
    echo "Run: source venv/bin/activate (Linux/Mac) or venv\Scripts\activate (Windows)"
    exit 1
fi

# Check environment file
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    exit 1
else
    echo "✅ Environment file found"
fi

# Check database connection
echo ""
echo "Checking database connection..."
python manage.py check --database default
if [ $? -eq 0 ]; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Check migrations
echo ""
echo "Checking migrations..."
python manage.py showmigrations --list | grep "\[ \]"
if [ $? -eq 0 ]; then
    echo "⚠️  Unapplied migrations found"
    echo "Run: python manage.py migrate"
else
    echo "✅ All migrations applied"
fi

# Check static files
echo ""
echo "Checking static files..."
if [ ! -d staticfiles ]; then
    echo "⚠️  Static files not collected"
    echo "Run: python manage.py collectstatic"
else
    echo "✅ Static files collected"
fi

# Check security settings
echo ""
echo "Checking Django security..."
python manage.py check --deploy
if [ $? -eq 0 ]; then
    echo "✅ Security check passed"
else
    echo "⚠️  Security warnings found (review above)"
fi

# Check AWS SES configuration
echo ""
echo "Checking AWS SES configuration..."
python -c "
import os
from decouple import config

use_ses = config('USE_SES', default=False, cast=bool)
if use_ses:
    aws_key = config('AWS_ACCESS_KEY_ID', default='')
    aws_secret = config('AWS_SECRET_ACCESS_KEY', default='')
    if aws_key and aws_secret:
        print('✅ AWS SES configured')
    else:
        print('❌ AWS SES credentials missing')
else:
    print('ℹ️  AWS SES not enabled')
"

echo ""
echo "===================================="
echo "🎉 Health check complete!"
echo ""
echo "Next steps:"
echo "1. Fix any ❌ errors above"
echo "2. Review ⚠️  warnings"
echo "3. Test locally: python manage.py runserver 8080"
echo "4. Deploy to Render: git push origin main"
echo ""
