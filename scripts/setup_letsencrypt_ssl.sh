#!/bin/bash
# =============================================================================
# Let's Encrypt SSL Setup Script for AWS EC2
# =============================================================================
# This script sets up HTTPS with Let's Encrypt SSL certificates
# Run on AWS EC2: bash setup_letsencrypt_ssl.sh
# =============================================================================

set -e  # Exit on error

echo "======================================================================"
echo "  Let's Encrypt SSL Setup - BintaCura"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="bintacura.org"
WWW_DOMAIN="www.bintacura.org"
EMAIL="contacts@bintacura.org"
WEBROOT="/usr/share/nginx/html"

echo -e "${YELLOW}Step 1: Cleaning up old certificates${NC}"
echo "----------------------------------------------------------------------"
sudo rm -rf /etc/ssl/cloudflare/ 2>/dev/null || true
echo -e "${GREEN}✓ Old certificates removed${NC}"
echo ""

echo -e "${YELLOW}Step 2: Setting up HTTP-only Nginx (temporary)${NC}"
echo "----------------------------------------------------------------------"
sudo cp /home/ec2-user/bintacura/nginx/bintacura_http_only.conf /etc/nginx/conf.d/bintacura.conf
sudo nginx -t
sudo systemctl reload nginx
echo -e "${GREEN}✓ HTTP configuration active${NC}"
echo ""

echo -e "${YELLOW}Step 3: Verifying DNS resolution${NC}"
echo "----------------------------------------------------------------------"
RESOLVED_IP=$(dig +short $DOMAIN | head -n1)
echo "  $DOMAIN resolves to: $RESOLVED_IP"
if [ -z "$RESOLVED_IP" ]; then
    echo -e "${RED}✗ DNS not resolving! Wait for propagation and try again.${NC}"
    exit 1
fi
echo -e "${GREEN}✓ DNS resolves correctly${NC}"
echo ""

echo -e "${YELLOW}Step 4: Obtaining Let's Encrypt certificate${NC}"
echo "----------------------------------------------------------------------"
sudo certbot certonly --webroot \
  -w $WEBROOT \
  -d $DOMAIN \
  -d $WWW_DOMAIN \
  --email $EMAIL \
  --agree-tos \
  --non-interactive

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Certificate obtained successfully${NC}"
else
    echo -e "${RED}✗ Certificate request failed${NC}"
    echo "Check logs: sudo tail -f /var/log/letsencrypt/letsencrypt.log"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 5: Configuring HTTPS in Nginx${NC}"
echo "----------------------------------------------------------------------"
sudo cp /home/ec2-user/bintacura/nginx/bintacura_https_letsencrypt.conf /etc/nginx/conf.d/bintacura.conf
sudo nginx -t
if [ $? -eq 0 ]; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ HTTPS configuration active${NC}"
else
    echo -e "${RED}✗ Nginx configuration error${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}Step 6: Setting up auto-renewal${NC}"
echo "----------------------------------------------------------------------"
sudo certbot renew --dry-run
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer
echo -e "${GREEN}✓ Auto-renewal configured${NC}"
echo ""

echo -e "${YELLOW}Step 7: Verifying SSL${NC}"
echo "----------------------------------------------------------------------"
sleep 3
HTTPS_STATUS=$(curl -o /dev/null -s -w "%{http_code}" https://$DOMAIN)
if [ "$HTTPS_STATUS" == "200" ]; then
    echo -e "${GREEN}✓ HTTPS is working! Status: $HTTPS_STATUS${NC}"
else
    echo -e "${RED}✗ HTTPS verification failed. Status: $HTTPS_STATUS${NC}"
fi
echo ""

echo "======================================================================"
echo -e "${GREEN}  SSL Setup Complete!${NC}"
echo "======================================================================"
echo ""
echo "  🔒 Your site is now secure:"
echo "     https://bintacura.org"
echo "     https://www.bintacura.org"
echo ""
echo "  📅 Certificate Details:"
sudo certbot certificates | grep -A 5 "Certificate Name: $DOMAIN"
echo ""
echo "  🔄 Auto-renewal Status:"
sudo systemctl status certbot-renew.timer --no-pager | grep Active
echo ""
echo "======================================================================"
