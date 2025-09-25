from sqlalchemy import Column, String, Integer, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Disciplina(Base):
    __tablename__ = "disciplina"
    
    id_disciplina = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)
    descripcion = Column(Text)
    
    # Relaciones
    reservas = relationship("Reserva", back_populates="disciplina")
    canchas = relationship("CanchaDisciplina", back_populates="disciplina")