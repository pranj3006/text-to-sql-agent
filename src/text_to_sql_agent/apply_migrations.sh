#!/bin/bash

set -a            # Automatically export all subsequent variables
source .env
set +a            # Turn off automatic exporting

uv run --no-sync alembic upgrade head