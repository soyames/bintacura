#!/bin/bash

# VitaCare.bj Domain Preparation Script
# This script ensures your platform is ready for the vitacare.bj domain

echo "=========================================="
echo "VitaCare.bj Domain Preparation"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "✗ Error: .env file not found"
    exit 1
fi

echo "✓ .env file found"

# Check if vitacare.bj is in ALLOWED_HOSTS
if grep -q "vitacare.bj" .env; then
    echo "✓ vitacare.bj found in configuration"
else
    echo "✗ vitacare.bj not found in .env"
    echo "  Please run this command to add it:"
    echo "  Add to ALLOWED_HOSTS: vitacare.bj,www.vitacare.bj"
    exit 1
fi

# Check if DomainSecurityMiddleware exists
if [ -f "core/domain_security_middleware.py" ]; then
    echo "✓ DomainSecurityMiddleware exists"
else
    echo "✗ DomainSecurityMiddleware not found"
    exit 1
fi

# Check Python availability
if command -v python &> /dev/null; then
    PYTHON_CMD=python
elif command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    echo "✗ Python not found"
    exit 1
fi

echo "✓ Python found: $PYTHON_CMD"

# Run security checks
echo ""
echo "Running security configuration checks..."
echo ""

$PYTHON_CMD scripts/configure_domain_security.py

echo ""
echo "=========================================="
echo "Next Steps for vitacare.bj Setup:"
echo "=========================================="
echo ""
echo "1. Configure DNS at your domain registrar:"
echo "   Type: CNAME"
echo "   Name: @"
echo "   Target: vitacare-ymfo.onrender.com"
echo ""
echo "   Type: CNAME"
echo "   Name: www"
echo "   Target: vitacare-ymfo.onrender.com"
echo ""
echo "2. Add custom domain in Render:"
echo "   - Go to dashboard.render.com"
echo "   - Settings → Custom Domains"
echo "   - Add: vitacare.bj"
echo "   - Add: www.vitacare.bj"
echo ""
echo "3. Wait for SSL provisioning (5-10 minutes)"
echo ""
echo "4. Enable SSL in Render environment variables:"
echo "   SECURE_SSL_REDIRECT=True"
echo "   SESSION_COOKIE_SECURE=True"
echo "   CSRF_COOKIE_SECURE=True"
echo ""
echo "5. Test the domain:"
echo "   https://vitacare.bj"
echo "   https://www.vitacare.bj"
echo ""
echo "Full guide: docs/VITACARE_BJ_DOMAIN_FORWARDING.md"
echo "=========================================="
