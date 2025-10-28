from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class NotificationBase(BaseModel):
    titulo: str
    mensaje: str
    tipo: str  # 'nuevo_usuario', 'usuario_aprobado', 'general'
    usuario_id: int

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id_notificacion: int
    leida: bool
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True