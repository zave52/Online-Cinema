#!/bin/sh

gunicorn main:app \
    --workers 10 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --log-lever info \
    --access-logfile - \
    --error-logfile -
