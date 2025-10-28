from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Notificacion(Base):
    __tablename__ = "notificaciones"
    
    id_notificacion = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    mensaje = Column(Text, nullable=False)
    tipo = Column(String(50), nullable=False)
    leida = Column(Boolean, default=False)
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    usuario_id = Column(Integer, ForeignKey('usuario.id_usuario'))
    
    # Relación
    usuario = relationship("Usuario", back_populates="notificaciones")