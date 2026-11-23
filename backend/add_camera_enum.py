import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL','postgresql+psycopg://postgres:postgres@localhost:5432/operix_db'))
with engine.begin() as conn:
    # PostgreSQL 13+ supports IF NOT EXISTS for enum add
    conn.execute(text("ALTER TYPE token_purpose ADD VALUE IF NOT EXISTS 'camera'"))
print('Enum updated')
