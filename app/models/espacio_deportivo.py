from sqlalchemy import Column, String, Integer, Text, DateTime, Float
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class EspacioDeportivo(Base):
    __tablename__ = "espacio_deportivo"
    
    id_espacio_deportivo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    ubicacion = Column(String(150))
    capacidad = Column(Integer)
    estado = Column(String(20), default="activo")
    descripcion = Column(Text)
    imagen = Column(String(255)) 
    latitud = Column(Float, nullable=True)    # NUEVO
    longitud = Column(Float, nullable=True)   # NUEVO
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relaciones
    canchas = relationship("Cancha", back_populates="espacio_deportivo")
    administraciones = relationship("Administra", back_populates="espacio_deportivo")