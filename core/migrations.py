"""Lightweight versioned migration runner for Health Deck PostgreSQL.

Tracks applied migrations in table schema_migrations.
Executes unapplied migrations in version order inside an atomic transaction.
"""

import os
import sys

_MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")

_MIGRATIONS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_available_migrations():
    """Retrieve all available migration files in lexicographical order."""
    if not os.path.exists(_MIGRATIONS_DIR):
        return []
    files = [f for f in os.listdir(_MIGRATIONS_DIR) if f.endswith(".sql")]
    files.sort()
    migrations = []
    for filename in files:
        version = filename.split("_", 1)[0]
        name = filename
        path = os.path.join(_MIGRATIONS_DIR, filename)
        migrations.append((version, name, path))
    return migrations


def get_applied_migrations(conn):
    """Retrieve set of already applied migration versions."""
    with conn.cursor() as cur:
        cur.execute(_MIGRATIONS_TABLE_DDL)
        cur.execute("SELECT version FROM schema_migrations ORDER BY version ASC")
        rows = cur.fetchall()
        applied = set()
        for r in rows:
            if isinstance(r, dict):
                applied.add(r["version"])
            else:
                applied.add(r[0])
        return applied


def apply_migrations(conn):
    """Apply all pending migrations in order inside a transaction."""
    available = get_available_migrations()
    applied = get_applied_migrations(conn)

    pending = [(v, n, p) for (v, n, p) in available if v not in applied]
    if not pending:
        return 0

    with conn.transaction():
        with conn.cursor() as cur:
            for version, name, path in pending:
                with open(path, "r", encoding="utf-8") as f:
                    sql = f.read()
                cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (%s, %s)",
                    (version, name),
                )
    return len(pending)


def migration_status(conn):
    """Return status of all migrations (applied or pending)."""
    available = get_available_migrations()
    applied = get_applied_migrations(conn)

    status_list = []
    for version, name, path in available:
        is_applied = version in applied
        status_list.append({
            "version": version,
            "name": name,
            "applied": is_applied,
        })
    return status_list


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Error: DATABASE_URL must be configured to run PostgreSQL migrations.")
        sys.exit(1)

    import psycopg

    command = sys.argv[1] if len(sys.argv) > 1 else "apply"

    with psycopg.connect(database_url) as conn:
        if command == "status":
            statuses = migration_status(conn)
            print(f"{'Version':<10} {'Name':<40} {'Status'}")
            print("-" * 65)
            for s in statuses:
                stat = "Applied" if s["applied"] else "Pending"
                print(f"{s['version']:<10} {s['name']:<40} {stat}")
        elif command == "apply":
            count = apply_migrations(conn)
            print(f"Successfully applied {count} migration(s).")
        else:
            print(f"Unknown command '{command}'. Use 'apply' or 'status'.")
            sys.exit(1)
