"""
Parse a database URL and reject the production database before any engine exists.

This module opens no connections and creates no engines.
OPERIX_ALLOW_LIVE_DB is intentionally never read.
"""
from urllib.parse import unquote, urlparse

PRODUCTION_DATABASE_NAME = "operix_db"


def database_name(url: str) -> str:
    """Return the database name from a SQLAlchemy or libpq URL.

    Parsing only. This never opens a socket.
    """
    raw = (url or "").strip()
    if not raw:
        return ""

    try:
        from sqlalchemy.engine.url import make_url

        parsed = make_url(raw)
        name = parsed.database or ""
    except Exception:
        parsed_std = urlparse(raw)
        path = unquote(parsed_std.path or "")
        name = path.lstrip("/").split("?")[0].split("/")[0]

    return name.strip()


def reject_operix_db(url: str) -> None:
    """Raise RuntimeError when ``url`` names the production database.

    The rejection is unconditional. ``OPERIX_ALLOW_LIVE_DB`` is not consulted
    and cannot bypass it. Call this before ``create_engine`` or any connection.
    """
    name = database_name(url)
    if name.lower() == PRODUCTION_DATABASE_NAME:
        raise RuntimeError(
            "BLOCKED: database target is 'operix_db' (the production database). "
            "Rejected before any engine or connection is created. "
            "OPERIX_ALLOW_LIVE_DB does not bypass this rejection."
        )


def enforce_configured_test_target(url: str) -> str:
    """Validate the URL pytest will hand to the application engine.

    An empty URL is rejected so Settings cannot fall through to the production
    default. ``operix_db`` is rejected with no bypass flag.
    """
    raw = (url or "").strip()
    if not raw:
        raise RuntimeError(
            "BLOCKED: DATABASE_URL is empty. Refusing to import the application "
            "because the Settings default names the production database. "
            "Set DATABASE_URL to sqlite or to an explicitly named disposable database."
        )
    reject_operix_db(raw)
    return raw


def require_disposable_live_postgres_url(url: str) -> str:
    """Require an explicitly named disposable PostgreSQL database.

    Raises RuntimeError before any engine is created when the URL is missing,
    unnamed, not PostgreSQL, or names ``operix_db``. ``OPERIX_ALLOW_LIVE_DB``
    is not consulted.
    """
    raw = (url or "").strip()
    if not raw:
        raise RuntimeError(
            "BLOCKED: live PostgreSQL tests require TEST_DATABASE_URL set to an "
            "explicitly named disposable database."
        )

    reject_operix_db(raw)

    try:
        from sqlalchemy.engine.url import make_url

        parsed = make_url(raw)
        driver = parsed.drivername or ""
        name = (parsed.database or "").strip()
    except Exception as exc:
        raise RuntimeError(
            "BLOCKED: TEST_DATABASE_URL cannot be parsed. "
            "Live tests require an explicitly named disposable PostgreSQL database."
        ) from exc

    if not driver.startswith("postgres"):
        raise RuntimeError(
            "BLOCKED: live PostgreSQL tests require a postgresql URL naming a "
            "disposable database. SQLite and other engines are not accepted here."
        )
    if not name:
        raise RuntimeError(
            "BLOCKED: TEST_DATABASE_URL does not name a database. "
            "Live tests require an explicitly named disposable database."
        )
    return raw
