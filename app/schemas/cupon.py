from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from decimal import Decimal

class CuponBase(BaseModel):
    codigo: str = Field(..., min_length=3, max_length=50, description="Código único del cupón")
    monto_descuento: Decimal = Field(..., gt=0, description="Monto del descuento")
    tipo: str = Field("porcentaje", pattern="^(porcentaje|fijo)$", description="Tipo de descuento: porcentaje o fijo")
    fecha_expiracion: Optional[date] = Field(None, description="Fecha de expiración del cupón")
    estado: str = Field("activo", pattern="^(activo|inactivo|utilizado)$", description="Estado del cupón")
    id_usuario: Optional[int] = Field(None, description="ID del usuario dueño del cupón (si es personalizado)")

class CuponCreate(CuponBase):
    pass

class CuponUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=3, max_length=50)
    monto_descuento: Optional[Decimal] = Field(None, gt=0)
    tipo: Optional[str] = Field(None, pattern="^(porcentaje|fijo)$")
    fecha_expiracion: Optional[date] = None
    estado: Optional[str] = Field(None, pattern="^(activo|inactivo|utilizado)$")
    id_usuario: Optional[int] = None

class CuponResponse(CuponBase):
    id_cupon: int
    id_reserva: Optional[int] = None
    fecha_creacion: datetime
    
    class Config:
        from_attributes = True

class CuponAplicar(BaseModel):
    codigo_cupon: str = Field(..., description="Código del cupón a aplicar")
    id_reserva: int = Field(..., description="ID de la reserva a la que aplicar el cupón")

class CuponGenerarLote(BaseModel):
    cantidad: int = Field(..., gt=0, le=100, description="Cantidad de cupones a generar")
    monto_descuento: Decimal = Field(..., gt=0)
    tipo: str = Field("porcentaje", pattern="^(porcentaje|fijo)$")
    fecha_expiracion: Optional[date] = None
    prefijo: str = Field("CUP", max_length=10, description="Prefijo para los códigos de cupón")