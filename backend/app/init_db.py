"""Create the pgvector extension and all tables.

Run from backend/:  uv run python -m app.init_db
"""

from app.database import create_tables

if __name__ == "__main__":
    create_tables()
    print("Database tables are ready.")
