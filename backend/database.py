import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from config import DATABASE_URL

logger = logging.getLogger(__name__)

# pool_recycle avoids MySQL closing idle connections server-side while they still sit in the pool
# (stale PyMySQL sockets often surface as "Packet sequence number wrong").
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=280,
    pool_size=5,
    max_overflow=10,
    connect_args={"connect_timeout": 10},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            db.close()
        except Exception as exc:
            # Broken connections can raise on rollback inside close(); avoid masking the real error
            # and reduce "Exception ignored in generator" noise from PyMySQL.
            logger.debug("Session close failed (connection may be stale): %s", exc)
            try:
                db.invalidate()
            except Exception:
                pass
