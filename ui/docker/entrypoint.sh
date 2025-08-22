#!/bin/sh
set -e

# Generate runtime config from env vars
# Default to relative '/api' so requests are proxied by Nginx to the agent
API_BASE_URL=${UI_API_BASE_URL:-/api}
cat > /usr/share/nginx/html/config.js <<EOF
window.__APP_CONFIG__ = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF

exec "$@"
