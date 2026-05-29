#!/bin/bash
# Run a specific SQL migration file
# Usage: ./run_migration.sh 005_remove_review_period.sql

if [ -z "$1" ]; then
    echo "❌ Error: Please provide migration file name"
    echo "Usage: ./run_migration.sh 005_remove_review_period.sql"
    exit 1
fi

MIGRATION_FILE="$1"

if [ ! -f "$MIGRATION_FILE" ]; then
    echo "❌ Error: Migration file not found: $MIGRATION_FILE"
    exit 1
fi

echo "🗄️  Running migration: $MIGRATION_FILE"
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Run migration using psql
psql "$DATABASE_URL" -f "$MIGRATION_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Migration completed successfully!"
else
    echo ""
    echo "❌ Migration failed!"
    exit 1
fi
