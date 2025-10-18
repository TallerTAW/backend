from sqlalchemy import Column, String, Integer, Time, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Cancha(Base):
    __tablename__ = "cancha"
    
    id_cancha = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    tipo = Column(String(50))
    hora_apertura = Column(Time, nullable=False)
    hora_cierre = Column(Time, nullable=False)
    precio_por_hora = Column(Numeric(10, 2), nullable=False)
    estado = Column(String(20), default="disponible")
    id_espacio_deportivo = Column(Integer, ForeignKey("espacio_deportivo.id_espacio_deportivo", ondelete="CASCADE"))
    imagen = Column(String(255))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    espacio_deportivo = relationship("EspacioDeportivo", back_populates="canchas")
    reservas = relationship("Reserva", back_populates="cancha")
    disciplinas = relationship("CanchaDisciplina", back_populates="cancha")
    comentarios = relationship("Comentario", back_populates="cancha")