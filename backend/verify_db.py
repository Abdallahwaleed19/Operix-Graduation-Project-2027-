import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL','postgresql+psycopg://postgres:postgres@localhost:5432/operix_db'))
with engine.connect() as conn:
    result = conn.execute(text('SELECT current_database()'))
    print(result.scalar())
