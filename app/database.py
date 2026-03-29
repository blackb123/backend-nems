# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---- Import your models ----
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase
from app.core.config import settings

# ---- Sync engine ----
engine = create_engine(
    settings.database_url.replace("postgresql+asyncpg://", "postgresql://"),
    echo=False,
    pool_pre_ping=True,
    pool_recycle=300,
)

# ---- Sync session factory ----
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


def get_db():
    """Dependency for FastAPI routes - yields sync session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables at startup"""
    UserBase.metadata.create_all(bind=engine)
    ProductBase.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")