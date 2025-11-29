#!/bin/bash
set -e

# Database migration script for Aurora
# Usage: ./scripts/migrate.sh [upgrade|downgrade|current|history] [revision]
#
# Examples:
#   ./scripts/migrate.sh upgrade head     # Run all pending migrations
#   ./scripts/migrate.sh downgrade -1     # Rollback one migration
#   ./scripts/migrate.sh current          # Show current revision
#   ./scripts/migrate.sh history          # Show migration history

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT/backend"

# Default command
COMMAND="${1:-upgrade}"
REVISION="${2:-head}"

echo "=========================================="
echo "Database Migration"
echo "=========================================="

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
  # Try to load from infra/.env
  if [ -f "$PROJECT_ROOT/infra/.env" ]; then
    echo "Loading credentials from infra/.env..."
    export $(grep -v '^#' "$PROJECT_ROOT/infra/.env" | xargs)
  fi

  # Try to load from backend/.env
  if [ -z "$DATABASE_URL" ] && [ -f "$BACKEND_DIR/.env" ]; then
    echo "Loading DATABASE_URL from backend/.env..."
    export $(grep -v '^#' "$BACKEND_DIR/.env" | grep DATABASE_URL | xargs)
  fi

  # If still not set, try to construct from infra env vars
  if [ -z "$DATABASE_URL" ] && [ -n "$DB_USERNAME" ] && [ -n "$DB_PASSWORD" ]; then
    # Get Aurora endpoint from CloudFormation
    echo "Fetching Aurora endpoint from CloudFormation..."
    AURORA_ENDPOINT=$(aws cloudformation describe-stacks \
      --stack-name JusticeStack \
      --query "Stacks[0].Outputs[?ExportName=='jpwhite-AuroraClusterEndpoint'].OutputValue" \
      --output text 2>/dev/null || echo "")

    if [ -n "$AURORA_ENDPOINT" ]; then
      DATABASE_URL="postgresql+asyncpg://${DB_USERNAME}:${DB_PASSWORD}@${AURORA_ENDPOINT}:5432/frontier_audio"
      echo "Constructed DATABASE_URL from CloudFormation outputs"
    fi
  fi
fi

if [ -z "$DATABASE_URL" ]; then
  echo "Error: DATABASE_URL not set"
  echo ""
  echo "Options:"
  echo "  1. Set DATABASE_URL environment variable directly"
  echo "  2. Create backend/.env with DATABASE_URL"
  echo "  3. Ensure infra/.env has DB_USERNAME and DB_PASSWORD, and Aurora is deployed"
  echo ""
  echo "Example DATABASE_URL format:"
  echo "  postgresql+asyncpg://user:password@hostname:5432/frontier_audio"
  exit 1
fi

echo "Running migration: $COMMAND $REVISION"
echo ""

cd "$BACKEND_DIR"

# Run alembic (uses async engine configured in env.py)
DATABASE_URL="$DATABASE_URL" python -m alembic $COMMAND $REVISION

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
