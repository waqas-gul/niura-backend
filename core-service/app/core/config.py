import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:root@postgres:5432/ear_db")

# Make sure to replace this with a strong, random string in production
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = os.getenv("JWT_ALGO","HS256")


JWT_ISSUER = os.getenv("JWT_ISSUER","niura-gateway")
JWT_AUDIENCE = os.getenv("JWT_AUDIENCE","niura-services")

