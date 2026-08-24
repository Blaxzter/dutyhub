#!/bin/sh
# Generate runtime config from environment variables before starting nginx.
cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = {
  LEGAL_NAME: '${LEGAL_NAME:-}',
  LEGAL_ADDRESS: '${LEGAL_ADDRESS:-}',
  LEGAL_CITY: '${LEGAL_CITY:-}',
  LEGAL_EMAIL: '${LEGAL_EMAIL:-}',
  LEGAL_PHONE: '${LEGAL_PHONE:-}',
  TURNSTILE_SITE_KEY: '${TURNSTILE_SITE_KEY:-}',
  // Defaults to on, like the backend setting it mirrors: an unset variable
  // must not silently take the demo away. Only the literal 'false' hides it.
  SANDBOX_ENABLED: '${SANDBOX_ENABLED:-true}',
};
EOF

exec nginx -g 'daemon off;'
