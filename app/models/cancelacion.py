from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Cancelacion(Base):
    __tablename__ = "cancelacion"
    
    id_cancelacion = Column(Integer, primary_key=True, index=True)
    motivo = Column(Text, nullable=False)
    fecha_cancelacion = Column(DateTime(timezone=True), server_default=func.now())
    id_reserva = Column(Integer, ForeignKey("reserva.id_reserva", ondelete="CASCADE"))
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    
    # Relaciones
    reserva = relationship("Reserva", back_populates="cancelacion")
    usuario = relationship("Usuario", back_populates="cancelaciones")