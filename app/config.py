from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    # Asumimos que quieres mantener la URL por defecto para referencia si .env falla,
    # pero el valor del .env prevalecerá si existe.
    DATABASE_URL: str = "postgresql+psycopg2://postgres:123456@localhost:5432/taw"
    
    # JWT
    # 🚨 CRÍTICO: Eliminamos el valor por defecto. Esto obliga a Pydantic a usar el valor del .env
    # Esto asegura que la llave sea CONSISTENTE para crear y validar tokens.
    SECRET_KEY: str 
    
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Email
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    EMAIL_USERNAME: Optional[str] = None
    EMAIL_PASSWORD: Optional[str] = None
    
    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    class Config:
        # Aseguramos que cargue las variables del archivo .env
        env_file = ".env"
        # Opcional: permitir que los valores no sean leídos de forma estricta al inicio
        # validate_assignment = True 

settings = Settings()