#!/bin/bash

set -a            # Automatically export all subsequent variables
source .env
set +a            # Turn off automatic exporting

alembic revision --autogenerate -m "describe change"