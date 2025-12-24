from asyncio import create_task
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import aggregation, eeg_controller, goals_controller
from app.events.kafka_consumer import start_consumer
from app.core.logging_config import setup_json_logger
from app.core.request_logger import ContextLoggingMiddleware, RequestLoggingMiddleware
from app.database import Base, engine


logger = setup_json_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Core service starting up")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized")
    # ℹ️  Kafka topics are created manually via bastion host (see backEnd/KAFKA_SETUP.md)
    start_consumer()  # ✅ Start consuming from existing topics
    yield
    logger.info("🛑 Core service shutting down")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="NIURA Core Service API",
    description="All Niura common mobile endpoints data are handled here.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",                 # docs at /api/docs
    openapi_url="/api/openapi.json",      # openapi at /api/openapi.json
    redoc_url=None,
    root_path="/core"
  
)

app.add_middleware(ContextLoggingMiddleware)  # sets request_id/user_id
app.add_middleware(RequestLoggingMiddleware)  # logs each request


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
   
    
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Include routers

app.include_router(eeg_controller.router, prefix="/api", tags=["EEG"])
app.include_router(goals_controller.router, prefix="/api", tags=["Goals"])
app.include_router(aggregation.router, prefix="/api", tags=["Aggregation"])
