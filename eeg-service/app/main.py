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
    logger.info("🚀 EEG service starting up")
    # ℹ️  Kafka topics are created manually via bastion host (see backEnd/KAFKA_SETUP.md)
    start_consumer()  # ✅ Start consuming from existing topics
    yield
    logger.info("🛑 EEG service shutting down")

# Create FastAPI app with lifespan management
app = FastAPI(
    title="NIURA EEG Service API",
    description="All Eeg data ml prediction and stroage to db happens here.",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
    root_path="/eeg"
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
app.include_router(fft_eeg_controller.router, prefix="/api", tags=["EEG-FFT"])
# Note: Aggregation endpoints are in core-service (has DB access)