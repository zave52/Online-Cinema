FROM alpine:latest
LABEL authors="zakhar"

RUN apk add --no-cache curl dos2unix minio-client

RUN ln -s /usr/bin/mcli /usr/bin/mc

COPY ./scripts/setup_minio.sh /scripts/setup_minio.sh

RUN dos2unix /scripts/setup_minio.sh && chmod +x /scripts/setup_minio.sh
