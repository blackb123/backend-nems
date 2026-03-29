# app/db/session.py

import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase

# ---- Optional SSL setup for Render/Postgres ----
# Render requires SSL in some environments; asyncpg expects an SSLContext
ssl_context = ssl.create_default_context()
# If your database has a self-signed certificate, you can disable verification (not recommended for production)
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

# ---- Create async engine ----
engine = create_async_engine(
    settings.database_url,               # Example: postgresql+asyncpg://user:pass@host:port/dbname
    connect_args={"ssl": ssl_context},   # Use this for SSL; remove if SSL not needed
    echo=True                            # Optional: logs SQL queries, useful for debugging
)

# ---- Async session factory ----
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# ---- Dependency for FastAPI routes ----
async def get_db():
    async with async_session() as session:
        yield session

# ---- Initialize database ----
async def init_db():
    """
    Run this at startup to create all tables.
    """
    async with engine.begin() as conn:
        # Create all tables for User and Product models
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(ProductBase.metadata.create_all)

    print("✅ Database tables created successfully!")