from sqlalchemy import Column, String, Integer, DateTime, Text, func
from sqlalchemy.orm import relationship
from app.database import Base

class Usuario(Base):
    __tablename__ = "usuario"
    
    id_usuario = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    apellido = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    contrasenia = Column(String(255), nullable=False)
    estado = Column(String(20), default="activo")
    rol = Column(String(20), nullable=False)  # admin, gestor, control_acceso, cliente
    telefono = Column(String(15))
    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_actualizacion = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relaciones
    reservas = relationship("Reserva", back_populates="usuario")
    administraciones = relationship("Administra", back_populates="usuario")
    cancelaciones = relationship("Cancelacion", back_populates="usuario")
    incidentes = relationship("Incidente", back_populates="usuario")
    comentarios = relationship("Comentario", back_populates="usuario")
    cupones = relationship("Cupon", back_populates="usuario")
    notificaciones = relationship("Notificacion", back_populates="usuario")