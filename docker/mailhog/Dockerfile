FROM debian:bookworm-slim
LABEL authors="zakhar"

RUN apt update && apt install -y \
    golang-go \
    wget \
    dos2unix \
    && apt clean

RUN go install github.com/mailhog/MailHog@latest

ENV PATH="/root/go/bin:$PATH"

COPY scripts/setup_mailhog_auth.sh /scripts/setup_mailhog_auth.sh

RUN dos2unix /scripts/setup_mailhog_auth.sh && chmod +x /scripts/setup_mailhog_auth.sh
