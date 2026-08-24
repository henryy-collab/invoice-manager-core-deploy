#!/bin/bash
set -e

python /bootstrap.py || echo "Warning: bootstrap failed"

exec "$@"