from sqlalchemy import Column, String, Integer, Date, Time, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Reserva(Base):
    __tablename__ = "reserva"
    
    id_reserva = Column(Integer, primary_key=True, index=True)
    fecha_reserva = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    estado = Column(String(20), default="pendiente")  # pendiente, confirmada, en_curso, completada, cancelada
    costo_total = Column(Numeric(10, 2), nullable=False)
    material_prestado = Column(Text)
    cantidad_asistentes = Column(Integer)
    codigo_reserva = Column(String(20), unique=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario", ondelete="CASCADE"))
    id_cancha = Column(Integer, ForeignKey("cancha.id_cancha", ondelete="CASCADE"))
    id_disciplina = Column(Integer, ForeignKey("disciplina.id_disciplina"))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    usuario = relationship("Usuario", back_populates="reservas")
    cancha = relationship("Cancha", back_populates="reservas")
    disciplina = relationship("Disciplina", back_populates="reservas")
    pago = relationship("Pago", back_populates="reserva", uselist=False)
    cancelacion = relationship("Cancelacion", back_populates="reserva", uselist=False)
    incidente = relationship("Incidente", back_populates="reserva", uselist=False)
    cupon = relationship("Cupon", back_populates="reserva", uselist=False)