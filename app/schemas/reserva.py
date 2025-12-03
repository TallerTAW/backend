from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date, time, datetime
from decimal import Decimal

class ReservaBase(BaseModel):
    fecha_reserva: date
    hora_inicio: time
    hora_fin: time
    cantidad_asistentes: int = Field(..., gt=0, description="Número de asistentes")
    material_prestado: Optional[str] = Field(None, description="Material adicional prestado")
    id_disciplina: int = Field(..., description="ID de la disciplina")
    id_cancha: int = Field(..., description="ID de la cancha")
    id_usuario: int = Field(..., description="ID del usuario")
    
    @validator('hora_inicio', 'hora_fin')
    def validate_full_hours(cls, v):
        if v.minute != 0:
            raise ValueError('La hora debe ser en punto (ej: 10:00, 11:00)')
        return v

class ReservaCreate(ReservaBase):
    """
    🎯 ESQUEMA PARA CREAR RESERVA - ACTUALIZADO
    💡 CAMBIO: Agregar campo opcional para código de cupón
    """
    codigo_cupon: Optional[str] = Field(None, description="Código de cupón a aplicar")

class ReservaUpdate(BaseModel):
    fecha_reserva: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    cantidad_asistentes: Optional[int] = Field(None, gt=0)
    material_prestado: Optional[str] = None
    estado: Optional[str] = Field(None, pattern="^(pendiente|confirmada|en_curso|completada|cancelada)$")
    id_disciplina: Optional[int] = None
    id_cancha: Optional[int] = None

class ReservaResponse(ReservaBase):
    """
    🎯 ESQUEMA DE RESPUESTA PARA RESERVA - CORREGIDO
    """
    id_reserva: int
    codigo_reserva: str
    estado: str
    costo_total: Decimal
    qr_code: Optional[str] = None 
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True