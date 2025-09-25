from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class EspacioDeportivoBase(BaseModel):
    nombre: str
    ubicacion: Optional[str] = None
    capacidad: Optional[int] = None
    estado: Optional[str] = "activo"
    descripcion: Optional[str] = None

class EspacioDeportivoCreate(EspacioDeportivoBase):
    pass

class EspacioDeportivoUpdate(BaseModel):
    nombre: Optional[str] = None
    ubicacion: Optional[str] = None
    capacidad: Optional[int] = None
    estado: Optional[str] = None
    descripcion: Optional[str] = None

class EspacioDeportivoResponse(EspacioDeportivoBase):
    id_espacio_deportivo: int
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True