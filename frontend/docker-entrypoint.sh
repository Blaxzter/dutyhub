#!/bin/sh
# Generate runtime config from environment variables before starting nginx.
cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = {
  LEGAL_NAME: '${LEGAL_NAME:-}',
  LEGAL_ADDRESS: '${LEGAL_ADDRESS:-}',
  LEGAL_CITY: '${LEGAL_CITY:-}',
  LEGAL_EMAIL: '${LEGAL_EMAIL:-}',
  LEGAL_PHONE: '${LEGAL_PHONE:-}',
};
EOF

exec nginx -g 'daemon off;'
