#!/bin/bash
# Generate self-signed SSL certificate for local development

echo "Generating self-signed SSL certificate for GmailMind..."
echo "========================================================"
echo ""

# Create ssl directory if it doesn't exist
mkdir -p ssl

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -days 365 \
    -nodes \
    -subj "/C=PK/ST=Sindh/L=Karachi/O=GmailMind/CN=localhost"

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ SSL certificate generated successfully!"
    echo ""
    echo "Files created:"
    echo "  - ssl/cert.pem (certificate)"
    echo "  - ssl/key.pem (private key)"
    echo ""
    echo "Note: This is a self-signed certificate for development only."
    echo "For production, use certificates from a trusted CA (Let's Encrypt, etc.)"
    echo ""
    echo "To use with uvicorn:"
    echo "  uvicorn api.main:app --ssl-keyfile=ssl/key.pem --ssl-certfile=ssl/cert.pem"
    echo ""
else
    echo ""
    echo "✗ Failed to generate SSL certificate"
    echo "Make sure openssl is installed: apt-get install openssl"
    exit 1
fi
