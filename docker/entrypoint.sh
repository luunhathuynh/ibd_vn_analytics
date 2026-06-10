#!/bin/sh
set -e

mkdir -p /app/data/raw /app/data/processed /app/reports

exec "$@"
