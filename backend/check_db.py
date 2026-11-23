import os
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.core.config import get_settings
from sqlalchemy import create_engine, text

settings = get_settings()
engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text('SELECT current_database(), current_user, version();'))
    db, user, version = result.fetchone()
    print(f'Current database: {db}')
    print(f'Current user: {user}')
    print(f'PostgreSQL version: {version.split(" ")[0]}')
    # Check enum values
    enum_res = conn.execute(text('SELECT enum_range(NULL::token_purpose);'))
    enum_vals = enum_res.scalar()
    print(f'token_purpose enum values: {enum_vals}')
    if 'camera' in str(enum_vals):
        print('Enum already contains "camera"')
    else:
        print('Enum does NOT contain "camera"')
