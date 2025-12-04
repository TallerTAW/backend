# app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str = "supersecreto123"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # reCAPTCHA
    RECAPTCHA_SECRET_KEY: str
    
    # Supabase (LEGACY KEYS)
    SUPABASE_URL: str
    SUPABASE_KEY: str           # anon public key
    SUPABASE_SERVICE_KEY: str   # service_role key
    
    # CORS
    FRONTEND_URLS: str = "http://localhost:5173,http://localhost:3000"
    
    @property
    def allowed_origins(self) -> List[str]:
        urls = self.FRONTEND_URLS.split(",")
        all_urls = []
        for url in urls:
            all_urls.append(url.strip())
            if url.startswith("http://"):
                all_urls.append(url.replace("http://", "https://"))
        return all_urls
    
    class Config:
        env_file = ".env"

settings = Settings()