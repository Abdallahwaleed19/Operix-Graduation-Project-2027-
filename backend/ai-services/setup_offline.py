import shutil, sys
from pathlib import Path

GLOBAL_SITE = Path("C:/Users/AbdallahWaleed/AppData/Local/Programs/Python/Python314/Lib/site-packages")
VENV_SITE   = Path(__file__).parent / ".venv" / "Lib" / "site-packages"

PACKAGES = [
    "dotenv", "pydantic", "pydantic_core", "annotated_types",
    "sqlalchemy", "psycopg2", "greenlet", "typing_inspection",
    "pytest", "_pytest", "pluggy", "iniconfig", "packaging",
    "pytest_asyncio",
]

DIST_PREFIXES = [
    "python_dotenv", "pydantic", "pydantic_core", "annotated_types",
    "SQLAlchemy", "psycopg2_binary", "greenlet", "pytest", "pluggy",
    "iniconfig", "packaging", "pytest_asyncio", "typing_inspection",
]

FILES = ["typing_extensions.py"]

def copy_item(name):
    src = GLOBAL_SITE / name
    dst = VENV_SITE / name
    if dst.exists():
        print(f"  [skip] {name}")
        return
    if src.is_dir():
        shutil.copytree(src, dst)
        print(f"  [ok]   {name}/")
    elif src.is_file():
        shutil.copy2(src, dst)
        print(f"  [ok]   {name}")
    else:
        print(f"  [miss] {name}")

def copy_dist(prefix):
    for m in GLOBAL_SITE.glob(prefix + "*.dist-info"):
        dst = VENV_SITE / m.name
        if dst.exists():
            print(f"  [skip] {m.name}")
            continue
        shutil.copytree(m, dst)
        print(f"  [ok]   {m.name}")

if not VENV_SITE.exists():
    print("ERROR: venv not found. Run: python -m venv .venv")
    sys.exit(1)

print("Source:", GLOBAL_SITE)
print("Target:", VENV_SITE)
print()
print("=== packages ===")
for p in PACKAGES + FILES:
    copy_item(p)
print()
print("=== dist-info ===")
for d in DIST_PREFIXES:
    copy_dist(d)
print()
print("Done!")
