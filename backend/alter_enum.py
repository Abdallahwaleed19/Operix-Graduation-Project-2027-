import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.core.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError, SQLAlchemyError
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    # Verify connection details
    db, user = conn.execute(text('SELECT current_database(), current_user')).fetchone()
    print(f'Current database: {db}')
    print(f'Current user: {user}')
    if db != 'operix_db':
        raise SystemExit('STOP: Connected to wrong database')
    # Check enum existence and values
    enum_vals = conn.execute(text("SELECT enum_range(NULL::token_purpose);")).scalar()
    print(f'Existing enum values: {enum_vals}')
    if 'camera' in str(enum_vals):
        print('Enum already contains "camera"; no action needed.')
        sys.exit(0)
    # Attempt to add enum value
    try:
        conn.execute(text("ALTER TYPE token_purpose ADD VALUE 'camera'"))
        print('ALTER TYPE executed successfully.')
    except Exception as e:
        print('Error during ALTER TYPE:', e)
        sys.exit(1)
    # Verify addition
    enum_vals2 = conn.execute(text("SELECT enum_range(NULL::token_purpose);")).scalar()
    print(f'Updated enum values: {enum_vals2}')
