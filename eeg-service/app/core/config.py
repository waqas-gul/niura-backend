import os

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:root@postgres:5432/ear_db")

# JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ISSUER = os.getenv("JWT_ISSUER", "niura-gateway")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "niura-services")
