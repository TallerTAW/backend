from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Comentario(Base):
    __tablename__ = "comentario"
    
    id_comentario = Column(Integer, primary_key=True, index=True)
    descripcion = Column(Text, nullable=False)
    calificacion = Column(Integer, nullable=True)  # 1-5
    fecha_comentario = Column(DateTime(timezone=True), server_default=func.now())
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"), nullable=False)
    id_cancha = Column(Integer, ForeignKey("cancha.id_cancha", ondelete="CASCADE"), nullable=False)

    # Relaciones
    usuario = relationship("Usuario", back_populates="comentarios")
    cancha = relationship("Cancha", back_populates="comentarios")