FROM golang:1.26.1-alpine3.23
LABEL authors="zakhar"

RUN go install github.com/mailhog/MailHog@v1.0.1

COPY scripts/setup_mailhog_auth.sh /scripts/setup_mailhog_auth.sh

EXPOSE 1025 8025

ENTRYPOINT ["sh", "-c", "/scripts/setup_mailhog_auth.sh && exec /go/bin/MailHog"]