from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class CanchaDisciplina(Base):
    __tablename__ = "cancha_disciplina"
    
    id_cancha = Column(Integer, ForeignKey("cancha.id_cancha", ondelete="CASCADE"), primary_key=True)
    id_disciplina = Column(Integer, ForeignKey("disciplina.id_disciplina", ondelete="CASCADE"), primary_key=True)
    
    # Relaciones
    cancha = relationship("Cancha", back_populates="disciplinas")
    disciplina = relationship("Disciplina", back_populates="canchas")