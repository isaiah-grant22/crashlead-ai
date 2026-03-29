from sqlalchemy import Column, Integer, String, Float, DateTime, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://crashlead:crashlead@db:5432/crashlead"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class CrashLead(Base):
    __tablename__ = "crash_leads"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=True)
    agency = Column(String(255), nullable=True)
    state = Column(String(10), nullable=True)
    nature = Column(String(500), nullable=True)
    injury = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    lead_score = Column(Integer, default=0)
    source = Column(String(100), nullable=True)
    ai_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)


class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    tier = Column(String(50), default="free")
    active = Column(Integer, default=1)
    created_at = Column(DateTime, nullable=True)


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI route injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
