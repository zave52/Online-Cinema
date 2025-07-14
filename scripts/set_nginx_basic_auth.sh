#!/bin/bash

set -e

if [ -z "$API_USER" ] || [ -z "$API_PASSWORD" ]; then
  echo "Error: API_USER and API_PASSWORD must be set."
  exit 1
fi

echo "Creating .htpasswd file."

if [ ! -f /etc/nginx/.htpasswd ]; then
  htpasswd -cb /etc/nginx/.htpasswd "$API_USER" "$API_PASSWORD"
else
  htpasswd -b /etc/nginx/.htpasswd "$API_USER" "$API_PASSWORD"
fi

cat <<EOL > /etc/nginx/conf.d/auth.conf
auth_basic "Restricted Access";
auth_basic_user_file /etc/nginx/.htpasswd;
EOL

echo "Basic Auth setup complete."

exec "$@"
