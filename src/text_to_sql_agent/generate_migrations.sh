#!/bin/bash

set -a            # Automatically export all subsequent variables
source .env
set +a            # Turn off automatic exporting

# alembic revision --autogenerate -m "YOUE COMMENT"
alembic revision --autogenerate -m "added embedding column to schema_documents table"