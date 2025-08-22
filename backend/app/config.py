from pydantic_settings import BaseSettings
from typing import Optional, List
import os

class Settings(BaseSettings):
    # Application settings
    ENV: str = "dev"
    DEBUG: bool = False
    SECRET_KEY: str = "your-secret-key-change-in-production"
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./news.db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # External services
    SENTRY_DSN: Optional[str] = None
    REDIS_URL: Optional[str] = None
    
    # Application specific
    FETCH_INTERVAL_MIN: int = 5
    MAX_ARTICLES_PER_FETCH: int = 1000
    USER_AGENT: str = "NewsAggregator/1.0 (+https://alternative-nyheter.no)"
    
    # Security
    ALLOWED_ORIGINS: str = "http://localhost:8080,http://127.0.0.1:8080"
    RATE_LIMIT_PER_MINUTE: int = 30
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS to list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "prod"

settings = Settings()
