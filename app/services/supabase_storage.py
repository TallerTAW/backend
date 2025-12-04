# app/services/supabase_storage.py
from fastapi import UploadFile, HTTPException
from supabase import create_client
import uuid
from app.config import settings
import os

class SupabaseStorage:
    def __init__(self):
        # Usar SERVICE KEY para escritura
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.bucket = "olympiaHub"
    
    async def upload_image(
        self, 
        file: UploadFile, 
        folder: str = "uploads",
        max_size_mb: int = 5
    ) -> str:
        """Sube imagen y retorna URL pública"""
        # Validar tamaño
        content = await file.read()
        if len(content) > max_size_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"La imagen es demasiado grande (máximo {max_size_mb}MB)"
            )
        
        # Validar tipo de archivo
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
        filename = file.filename or "image"
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        
        if ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail="Tipo de archivo no permitido. Use PNG, JPG, JPEG, GIF o WEBP"
            )
        
        # Generar nombre único
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        storage_path = f"{folder}/{unique_filename}"
        
        try:
            # Subir a Supabase Storage
            self.client.storage.from_(self.bucket).upload(
                storage_path,
                content,
                {"content-type": file.content_type or f"image/{ext}"}
            )
            
            # Obtener URL pública
            return self.client.storage.from_(self.bucket).get_public_url(storage_path)
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error al subir imagen: {str(e)}"
            )

# Instancia global
storage_service = SupabaseStorage()