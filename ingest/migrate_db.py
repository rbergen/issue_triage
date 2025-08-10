#!/usr/bin/env python3
"""
Migration script to add unique constraint to source_id and reindex with chunking.
"""

import argparse
import psycopg
from config import DATABASE_URL

def migrate_database():
    """Add unique constraint to source_id column"""
    print("Migrating database schema...")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Check if unique constraint already exists
            cur.execute("""
                SELECT constraint_name
                FROM information_schema.table_constraints
                WHERE table_name = 'docs'
                AND constraint_type = 'UNIQUE'
                AND constraint_name LIKE '%source_id%'
            """)

            if cur.fetchone():
                print("Unique constraint on source_id already exists.")
                return

            print("Adding unique constraint to source_id...")

            # First, remove any duplicate source_ids (keep the first one)
            cur.execute("""
                DELETE FROM docs
                WHERE id NOT IN (
                    SELECT MIN(id)
                    FROM docs
                    GROUP BY source_id
                )
            """)

            affected = cur.rowcount
            if affected > 0:
                print(f"Removed {affected} duplicate entries.")

            # Add unique constraint
            cur.execute("ALTER TABLE docs ADD CONSTRAINT docs_source_id_unique UNIQUE (source_id);")

            # Add index on source_id if it doesn't exist
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_source_id ON docs(source_id);
            """)

        conn.commit()

    print("Migration completed successfully!")

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Migrate database for chunking support")
    args = ap.parse_args()

    migrate_database()
