from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Administra(Base):
    __tablename__ = "administra"
    
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"), primary_key=True)
    id_espacio_deportivo = Column(Integer, ForeignKey("espacio_deportivo.id_espacio_deportivo", ondelete="CASCADE"), primary_key=True)
    fecha_asignacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="administraciones")
    espacio_deportivo = relationship("EspacioDeportivo", back_populates="administraciones")