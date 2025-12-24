from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
import logging
from dotenv import load_dotenv


load_dotenv()

# Configure logging for database operations
logging.basicConfig(level=logging.INFO)
db_logger = logging.getLogger("database")

DATABASE_URL = os.getenv("DATABASE_URL")

Base = declarative_base()

# # Professional connection pool configuration
engine = create_engine(
    DATABASE_URL,
    # Connection Pool Settings
    poolclass=QueuePool,
    pool_size=15,                    # Base connections (increased from default 5)
    max_overflow=25,                 # Additional connections (increased from default 10)
    pool_timeout=60,                 # Wait time for connection (increased from 30s)
    pool_recycle=3600,               # Recycle connections every hour
    pool_pre_ping=True,              # Validate connections before use
    
    # Connection Settings
    connect_args={
        "connect_timeout": 10,       # Connection timeout
        "application_name": "niura_backend",  # For monitoring
    },
    
    # Engine Settings
    echo=False,                      # Set to True for SQL debugging
    future=True,                     # Use SQLAlchemy 2.0 style
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Keep objects accessible after commit
)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()