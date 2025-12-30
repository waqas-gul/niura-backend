from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
import asyncio

from app.routes import (
    user_controller,
    proxy,
    eeg_gateway_controller,
)

from app.database import Base, engine
from app.websocket import routes as websocket_routes
from app.core.logging_config import setup_json_logger
from app.core.request_logger import ContextLoggingMiddleware, RequestLoggingMiddleware


# Lifespan handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    logger.info("🚀 Gateway service starting up")
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database initialized")

    # Set event loop for Kafka consumer
    from app.events.kafka_consumer import start_consumer, set_event_loop

    set_event_loop(asyncio.get_event_loop())
    start_consumer()

    # ℹ️  Kafka topics are created manually via bastion host (see backEnd/KAFKA_SETUP.md)
    # This follows AWS MSK Serverless best practices for topic management

    yield

    # --- Shutdown ---
    logger.info("🛑 Gateway service shutting down")
    engine.dispose()
    logger.info("🛑 Database engine disposed")


logger = setup_json_logger()

# Create FastAPI app
app = FastAPI(
    title="NIURA Gateway Service API",
    description="Handles user, proxy, and EEG gateway routes for Niura.",
    version="2.0.0",
    lifespan=lifespan,
    root_path="/gateway",
)

# Middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ContextLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ HEALTH CHECK ENDPOINT
@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Include routers
app.include_router(user_controller.router, prefix="/api", tags=["User"])
app.include_router(proxy.router, prefix="/api", tags=["Proxy"])
app.include_router(eeg_gateway_controller.router, prefix="/api", tags=["EEG"])
app.include_router(websocket_routes.router)
