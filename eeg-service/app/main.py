from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging_config import setup_json_logger
from app.routes import eeg_controller, fft_eeg_controller
from app.events.kafka_consumer import start_consumer
from app.core.request_logger import ContextLoggingMiddleware, RequestLoggingMiddleware


logger = setup_json_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 EEG service starting up (PERFORMANCE-OPTIMIZED)")
    # ℹ️  Kafka topics are created manually via bastion host (see backEnd/KAFKA_SETUP.md)
    start_consumer()  # ✅ Start consuming from existing topics
    yield
    logger.info("🛑 EEG service shutting down")

# Create FastAPI app with lifespan management
# Performance: Disable automatic OpenAPI docs in production by setting docs_url=None
app = FastAPI(
    title="NIURA EEG Service API",
    description="High-performance EEG data processing with FFT pipeline",
    version="2.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,  # Disabled - reduces startup overhead
    root_path="/eeg"
)

# PERFORMANCE NOTE: Middleware runs on every request
# Keep middleware stack minimal for hot paths
# Consider disabling non-essential middleware in production

# Essential: CORS for frontend access    
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Request logging (disable in production for max performance)
# Comment out these lines if you need <200ms latency
app.add_middleware(ContextLoggingMiddleware)  # sets request_id/user_id
app.add_middleware(RequestLoggingMiddleware)  # logs each request


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Include routers

app.include_router(eeg_controller.router, prefix="/api", tags=["EEG"])
app.include_router(fft_eeg_controller.router, prefix="/api", tags=["EEG-FFT"])
# Note: Aggregation endpoints are in core-service (has DB access)