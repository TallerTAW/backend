# BACKEND/app/routers/content.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# Importaciones de tu proyecto
from app.database import get_db 
from app.models.website_content import WebsiteContent # Asume que este modelo existe
from app.schemas.content import ContentUpdate 

# 🚨 Importaciones de Seguridad y Roles
from .auth import get_current_user 
from app.core.core import allowed_roles # Asume que esta función ya fue creada en app/core/core.py

router = APIRouter(
    prefix="/content",
    tags=["Contenido Dinámico"]
)

# -----------------------------------------------------------
# RUTA GET (Solo Lectura)
# -----------------------------------------------------------

@router.get("/", response_model=Dict[str, str])
def get_website_content(db: Session = Depends(get_db)):
    """Obtiene todo el contenido editable del sitio web y lo retorna como un mapa {key: value}."""
    try:
        content_objects: List[WebsiteContent] = db.query(WebsiteContent).all()
        content_map = {item.key: item.value for item in content_objects}
        return content_map
    except Exception as e:
        # En caso de error de conexión o modelo
        raise HTTPException(status_code=500, detail="Error al obtener contenido del sitio web.")

# -----------------------------------------------------------
# RUTA PUT (Actualización - Protegida por Token y Rol)
# -----------------------------------------------------------

@router.put("/{content_key}", response_model=Dict[str, str])
def update_website_content(
    content_key: str, 
    update_data: ContentUpdate, 
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user) 
):
    """Actualiza el valor de una clave de contenido específica en la BD."""
    
    # 1. Verificación de Rol
    if not allowed_roles(current_user, ['admin', 'gestor']):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar el contenido del sitio."
        )

    # 2. Buscar el contenido por la clave
    content_item: WebsiteContent = db.query(WebsiteContent).filter(
        WebsiteContent.key == content_key
    ).first()

    if not content_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clave de contenido '{content_key}' no encontrada."
        )

    # 3. Actualizar el valor y guardar
    content_item.value = update_data.new_value
    db.commit()
    db.refresh(content_item)

    return {"message": f"Contenido '{content_key}' actualizado exitosamente."}