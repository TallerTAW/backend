from sqlalchemy import Column, String, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base
from sqlalchemy.sql import func

class Pago(Base):
    __tablename__ = "pago"
    
    id_pago = Column(Integer, primary_key=True, index=True)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_pago = Column(DateTime(timezone=True), server_default=func.now())
    metodo_pago = Column(String(50), nullable=False)
    estado = Column(String(20), default="pendiente")
    id_transaccion = Column(String(100))
    id_reserva = Column(Integer, ForeignKey("reserva.id_reserva", ondelete="CASCADE"))
    
    # Relaciones
    reserva = relationship("Reserva", back_populates="pago")