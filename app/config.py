from pydantic_settings import BaseSettings
from typing import Optional
# 🚨 Nueva importación y función para cargar el .env ANTES de Pydantic
from dotenv import load_dotenv

# Cargar el archivo .env desde el directorio raíz del proyecto (backend/)
# Pydantic-settings debería encontrarlo, pero esto lo hace explícito y seguro.
load_dotenv()

class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str
    
    # --- JWT (Token Security) ---
    SECRET_KEY: str 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # --- reCAPTCHA ---
    RECAPTCHA_SECRET_KEY: str
    
    # --- Email ---
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    # --- Stripe/Payment ---
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    class Config:
        # Pydantic aún usa esta configuración, pero ya hemos cargado las variables
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Pydantic ahora puede acceder a las variables de entorno ya cargadas
settings = Settings()
