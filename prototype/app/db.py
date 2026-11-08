from sqlalchemy.ext.asyncio import create_async_engine
from .config import database_url


def make_engine():
    return create_async_engine(
        database_url(),
        pool_pre_ping=True,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 5,
            "options": "-c statement_timeout=10000 -c lock_timeout=3000",
        },
    )
