from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class AsistenteReserva(Base):
    __tablename__ = "asistentes_reserva"
    
    id_asistente = Column(Integer, primary_key=True, index=True)
    id_reserva = Column(Integer, ForeignKey("reserva.id_reserva"), nullable=False)
    nombre = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    codigo_qr = Column(String(255), unique=True, nullable=False)
    token_verificacion = Column(String(255), unique=True, nullable=False)
    asistio = Column(Boolean, default=False, nullable=False)
    fecha_validacion = Column(DateTime, nullable=True)
    fecha_creacion = Column(DateTime, server_default=func.now(), nullable=False)
    fecha_actualizacion = Column(DateTime, onupdate=func.now(), nullable=True)
    
    # Relación con reserva
    reserva = relationship("Reserva", back_populates="asistentes")