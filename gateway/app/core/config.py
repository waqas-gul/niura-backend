import os

# Make sure to replace this with a strong, random string in production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGO", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

JWT_ISSUER = os.getenv("JWT_ISSUER", "niura-gateway")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "niura-services")

CORE_SERVICE_URL = os.getenv("CORE_SERVICE_URL", "http://core-service:8001")
EEG_SERVICE_URL = os.getenv("EEG_SERVICE_URL", "http://eeg-service:8002")
OCR_STT_SERVICE_URL = os.getenv("OCR_STT_SERVICE_URL", "http://ocr-service:8003")
