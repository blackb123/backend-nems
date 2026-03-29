# app/db/session.py
import ssl
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ---- Import your models ----
from app.models.user import Base as UserBase
from app.models.product import Base as ProductBase
from app.core.config import settings

# ---- SSL setup for Render ----
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE  # Needed for Render's self-signed cert

# ---- Async engine ----
engine = create_async_engine(
    settings.database_url,
    connect_args={"ssl": ssl_context},  # Pass SSL only here
    echo=True,  # optional: logs SQL queries
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

# ---- Initialize database tables ----
async def init_db():
    """
    Run this at startup to create all tables.
    """
    async with engine.begin() as conn:
        # Create all tables for User and Product models
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(ProductBase.metadata.create_all)

    print("✅ Database tables created successfully!")