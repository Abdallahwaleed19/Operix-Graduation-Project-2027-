import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.app.core.config import get_settings
from sqlalchemy import create_engine, inspect, MetaData, Table
from sqlalchemy.schema import CreateTable
settings = get_settings()
engine = create_engine(settings.DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine, only=['factory_memberships'])
factory_tbl = metadata.tables.get('factory_memberships')
if factory_tbl is None:
    print('Table factory_memberships not found')
else:
    print(str(CreateTable(factory_tbl).compile(dialect=engine.dialect)))
