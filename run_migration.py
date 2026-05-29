#!/usr/bin/env python3
"""Run database migration for reports feature."""
import psycopg2
from config import settings

def run_migration():
    """Execute the migration SQL file."""
    try:
        # Connect to database
        conn = psycopg2.connect(settings.database_url)
        cur = conn.cursor()

        # Read migration file
        with open('migrations/add_report_settings.sql', 'r') as f:
            migration_sql = f.read()

        # Execute migration
        print("Running migration...")
        cur.execute(migration_sql)
        conn.commit()

        # Get result
        cur.execute("SELECT 'Migration completed successfully!' as status")
        result = cur.fetchone()
        print(result[0])

        cur.close()
        conn.close()

        print("\n✓ Migration executed successfully!")
        return True

    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
