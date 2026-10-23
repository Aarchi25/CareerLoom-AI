import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "CareerLoom AI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Secrets
    JWT_SECRET: str = os.getenv("JWT_SECRET", "careerloom-secret-key-change-in-production-2026")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Environment credentials
    MONGODB_URI: str = os.getenv("MONGODB_URI", "")
    DATABASE_NAME: str = "careerloom_ai"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))
    CORS_ORIGINS: list = ["*"]

settings = Settings()
