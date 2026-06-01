from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # Recycle connections before MySQL's idle timeout (default 8h) drops them.
    # We avoid pool_pre_ping because the aiomysql adapter's ping() signature is
    # incompatible with SQLAlchemy's pre-ping call.
    pool_recycle=3600,
)

session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
