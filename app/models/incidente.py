from sqlalchemy import Column, String, Integer, Text, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Incidente(Base):
    __tablename__ = "incidente"
    
    id_incidente = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False)
    descripcion = Column(Text, nullable=False)
    multa = Column(Numeric(10, 2), default=0)
    fecha_incidente = Column(DateTime(timezone=True), server_default=func.now())
    id_reserva = Column(Integer, ForeignKey("reserva.id_reserva", ondelete="CASCADE"))
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    
    # Relaciones
    reserva = relationship("Reserva", back_populates="incidente")
    usuario = relationship("Usuario", back_populates="incidentes")