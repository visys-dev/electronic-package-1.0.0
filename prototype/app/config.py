import os
from urllib.parse import urlsplit
from sqlalchemy import URL


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.getenv("DB_HOST", "db"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.environ["DB_NAME"],
    )


def origin() -> str:
    value = os.environ["APP_ORIGIN"]
    parts = urlsplit(value)
    if (
        parts.scheme != "https"
        or not parts.netloc
        or parts.path
        or parts.query
        or parts.fragment
        or parts.username
    ):
        raise ValueError(
            "APP_ORIGIN must be an HTTPS origin without a path or credentials"
        )
    return value
