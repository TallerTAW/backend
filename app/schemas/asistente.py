from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class AsistenteBase(BaseModel):
    nombre: str
    email: EmailStr

class AsistenteCreate(AsistenteBase):
    pass

class AsistenteResponse(AsistenteBase):
    id_asistente: int
    id_reserva: int
    codigo_qr: str
    token_verificacion: str
    asistio: bool
    fecha_creacion: datetime
    fecha_validacion: Optional[datetime]
    
    class Config:
        from_attributes = True

class AsistenteUpdate(BaseModel):
    asistio: bool
    fecha_validacion: Optional[datetime] = None