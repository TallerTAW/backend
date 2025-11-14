from sqlalchemy import Column, String, Integer, Numeric, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Cupon(Base):
    __tablename__ = "cupon"
    
    id_cupon = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(50), unique=True, nullable=False)
    monto_descuento = Column(Numeric(10, 2), nullable=False)
    tipo = Column(String(20), default="porcentaje")  # porcentaje o fijo
    fecha_expiracion = Column(Date)
    estado = Column(String(20), default="activo")
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    id_reserva = Column(Integer, ForeignKey("reserva.id_reserva", ondelete="SET NULL"))
    fecha_creacion = Column(DateTime, default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="cupones")
    reserva = relationship("Reserva", back_populates="cupon")