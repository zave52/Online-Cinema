FROM alpine:3.23.3
LABEL authors="zakhar"

RUN apk add --no-cache \
    curl \
    minio-client \
    && ln -s /usr/bin/mcli /usr/bin/mc

COPY ./scripts/setup_minio.sh /scripts/setup_minio.sh

ENTRYPOINT ["/scripts/setup_minio.sh"]