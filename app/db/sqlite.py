"""
SQLite database initialization and models
"""

from sqlalchemy import Column, String, Integer, DateTime, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from app.config import settings
from app.utils import logger

Base = declarative_base()


class ChatRecord(Base):
    """Chat message record"""
    __tablename__ = "chat_records"
    
    id = Column(String, primary_key=True)
    role = Column(String, nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    record_metadata = Column("metadata", Text)  # JSON string


class TaskRecord(Base):
    """Task record"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default="pending", nullable=False)
    agent_type = Column(String)  # planner, builder, reviewer, tester
    priority = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MemoryRecord(Base):
    """Memory/knowledge record"""
    __tablename__ = "memory"
    
    id = Column(String, primary_key=True)
    key = Column(String, nullable=False, index=True)
    value = Column(Text, nullable=False)
    category = Column(String, nullable=False)  # chat, task, log, system
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class LogRecord(Base):
    """Application log record"""
    __tablename__ = "logs"
    
    id = Column(String, primary_key=True)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR, DEBUG
    message = Column(Text, nullable=False)
    source = Column(String)  # module/function name
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


def get_database_url() -> str:
    """Get database URL"""
    url = settings.database_url
    # Convert relative paths to absolute for SQLite
    if url.startswith("sqlite:///"):
        db_path = settings.get_absolute_path(url.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{db_path}"
    return url


def init_database():
    """Initialize database and create tables"""
    try:
        db_url = get_database_url()
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized at {db_url}")
        return engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def get_session_maker(engine=None):
    """Get SQLAlchemy session maker"""
    if engine is None:
        engine = init_database()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Initialize database on module import
_engine = None

try:
    _engine = init_database()
except Exception as e:
    logger.warning(f"Database not available: {e}")
