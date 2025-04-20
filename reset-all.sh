#!/bin/bash
set -e

echo "Stopping all containers..."
docker compose down

echo "Removing database and redis volumes..."
docker volume rm windsurf-project_db_data || true
docker volume rm windsurf-project_redis_data || true

echo "Starting containers..."
docker compose up -d

echo "Waiting for database to be ready..."
sleep 5

echo "Running Alembic migrations..."
docker compose exec backend alembic upgrade head

echo "All done! Your environment is now a clean slate."
