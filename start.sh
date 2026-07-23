#!/data/data/com.termux/files/usr/bin/bash

set -e

cd ~/cometfallpress/cometfallpress.backend/
source .venv/bin/activate

# Environment variables
set -a
source .env
set +a

echo "Running database migrations..."
flask db upgrade

echo "Starting Gunicorn..."
exec gunicorn app:app \
    --bind 127.0.0.1:${PORT:-5000} \
    --workers 2 \
    --threads 4 \
    --timeout 60 \
    --log-level info \
    --access-logfile - \
    --error-logfile - \
    --capture-output