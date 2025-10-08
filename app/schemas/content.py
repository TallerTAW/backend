# BACKEND/app/schemas/content.py

from pydantic import BaseModel
from typing import Optional

class ContentUpdate(BaseModel):
    """Esquema para recibir el nuevo valor del contenido."""
    new_value: str
    
    class Config:
        from_attributes = True