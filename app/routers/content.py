from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.database import get_db 
from app.models.website_content import WebsiteContent
from app.schemas.content import ContentUpdate 

from app.core.core import allowed_roles

router = APIRouter()

@router.get("/", response_model=Dict[str, str])
def get_website_content(db: Session = Depends(get_db)):
    """Obtiene todo el contenido editable del sitio web y lo retorna como un mapa {key: value}."""
    try:
        content_objects: List[WebsiteContent] = db.query(WebsiteContent).all()
        content_map = {item.key: item.value for item in content_objects}
        return content_map
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error al obtener contenido del sitio web.")

@router.put("/{content_key}", response_model=Dict[str, str])
def update_website_content(
    content_key: str, 
    update_data: ContentUpdate, 
    db: Session = Depends(get_db)
):
    """Actualiza un contenido sin validación de usuario."""
    content_item = db.query(WebsiteContent).filter(WebsiteContent.key == content_key).first()
    if not content_item:
        raise HTTPException(status_code=404, detail=f"Clave '{content_key}' no encontrada.")
    content_item.value = update_data.new_value
    db.commit()
    db.refresh(content_item)
    return {"message": f"Contenido '{content_key}' actualizado exitosamente."}
