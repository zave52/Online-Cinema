#!/bin/sh

if [ -n "$MAILHOG_USER" ] && [ -n "$MAILHOG_PASSWORD" ]; then
  HASHED_PASSWORD=$(MailHog bcrypt "$MAILHOG_PASSWORD")

  echo "$MAILHOG_USER:$HASHED_PASSWORD" > /mailhog.auth
  echo "Auth file created with user: $MAILHOG_USER and hashed password."
else
  echo "MAILHOG_USER or MAILHOG_PASSWORD not set. Auth file not created."
fi
