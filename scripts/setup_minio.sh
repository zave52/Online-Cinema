#!/bin/sh

MAX_RETRIES=30

echo "Waiting for MinIO service at $MINIO_HOST:$MINIO_PORT to be ready..."

for i in $(seq 1 ${MAX_RETRIES}); do
  if curl --silent --fail http://${MINIO_HOST}:${MINIO_PORT}/minio/health/live; then
    echo "MinIO is up!"
    break
  fi

  echo "Waiting for MinIO... (${i}/${MAX_RETRIES}"
  sleep 1
done

echo "Configuring MinIO to be ready..."
mc alias set minio http://"$MINIO_HOST":"$MINIO_PORT" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

if mc ls minio | grep -q "$MINIO_STORAGE"; then
  echo "Bucket '$MINIO_STORAGE' already exists. Skipping creation."
else
  echo "Creating bucket: $MINIO_STORAGE"
  mc mb minio/"$MINIO_STORAGE"
fi

echo "Setting bucket policy to public..."
mc anonymous set download minio/"$MINIO_STORAGE"

echo "Getting policy info..."
mc anonymous get minio/"$MINIO_STORAGE"

echo "MinIO configuration completed!"
exit 0
