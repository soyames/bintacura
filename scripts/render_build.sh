#!/usr/bin/env bash
# =============================================================================
# RENDER BUILD SCRIPT FOR BINTACURA
# =============================================================================
# This script runs during the build phase on Render.com
# It installs dependencies, collects static files, and runs migrations
# =============================================================================

set -o errexit  # Exit on error

echo "🚀 Starting BINTACURA build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install additional production dependencies
echo "📦 Installing production dependencies..."
pip install gunicorn whitenoise psycopg2-binary dj-database-url

# Pre-migration database check
echo "🔍 Checking database integrity before migration..."
python manage.py check_database_integrity || echo "⚠️ Database integrity check unavailable"

# Run database migrations
echo "🔄 Running database migrations..."
python manage.py migrate --no-input

# Post-migration database check
echo "✅ Verifying database after migration..."
python manage.py check_database_integrity || echo "⚠️ Database integrity check unavailable"

# Collect static files (CRITICAL for CSS/JS to work on production)
echo "📁 Collecting static files..."
python manage.py collectstatic --no-input --clear
echo "✅ Static files collected to staticfiles/"

# Create cache table
echo "💾 Creating cache table..."
python manage.py createcachetable || echo "Cache table already exists"

# Sync system configuration with settings
echo "⚙️  Syncing system configuration..."
python manage.py sync_system_config || echo "⚠️ System config sync unavailable"

# Compile translations
echo "🌍 Compiling translations..."
python manage.py compilemessages || echo "No translations to compile"

# Verify static files were collected
echo "📊 Verifying static files..."
if [ -d "staticfiles" ]; then
    echo "✅ staticfiles/ directory exists"
    ls -lh staticfiles/ || true
else
    echo "⚠️ Warning: staticfiles/ directory not found"
fi

echo "✅ Build completed successfully!"
