from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ComentarioBase(BaseModel):
    descripcion: str
    calificacion: Optional[int] = Field(None, ge=1, le=5)
    id_usuario: int
    id_cancha: Optional[int] = None

class ComentarioCreate(ComentarioBase):
    pass

class ComentarioUpdate(BaseModel):
    descripcion: Optional[str] = None
    calificacion: Optional[int] = Field(None, ge=1, le=5)

class ComentarioResponse(ComentarioBase):
    id_comentario: int
    fecha_comentario: datetime

    class Config:
        from_attributes = True