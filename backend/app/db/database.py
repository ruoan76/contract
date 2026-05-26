from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

_engine = None
_async_session = None


def _get_engine():
    global _engine, _async_session
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            echo=settings.DEBUG,
        )
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
