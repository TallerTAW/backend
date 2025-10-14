from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class AdministraBase(BaseModel):
    id_usuario: int
    id_espacio_deportivo: int

class AdministraCreate(AdministraBase):
    pass

class Administra(AdministraBase):
    fecha_asignacion: datetime

    class Config:
        from_attributes = True