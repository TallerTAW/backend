from sqlalchemy import Column, String, Text, DateTime
from datetime import datetime
from app.database import Base 

class WebsiteContent(Base):
    __tablename__ = "website_content"
    
    # 'key' es la clave de contenido (ej: 'hero_title')
    key = Column(String(100), primary_key=True, unique=True, index=True) 
    value = Column(Text, nullable=True) # El contenido real
    description = Column(String, nullable=True) 
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)