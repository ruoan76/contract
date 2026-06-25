from fastapi import HTTPException
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine = None
_async_session = None


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def _configure_sqlite_connection(dbapi_conn, _connection_record) -> None:
    """SQLite 本地开发：WAL + busy_timeout，减轻长事务写锁。"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def _get_engine():
    global _engine, _async_session
    if _engine is None:
        engine_kwargs: dict = {
            "echo": settings.DEBUG,
        }
        if _is_sqlite_url(settings.DATABASE_URL):
            # 文件型 SQLite：避免连接池多写者争锁
            engine_kwargs["connect_args"] = {"timeout": 30}
            engine_kwargs["poolclass"] = NullPool
        else:
            engine_kwargs["pool_size"] = settings.DATABASE_POOL_SIZE
            engine_kwargs["max_overflow"] = settings.DATABASE_MAX_OVERFLOW

        _engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

        if _is_sqlite_url(settings.DATABASE_URL):
            event.listen(_engine.sync_engine, "connect", _configure_sqlite_connection)

        _async_session = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _engine


def _get_async_session():
    _get_engine()
    return _async_session


def reset_async_engine() -> None:
    """Celery prefork 子进程须重置 async engine，避免 event loop 冲突。"""
    global _engine, _async_session
    if _engine is not None:
        _engine.sync_engine.dispose()
    _engine = None
    _async_session = None


async def get_db() -> AsyncSession:
    async with _get_async_session()() as session:
        try:
            yield session
            await session.commit()
        except HTTPException:
            await session.rollback()
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class _LazyEngine:
    def __getattr__(self, name):
        return getattr(_get_engine(), name)


class _LazySession:
    def __call__(self, *args, **kwargs):
        return _get_async_session()(*args, **kwargs)


engine = _LazyEngine()
async_session = _LazySession()
